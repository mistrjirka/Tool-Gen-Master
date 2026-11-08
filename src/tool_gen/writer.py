"""Writer stage: turn seeded goals into natural human requests.

The writer stays blind to implementation identifiers: chained ``API_call_<i>``
argument values are verbalized ("the value returned by operation N") before
they reach the model, and any candidate request containing an ``API_call_``
token is rejected as a data refusal with bounded regeneration. Writer
temperature is separately configurable (default 0.9); the reader default stays
0.0 (see ``reader.py``).

Error honesty: writer refusals and mechanical validation rejections are data
refusals (``error_kind="refusal"``); unusable model output is
``error_kind="model_output"`` and is recorded without retry; transport and
budget failures (``error_kind="transport"``) persist the current goal's
evidence row, abort the run nonzero, and never mark unprocessed goals.
"""

from __future__ import annotations

import json
import random
import re
from string import Template
from typing import Literal, Protocol

from pydantic import ValidationError

from tool_gen.client import BudgetError, ClientError, OutputError
from tool_gen.models import GoalRecord, StrictModel, WriterResult, normalize_goal_record
from tool_gen.prompts import load_prompt, writer_prompt
from tool_gen.store import (
    AbortError,
    StageContext,
    append_jsonl,
    cumulative_counts,
    ensure_manifest,
    finalize_manifest,
    read_done_ids,
)

MAX_ATTEMPTS = 3
TERSE_WORDS = 5

UNSUP_TOPICS = [
    "Translate this paragraph to Japanese",
    "What is the current price of Ethereum",
    "Send a notification to all subscribers",
    "Calculate the mortgage payment for a 30-year loan",
    "Find the nearest pharmacy to my location",
    "What are the reviews for this restaurant",
    "How do I reset my password",
    "What is the capital of Australia",
    "Convert 100 USD to EUR",
    "What is the population of Tokyo",
    "How to bake a chocolate cake",
    "What is the stock price of Tesla",
    "Translate hello to Spanish",
    "Find the nearest hospital",
    "Delete my account and erase all associated data",
    "Rename every file in my downloads folder to include today's date",
    "Remind me to call my dentist tomorrow at 9am",
    "How do I change the oil in my car",
    "What did the president say in yesterday's speech",
    "What is the best way to remove a red wine stain from wool",
]


class Completer(Protocol):
    def __call__(
        self,
        request_id: str,
        system: str,
        payload: str | dict[str, object],
        schema: dict[str, object],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, object]: ...


class WriterOutput(StrictModel):
    decision: Literal["accept", "reject"]
    reason: str
    request: str


class WriterRejected(Exception):
    """A candidate request failed the mechanical acceptance checks."""


def _natural_key(key: str) -> str:
    """Generic camelCase/snake_case humanization; values stay verbatim."""
    spaced = (
        re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key).replace("_", " ").replace("-", " ")
    )
    words = spaced.split()
    fixed: list[str] = []
    for word in words:
        if word.upper() in ("ID", "IDs"):
            fixed.append(word.upper())
        else:
            fixed.append(word.lower())
    return " ".join(fixed)


def describe_chained_reference(token: str) -> str:
    """Verbalize one ``API_call_<i>`` token without leaking the identifier.

    The reference contract is not yet declared, so no response fields are
    named here.
    """
    try:
        return f"the value returned by operation {int(token.split('_')[-1]) + 1}"
    except ValueError:
        return "the value returned by an earlier operation"


