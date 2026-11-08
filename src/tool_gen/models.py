"""Shared checked record boundaries for the tool_gen pipeline (Pydantic v2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ToolCall(StrictModel):
    name: str = Field(min_length=1)
    arguments: dict[str, object]


class GoalRecord(StrictModel):
    """One seeded goal as written by ``tool-gen goals`` (JSONL boundary)."""

    id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    split: str = "train"
    family_id: str = Field(min_length=1)
    style: str = Field(min_length=1)
    no_call: bool = False
    context_mode: str = "api_only"
    context: dict[str, JsonValue] = Field(default_factory=dict)
    tools: list[dict[str, object]] = Field(min_length=1)
    witness: list[ToolCall] = Field(default_factory=list)
    fixtures: dict[str, object] = Field(default_factory=dict)
    observations: list[object] = Field(default_factory=list)


class WriterResult(StrictModel):
    goal: GoalRecord
    request: str = ""
    decision: Literal["accept", "rejected"] = "accept"
    reason: str = ""
    error_kind: str = ""


class ReaderResult(StrictModel):
    id: str = Field(min_length=1)
    accepted: bool
    reason: str = ""
    status: str = ""
    witness: list[ToolCall] = Field(default_factory=list)
    reader_calls: list[ToolCall] = Field(default_factory=list)
    reader_reason: str = ""
    error_kind: str = ""
    source_fingerprint: str = ""


class ParaphraseResult(StrictModel):
    goal: GoalRecord
    original: str = ""
    paraphrases: list[dict[str, str]] = Field(default_factory=list)
    error: str = ""
    error_kind: str = ""


def normalize_goal_record(raw: object) -> GoalRecord:
    """Validate an external goal mapping into GoalRecord.

    Accepts the current ``witness``/``tools`` keys and the legacy pilot
    ``calls``/``catalog`` aliases (current keys win when both are present).
    Raises ValueError with the goal id on any boundary violation.
    """
    if not isinstance(raw, dict):
        raise TypeError("goal record must be a JSON object")
    goal_id = raw.get("id")
    label = goal_id if isinstance(goal_id, str) else "<missing id>"
    data = dict(raw)
    witness = data.get("witness", data.get("calls"))
    if witness is not None:
        data["witness"] = witness
        data.pop("calls", None)
    tools = data.get("tools", data.get("catalog"))
    if tools is not None:
        data["tools"] = tools
        data.pop("catalog", None)
    # Full visible context is preserved verbatim (no truncation, no whitelist):
    # every name-to-ID mapping and record stays in the object both stages see.
    # Legacy top-level names/entity_directory merge into it so nothing is lost.
    if "context" in data or "names" in data or "entity_directory" in data:
        merged: dict[str, object] = {}
        context = data.get("context")
        if context is None:
            pass
        elif isinstance(context, dict):
            merged.update(context)
        else:
            raise TypeError(f"goal {label}: 'context' must be a JSON object")
        for key in ("names", "entity_directory"):
            if key in data:
                merged[key] = data[key]
        data["context"] = merged
        data.pop("names", None)
        data.pop("entity_directory", None)
    try:
        return GoalRecord.model_validate(data)
    except ValidationError as exc:
        raise ValueError(
            f"goal {label} fails validation: {exc.errors()[0]['msg']}"
        ) from None
