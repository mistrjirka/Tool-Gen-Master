"""Semantic creation stage: model-chosen goals under deterministic controls.

The sampler reuses :func:`tool_gen.goals.gen_goals` to derive allowed
catalogues and structural controls (call counts, required shapes); all sampled
values and call identities are discarded before the model stage. The model
sees only the allowed catalogue plus structural controls and jointly chooses a
meaningful new goal: tool selection, fictional values, calls and the natural
request. Deterministic hard validation (call count, required shapes,
catalogue membership, schema validity, near-duplicate, no chaining) runs
server-side; a separate quality-judge invocation assesses the whole goal.
"""

from __future__ import annotations

import hashlib
import os
from typing import Literal

from pydantic import Field, JsonValue, ValidationError, model_validator

from tool_gen.client import BudgetError, ClientError, OutputError
from tool_gen.comparison import validate_calls
from tool_gen.goals import gen_goals, near_duplicate
from tool_gen.models import GoalRecord, StrictModel, ToolCall, WriterResult
from tool_gen.prompts import load_prompt
from tool_gen.quality import QualityReview, review_candidate
from tool_gen.reader import (
    ReaderCallOutput,
    ReaderOutput,
    interpret_reading,
    reader_schema,
)
from tool_gen.store import (
    AbortError,
    StageContext,
    StageError,
    append_jsonl,
    canonical_json,
    ensure_manifest,
    ensure_unique_ids,
    finalize_manifest,
    read_done_ids,
    read_jsonl_strict,
    strict_dumps,
)
from tool_gen.validate import audit_goal
from tool_gen.writer import Completer

ShapeName = Literal["array", "object", "unfiltered"]


class CreationSpec(StrictModel):
    """Deterministic structural spec: catalogue plus controls, no values."""

    id: str = Field(min_length=1)
    split: str = "train"
    family_id: str = Field(min_length=1)
    style: str = Field(min_length=1)
    no_call: bool = False
    tools: list[dict[str, object]] = Field(min_length=1)
    context: dict[str, JsonValue] = Field(default_factory=dict)
    call_count: int = Field(ge=0)
    required_shapes: list[ShapeName] = Field(default_factory=list)
    exploration_cue: str | None = Field(default=None)

    @model_validator(mode="after")
    def _coherent_controls(self) -> CreationSpec:
        if self.no_call and (self.call_count != 0 or self.required_shapes):
            raise ValueError(
                "unsupported examples need zero calls and no argument shapes"
            )
        if not self.no_call and self.call_count < 1:
            raise ValueError("supported examples need at least one call")
        if len(self.required_shapes) != len(set(self.required_shapes)):
            raise ValueError("required argument shapes must be unique")
        return self


class CreatorOutput(StrictModel):
    decision: Literal["candidate", "cannot_create"]
    intent: str = ""
    request: str = ""
    calls: list[ReaderCallOutput] = Field(default_factory=list)


class CreationAttempt(StrictModel):
    """One recorded try: candidate evidence plus quality/error evidence."""

    attempt: int = Field(ge=1)
    create_request_id: str = Field(min_length=1)
    decision: str = ""
    intent: str = ""
    request: str = ""
    calls: list[ToolCall] = Field(default_factory=list)
    quality: QualityReview | None = None
    judge_request_id: str = ""
    error_kind: str = ""
    detail: str = ""


class CreationRecord(StrictModel):
    """One terminal typed record per spec; the canonical authority."""

    id: str = Field(min_length=1)
    status: Literal["accepted", "unresolved"]
    attempts: list[CreationAttempt] = Field(default_factory=list)
    goal: GoalRecord | None = None
    request: str = ""
    intent: str = ""


def creation_prompt() -> str:
    return load_prompt("creation", "base")


def _draft_shapes(witness: list[dict[str, object]]) -> list[ShapeName]:
    """Required shapes from a sampled draft's supplied types/zero-arg calls."""
    found: list[ShapeName] = []

    def walk(value: object) -> None:
        if isinstance(value, list):
            if "array" not in found:
                found.append("array")
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            if "object" not in found:
                found.append("object")
            for item in value.values():
                walk(item)

    for call in witness:
        args = call.get("arguments")
        if not isinstance(args, dict):
            continue
        if not args:
            if "unfiltered" not in found:
                found.append("unfiltered")
            continue
        for value in args.values():
            walk(value)
    return found