def render_value(value: object) -> str:
    """Render one value: chained refs verbalized, strings JSON-quoted.

    Shared by writer and paraphrase briefs. Quoting keeps literal strings
    unambiguous against numbers/booleans while types are preserved verbatim.
    """
    if isinstance(value, str):
        if value.startswith("API_call_"):
            return describe_chained_reference(value)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        inner = ", ".join(f"{k!s}: {render_value(v)}" for k, v in value.items())
        return "{" + inner + "}"
    if isinstance(value, list):
        return "[" + ", ".join(render_value(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def build_writer_payload(goal: GoalRecord) -> dict[str, object]:
    """Describe the goal's witness calls in plain language for the writer model.

    Never exposes ``API_call_<i>`` tokens (chained arguments are verbalized)
    and never exposes the witness calls themselves as structured data.
    """
    desired: list[dict[str, str]] = []
    index = _tool_function_index(goal)
    for call in goal.witness:
        info = _readable_need(call.name, dict(call.arguments), index.get(call.name))
        desired.append({"information": info})
    if goal.no_call:
        # Deterministic per goal id (not global RNG): the same goal always
        # yields the same request, keeping request ids and caches stable.
        # The pilot drew from the shared stream; payloads for no-call goals
        # differ while seeded goals stay byte-identical.
        desired = [
            {"information": random.Random(f"unsup:{goal.id}").choice(UNSUP_TOPICS)}
        ]
    payload: dict[str, object] = {
        "id": goal.id,
        "style": goal.style,
        # Same actual full visible context the reader receives; only private
        # fixtures/witness stay hidden. Never truncated to a label projection.
        "known_context": dict(goal.context),
        "desired_information": desired,
    }
    # Checked invariant on our own construction (never silently dropped):
    # a leak here is a renderer bug, so fail loudly before anything is sent.
    if "API_call_" in json.dumps(payload, ensure_ascii=False):
        raise ValueError(f"writer payload for goal {goal.id} leaks a hidden reference")
    return payload


def _schema_reference_text(description: str) -> str:
    """Omit only a trailing single-token illustration, never following semantics.

    Bundled identifiers include examples such as ', e.g. CASE-601'. A fresh
    writer probe promoted one into a user fact despite the prompt boundary.
    Keep all contract text; omit only this end-anchored illustration shape.
    """
    return re.sub(
        r",?\s+e\.g\.\s+[\w-]+\.?\s*$", "", description.strip(), flags=re.IGNORECASE
    )


def _tool_function_index(goal: GoalRecord) -> dict[str, dict[str, object]]:
    """Index goal tools by function name (generic over all catalogues)."""
    index: dict[str, dict[str, object]] = {}
    for entry in goal.tools:
        if not isinstance(entry, dict):
            continue
        fn = entry.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if isinstance(name, str) and name not in index:
            index[name] = fn
    return index


def _describe_argument(key: str, value: object, prop: object) -> str:
    """Render one supplied value with its schema meaning (generic).

    Only listed values are goal facts; ``prop`` descriptions/examples
    establish meanings. Descriptions lead so the writer sees semantics
    (inclusive endpoints, units, bounds, projection roles) instead of a
    parameter label; raw key names are never emitted when a description
    exists. Nested objects recurse through their subschema descriptions.
    """
    schema: dict[str, object] = prop if isinstance(prop, dict) else {}
    rendered = render_value(value)
    if isinstance(value, dict):
        sub_props = schema.get("properties")
        if isinstance(sub_props, dict):
            inner = "; ".join(
                _describe_argument(str(k), v, sub_props.get(k))
                for k, v in value.items()
            )
            desc = schema.get("description")
            prefix = _schema_reference_text(desc) if isinstance(desc, str) else ""
            if prefix:
                return f"{prefix}: {{{inner}}}" if inner else f"{prefix}: {rendered}"
            return "{" + inner + "}" if inner else rendered
    desc = schema.get("description")
    if isinstance(desc, str) and desc.strip():
        return f"{_schema_reference_text(desc)}: {rendered}"
    return f"{_natural_key(str(key))} is {rendered}"


def _readable_need(
    call_name: str,
    arguments: dict[str, object],
    tool_fn: dict[str, object] | None = None,
) -> str:
    """One need in plain words; chained refs verbalized, literals verbatim.

    Generic and data-driven: each supplied value carries its parameter
    description (endpoints, units, bounds, projection roles). The tool's
    description is separately marked as capability reference, never extra
    user selections. Raw parameter labels are omitted when descriptions
    exist. Only supplied values are facts; schema text establishes meanings.
    """
    tool_fn = tool_fn or {}
    op_desc = tool_fn.get("description")
    if isinstance(op_desc, str) and op_desc.strip():
        operation = _schema_reference_text(op_desc)
    else:
        operation = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", call_name).strip().lower()
    props: dict[str, object] = {}
    params = tool_fn.get("parameters")
    if isinstance(params, dict):
        raw_props = params.get("properties")
        if isinstance(raw_props, dict):
            props = raw_props
    parts = [_describe_argument(str(k), v, props.get(k)) for k, v in arguments.items()]
    requested = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", call_name).strip().lower()
    choices = (
        "\n".join(f"    - {part}" for part in parts)
        if parts
        else "    None: no argument values or optional constraints were supplied."
    )
    return (
        f"Requested operation: {requested}\n"
        f"  Supplied choices (the complete user selections):\n{choices}\n"
        "  Capability reference only (not additional user selections): " + operation
    )


def render_goal_needs(goal: GoalRecord) -> list[str]:
    """Shared need lines for writer and paraphrase briefs (no internal tokens)."""
    if goal.no_call:
        topic = random.Random(f"unsup:{goal.id}").choice(UNSUP_TOPICS)
        return [topic]
    index = _tool_function_index(goal)
    return [
        _readable_need(call.name, dict(call.arguments), index.get(call.name))
        for call in goal.witness
    ]


def render_context_section(goal: GoalRecord) -> str:
    """Full visible context, verbatim values, one line per entry."""
    if not goal.context:
        return "Nothing beyond the needs below."
    lines: list[str] = []
    for key in sorted(goal.context):
        shown = json.dumps(goal.context[key], ensure_ascii=False)
        lines.append(f"- {key}: {shown}")
    return "\n".join(lines)


def build_writer_brief(goal: GoalRecord) -> str:
    """Render the readable per-goal brief sent as the actual user message.

    System policy stays in the system prompt; this is data only. The
    structured :func:`build_writer_payload` remains for local provenance, but
    the LLM request body carries this text, never compact JSON.
    """
    needs = render_goal_needs(goal)
    numbered = "\n".join(f"{i}. {need}" for i, need in enumerate(needs, 1))
    template = load_prompt("writer", "brief_template")
    # One-pass substitution: inserted values are never re-expanded, so a
    # literal value containing a placeholder never injects template syntax.
    brief = Template(template).substitute(
        STYLE=goal.style,
        CONTEXT_SECTION=render_context_section(goal),
        NEEDS_SECTION=numbered,
    )
    # Checked invariant on our own construction (never silently dropped):
    # a leak here is a renderer bug, so fail loudly before anything is sent.
    if "API_call_" in brief:
        raise ValueError(f"writer brief for goal {goal.id} leaks a hidden reference")
    return brief


def writer_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["accept", "reject"]},
            "reason": {"type": "string"},
            "request": {"type": "string"},
        },
        "required": ["decision", "reason", "request"],
        "additionalProperties": False,
    }


