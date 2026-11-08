"""Shared durable stage storage: strict JSONL, resume manifests, input pins.

Every paid stage owns one shard directory (``<root>/shard-<N>``) holding the
budget ledger, the stage ``manifest.json`` and the stage output rows. A manifest
pins the exact input content, prompt text and config a run started with; a
resume with any changed pin is refused instead of silently skipping or mixing
goals by id.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


class StageError(Exception):
    """A stage cannot start, resume or finish honestly."""


class MalformedLogError(StageError):
    """An input or resume log contains a malformed line; never silently skipped."""


class ManifestMismatchError(StageError):
    """The existing manifest pins different inputs/prompts/config; use a fresh root."""


class NoInputFilesError(StageError):
    """A file-or-root input matched nothing."""


class DuplicateIdError(StageError):
    """Duplicate ids in one stage input."""


class ShardRangeError(StageError):
    """Shard index/count out of range."""


class AbortError(StageError):
    """The run stopped on transport/budget failure after persisting evidence."""

    def __init__(self, reason: str, processed: int) -> None:
        super().__init__(reason)
        self.processed = processed


def strict_loads(text: str, what: str) -> object:
    """Strict JSON: no NaN/Infinity/-Infinity literals."""

    def _reject(value: str) -> object:
        raise MalformedLogError(f"{what} uses non-standard JSON literal {value}")

    try:
        return json.loads(text, parse_constant=_reject)
    except json.JSONDecodeError as exc:
        raise MalformedLogError(f"{what} is not valid JSON: {exc}") from None


def strict_dumps(record: Mapping[str, object]) -> str:
    try:
        return json.dumps(record, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise StageError(f"record is not strict JSON: {exc}") from None


def canonical_json(value: object) -> str:
    """Canonical JSON for content fingerprints: sorted keys, compact, strict."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (ValueError, TypeError) as exc:
        raise StageError(f"value is not strict JSON: {exc}") from None


def content_fingerprint(content: Mapping[str, object]) -> str:
    """Bind a verification to exact source content (never sent to any model)."""
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class InputFile:
    path: str
    sha256: str


@dataclass(frozen=True)
class StageContext:
    stage: str
    shard_dir: Path
    shard: int
    shards: int
    prompt_text: str
    config: dict[str, str] = field(default_factory=dict)
    inputs: list[InputFile] = field(default_factory=list)


def validate_shard_args(shard: int, shards: int) -> None:
    if shards < 1:
        raise ShardRangeError(f"--shards must be >= 1, got {shards}")
    if not 0 <= shard < shards:
        raise ShardRangeError(f"--shard {shard} out of range for --shards {shards}")


def ensure_unique_ids(ids: list[str], what: str) -> None:
    seen: set[str] = set()
    dupes: list[str] = []
    for item in ids:
        if item in seen and item not in dupes:
            dupes.append(item)
        seen.add(item)
    if dupes:
        raise DuplicateIdError(f"{what} has duplicate ids: {dupes[:5]}")


def collect_stage_files(path: Path, filename: str) -> list[Path]:
    """Accept a results file or a root holding shard output files (recursive)."""
    if path.is_file():
        return [path]
    if path.is_dir():
        found = sorted(path.rglob(filename))
        if not found:
            raise NoInputFilesError(
                f"{path} holds no {filename} files; pass a results file or a stage root containing shard output"
            )
        return found
    raise NoInputFilesError(f"input {path} is neither a file nor a directory")


def read_jsonl_strict(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            parsed = strict_loads(line, f"{path}:{lineno}")
            if not isinstance(parsed, dict):
                raise MalformedLogError(f"{path}:{lineno} is not a JSON object")
            rows.append(parsed)
    return rows


def append_jsonl(path: Path, record: Mapping[str, object]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(strict_dumps(record) + "\n")
        fh.flush()


def _manifest_path(ctx: StageContext) -> Path:
    return ctx.shard_dir / "manifest.json"


def _manifest_payload(
    ctx: StageContext, status: str, extra: Mapping[str, object]
) -> dict[str, object]:
    payload: dict[str, object] = {
        "stage": ctx.stage,
        "version": 1,
        "shard": ctx.shard,
        "shards": ctx.shards,
        "inputs": [{"path": f.path, "sha256": f.sha256} for f in ctx.inputs],
        "prompt_sha256": hash_text(ctx.prompt_text),
        "config": dict(ctx.config),
        "status": status,
    }
    payload.update(extra)
    return payload


def ensure_manifest(ctx: StageContext) -> None:
    """Create the manifest, or refuse a resume whose pins changed."""
    ctx.shard_dir.mkdir(parents=True, exist_ok=True)
    path = _manifest_path(ctx)
    if not path.exists():
        path.write_text(
            strict_dumps(_manifest_payload(ctx, "running", {})) + "\n", encoding="utf-8"
        )
        return
    raw = strict_loads(path.read_text(encoding="utf-8"), str(path))
    if not isinstance(raw, dict):
        raise MalformedLogError(f"{path} manifest is not a JSON object")
    expected = _manifest_payload(ctx, "running", {})
    for key in ("stage", "shard", "shards", "inputs", "prompt_sha256", "config"):
        if raw.get(key) != expected[key]:
            raise ManifestMismatchError(
                f"{path} pins a different {key}; refusing resume with changed inputs/prompts/config/shards (start a fresh output root instead)"
            )


def finalize_manifest(
    ctx: StageContext, status: str, extra: Mapping[str, object]
) -> None:
    _manifest_path(ctx).write_text(
        strict_dumps(_manifest_payload(ctx, status, extra)) + "\n", encoding="utf-8"
    )


def cumulative_counts(ctx: StageContext, current: dict[str, int]) -> dict[str, object]:
    """Merge current-run counts with the prior manifest so resumes accumulate
    instead of a no-op resume overwriting history with zeros."""
    merged: dict[str, object] = dict(current)
    path = ctx.shard_dir / "manifest.json"
    if not path.exists():
        return merged
    try:
        raw = strict_loads(path.read_text(encoding="utf-8"), str(path))
    except StageError:
        return merged
    if not isinstance(raw, dict):
        return merged
    for key, value in current.items():
        prior = raw.get(key)
        if isinstance(prior, int) and not isinstance(prior, bool):
            merged[key] = prior + value
    return merged


def read_done_ids(path: Path, kind: Literal["goal", "row"]) -> set[str]:
    """Ids already recorded in a shard output file (only read after manifest check)."""
    done: set[str] = set()
    for row in read_jsonl_strict(path):
        if kind == "goal":
            goal = row.get("goal")
            goal_id = goal.get("id") if isinstance(goal, dict) else None
            if isinstance(goal_id, str):
                done.add(goal_id)
        else:
            row_id = row.get("id")
            if isinstance(row_id, str):
                done.add(row_id)
    return done