def _scalar_enum_candidates(
    tools: list[dict[str, object]],
) -> list[tuple[str, str, str]]:
    """Eligible (tool, dotted-param, value) cue candidates from catalogue schemas.

    Only scalar string enums on original parameters (including nested original
    objects such as ``searchBooks.filter.genre``). Eligibility follows the
    original schema type: array-typed parameters (projection/output-key
    lists, whose items carry an enum of record keys) describe output keys,
    not interchangeable query values, and are excluded by type, as is any
    parameter whose declared description states projection semantics. No type
    escapes: values are plain strings.
    """
    candidates: set[tuple[str, str, str]] = set()

    def walk(tool: str, path: str, schema: object) -> None:
        if not isinstance(schema, dict):
            return
        description = str(schema.get("description", "")).lower()
        if "projection" in description or "record keys" in description:
            return
        enum = schema.get("enum")
        if (
            isinstance(enum, list)
            and enum
            and all(isinstance(v, str) for v in enum)
            and schema.get("type") == "string"
        ):
            for value in enum:
                assert isinstance(value, str)
                candidates.add((tool, path, value))
            return
        sub = schema.get("properties")
        if isinstance(sub, dict):
            for sname, sspec in sub.items():
                if isinstance(sname, str):
                    walk(tool, f"{path}.{sname}" if path else sname, sspec)

    for entry in tools:
        if not isinstance(entry, dict):
            continue
        function = entry.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        parameters = function.get("parameters")
        if not isinstance(parameters, dict):
            continue
        properties = parameters.get("properties")
        if not isinstance(properties, dict):
            continue
        for pname, pspec in properties.items():
            if isinstance(pname, str):
                walk(name, pname, pspec)
    # Deterministic pool order so every caller derives identical cues.
    return sorted(candidates)


def _cue_text(tool: str, param: str, value: str) -> str:
    return (
        "Exploration cue (optional, ignore if it does not fit a sensible goal): "
        f"consider planning one call with {tool} where {param} is {value!r}. "
        "Use it only for a genuinely fitting request; never force it."
    )