def validate_request(candidate: str) -> None:
    """Semantic acceptance checks only.

    The pilot's opener-concentration quota and forced-terse rewriting were
    aesthetic distribution gates, not semantic invariants, and are
    intentionally removed: opener/register/length distributions are measured
    by reporting, never enforced by rejection. Only leakage of internal
    identifiers and empty requests fail here.
    """
    if "API_call_" in candidate:
        raise WriterRejected("api_call token leaked")
    if not candidate.strip():
        raise WriterRejected("empty request")


def is_terse(request: str) -> bool:
    return len(request.split()) <= TERSE_WORDS


def _parse_output(raw: object, request_id: str) -> WriterOutput:
    if not isinstance(raw, dict):
        raise OutputError(f"{request_id}: model output is not a JSON object")
    try:
        return WriterOutput.model_validate(raw)
    except ValidationError as exc:
        raise OutputError(
            f"{request_id}: model output violates writer schema: {exc.errors()[0]['msg']}"
        ) from None


def run_writer(
    raw_goals: list[dict[str, object]],
    ctx: StageContext,
    complete: Completer,
    temperature: float = 0.9,
) -> dict[str, int]:
    """Write one validated JSONL result per goal, streaming rows as they complete.

    Already-recorded goal ids are resumed only when the stage manifest pins the
    same inputs/prompts/config. Transport or budget failure records the current
    goal's evidence row and raises AbortError; unprocessed goals are left
    unwritten, never marked as failures.
    """
    ensure_manifest(ctx)
    out_path = ctx.shard_dir / "results.jsonl"
    done: set[str] = read_done_ids(out_path, "goal") if out_path.exists() else set()
    goals = [normalize_goal_record(raw) for raw in raw_goals]
    mine = [
        g
        for i, g in enumerate(goals)
        if i % ctx.shards == ctx.shard and g.id not in done
    ]
    system = writer_prompt()
    accepted = terse_n = retried = failed = transport = processed = 0
    status = "complete"
    try:
        for pos, goal in enumerate(mine):
            request: str | None = None
            reason = ""
            error_kind = ""
            request_id = f"w-{ctx.shard}-{goal.id}"
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    # The requested style travels through untouched: no adaptive
                    # forced-terse rewriting. Terse share is measured in stats.
                    # Structured payload stays available for provenance; the
                    # wire carries the readable brief as the user message.
                    # Both builders raise ValueError on a hidden-reference
                    # leak, so raw tokens never reach the wire; the handler
                    # below records it honestly instead of as model refusal.
                    build_writer_payload(goal)
                    brief = build_writer_brief(goal)
                    resp = complete(
                        f"{request_id}-a{attempt}",
                        system,
                        brief,
                        writer_schema(),
                        temperature,
                        2048,
                    )
                    output = _parse_output(resp.get("output"), request_id)
                    if output.decision != "accept":
                        # The writer's own judgment is data, not a failure: no retry.
                        reason = f"writer rejected: {output.reason[:80]}"
                        error_kind = "refusal"
                        break
                    validate_request(output.request)
                    request = output.request
                    break
                except ValueError as exc:
                    # Input-render failure is local data handling, never a
                    # model judgment: record it as such, no retry (retrying
                    # a deterministic render cannot help).
                    reason = f"input render failed: {exc}"
                    error_kind = "render"
                    break
                except WriterRejected as exc:
                    reason = str(exc)
                    error_kind = "refusal"
                    retried += 1
                except OutputError as exc:
                    # Unusable model output is recorded once, never opaquely retried.
                    reason = f"model output unusable: {exc}"
                    error_kind = "model_output"
                    break
                except (BudgetError, ClientError) as exc:
                    reason = f"transport: {exc}"
                    error_kind = "transport"
                    transport += 1
                    break
            processed = pos + 1
            if request is None:
                failed += 1
                row = WriterResult(
                    goal=goal,
                    request="",
                    decision="rejected",
                    reason=reason,
                    error_kind=error_kind,
                )
                append_jsonl(out_path, row.model_dump(mode="json"))
                if error_kind == "transport":
                    raise AbortError(reason, processed)
            else:
                accepted += 1
                terse_n += int(is_terse(request))
                row = WriterResult(
                    goal=goal, request=request, decision="accept", reason=""
                )
                append_jsonl(out_path, row.model_dump(mode="json"))
            if (pos + 1) % 25 == 0:
                print(
                    f"[writer shard {ctx.shard}] {pos + 1}/{len(mine)} accepted={accepted} terse={terse_n} retried={retried} failed={failed}",
                    flush=True,
                )
    # A transport/budget abort finalizes the manifest as aborted (never
    # complete), and counts accumulate with prior runs so a no-op resume
    # preserves history instead of overwriting it with zeros.
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
                    "terse": terse_n,
                    "retried": retried,
                    "failed": failed,
                    "transport_errors": transport,
                    "processed": processed,
                },
            ),
        )
    print(
        f"[writer shard {ctx.shard}] DONE {accepted}/{len(mine)} accepted terse={terse_n} retried={retried} failed={failed} transport={transport}",
        flush=True,
    )
    return {
        "accepted": accepted,
        "terse": terse_n,
        "retried": retried,
        "failed": failed,
        "transport": transport,
    }
