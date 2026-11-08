"""Offline triage of stored reader verdicts: classify, never re-judge.

Joins writer entries to reader result rows by goal id, re-checks any present
source fingerprint against the writer entry, then runs the SAME goal
preflight the live reader uses (alias normalization, mechanical audit) on the
source before interpreting the STORED reading: malformed sources,
unsupported chained dependencies, and missing-tool targets are explicit
``invalid_goal`` detail, never reader errors. Stored calls are re-evaluated
through the same literal-call comparator; opaque grounding is re-checked on
stored canonical calls, so deterministic false-example IDs cannot earn
offline-match labels either. Both the original failure outputs
(``argument_presence``, ``status``, ``reader_calls``) and the new attempt
history are understood: redundant legacy presence flags are ignored, never
synthesized, and no missing requested values are ever guessed. Genuinely
absent stored status/calls are ``insufficient_evidence``, not automatic
model fault.

A triage report is NOT a fresh reader verdict: rows carry no ``accepted``
flag and no ``source_fingerprint``, so they can never serve as export proofs.
``replay_ids`` names the unresolved, invalid-goal, and legacy non-accepted
ids worth one more blind pass in a fresh output root: an ``invalid_goal``
label is only trusted when its source fingerprint still matches, and
preflight cheaply re-catches goals that are still invalid. ``triage_summary``
reports source/reader/matched coverage so union counts stay transparent.
"""

from __future__ import annotations

from tool_gen.comparison import compare_calls, validate_calls
from tool_gen.export import fingerprint_of
from tool_gen.models import ToolCall, normalize_goal_record
from tool_gen.reader import check_opaque_grounding
from tool_gen.store import ensure_unique_ids
from tool_gen.validate import audit_goal

MATCHED = ("match", "equivalent")


def _normalize_calls(raw: object) -> list[dict[str, object]] | None:
    """Name + arguments only; legacy presence flags are ignored, never read."""
    if not isinstance(raw, list):
        return None
    calls: list[dict[str, object]] = []
    for call in raw:
        if not isinstance(call, dict):
            return None
        name = call.get("name")
        arguments = call.get("arguments")
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return None
        calls.append({"name": name, "arguments": dict(arguments)})
    return calls


def _extract_reading(
    row: dict[str, object],
) -> tuple[str, list[dict[str, object]] | None]:
    """Stored (status, calls): final attempt first, legacy row fields after."""
    attempts = row.get("attempts")
    if isinstance(attempts, list) and attempts:
        last = attempts[-1]
        if isinstance(last, dict):
            status = last.get("status")
            calls = _normalize_calls(last.get("calls"))
            if isinstance(status, str) and status and calls is not None:
                return status, calls
    status = row.get("status")
    calls = _normalize_calls(row.get("reader_calls"))
    if isinstance(status, str) and status and calls is not None:
        return status, calls
    return "", None


def _report(
    goal_id: str,
    classification: str,
    fingerprint: str,
    detail: str,
    comparison: str | None = None,
    false_ambiguity: bool = False,
) -> dict[str, object]:
    return {
        "id": goal_id,
        "category": classification,
        "fingerprint": fingerprint,
        "comparison": comparison,
        "false_ambiguity_candidate": false_ambiguity,
        "detail": detail,
    }