def _cue_selector(spec_id: str) -> int:
    digest = hashlib.sha256(f"exploration-cue-v1:{spec_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _cue_eligible(spec: CreationSpec) -> bool:
    """Obviously impossible cue situations are skipped instead of filler."""
    if spec.no_call:
        return False
    return not (spec.call_count == 1 and spec.required_shapes == ["unfiltered"])


def attach_exploration_cues(specs: list[CreationSpec]) -> list[CreationSpec]:
    """Return copies of the batch with deterministic cues attached.

    Balances *planned* cue exposure within these immutable specs via a simple
    local count: each newly cued spec takes among its own available
    (tool, param, value) options one with the lowest planned count so far,
    with a deterministic id-hash tie-break. No observed-corpus claim, no
    shared scheduler, no extra workflow or state: the count lives only in
    this call, so the same input list always yields the same cues. Lets the
    parent reuse the exact same cues on preselected saved specs without
    resampling catalogues, counts, shapes or ids. Specs that already carry a
    cue keep it (and seed the count when the cue matches one of their own
    options); cue-less saved specs (default absent) stay compatible; a
    deterministic selected subset stays uncued so uncued variety survives.
    """
    planned: dict[tuple[str, str, str], int] = {}
    for spec in specs:
        if spec.exploration_cue is None:
            continue
        for triple in _scalar_enum_candidates(spec.tools):
            if _cue_text(*triple) == spec.exploration_cue:
                planned[triple] = planned.get(triple, 0) + 1
                break
    out: list[CreationSpec] = []
    for spec in specs:
        if spec.exploration_cue is not None:
            out.append(spec)
            continue
        cue: str | None = None
        if _cue_eligible(spec):
            candidates = _scalar_enum_candidates(spec.tools)
            if candidates:
                selector = _cue_selector(spec.id)
                if selector % 2 == 0:
                    least = min(planned.get(t, 0) for t in candidates)
                    tied = [t for t in candidates if planned.get(t, 0) == least]
                    triple = tied[(selector >> 1) % len(tied)]
                    cue = _cue_text(*triple)
                    planned[triple] = planned.get(triple, 0) + 1
        out.append(spec.model_copy(update={"exploration_cue": cue}))
    return out


def sample_specs(n: int, seed: int) -> list[CreationSpec]:
    """Deterministic structural specs with fresh ``semantic-`` ids.

    Catalogues, styles, contexts and call counts derive from seeded drafts;
    every sampled value and call identity is discarded before the model stage.
    """
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be at least 1")
    drafts = gen_goals(n, seed)
    specs: list[CreationSpec] = []
    for i, draft in enumerate(drafts):
        no_call = bool(draft.get("no_call", False))
        witness = draft.get("witness")
        calls: list[dict[str, object]] = (
            [c for c in witness if isinstance(c, dict)]
            if isinstance(witness, list)
            else []
        )
        tools = draft.get("tools")
        if not isinstance(tools, list) or not tools:
            raise ValueError(f"draft {i}: sampled catalogue is empty")
        family = draft.get("family_id")
        style = draft.get("style")
        if not isinstance(family, str) or not family:
            raise ValueError(f"draft {i}: missing family_id")
        if not isinstance(style, str) or not style:
            raise ValueError(f"draft {i}: missing style")
        spec = CreationSpec(
            id=f"semantic-{seed}-{i:04d}",
            split="train",
            family_id=family,
            style=style,
            no_call=no_call,
            tools=[t for t in tools if isinstance(t, dict)],
            context={},
            call_count=0 if no_call else len(calls),
            required_shapes=[] if no_call else _draft_shapes(calls),
        )
        specs.append(spec)
    return attach_exploration_cues(specs)


def _public_contracts(tools: list[dict[str, object]]) -> list[dict[str, object]]:
    """Public tool contracts only: name, description, parameter schema."""
    contracts: list[dict[str, object]] = []
    for entry in tools:
        if not isinstance(entry, dict):
            continue
        function = entry.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue
        contract: dict[str, object] = {"name": name}
        description = function.get("description")
        if isinstance(description, str) and description.strip():
            contract["description"] = description
        parameters = function.get("parameters")
        if isinstance(parameters, dict):
            contract["parameters"] = parameters
        contracts.append(contract)
    return contracts


def build_creation_brief(spec: CreationSpec, feedback: str = "") -> str:
    """Render the readable per-spec brief sent as the actual user message.

    Carries only the allowed catalogue plus structural controls; never the
    original random witness or placeholder pools (those are discarded by
    :func:`sample_specs` and never reach this builder).
    """
    lines = [
        "Allowed tool catalogue (public contracts only):",
        canonical_json(_public_contracts(spec.tools)),
        "",
        f"Structural controls: call_count={spec.call_count}",
        f"required_shapes={canonical_json(list(spec.required_shapes))}",
        f"style={spec.style}",
        f"no_call={spec.no_call!r}",
        "Known context (JSON, immutable user facts):",
        canonical_json(dict(spec.context)) if spec.context else "{}",
        "",
        "Choose the goal jointly and return only the supplied JSON shape.",
    ]
    if spec.exploration_cue:
        lines += ["", spec.exploration_cue]
    if feedback:
        lines += ["", "---", "Retry guidance (same controls, no new facts):", feedback]
    return "\n".join(lines)


def creator_schema(tools: list[dict[str, object]]) -> dict[str, object]:
    """Creator response shape reusing the reader slot wire (no duplicate codec)."""
    schema = reader_schema(tools)
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise TypeError("reader schema lacks properties")
    calls_schema = properties.get("calls")
    if not isinstance(calls_schema, dict):
        raise TypeError("reader schema lacks calls")
    items = calls_schema.get("items")
    if not isinstance(items, dict):
        raise TypeError("reader calls schema lacks items")
    variants = items.get("anyOf")
    if not isinstance(variants, list) or not variants:
        raise TypeError("reader calls schema lacks variants")
    return {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["candidate", "cannot_create"]},
            "intent": {"type": "string"},
            "request": {"type": "string"},
            "calls": {"type": "array", "items": {"anyOf": variants}},
        },
        "required": ["decision", "intent", "request", "calls"],
        "additionalProperties": False,
    }


def _parse_output(raw: object, request_id: str) -> CreatorOutput:
    if not isinstance(raw, dict):
        raise OutputError(f"{request_id}: model output is not a JSON object")
    try:
        return CreatorOutput.model_validate(raw)
    except ValidationError as exc:
        raise OutputError(
            f"{request_id}: model output violates creator schema: {exc.errors()[0]['msg']}"
        ) from None


