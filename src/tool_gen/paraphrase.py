"""Paraphrase stage: 3 human registers per accepted writer request.

Each accepted request is rewritten into exactly three usable paraphrases with
pairwise-distinct text and pairwise-distinct register labels. Fewer than three
usable outputs is a visible failure row, never a silently accepted partial set.
No blanket bans are imposed on list or identifier styles in general prose.

The goal operations sent to the paraphraser are verbalized first, so chained
``API_call_<i>`` tokens never appear in paraphrase payloads (or in
writer-visible text anywhere). Outputs containing ``API_call_`` are filtered;
an entry with unusable output keeps an ``error`` note.
"""

from __future__ import annotations

from pydantic import Field, ValidationError

from tool_gen.client import BudgetError, ClientError, OutputError
from tool_gen.models import (
    GoalRecord,
    ParaphraseResult,
    StrictModel,
    normalize_goal_record,
)
from tool_gen.prompts import load_prompt
from tool_gen.store import (
    AbortError,
    StageContext,
    append_jsonl,
    cumulative_counts,
    ensure_manifest,
    finalize_manifest,
    read_done_ids,
)
from tool_gen.writer import Completer

NUM_PARAPHRASES = 3


class ParaphraseEntry(StrictModel):
    text: str
    register_label: str = Field(alias="register")


class ParaphraseOutput(StrictModel):
    paraphrases: list[ParaphraseEntry]


def verbalize_operations(goal: GoalRecord) -> list[str]:
    """Render witness calls as plain text with chained refs verbalized."""
    lines: list[str] = []
    for index, call in enumerate(goal.witness):
        parts: list[str] = []
        for key, value in call.arguments.items():
            if isinstance(value, str) and value.startswith("API_call_"):
                try:
                    ref = int(value.split("_")[-1]) + 1
                    parts.append(f"{key}=the result of operation {ref}")
                except ValueError:
                    parts.append(f"{key}=the result of an earlier operation")
            elif isinstance(value, str):
                parts.append(f"{key}={value}")
            else:
                parts.append(f"{key}={value!r}")
        lines.append(f"{index + 1}. {call.name}({', '.join(parts)})")
    return lines


def paraphrase_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "paraphrases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "register": {"type": "string"},
                    },
                    "required": ["text", "register"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["paraphrases"],
        "additionalProperties": False,
    }


def select_paraphrases(raw: object, goal_id: str) -> list[dict[str, str]]:
    """Enforce exactly three usable, distinct paraphrases or fail visibly."""
    if not isinstance(raw, dict):
        raise OutputError(f"paraphrase {goal_id}: model output is not a JSON object")
    try:
        output = ParaphraseOutput.model_validate(raw)
    except ValidationError as exc:
        raise OutputError(
            f"paraphrase {goal_id}: model output violates paraphrase schema: {exc.errors()[0]['msg']}"
        ) from None
    usable: list[dict[str, str]] = []
    seen_texts: set[str] = set()
    seen_registers: set[str] = set()
    for entry in output.paraphrases:
        text = entry.text.strip()
        register = entry.register_label.strip()
        if not text or "API_call_" in text or not register:
            continue
        if text in seen_texts or register in seen_registers:
            continue
        seen_texts.add(text)
        seen_registers.add(register)
        usable.append({"text": text, "register": register})
        if len(usable) == NUM_PARAPHRASES:
            break
    if len(usable) < NUM_PARAPHRASES:
        raise ValueError(
            f"paraphrase {goal_id}: only {len(usable)} usable distinct paraphrases, need {NUM_PARAPHRASES}"
        )
    return usable


def run_paraphrase(
    raw_accepted: list[dict[str, object]],
    ctx: StageContext,
    complete: Completer,
) -> dict[str, int]:
    ensure_manifest(ctx)
    out_path = ctx.shard_dir / "paraphrases.jsonl"
    done: set[str] = read_done_ids(out_path, "goal") if out_path.exists() else set()
    # Shard on original input positions first, then drop already-recorded ids,
    # so resumed or filtered inputs never shift rows between shards.
    all_entries: list[tuple[GoalRecord, str]] = []
    for raw in raw_accepted:
        if not isinstance(raw, dict):
            raise TypeError("paraphrase input rows must be JSON objects")
        goal = normalize_goal_record(raw.get("goal"))
        request = raw.get("request", "")
        if not isinstance(request, str):
            raise TypeError(
                f"goal {goal.id}: paraphrase input needs a string 'request'"
            )
        all_entries.append((goal, request))
    mine = [
        e
        for i, e in enumerate(all_entries)
        if i % ctx.shards == ctx.shard and e[0].id not in done
    ]
    system = load_prompt("paraphraser", "base")
    ok = failed = processed = 0
    status = "complete"

    def record(row: ParaphraseResult) -> None:
        append_jsonl(out_path, row.model_dump(mode="json"))

    try:
        for pos, (goal, request) in enumerate(mine):
            payload: dict[str, object] = {
                "original_request": request,
                "goal_operations": verbalize_operations(goal),
                "num_paraphrases": NUM_PARAPHRASES,
            }
            try:
                resp = complete(
                    f"p-{ctx.shard}-{goal.id}",
                    system,
                    payload,
                    paraphrase_schema(),
                    0.9,
                    1024,
                )
                paras = select_paraphrases(resp.get("output"), goal.id)
                ok += 1
                record(ParaphraseResult(goal=goal, original=request, paraphrases=paras))
            except (ValueError, OutputError) as exc:
                failed += 1
                record(
                    ParaphraseResult(
                        goal=goal,
                        original=request,
                        paraphrases=[],
                        error=f"refusal: {exc}",
                        error_kind="refusal",
                    )
                )
            except (BudgetError, ClientError) as exc:
                failed += 1
                record(
                    ParaphraseResult(
                        goal=goal,
                        original=request,
                        paraphrases=[],
                        error=f"transport: {exc}",
                        error_kind="transport",
                    )
                )
                processed = pos + 1
                raise AbortError(f"transport: {exc}", processed) from None
            processed = pos + 1
            if (pos + 1) % 25 == 0:
                print(
                    f"[paraphrase shard {ctx.shard}] {pos + 1}/{len(mine)} ok={ok}",
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
                    "ok": ok,
                    "failed": failed,
                    "processed": processed,
                },
            ),
        )
    print(
        f"[paraphrase shard {ctx.shard}] DONE {ok}/{len(mine)} failed={failed}",
        flush=True,
    )
    return {"ok": ok, "failed": failed}