def triage_entries(
    writer_entries: list[dict[str, object]],
    reader_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Classify stored verdicts per goal id. Pure offline analysis."""
    writer_index: dict[str, dict[str, object]] = {}
    source_ids: list[str] = []
    for entry in writer_entries:
        if not isinstance(entry, dict):
            continue
        goal = entry.get("goal")
        goal_id = goal.get("id") if isinstance(goal, dict) else None
        if isinstance(goal_id, str):
            source_ids.append(goal_id)
    ensure_unique_ids(source_ids, "triage writer entries")
    for entry in writer_entries:
        if not isinstance(entry, dict):
            continue
        goal = entry.get("goal")
        goal_id = goal.get("id") if isinstance(goal, dict) else None
        if isinstance(goal_id, str):
            writer_index[goal_id] = entry
    reader_index: dict[str, dict[str, object]] = {}
    reader_ids: list[str] = []
    for row in reader_results:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        if isinstance(row_id, str):
            reader_ids.append(row_id)
    ensure_unique_ids(reader_ids, "triage reader results")
    for row in reader_results:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        if isinstance(row_id, str):
            reader_index[row_id] = row

    reports: list[dict[str, object]] = []
    for goal_id in sorted(set(writer_index) | set(reader_index)):
        maybe_entry = writer_index.get(goal_id)
        maybe_row = reader_index.get(goal_id)
        if maybe_row is None:
            reports.append(
                _report(goal_id, "missing_result", "unchecked", "no reader row")
            )
            continue
        entry_row: dict[str, object] = maybe_row
        source_entry: dict[str, object] | None = maybe_entry
        if source_entry is None:
            reports.append(
                _report(goal_id, "missing_source", "unchecked", "no writer entry")
            )
            continue
        goal = source_entry.get("goal")
        request = source_entry.get("request")
        try:
            expected_fp = (
                fingerprint_of(goal, request)
                if isinstance(goal, dict) and isinstance(request, str)
                else None
            )
        except (TypeError, ValueError):
            expected_fp = None
        stored_fp = entry_row.get("source_fingerprint")
        if not isinstance(stored_fp, str) or not stored_fp:
            fp_status = "legacy_unbound"
        elif expected_fp is None:
            fp_status = "unchecked"
        elif stored_fp == expected_fp:
            fp_status = "match"
        else:
            fp_status = "mismatch"
        if fp_status == "mismatch":
            # Fingerprint first: a stale verdict never overrides current source
            # content, so a repaired input is re-read rather than re-tagged
            # from an old label — including an old invalid_goal verdict.
            reports.append(
                _report(
                    goal_id,
                    "stale_content",
                    fp_status,
                    "stored fingerprint does not match the writer entry; "
                    "the reading belongs to different content",
                )
            )
            continue
        # Re-audit current source after checking its binding. Historical labels
        # cannot override a repaired source or a corrected audit implementation.
        if not isinstance(request, str):
            reports.append(
                _report(
                    goal_id,
                    "invalid_goal",
                    fp_status,
                    "writer entry lacks a string 'request'; not guessed",
                )
            )
            continue
        try:
            source = normalize_goal_record(goal)
        except (TypeError, ValueError) as exc:
            reports.append(
                _report(
                    goal_id,
                    "invalid_goal",
                    fp_status,
                    f"malformed source goal: {exc}"[:300],
                )
            )
            continue
        tools = list(source.tools)
        witness = [
            ToolCall(name=c.name, arguments=dict(c.arguments)) for c in source.witness
        ]
        context = dict(source.context)
        problems = audit_goal(
            {
                "id": goal_id,
                "tools": tools,
                "witness": [
                    {"name": c.name, "arguments": dict(c.arguments)} for c in witness
                ],
                "no_call": source.no_call,
            }
        )
        if problems:
            reports.append(
                _report(
                    goal_id,
                    "invalid_goal",
                    fp_status,
                    "; ".join(problems)[:300],
                )
            )
            continue
        # Unsupported legacy references already fail source preflight above
        # under the recursive audit; all unsupported refs are invalid_goal.
        if entry_row.get("outcome") == "invalid_goal" or (
            entry_row.get("error_kind") == "invalid_goal"
            and entry_row.get("outcome") != "accepted"
        ):
            reports.append(
                _report(
                    goal_id,
                    "insufficient_evidence",
                    fp_status,
                    "current source passes audit, but the previous invalid-goal "
                    "record has no reader interpretation; replay is required",
                )
            )
            continue
        status, stored_calls = _extract_reading(entry_row)
        if stored_calls is None or status not in ("clear", "ambiguous", "unsupported"):
            # Explicit producer evidence of a model/contract failure is usable
            # even when no canonical calls survived parsing. A transport error
            # or incomplete historical row does not establish model fault.
            error_kind = entry_row.get("error_kind")
            known_model_failure = error_kind in ("model_output", "reader_contract")
            reports.append(
                _report(
                    goal_id,
                    "reader_error" if known_model_failure else "insufficient_evidence",
                    fp_status,
                    f"no usable stored reading (status={status!r}); "
                    f"{error_kind or ''} {entry_row.get('reason', '')}"[:300],
                )
            )
            continue
        actual: list[ToolCall] = [
            ToolCall(name=c["name"], arguments=dict(c["arguments"]))
            for c in stored_calls
            if isinstance(c["name"], str) and isinstance(c["arguments"], dict)
        ]
        if len(actual) != len(stored_calls):
            reports.append(
                _report(
                    goal_id,
                    "insufficient_evidence",
                    fp_status,
                    "stored call malformed; not reconstructed or guessed",
                )
            )
            continue
        try:
            validate_calls(actual, tools)
        except ValueError as exc:
            reports.append(_report(goal_id, "reader_error", fp_status, str(exc)[:300]))
            continue
        try:
            compared = compare_calls(witness, actual, tools)
        except ValueError as exc:
            # The stored actual side already validated: the failure is
            # source-side (catalog or witness values), an invalid goal.
            reports.append(
                _report(
                    goal_id,
                    "invalid_goal",
                    fp_status,
                    f"source comparison failure: {exc}"[:300],
                )
            )
            continue
        grounded = True
        grounding_note = ""
        if compared.category in MATCHED:
            try:
                check_opaque_grounding(actual, tools, request, context)
            except ValueError as exc:
                grounded = False
                grounding_note = f" stored opaque value ungrounded: {exc}"[:200]
        if compared.category in MATCHED and not grounded:
            reports.append(
                _report(
                    goal_id,
                    "reader_error",
                    fp_status,
                    f"stored reading claims {compared.category} but{grounding_note}",
                    comparison=compared.category,
                )
            )
            continue
        no_call = source.no_call
        expected_status = "unsupported" if no_call else "clear"
        status_note = (
            ""
            if status == expected_status
            else f" status {status!r} differs from expected {expected_status!r};"
        )
        if status == "ambiguous" and status != expected_status:
            reports.append(
                _report(
                    goal_id,
                    "ambiguous",
                    fp_status,
                    f"model declared ambiguous; stored calls {compared.category};{grounding_note}".strip(),
                    comparison=compared.category,
                    false_ambiguity=compared.category in MATCHED and grounded,
                )
            )
            continue
        reports.append(
            _report(
                goal_id,
                compared.category,
                fp_status,
                f"stored {status} reading {compared.category};{status_note}".strip(),
                comparison=compared.category,
            )
        )
    return reports


def replay_ids(results: list[dict[str, object]]) -> set[str]:
    """Ids worth one more blind pass in a fresh output root.

    Unresolved, invalid-goal, and legacy non-accepted verdicts are all
    included: the operator is expected to supply repaired source, and
    preflight cheaply re-catches goals that are still invalid. Accepted
    proofs stay untouched and are never replayed.
    """
    ids: set[str] = set()
    for row in results:
        if not isinstance(row, dict):
            continue
        goal_id = row.get("id")
        if not isinstance(goal_id, str):
            continue
        outcome = row.get("outcome")
        if outcome == "accepted":
            continue
        if outcome in ("unresolved", "invalid_goal"):
            ids.add(goal_id)
            continue
        if row.get("accepted") is True:
            continue
        ids.add(goal_id)
    return ids


def triage_summary(reports: list[dict[str, object]]) -> dict[str, int]:
    """Source/reader/matched coverage over triage reports.

    ``matched`` counts reports joined on both sides (every category except
    ``missing_result`` and ``missing_source``); per-category counts travel
    alongside so union totals stay transparent instead of misleading.
    """
    counts: dict[str, int] = {}
    for report in reports:
        category = report.get("category")
        key = category if isinstance(category, str) else "unknown"
        counts[key] = counts.get(key, 0) + 1
    summary: dict[str, int] = {
        "reports": len(reports),
        "matched": len(reports)
        - counts.get("missing_result", 0)
        - counts.get("missing_source", 0),
    }
    for key in sorted(counts):
        summary[key] = counts[key]
    return summary