def _evidenced_shapes(calls: list[ToolCall]) -> set[str]:
    evidenced: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, list):
            evidenced.add("array")
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            evidenced.add("object")
            for item in value.values():
                walk(item)

    for call in calls:
        if not call.arguments:
            evidenced.add("unfiltered")
        for value in call.arguments.values():
            walk(value)
    return evidenced


def _hard_validate(
    spec: CreationSpec, output: CreatorOutput
) -> tuple[GoalRecord, list[ToolCall], str, str]:
    """Server-side deterministic checks; raises OutputError naming the defect."""
    request = output.request
    if not request.strip():
        raise OutputError("hard-invalid: empty request")
    if "API_call_" in request or "API_call_" in output.intent:
        raise OutputError("hard-invalid: internal reference leaked")
    if not output.intent.strip():
        raise OutputError("hard-invalid: empty intent")
    status: Literal["clear", "unsupported"] = "unsupported" if spec.no_call else "clear"
    try:
        interp = interpret_reading(
            ReaderOutput(status=status, reason=output.intent, calls=output.calls),
            spec.tools,
        )
    except ValueError as exc:
        raise OutputError(f"hard-invalid: {exc}") from None
    parsed: list[ToolCall] = []
    for entry in interp.calls:
        entry_name = entry.get("name")
        entry_args = entry.get("arguments")
        if not isinstance(entry_name, str) or not isinstance(entry_args, dict):
            raise OutputError("hard-invalid: malformed interpreted call")
        parsed.append(ToolCall(name=entry_name, arguments=dict(entry_args)))
    if spec.no_call:
        if parsed or output.decision != "candidate":
            raise OutputError("hard-invalid: no_call candidate must carry zero calls")
    else:
        if output.decision != "candidate":
            raise OutputError("hard-invalid: call spec refused as cannot_create")
        if len(parsed) != spec.call_count:
            raise OutputError(
                f"hard-invalid: got {len(parsed)} calls, need {spec.call_count}"
            )
    try:
        validate_calls(parsed, spec.tools)
    except (ValueError, TypeError) as exc:
        raise OutputError(f"hard-invalid: {exc}") from None
    evidenced = _evidenced_shapes(parsed)
    for shape in spec.required_shapes:
        if shape not in evidenced:
            raise OutputError(f"hard-invalid: required shape {shape!r} not evidenced")
    seen: list[dict[str, object]] = []
    for call in parsed:
        if near_duplicate(seen, call.name, dict(call.arguments)):
            raise OutputError("hard-invalid: near-duplicate calls")
        seen.append({"name": call.name, "arguments": dict(call.arguments)})
    witness = [{"name": c.name, "arguments": dict(c.arguments)} for c in parsed]
    problems = audit_goal(
        {
            "id": spec.id,
            "tools": spec.tools,
            "witness": witness,
            "no_call": spec.no_call,
        }
    )
    if problems:
        raise OutputError(f"hard-invalid: {problems[0][:200]}")
    group_content: dict[str, object] = {
        "witness": witness,
        "context": dict(spec.context),
        "no_call": spec.no_call,
    }
    if spec.no_call:
        group_content["intent"] = output.intent
    group_id = hashlib.sha256(canonical_json(group_content).encode("utf-8")).hexdigest()
    goal = GoalRecord(
        id=spec.id,
        group_id=group_id,
        split=spec.split,
        family_id=spec.family_id,
        style=spec.style,
        no_call=spec.no_call,
        context_mode="api_only",
        context=dict(spec.context),
        tools=list(spec.tools),
        witness=parsed,
        fixtures={},
        observations=[],
    )
    return goal, parsed, request, output.intent


def _quality_feedback(review: QualityReview) -> str:
    parts: list[str] = []
    for name, assessment in review.assessments():
        if assessment.status != "acceptable":
            parts.append(f"{name} ({assessment.status}): {assessment.evidence[:200]}")
    return "Previous candidate had concrete quality problems: " + "; ".join(parts)


