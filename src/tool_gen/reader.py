"""Blind-reader stage: verify writer requests against the goal's tools.

The reader stays blind: it receives the user request plus the goal catalog's
COMPLETE tool schemas (names, descriptions, full parameter schemas) and the
full visible context object — never the witness calls, the gold status, or
writer judgments. The content fingerprint binding each accepted verdict to
its exact source is computed locally and is never sent to the reader. The prompt builder below serializes full schemas; it does
not copy the pilot's lossy name-only builder (tool names + bare parameter
keys), which hid descriptions, enums, and required-ness from the reader.

The dynamic reader schema carries NO call-count cap (``maxItems`` uncapped)
and NO ``argument_presence`` flags: the request determines the call count.
Instead every call uses a slot envelope — ``output.arguments`` must contain
EVERY declared argument key exactly once: a required argument is always
``{"value": <the value>}``, an optional argument is ``{"value": <value>}``
only when explicitly requested and ``{}`` when omitted (an actual null value
stays ``{"value": null}``; ``{}`` always means omitted). ``interpret_reading``
losslessly unwraps slots to canonical calls and validates the original full
tool schema (all slot keys, requiredness, types); the literal-call comparator
catches missing expected values. Arguments the catalog explicitly declares
opaque identifiers must additionally occur as whole identifier tokens in the
request or visible context — schema examples are never source facts. Reader temperature is separately configurable (default 0.0); the writer
default stays 0.9 (see ``writer.py``).

Recovery is bounded, never majority voting: one extra blind attempt by
default (``max_attempts=2``). Only two failure families are retried: unusable
model output (``OutputError``: schema violations, empty completions,
stopped-early replies) and public contract/mismatch readings of a VALID goal
(unknown tools, schema-violating values, ambiguous or mismatching
interpretations) with public-contract feedback only — a re-read of the same
visible request/catalog, never hidden gold details. Every other
``ClientError``/``BudgetError`` is an operational failure: the current goal's
evidence is preserved and the run aborts nonzero via ``AbortError`` with no
retry and no batch-failing of later goals.
Every attempt and its classification is preserved; match/equivalence accepts,
anything else stays UNRESOLVED after the bound (never "data bad"). Goals that
fail preflight are ``invalid_goal``: recorded without any model request and
never retried. A genuine comparison difference is evidence about the reading,
never proof the user prompt is bad. Unsupported ``API_call_<i>`` references
fail preflight as ``invalid_goal`` under the recursive audit; no dependency
behavior is implemented pending the user decision.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Literal, NamedTuple

import jsonschema
from pydantic import JsonValue, ValidationError

from tool_gen.client import ClientError, OutputError
from tool_gen.comparison import compare_calls, validate_calls
from tool_gen.models import (
    ReaderAttempt,
    ReaderResult,
    StrictModel,
    ToolCall,
    normalize_goal_record,
)
from tool_gen.prompts import reader_prompt
from tool_gen.store import (
    AbortError,
    StageContext,
    append_jsonl,
    canonical_json,
    content_fingerprint,
    cumulative_counts,
    ensure_manifest,
    finalize_manifest,
    read_done_ids,
)
from tool_gen.validate import audit_goal
from tool_gen.writer import Completer

Tool = dict[str, object]


class OmittedSlot(StrictModel):
    """``{}`` — the optional argument is omitted, never a null sentinel."""


class PresentSlot(StrictModel):
    """``{"value": ...}`` — the argument is supplied (null stays a value)."""

    value: JsonValue


class ReaderCallOutput(StrictModel):
    name: str
    arguments: dict[str, OmittedSlot | PresentSlot]


class ReaderOutput(StrictModel):
    status: Literal["clear", "ambiguous", "unsupported"]
    reason: str
    calls: list[ReaderCallOutput]


class Interpretation(NamedTuple):
    status: str
    reason: str
    calls: list[dict[str, object]]


def student_prompt(
    tools: list[Tool], request: str, context: dict[str, JsonValue]
) -> str:
    """Render the full student-visible prompt: schemas + full context + request.

    The visible context object travels verbatim (all name-to-ID mappings and
    records); only private fixtures/witness stay hidden.
    """
    blocks: list[str] = []
    for tool in tools:
        function = tool["function"]
        if not isinstance(function, dict):
            raise TypeError("catalog entry lacks a 'function' object")
        parameters = function.get("parameters")
        if not isinstance(parameters, dict):
            raise TypeError(
                f"tool {function.get('name')}: parameters must be an object schema"
            )
        blocks.append(
            f"Tool {function.get('name')}: {function.get('description', '')}\nParameters: {canonical_json(parameters)}"
        )
    prompt = "Available tools (complete schemas):\n" + "\n\n".join(blocks)
    if context:
        prompt += "\n\nKnown context (JSON):\n" + canonical_json(context)
    return prompt + f"\n\nUser request: {request}\n\nReturn the minimal calls needed."


def _slot_schema(arg_schema: dict[str, object], required: bool) -> dict[str, object]:
    """Closed slot envelope: required args always carry a value; optional args
    carry a value or the closed empty object (omitted). No null sentinel."""
    value_slot: dict[str, object] = {
        "type": "object",
        "properties": {"value": deepcopy(arg_schema)},
        "required": ["value"],
        "additionalProperties": False,
    }
    if required:
        return value_slot
    return {
        "anyOf": [
            {"type": "object", "properties": {}, "additionalProperties": False},
            value_slot,
        ]
    }


def reader_schema(tools: list[Tool]) -> dict[str, object]:
    """Per-tool call variants; every declared argument key is required in output.

    The call count is determined by the request (no ``maxItems`` cap); the
    argument count is fixed by the catalog (all keys required, slots decide
    present vs omitted).
    """
    variants: list[dict[str, object]] = []
    for tool in tools:
        function = tool["function"]
        if not isinstance(function, dict):
            raise TypeError("catalog entry lacks a 'function' object")
        parameters = function.get("parameters")
        if not isinstance(parameters, dict):
            raise TypeError(
                f"tool {function.get('name')}: parameters must be an object schema"
            )
        props = parameters.get("properties", {})
        if not isinstance(props, dict):
            raise TypeError(
                f"tool {function.get('name')}: properties must be an object"
            )
        required = parameters.get("required", [])
        if not isinstance(required, list) or not all(
            isinstance(key, str) for key in required
        ):
            raise TypeError(
                f"tool {function.get('name')}: required must be a string list"
            )
        required_set = set(required)
        arguments_schema: dict[str, object] = {
            "type": "object",
            "properties": {
                str(key): _slot_schema(
                    child if isinstance(child, dict) else {},
                    str(key) in required_set,
                )
                for key, child in props.items()
            },
            "required": [str(key) for key in props],
            "additionalProperties": False,
        }
        variants.append(
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": [function["name"]]},
                    "arguments": arguments_schema,
                },
                "required": ["name", "arguments"],
                "additionalProperties": False,
            }
        )
    if not variants:
        raise ValueError("reader requires a nonempty catalog")
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["clear", "ambiguous", "unsupported"]},
            "reason": {"type": "string"},
            "calls": {"type": "array", "items": {"anyOf": variants}},
        },
        "required": ["status", "reason", "calls"],
        "additionalProperties": False,
    }


def _parameter_schemas(tools: list[Tool]) -> dict[str, dict[str, object]]:
    """Original parameter schema per catalog tool name."""
    definitions: dict[str, dict[str, object]] = {}
    for tool in tools:
        function = tool["function"]
        if not isinstance(function, dict):
            raise TypeError("catalog entry lacks a 'function' object")
        parameters = function.get("parameters")
        if not isinstance(parameters, dict):
            raise TypeError(
                f"tool {function.get('name')}: parameters must be an object schema"
            )
        name = function.get("name")
        if not isinstance(name, str):
            raise TypeError("catalog tool lacks a string name")
        definitions[name] = parameters
    return definitions


def _is_opaque_schema(schema: dict[str, object]) -> bool:
    """Only arguments explicitly declared as opaque identifiers.

    The argument's own schema description must say ``opaque`` (the catalog's
    explicit identity declaration, e.g. "opaque identifier, copy exactly").
    Generic "copy exactly" names, enums, numeric IDs, and plain values never
    qualify: this guard covers declared opaque identifiers only.
    """
    if schema.get("type") != "string" or "enum" in schema:
        return False
    description = schema.get("description", "")
    return isinstance(description, str) and "opaque" in description.casefold()


def _opaque_strings(value: object, schema: dict[str, object]) -> list[str]:
    """String values at explicitly opaque-declared schema nodes, if any."""
    if _is_opaque_schema(schema):
        return [value] if isinstance(value, str) else []
    found: list[str] = []
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if isinstance(props, dict):
            for key, item in value.items():
                child = props.get(key, {})
                if isinstance(child, dict):
                    found.extend(_opaque_strings(item, child))
    elif isinstance(value, list):
        items = schema.get("items", {})
        if isinstance(items, dict):
            for item in value:
                found.extend(_opaque_strings(item, items))
    return found


def _is_token_char(char: str) -> bool:
    """Identifier-token characters: word characters plus hyphen."""
    return char.isalnum() or char == "_" or char == "-"


def _contains_token(haystack: str, needle: str) -> bool:
    """Whole-identifier occurrence: token boundaries on both sides.

    ``WH-12`` does not occur in ``WH-1234`` (digit continues the token) and
    ``BK`` does not occur in ``BK-101`` (hyphen continues it), while a pasted
    full ID, a punctuation-terminated ID, or an exact scalar all match.
    Case-sensitive, no normalization.
    """
    if not needle:
        return False
    start = 0
    while True:
        index = haystack.find(needle, start)
        if index < 0:
            return False
        before = haystack[index - 1] if index > 0 else ""
        end = index + len(needle)
        after = haystack[end] if end < len(haystack) else ""
        if (not before or not _is_token_char(before)) and (
            not after or not _is_token_char(after)
        ):
            return True
        start = index + 1


def _context_strings(context: dict[str, JsonValue]) -> list[str]:
    """Every string leaf of the full visible context, verbatim."""
    leaves: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, str):
            leaves.append(node)
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(context)
    return leaves


def check_opaque_grounding(
    calls: list[ToolCall],
    tools: list[Tool],
    request: str,
    context: dict[str, JsonValue],
) -> None:
    """Narrow anti-hallucination check on declared opaque identifiers.

    Each returned string at an explicitly opaque-declared schema node must
    occur as a whole identifier token in the actual user request or the full
    visible context: bare pasted IDs match the request, context-resolved IDs
    match a visible mapping (scalar exact equality is strongest; note text
    uses the same token boundaries). Exact token match only — no case-folding,
    no normalization. Raises ``ValueError`` (a public reader-contract
    failure, blindly retryable); never consults gold. This proves nothing
    semantic: undeclared or exotic identifier shapes stay outside this guard.
    """
    definitions = _parameter_schemas(tools)
    leaves = _context_strings(context)
    for call in calls:
        schema = definitions.get(call.name)
        if schema is None:
            continue
        for opaque in _opaque_strings(call.arguments, schema):
            if (
                not opaque
                or not _contains_token(request, opaque)
                and not any(
                    opaque == leaf or _contains_token(leaf, opaque) for leaf in leaves
                )
            ):
                raise ValueError(
                    f"opaque identifier {opaque!r} of tool {call.name!r} "
                    "occurs nowhere in the visible request or known context; "
                    "copy opaque values only from the request or visible "
                    "context, never from schema examples"
                )


def interpret_reading(reading: ReaderOutput, tools: list[Tool]) -> Interpretation:
    """Unwrap slot envelopes losslessly, then validate the original schema.

    Every declared argument key must appear exactly once: required arguments
    as ``{"value": ...}``, optional arguments as ``{"value": ...}`` when
    requested and ``{}`` when omitted. Unwrapped calls are validated against
    the original full tool schema (requiredness and types)."""
    definitions = _parameter_schemas(tools)
    calls: list[dict[str, object]] = []
    for call in reading.calls:
        if call.name not in definitions:
            raise ValueError(f"reader called unknown tool {call.name!r}")
        schema = definitions[call.name]
        props = schema.get("properties", {})
        if not isinstance(props, dict):
            raise TypeError(f"tool {call.name}: properties must be an object")
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(
            isinstance(key, str) for key in required
        ):
            raise TypeError(f"tool {call.name}: required must be a string list")
        required_set = set(required)
        if set(call.arguments) != {str(key) for key in props}:
            raise ValueError(
                f"reader call {call.name!r} must list every declared "
                "argument key exactly once"
            )
        unwrapped: dict[str, object] = {}
        for key, slot in call.arguments.items():
            if isinstance(slot, OmittedSlot):
                if key in required_set:
                    raise ValueError(
                        f"reader omitted required argument {key!r} "
                        f"of tool {call.name!r}"
                    )
                continue
            unwrapped[key] = slot.value
        try:
            jsonschema.Draft202012Validator(schema).validate(unwrapped)
        except jsonschema.ValidationError as exc:
            raise ValueError(
                f"reader arguments violate tool schema: {exc.message}"
            ) from None
        calls.append({"name": call.name, "arguments": unwrapped})
    if reading.status != "clear" and calls:
        raise ValueError(
            "ambiguous/unsupported readings must not contain partial calls"
        )
    return Interpretation(status=reading.status, reason=reading.reason, calls=calls)


def _retry_note(classification: str, detail: str) -> str:
    """Public-contract feedback for one extra blind attempt. No gold details.

    Only the same visible request/catalog the first attempt saw, plus a
    reminder of the public shape contract. Comparison missing/extra contents
    derive from the hidden witness and are never echoed here.
    """
    if classification in ("output_error", "schema_error"):
        hint = f" Your previous output was unusable and discarded: {detail[:200]}."
        return (
            "Re-read the visible request and catalog above and return only the"
            " supplied JSON shape: every call lists EVERY declared argument key"
            ' exactly once — required arguments as {"value": ...}, unrequested'
            " optional arguments as {}. Omit nothing, invent nothing, use only"
            " values from the request or visible context: schema examples"
            " illustrate shape only and are never user facts; never select a"
            " call or guess a value just to fill a slot."
            f"{hint}"
        )
    if classification == "ambiguous":
        return (
            "Re-read the visible request and catalog above. If every required"
            " value is literally present in the request or known context, return"
            " status clear with the minimal calls; an unfiltered search or list"
            " is valid when no filter value is stated, and an unfamiliar literal"
            " name alone is not ambiguity. Do not invent filters or values;"
            " genuinely missing required facts still mean ambiguous."
        )
    return (
        "Re-read the visible request and catalog above and return the minimal"
        " calls needed for all explicitly requested operations and constraints,"
        " in a valid order consistent with any explicit sequence in the request."
    )


def _parse_output(raw: object, goal_id: str) -> ReaderOutput:
    if not isinstance(raw, dict):
        raise OutputError(f"reader {goal_id}: model output is not a JSON object")
    try:
        return ReaderOutput.model_validate(raw)
    except ValidationError as exc:
        raise OutputError(
            f"reader {goal_id}: model output violates reader schema: {exc.errors()[0]['msg']}"
        ) from None


def _to_tool_calls(calls: list[dict[str, object]], goal_id: str) -> list[ToolCall]:
    parsed: list[ToolCall] = []
    for call in calls:
        name = call.get("name")
        arguments = call.get("arguments")
        if not isinstance(name, str) or not isinstance(arguments, dict):
            raise TypeError(
                f"goal {goal_id}: witness call must have string name and object arguments"
            )
        parsed.append(ToolCall(name=name, arguments=arguments))
    return parsed


def run_reader(
    raw_entries: list[dict[str, object]],
    ctx: StageContext,
    complete: Completer,
    temperature: float = 0.0,
    max_attempts: int = 2,
) -> dict[str, int]:
    """Verify writer entries; streams one validated JSONL verdict per entry."""
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool):
        raise TypeError("max_attempts must be an integer")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    ensure_manifest(ctx)
    out_path = ctx.shard_dir / "results.jsonl"
    done: set[str] = read_done_ids(out_path, "row") if out_path.exists() else set()
    # Malformed rows carry no goal id, so their resume identity is the stable
    # original-input index: the stage manifest pins the input order, so the
    # same synthetic id recurs across runs and resume skips recorded rows
    # instead of duplicating artifact rows and double-counting them.
    mine: list[tuple[int, dict[str, object]]] = []
    for i, raw in enumerate(raw_entries):
        if i % ctx.shards != ctx.shard:
            continue
        if not isinstance(raw, dict):
            raise TypeError("reader input rows must be JSON objects")
        goal_raw = raw.get("goal")
        goal_id = goal_raw.get("id") if isinstance(goal_raw, dict) else None
        if isinstance(goal_id, str):
            if goal_id in done:
                continue
        elif f"unidentified-{ctx.shard}-{i}" in done:
            continue
        mine.append((i, raw))
    system = reader_prompt()
    accepted = unresolved = invalid_goal = processed = 0
    status = "complete"

    def record(row: ReaderResult) -> None:
        append_jsonl(out_path, row.model_dump(mode="json"))

    def record_invalid(goal_id: str, reason: str) -> None:
        nonlocal invalid_goal, processed
        invalid_goal += 1
        processed += 1
        record(
            ReaderResult(
                id=goal_id,
                accepted=False,
                outcome="invalid_goal",
                reason=f"invalid_goal: {reason}"[:500],
                error_kind="invalid_goal",
            )
        )

    try:
        for pos, (src_index, raw) in enumerate(mine):
            goal_raw = raw.get("goal")
            request = raw.get("request", "")
            goal_id = goal_raw.get("id") if isinstance(goal_raw, dict) else None
            if not isinstance(goal_id, str):
                record_invalid(
                    f"unidentified-{ctx.shard}-{src_index}", "missing string id"
                )
                continue
            if not isinstance(request, str):
                record_invalid(goal_id, "missing string 'request'")
                continue
            try:
                goal = normalize_goal_record(goal_raw)
            except (TypeError, ValueError) as exc:
                record_invalid(goal_id, str(exc))
                continue
            tools_raw = (
                goal_raw.get("tools", goal_raw.get("catalog", []))
                if isinstance(goal_raw, dict)
                else []
            )
            if not isinstance(tools_raw, list) or not all(
                isinstance(t, dict) for t in tools_raw
            ):
                record_invalid(goal_id, "catalog must be a list of tool objects")
                continue
            tools: list[Tool] = [t for t in tools_raw if isinstance(t, dict)]
            witness = [
                ToolCall(name=c.name, arguments=c.arguments) for c in goal.witness
            ]
            context = dict(goal.context)
            problems = audit_goal(
                {
                    "id": goal_id,
                    "tools": tools,
                    "witness": [
                        {"name": c.name, "arguments": dict(c.arguments)}
                        for c in witness
                    ],
                    "no_call": goal.no_call,
                }
            )
            if problems:
                record_invalid(goal_id, "; ".join(problems))
                continue
            fingerprint = content_fingerprint(
                {
                    "id": goal_id,
                    "request": request,
                    "tools": tools,
                    "context": context,
                    "witness": [
                        {"name": c.name, "arguments": c.arguments} for c in witness
                    ],
                    "no_call": goal.no_call,
                }
            )
            expected_status = "unsupported" if goal.no_call else "clear"
            attempts: list[ReaderAttempt] = []
            accepted_now = False
            accepted_calls: list[ToolCall] = []
            comparison: Literal["match", "equivalent", "different"] | None = None
            final_status = ""
            final_reason = ""
            terminal_kind = ""
            feedback = ""
            for attempt_no in range(1, max_attempts + 1):
                request_id = f"r-{ctx.shard}-{goal_id}-a{attempt_no}"
                # The first-attempt prompt is byte-identical on every retry;
                # bounded public guidance is only appended under its own heading.
                prompt = student_prompt(tools, request, context)
                if feedback:
                    prompt += (
                        "\n\n---\nRetry guidance "
                        "(same visible request, no new facts):\n" + feedback
                    )
                try:
                    resp = complete(
                        request_id,
                        system,
                        prompt,
                        reader_schema(tools),
                        temperature,
                        3072,
                    )
                    reading = _parse_output(resp.get("output"), goal_id)
                    interp = interpret_reading(reading, tools)
                    # Canonical unwrapped calls feed history, validation, and
                    # comparison alike; the slot envelope never leaves this stage.
                    parsed_calls = _to_tool_calls(interp.calls, goal_id)
                    validate_calls(parsed_calls, tools)
                    check_opaque_grounding(parsed_calls, tools, request, context)
                    actual = parsed_calls
                    if interp.status != expected_status:
                        classification = (
                            "ambiguous"
                            if interp.status == "ambiguous"
                            else "status_mismatch"
                        )
                        attempts.append(
                            ReaderAttempt(
                                attempt=attempt_no,
                                request_id=request_id,
                                status=interp.status,
                                reason=interp.reason,
                                calls=parsed_calls,
                                classification=classification,
                                error_kind="status_mismatch"
                                if classification == "status_mismatch"
                                else "ambiguous",
                                detail=(
                                    f"got {interp.status} expected {expected_status}"
                                ),
                            )
                        )
                        final_status, final_reason = interp.status, interp.reason
                        terminal_kind = attempts[-1].error_kind
                        feedback = _retry_note(classification, "")
                        continue
                    try:
                        compared = compare_calls(witness, actual, tools)
                    except ValueError as exc:
                        # Expected-side or catalog-side comparison failure (the
                        # actual side already validated): deterministic, not a
                        # model retry candidate and not proof the prompt is bad.
                        attempts.append(
                            ReaderAttempt(
                                attempt=attempt_no,
                                request_id=request_id,
                                status=interp.status,
                                reason=interp.reason,
                                calls=parsed_calls,
                                classification="comparison_error",
                                error_kind="comparison_error",
                                detail=str(exc)[:300],
                            )
                        )
                        final_status, final_reason = interp.status, interp.reason
                        terminal_kind = "comparison_error"
                        break
                    comparison = compared.category
                    if compared.matched:
                        attempts.append(
                            ReaderAttempt(
                                attempt=attempt_no,
                                request_id=request_id,
                                status=interp.status,
                                reason=interp.reason,
                                calls=parsed_calls,
                                classification=compared.category,
                                detail="",
                            )
                        )
                        accepted_now = True
                        accepted_calls = actual
                        final_status, final_reason = interp.status, interp.reason
                        terminal_kind = ""
                        break
                    attempts.append(
                        ReaderAttempt(
                            attempt=attempt_no,
                            request_id=request_id,
                            status=interp.status,
                            reason=interp.reason,
                            calls=parsed_calls,
                            classification="different",
                            error_kind="call_mismatch",
                            detail="independent comparison differs",
                        )
                    )
                    final_status, final_reason = interp.status, interp.reason
                    terminal_kind = "call_mismatch"
                    feedback = _retry_note("different", "")
                except ValueError as exc:
                    # Model-side contract failure (unknown tool, schema-violating
                    # values, partial calls with a non-clear status): retryable
                    # within the bound; the goal itself already passed preflight.
                    message = str(exc)
                    attempts.append(
                        ReaderAttempt(
                            attempt=attempt_no,
                            request_id=request_id,
                            classification="schema_error",
                            error_kind="reader_contract",
                            detail=message[:300],
                        )
                    )
                    terminal_kind = "reader_contract"
                    feedback = _retry_note("schema_error", message)
                except OutputError as exc:
                    message = str(exc)
                    attempts.append(
                        ReaderAttempt(
                            attempt=attempt_no,
                            request_id=request_id,
                            classification="output_error",
                            error_kind="model_output",
                            detail=message[:300],
                        )
                    )
                    terminal_kind = "model_output"
                    feedback = _retry_note("output_error", message)
                except ClientError as exc:
                    # Operational failure (transport, budget, provider or
                    # ledger errors): preserve this goal's evidence, abort the
                    # run nonzero, never retry opaquely or batch-fail later goals.
                    attempts.append(
                        ReaderAttempt(
                            attempt=attempt_no,
                            request_id=request_id,
                            classification="transport",
                            error_kind="transport",
                            detail=str(exc)[:300],
                        )
                    )
                    processed = pos + 1
                    record(
                        ReaderResult(
                            id=goal_id,
                            accepted=False,
                            outcome="unresolved",
                            attempts=attempts,
                            reason=f"transport: {exc}"[:500],
                            witness=witness,
                            reader_calls=(
                                attempts[-1].calls
                                if attempts and attempts[-1].calls
                                else []
                            ),
                            error_kind="transport",
                            source_fingerprint=fingerprint,
                        )
                    )
                    raise AbortError(f"transport: {exc}", processed) from None
            processed = pos + 1
            if accepted_now:
                accepted += 1
                record(
                    ReaderResult(
                        id=goal_id,
                        accepted=True,
                        outcome="accepted",
                        comparison=comparison,
                        attempts=attempts,
                        reason=comparison if comparison is not None else "match",
                        status=final_status,
                        witness=witness,
                        reader_calls=accepted_calls,
                        reader_reason=final_reason,
                        source_fingerprint=fingerprint,
                    )
                )
            else:
                unresolved += 1
                last_calls = attempts[-1].calls if attempts else []
                record(
                    ReaderResult(
                        id=goal_id,
                        accepted=False,
                        outcome="unresolved",
                        comparison=comparison if comparison == "different" else None,
                        attempts=attempts,
                        reason=f"unresolved after {len(attempts)} attempt(s): {terminal_kind}"[
                            :500
                        ],
                        status=final_status,
                        witness=witness,
                        reader_calls=last_calls,
                        reader_reason=final_reason,
                        error_kind=terminal_kind,
                        source_fingerprint=fingerprint,
                    )
                )
            if (pos + 1) % 50 == 0:
                print(
                    f"[reader shard {ctx.shard}] {pos + 1}/{len(mine)} accepted={accepted} unresolved={unresolved} invalid={invalid_goal}",
                    flush=True,
                )
    except AbortError:
        status = "aborted"
        raise
    finally:
        finalize_manifest(
            ctx,
            status,
            cumulative_counts(
                ctx,
                {
                    "accepted": accepted,
                    "unresolved": unresolved,
                    "invalid_goal": invalid_goal,
                    "processed": processed,
                },
            ),
        )
    print(
        f"[reader shard {ctx.shard}] DONE: {accepted}/{len(mine)} accepted, {unresolved} unresolved, {invalid_goal} invalid",
        flush=True,
    )
    return {
        "accepted": accepted,
        "unresolved": unresolved,
        "invalid_goal": invalid_goal,
        "processed": processed,
    }
