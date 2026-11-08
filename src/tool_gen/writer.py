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
from typing import Literal, Protocol

from pydantic import ValidationError

from tool_gen.client import BudgetError, ClientError, OutputError
from tool_gen.models import GoalRecord, StrictModel, WriterResult, normalize_goal_record
from tool_gen.prompts import writer_prompt
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
    "What is the weather forecast for Tokyo tomorrow",
    "Translate this paragraph to Japanese",
    "Book a hotel in Paris for next weekend",
    "What is the current price of Ethereum",
    "Send a notification to all subscribers",
    "Calculate the mortgage payment for a 30-year loan",
    "Find the nearest pharmacy to my location",
    "Summarize the latest news about climate change",
    "Get directions to the airport from downtown",
    "What are the reviews for this restaurant",
    "How do I reset my password",
    "What is the capital of Australia",
    "Convert 100 USD to EUR",
    "Find flights from New York to London",
    "What is the population of Tokyo",
    "How to bake a chocolate cake",
    "What is the stock price of Tesla",
    "Translate hello to Spanish",
    "Find the nearest hospital",
    "What is the weather in London today",
]

_VERBS = [
    "get",
    "list",
    "search",
    "find",
    "check",
    "calculate",
    "fetch",
    "retrieve",
    "query",
    "lookup",
    "count",
    "compare",
    "validate",
    "estimate",
]


class Completer(Protocol):
    def __call__(
        self,
        request_id: str,
        system: str,
        payload: dict[str, object],
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
    return (
        key.replace("Id", " ID")
        .replace("Code", " code")
        .replace("On", " on")
        .replace("After", " after")
        .replace("_", " ")
    )


def _display_value(value: object) -> str:
    if isinstance(value, str) and value.startswith("API_call_"):
        try:
            return f"the value returned by operation {int(value.split('_')[-1]) + 1}"
        except ValueError:
            return "the value returned by an earlier operation"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def build_writer_payload(goal: GoalRecord) -> dict[str, object]:
    """Describe the goal's witness calls in plain language for the writer model.

    Never exposes ``API_call_<i>`` tokens (chained arguments are verbalized)
    and never exposes the witness calls themselves as structured data.
    """
    desired: list[dict[str, str]] = []
    for call in goal.witness:
        readable = (
            "".join(
                " " + c if c.isupper() and i > 0 else c
                for i, c in enumerate(call.name[len(_verb_prefix(call.name)) :])
            )
            .strip()
            .lower()
        )
        parts = [
            f"{_natural_key(k)} is {_display_value(v)}"
            for k, v in call.arguments.items()
        ]
        info = f"{_verb_prefix(call.name)} {readable}"
        if parts:
            info += f" where {', '.join(parts)}"
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
    # Internal invariant on our own construction (not external input).
    assert "API_call_" not in json.dumps(payload, ensure_ascii=False)
    return payload


def _verb_prefix(tool_name: str) -> str:
    for verb in _VERBS:
        if tool_name.lower().startswith(verb.lower()):
            return verb
    return "get"


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
                    payload = build_writer_payload(goal)
                    resp = complete(
                        f"{request_id}-a{attempt}",
                        system,
                        payload,
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