def _load_records(ctx: StageContext) -> list[CreationRecord]:
    path = ctx.shard_dir / "creation.jsonl"
    if not path.exists():
        return []
    records: list[CreationRecord] = []
    for index, raw in enumerate(read_jsonl_strict(path), 1):
        try:
            record = CreationRecord.model_validate(raw)
        except ValidationError as exc:
            raise StageError(
                f"{path}:{index}: invalid creation record: {exc}"
            ) from None
        if record.status == "accepted":
            last = record.attempts[-1] if record.attempts else None
            if (
                record.goal is None
                or record.goal.id != record.id
                or not record.request.strip()
                or last is None
                or last.quality is None
                or not last.quality.accepted
                or record.request != last.request
                or record.intent != last.intent
                or record.goal.witness != last.calls
            ):
                raise StageError(
                    f"{path}:{index}: accepted record lacks matching quality evidence"
                )
        records.append(record)
    ensure_unique_ids([record.id for record in records], str(path))
    return records


def _rewrite_compat(ctx: StageContext) -> None:
    """Derive the WriterResult-only results.jsonl from canonical records.

    Atomic replace: accepted records only, so export/paraphrase/reader work
    unchanged. The canonical creation.jsonl stays the sole authority.
    """
    compat_path = ctx.shard_dir / "results.jsonl"
    tmp_path = ctx.shard_dir / "results.jsonl.tmp"
    rows: list[str] = []
    for record in _load_records(ctx):
        if record.status == "accepted" and record.goal is not None:
            row = WriterResult(
                goal=record.goal, request=record.request, decision="accept"
            )
            rows.append(strict_dumps(row.model_dump(mode="json")))
    tmp_path.write_text("".join(line + "\n" for line in rows), encoding="utf-8")
    os.replace(tmp_path, compat_path)


def _recompute_counts(ctx: StageContext) -> dict[str, int]:
    """Counts from canonical records so a no-op resume never double-counts."""
    accepted = unresolved = 0
    for record in _load_records(ctx):
        if record.status == "accepted":
            accepted += 1
        else:
            unresolved += 1
    return {
        "accepted": accepted,
        "unresolved": unresolved,
        "processed": accepted + unresolved,
    }


