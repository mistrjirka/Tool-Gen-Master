"""Export stage: convert accepted goals (and paraphrases) to SFT rows.

The function-call envelope is preserved exactly: assistant messages carry
``tool_calls`` with deep-copied witness calls, and the no-call literal is the
exact string ``'<no_call/>\\n'``. Group ids and the ``train`` split travel with
each row for provenance.

Reader verification is opt-in: ``--verification`` accepts a reader results
file or a reader stage root. A writer row is exported as verified only when
a reader verdict carries the matching content fingerprint (id + request +
tools + full visible context + witness/no_call). Rows whose goal id has no
accepted proof are skipped and counted, without aborting the valid subset;
a row whose id is accepted but whose fingerprint differs is stale content
and aborts with an explicit error. Old verdict rows without content
provenance stay inspectable but can never match.

Paraphrase strings are rewritten text the reader never saw: verifying their
parent goals is recorded as parent-verified with paraphrases unverified, never
as reader-verified.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tool_gen.models import normalize_goal_record
from tool_gen.store import (
    StageError,
    canonical_json,
    collect_stage_files,
    content_fingerprint,
    read_jsonl_strict,
    strict_dumps,
)

NO_CALL_LITERAL = "<no_call/>\n"
PARAPHRASE_VERIFICATION = "parent-verified-paraphrases-unverified"


def to_sft_row(
    goal: dict[str, object], request: str, augmentation: str = "none"
) -> dict[str, object]:
    parsed = normalize_goal_record(goal)
    witness = [{"name": c.name, "arguments": dict(c.arguments)} for c in parsed.witness]
    tools = goal.get("tools", goal.get("catalog", []))
    if not isinstance(tools, list):
        raise TypeError(f"goal {parsed.id}: catalog must be a list of tool objects")
    messages: list[dict[str, object]] = []
    if parsed.context:
        # Nonempty visible context travels in a system message so
        # name-resolved tasks stay specified. Empty context (legacy) skips
        # this message, keeping the envelope byte-compatible.
        messages.append(
            {
                "role": "system",
                "content": "Known context (JSON): "
                + canonical_json(dict(parsed.context)),
            }
        )
    messages.append({"role": "user", "content": request})
    if witness:
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"type": "function", "function": deepcopy(call)} for call in witness
                ],
            }
        )
    else:
        messages.append({"role": "assistant", "content": NO_CALL_LITERAL})
    return {
        "messages": messages,
        "tools": deepcopy(tools),
        "source": "coherent_v3",
        "split": parsed.split,
        "augmentation": augmentation,
        "parent_group": parsed.group_id,
        "provenance": "coherent_v3_bulk",
        "request": request,
        "length": 0,
        "id": parsed.id,
    }


def fingerprint_of(goal: dict[str, object], request: str) -> str:
    """Recompute the content fingerprint a reader verdict must carry to prove this row."""
    parsed = normalize_goal_record(goal)
    tools = goal.get("tools", goal.get("catalog", []))
    return content_fingerprint(
        {
            "id": parsed.id,
            "request": request,
            "tools": tools if isinstance(tools, list) else [],
            "context": dict(parsed.context),
            "witness": [
                {"name": c.name, "arguments": dict(c.arguments)} for c in parsed.witness
            ],
            "no_call": parsed.no_call,
        }
    )


def _verification_files(path: Path) -> list[Path]:
    """Reader verdict files: new per-shard results.jsonl or pilot results-shard*.jsonl."""
    if path.is_file():
        return [path]
    if path.is_dir():
        found = sorted(path.rglob("results.jsonl")) + sorted(
            path.glob("results-shard*.jsonl")
        )
        if not found:
            raise StageError(
                f"{path} holds no reader results files; pass a results file or "
                "a reader stage root"
            )
        return found
    raise StageError(f"input {path} is neither a file nor a directory")


def load_verified_proofs(path: Path) -> tuple[dict[str, str], int, int]:
    """Content fingerprints with accepted reader verdicts, mapped to goal ids.

    Returns ``(proofs, accepted_rows, accepted_without_proof)``. Old verdict
    rows without ``source_fingerprint`` stay readable elsewhere but
    contribute no proof here; the caller reports them explicitly instead of
    silently certifying stale ids.
    """
    proofs: dict[str, str] = {}
    accepted_rows = accepted_without_proof = 0
    for found in _verification_files(path):
        for row in read_jsonl_strict(found):
            if row.get("accepted") is True:
                accepted_rows += 1
                fingerprint = row.get("source_fingerprint")
                row_id = row.get("id")
                if (
                    isinstance(fingerprint, str)
                    and fingerprint
                    and isinstance(row_id, str)
                ):
                    proofs[fingerprint] = row_id
                else:
                    accepted_without_proof += 1
    return proofs, accepted_rows, accepted_without_proof


def _split_verified(
    candidates: list[tuple[dict[str, object], str]],
    proofs: dict[str, str],
) -> tuple[list[tuple[dict[str, object], str]], int]:
    """Keep candidates with matching content proof; skip ids with no proof.

    A candidate whose goal id has accepted proof(s) but whose fingerprint
    matches none of them is stale content and aborts the export: the valid
    subset is never silently certified alongside it. Ids with no accepted
    proof at all are skipped and counted, never aborting the valid subset.
    """
    by_id: dict[str, set[str]] = {}
    for fingerprint, goal_id in proofs.items():
        by_id.setdefault(goal_id, set()).add(fingerprint)
    kept: list[tuple[dict[str, object], str]] = []
    skipped = 0
    for goal, request in candidates:
        candidate_id = goal.get("id")
        if not isinstance(candidate_id, str) or candidate_id not in by_id:
            skipped += 1
            continue
        if fingerprint_of(goal, request) not in by_id[candidate_id]:
            raise StageError(
                f"goal {candidate_id}: accepted reader proof exists but the content "
                "fingerprint differs (id+request+tools+context+witness/no_call); "
                "refusing to certify stale content as verified"
            )
        kept.append((goal, request))
    return kept, skipped


def export_writer_results(
    results_path: Path,
    out_path: Path,
    verification: dict[str, str] | None = None,
) -> dict[str, object]:
    candidates: list[tuple[dict[str, object], str]] = []
    for found in collect_stage_files(results_path, "results.jsonl"):
        for entry in read_jsonl_strict(found):
            if entry.get("decision") != "accept" or not entry.get("request"):
                continue
            goal = entry.get("goal")
            if not isinstance(goal, dict):
                raise TypeError("writer result rows need an object 'goal'")
            request = entry.get("request")
            if not isinstance(request, str):
                raise TypeError(
                    f"goal {goal.get('id')}: writer result needs a string 'request'"
                )
            candidates.append((goal, request))
    skipped_without_accepted_proof = 0
    if verification is not None:
        candidates, skipped_without_accepted_proof = _split_verified(
            candidates, verification
        )
    rows = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as dst:
        for goal, request in candidates:
            dst.write(strict_dumps(to_sft_row(goal, request)) + "\n")
            rows += 1
    manifest = {
        "status": "coherent_v3_bulk",
        "rows": rows,
        "source": "tool_composition_v3",
        "verification": "reader-verified" if verification is not None else "none",
        "skipped_without_accepted_proof": skipped_without_accepted_proof,
    }
    (out_path.parent / "manifest.json").write_text(
        strict_dumps(manifest) + "\n", encoding="utf-8"
    )
    return {
        "rows": rows,
        "verification": manifest["verification"],
        "skipped_without_accepted_proof": skipped_without_accepted_proof,
    }


def export_paraphrases(
    paraphrases_path: Path,
    out_path: Path,
    verification: dict[str, str] | None = None,
) -> dict[str, object]:
    candidates: list[tuple[dict[str, object], str, str, str]] = []
    for found in collect_stage_files(paraphrases_path, "paraphrases.jsonl"):
        for entry in read_jsonl_strict(found):
            goal = entry.get("goal")
            if not isinstance(goal, dict):
                raise TypeError("paraphrase rows need an object 'goal'")
            original = entry.get("original", "")
            if not isinstance(original, str):
                raise TypeError(
                    f"goal {goal.get('id')}: paraphrase needs a string 'original'"
                )
            paras = entry.get("paraphrases", [])
            if not isinstance(paras, list) or not paras:
                continue
            for para in paras:
                if not isinstance(para, dict) or not para.get("text"):
                    continue
                register = para.get("register", "")
                if not isinstance(register, str):
                    raise TypeError(
                        f"goal {goal.get('id')}: paraphrase needs a string 'register'"
                    )
                text = para.get("text")
                if not isinstance(text, str):
                    raise TypeError(
                        f"goal {goal.get('id')}: paraphrase needs a string 'text'"
                    )
                candidates.append((goal, original, text, register))
    skipped_without_accepted_proof = 0
    if verification is not None:
        # One proof check per parent goal: all paraphrase strings of a goal
        # share its parent fingerprint.
        parents: list[tuple[dict[str, object], str]] = []
        seen_ids: set[str] = set()
        for goal, original, _text, _register in candidates:
            goal_id = goal.get("id")
            if isinstance(goal_id, str) and goal_id not in seen_ids:
                seen_ids.add(goal_id)
                parents.append((goal, original))
        kept_parents, skipped_without_accepted_proof = _split_verified(
            parents, verification
        )
        kept_keys = {fingerprint_of(goal, original) for goal, original in kept_parents}
        candidates = [
            (goal, original, text, register)
            for goal, original, text, register in candidates
            if fingerprint_of(goal, original) in kept_keys
        ]
    rows = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as dst:
        for goal, _original, text, register in candidates:
            dst.write(
                strict_dumps(
                    to_sft_row(goal, text, augmentation=f"paraphrase:{register}")
                )
                + "\n"
            )
            rows += 1
    manifest = {
        "status": "coherent_v3_bulk",
        "rows": rows,
        "source": "tool_composition_v3",
        "verification": PARAPHRASE_VERIFICATION if verification is not None else "none",
        "skipped_without_accepted_proof": skipped_without_accepted_proof,
    }
    (out_path.parent / "manifest.json").write_text(
        strict_dumps(manifest) + "\n", encoding="utf-8"
    )
    return {
        "rows": rows,
        "verification": manifest["verification"],
        "skipped_without_accepted_proof": skipped_without_accepted_proof,
    }
