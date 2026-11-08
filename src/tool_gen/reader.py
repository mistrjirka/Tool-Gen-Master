"""Blind-reader stage: verify writer requests against the goal's tools.

The reader stays blind: it receives the user request plus the goal catalog's
COMPLETE tool schemas (names, descriptions, full parameter schemas) and the
full visible context object — never the witness calls, the gold status, or
writer judgments. The content fingerprint binding each accepted verdict to
its exact source is computed locally and is never sent to the reader. The prompt builder below serializes full schemas; it does
not copy the pilot's lossy name-only builder (tool names + bare parameter
keys), which hid descriptions, enums, and required-ness from the reader.

The dynamic reader schema carries per-tool ``argument_presence`` decisions with
NO call-count cap (``maxItems`` uncapped): the request determines the call
count. Reader temperature is separately configurable (default 0.0); the writer
default stays 0.9 (see ``writer.py``).
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from typing import Literal, NamedTuple

import jsonschema
from pydantic import JsonValue, ValidationError

from tool_gen.client import BudgetError, ClientError, OutputError
from tool_gen.models import ReaderResult, StrictModel, ToolCall, normalize_goal_record
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
from tool_gen.writer import Completer

Tool = dict[str, object]


class ReaderCallOutput(StrictModel):
    name: str
    arguments: dict[str, object]
    argument_presence: dict[str, bool]


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
            f"Tool {function.get('name')}: {function.get('description', '')}\nParameters: {json.dumps(parameters, ensure_ascii=False)}"
        )
    prompt = "Available tools (complete schemas):\n" + "\n\n".join(blocks)
    if context:
        prompt += "\n\nKnown context (JSON):\n" + canonical_json(context)
    return prompt + f"\n\nUser request: {request}\n\nReturn the minimal calls needed."


def reader_schema(tools: list[Tool]) -> dict[str, object]:
    """Flat presence decisions; call count is determined by the request."""
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
        decisions = {str(key): {"type": "boolean"} for key in props}
        variants.append(
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": [function["name"]]},
                    "arguments": deepcopy(parameters),
                    "argument_presence": {
                        "type": "object",
                        "properties": decisions,
                        "required": list(decisions),
                        "additionalProperties": False,
                    },
                },
                "required": ["name", "arguments", "argument_presence"],
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


def interpret_reading(reading: ReaderOutput, tools: list[Tool]) -> Interpretation:
    """Validate presence/value invariants, then build canonical calls losslessly."""
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
    calls: list[dict[str, object]] = []
    for call in reading.calls:
        if call.name not in definitions:
            raise ValueError(f"reader called unknown tool {call.name!r}")
        schema = definitions[call.name]
        arguments = deepcopy(call.arguments)
        for key, present in call.argument_presence.items():
            if present != (key in arguments):
                raise ValueError(
                    "argument presence disagrees with its supplied value: " + key
                )
        try:
            jsonschema.Draft202012Validator(schema).validate(arguments)
        except jsonschema.ValidationError as exc:
            raise ValueError(
                f"reader arguments violate tool schema: {exc.message}"
            ) from None
        calls.append({"name": call.name, "arguments": arguments})
    if reading.status != "clear" and calls:
        raise ValueError(
            "ambiguous/unsupported readings must not contain partial calls"
        )
    return Interpretation(status=reading.status, reason=reading.reason, calls=calls)


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
) -> dict[str, int]:
    """Verify writer entries; streams one validated JSONL verdict per entry."""
    ensure_manifest(ctx)
    out_path = ctx.shard_dir / "results.jsonl"
    done: set[str] = read_done_ids(out_path, "row") if out_path.exists() else set()
    entries: list[
        tuple[str, list[Tool], list[ToolCall], bool, str, dict[str, JsonValue]]
    ] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise TypeError("reader input rows must be JSON objects")
        goal_raw = raw.get("goal")
        request = raw.get("request", "")
        if not isinstance(request, str):
            raise TypeError("reader input rows need a string 'request'")
        goal = normalize_goal_record(goal_raw)
        tools_raw = (
            goal_raw.get("tools", goal_raw.get("catalog", []))
            if isinstance(goal_raw, dict)
            else []
        )
        if not isinstance(tools_raw, list) or not all(
            isinstance(t, dict) for t in tools_raw
        ):
            raise TypeError(f"goal {goal.id}: catalog must be a list of tool objects")
        tools: list[Tool] = [t for t in tools_raw if isinstance(t, dict)]
        entries.append(
            (
                goal.id,
                tools,
                [ToolCall(name=c.name, arguments=c.arguments) for c in goal.witness],
                goal.no_call,
                request,
                dict(goal.context),
            )
        )
    mine = [
        e
        for i, e in enumerate(entries)
        if i % ctx.shards == ctx.shard and e[0] not in done
    ]
    system = reader_prompt()
    accepted = rejected = errors = processed = 0
    status = "complete"

    def record(row: ReaderResult) -> None:
        append_jsonl(out_path, row.model_dump(mode="json"))

    try:
        for pos, (goal_id, tools, witness, no_call, request, context) in enumerate(
            mine
        ):
            fingerprint = content_fingerprint(
                {
                    "id": goal_id,
                    "request": request,
                    "tools": tools,
                    "context": context,
                    "witness": [
                        {"name": c.name, "arguments": c.arguments} for c in witness
                    ],
                    "no_call": no_call,
                }
            )
            try:
                resp = complete(
                    f"r-{ctx.shard}-{goal_id}",
                    system,
                    {"student_prompt": student_prompt(tools, request, context)},
                    reader_schema(tools),
                    temperature,
                    3072,
                )
                reading = _parse_output(resp.get("output"), goal_id)
                try:
                    interp = interpret_reading(reading, tools)
                except ValueError as exc:
                    rejected += 1
                    record(
                        ReaderResult(
                            id=goal_id,
                            accepted=False,
                            reason=f"interpret_error: {exc}",
                            status=reading.status,
                            witness=witness,
                            reader_calls=_reader_calls_of(reading),
                            reader_reason=reading.reason,
                            error_kind="reader_contract",
                            source_fingerprint=fingerprint,
                        ),
                    )
                    continue
                expected_status = "unsupported" if no_call else "clear"
                if interp.status != expected_status:
                    rejected += 1
                    record(
                        ReaderResult(
                            id=goal_id,
                            accepted=False,
                            reason=f"status_mismatch: got {interp.status} expected {expected_status}",
                            reader_reason=interp.reason,
                            witness=witness,
                            reader_calls=_to_tool_calls(interp.calls, goal_id),
                            error_kind="status_mismatch",
                            source_fingerprint=fingerprint,
                        ),
                    )
                    continue
                reader_counter = Counter(
                    json.dumps(c, sort_keys=True) for c in interp.calls
                )
                witness_counter = Counter(
                    json.dumps(
                        {"name": c.name, "arguments": c.arguments}, sort_keys=True
                    )
                    for c in witness
                )
                if reader_counter == witness_counter:
                    accepted += 1
                    record(
                        ReaderResult(
                            id=goal_id,
                            accepted=True,
                            reason="match",
                            status=interp.status,
                            witness=witness,
                            reader_calls=_to_tool_calls(interp.calls, goal_id),
                            source_fingerprint=fingerprint,
                        ),
                    )
                else:
                    rejected += 1
                    record(
                        ReaderResult(
                            id=goal_id,
                            accepted=False,
                            reason="call_mismatch",
                            status=interp.status,
                            reader_reason=interp.reason,
                            witness=witness,
                            reader_calls=_to_tool_calls(interp.calls, goal_id),
                            error_kind="call_mismatch",
                            source_fingerprint=fingerprint,
                        ),
                    )
            except OutputError as exc:
                errors += 1
                record(
                    ReaderResult(
                        id=goal_id,
                        accepted=False,
                        reason=f"model_output: {exc}",
                        witness=witness,
                        error_kind="model_output",
                        source_fingerprint=fingerprint,
                    ),
                )
            except (BudgetError, ClientError) as exc:
                errors += 1
                record(
                    ReaderResult(
                        id=goal_id,
                        accepted=False,
                        reason=f"transport: {exc}",
                        witness=witness,
                        error_kind="transport",
                        source_fingerprint=fingerprint,
                    ),
                )
                processed = pos + 1
                raise AbortError(f"transport: {exc}", processed) from None
            processed = pos + 1
            if (pos + 1) % 50 == 0:
                print(
                    f"[reader shard {ctx.shard}] {pos + 1}/{len(mine)} accepted={accepted} rejected={rejected} errors={errors}",
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
                    "rejected": rejected,
                    "errors": errors,
                    "processed": processed,
                },
            ),
        )
    print(
        f"[reader shard {ctx.shard}] DONE: {accepted}/{len(mine)} accepted, {rejected} rejected, {errors} errors",
        flush=True,
    )
    return {"accepted": accepted, "rejected": rejected, "errors": errors}


def _reader_calls_of(reading: ReaderOutput) -> list[ToolCall]:
    return [ToolCall(name=c.name, arguments=dict(c.arguments)) for c in reading.calls]