def run_creation(
    specs: list[CreationSpec],
    ctx: StageContext,
    complete: Completer,
    temperature: float = 0.9,
    max_attempts: int = 2,
) -> dict[str, int]:
    """Create one terminal typed record per spec in creation.jsonl.

    Already-recorded spec ids are skipped only when the stage manifest pins
    the same specs input, combined creator+quality prompt and config.
    Transport/budget failure records the current spec's evidence and raises
    AbortError; later specs stay unwritten, never blanket-failed.
    """
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool):
        raise TypeError("max_attempts must be an integer")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    ensure_manifest(ctx)
    canonical_path = ctx.shard_dir / "creation.jsonl"
    done: set[str] = set()
    if canonical_path.exists():
        done = read_done_ids(canonical_path, "row")
        _rewrite_compat(ctx)
    mine: list[tuple[int, CreationSpec]] = [
        (i, s)
        for i, s in enumerate(specs)
        if i % ctx.shards == ctx.shard and s.id not in done
    ]
    if not isinstance(temperature, float):
        raise TypeError("temperature must be a float")
    system = creation_prompt()
    status = "complete"
    transport = 0
    try:
        for pos, (src_index, spec) in enumerate(mine):
            _ = src_index
            attempts: list[CreationAttempt] = []
            feedback = ""
            final_goal: GoalRecord | None = None
            final_request = ""
            final_intent = ""
            accepted = False
            pending: tuple[GoalRecord, list[ToolCall], str, str, str] | None = None
            processed = pos + 1
            for attempt_no in range(1, max_attempts + 1):
                if pending is None:
                    create_id = f"c-{ctx.shard}-{spec.id}-a{attempt_no}"
                    try:
                        resp = complete(
                            create_id,
                            system,
                            build_creation_brief(spec, feedback),
                            creator_schema(spec.tools),
                            temperature,
                            3072,
                        )
                        output = _parse_output(resp.get("output"), create_id)
                        if output.decision == "cannot_create":
                            if (
                                output.calls
                                or output.request.strip()
                                or not output.intent.strip()
                            ):
                                raise OutputError(
                                    "declined creation must give a reason, no calls or request"
                                )
                            attempts.append(
                                CreationAttempt(
                                    attempt=attempt_no,
                                    create_request_id=create_id,
                                    decision="cannot_create",
                                    intent=output.intent,
                                    error_kind="creation_declined",
                                    detail=output.intent,
                                )
                            )
                            break
                        goal, parsed, request, intent = _hard_validate(spec, output)
                        final_goal, final_request, final_intent = goal, request, intent
                    except OutputError as exc:
                        attempts.append(
                            CreationAttempt(
                                attempt=attempt_no,
                                create_request_id=create_id,
                                error_kind="model_output",
                                detail=str(exc)[:300],
                            )
                        )
                        feedback = f"Your previous output was discarded: {exc}"[:300]
                        continue
                    except (BudgetError, ClientError) as exc:
                        transport += 1
                        attempts.append(
                            CreationAttempt(
                                attempt=attempt_no,
                                create_request_id=create_id,
                                error_kind="transport",
                                detail=str(exc)[:300],
                            )
                        )
                        record = CreationRecord(
                            id=spec.id, status="unresolved", attempts=attempts
                        )
                        append_jsonl(canonical_path, record.model_dump(mode="json"))
                        raise AbortError(f"transport: {exc}", processed) from None
                    pending = (goal, parsed, request, intent, create_id)
                else:
                    goal, parsed, request, intent, create_id = pending
                judge_id = f"j-{ctx.shard}-{spec.id}-a{attempt_no}"
                try:
                    review = review_candidate(goal, request, intent, complete, judge_id)
                except OutputError as exc:
                    # Valid candidate retained; only the judging is retried,
                    # never an arbitrary regeneration.
                    attempts.append(
                        CreationAttempt(
                            attempt=attempt_no,
                            create_request_id=create_id,
                            decision="candidate",
                            intent=intent,
                            request=request,
                            calls=parsed,
                            judge_request_id=judge_id,
                            error_kind="model_output",
                            detail=f"judge unusable: {exc}"[:300],
                        )
                    )
                    continue
                except (BudgetError, ClientError) as exc:
                    transport += 1
                    attempts.append(
                        CreationAttempt(
                            attempt=attempt_no,
                            create_request_id=create_id,
                            decision="candidate",
                            intent=intent,
                            request=request,
                            calls=parsed,
                            judge_request_id=judge_id,
                            error_kind="transport",
                            detail=str(exc)[:300],
                        )
                    )
                    record = CreationRecord(
                        id=spec.id, status="unresolved", attempts=attempts
                    )
                    append_jsonl(canonical_path, record.model_dump(mode="json"))
                    raise AbortError(f"transport: {exc}", processed) from None
                if review.accepted:
                    attempts.append(
                        CreationAttempt(
                            attempt=attempt_no,
                            create_request_id=create_id,
                            decision="candidate",
                            intent=intent,
                            request=request,
                            calls=parsed,
                            quality=review,
                            judge_request_id=judge_id,
                        )
                    )
                    final_goal, final_request, final_intent = goal, request, intent
                    accepted = True
                    break
                if review.uncertain:
                    # Uncertainty is retained unresolved, never looped green.
                    attempts.append(
                        CreationAttempt(
                            attempt=attempt_no,
                            create_request_id=create_id,
                            decision="candidate",
                            intent=intent,
                            request=request,
                            calls=parsed,
                            quality=review,
                            judge_request_id=judge_id,
                            error_kind="uncertain",
                            detail="quality uncertain; retained unresolved",
                        )
                    )
                    break
                attempts.append(
                    CreationAttempt(
                        attempt=attempt_no,
                        create_request_id=create_id,
                        decision="candidate",
                        intent=intent,
                        request=request,
                        calls=parsed,
                        quality=review,
                        judge_request_id=judge_id,
                        error_kind="quality_problem",
                        detail=_quality_feedback(review)[:300],
                    )
                )
                # Quality problems regenerate a NEW candidate next attempt;
                # the rejected target is never silently patched.
                pending = None
                feedback = _quality_feedback(review)
            record = CreationRecord(
                id=spec.id,
                status="accepted" if accepted else "unresolved",
                attempts=attempts,
                goal=final_goal,
                request=final_request,
                intent=final_intent,
            )
            append_jsonl(canonical_path, record.model_dump(mode="json"))
    except AbortError:
        status = "aborted"
        raise
    except BaseException:
        status = "failed"
        raise
    finally:
        _rewrite_compat(ctx)
        finalize_manifest(ctx, status, _recompute_counts(ctx))
    counts = _recompute_counts(ctx)
    print(
        f"[creation shard {ctx.shard}] DONE accepted={counts['accepted']} "
        f"unresolved={counts['unresolved']} transport={transport}",
        flush=True,
    )
    return {"transport": transport, **counts}
