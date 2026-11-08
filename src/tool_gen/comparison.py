"""Schema-aware call comparison; never normalize arbitrary identifiers or names.

Only declared instants (including the exact legacy instant declaration) are
canonicalized. Dates, string identifiers, arrays, nulls and omitted arguments
retain their meaning. Independent calls can reorder, but multiplicity remains.
Dependency validation/order belongs to the dependency contract, not timestamp
normalization.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import jsonschema

from tool_gen.models import ToolCall

_LEGACY_INSTANT_PATTERN = (
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:?\d{2})$"
)


@dataclass(frozen=True)
class CallComparison:
    category: Literal["match", "equivalent", "different"]
    missing: tuple[str, ...] = ()
    extra: tuple[str, ...] = ()

    @property
    def matched(self) -> bool:
        return self.category != "different"


def is_instant_schema(schema: dict[str, object]) -> bool:
    """Require explicit time semantics, not a time-looking argument name/value."""
    declared_type = schema.get("type")
    if declared_type != "string" and not (
        isinstance(declared_type, list) and "string" in declared_type
    ):
        return False
    description = schema.get("description", "")
    semantic_type = schema.get("x-semantic-type")
    if semantic_type in ("identifier", "name", "literal") or (
        isinstance(description, str) and "opaque identifier" in description.casefold()
    ):
        return False
    if schema.get("format") == "date-time" or semantic_type == "instant":
        return True
    return (
        isinstance(description, str)
        and "full instant" in description.casefold()
        and schema.get("pattern") == _LEGACY_INSTANT_PATTERN
    )


def canonical_instant(value: str) -> str:
    """Preserve the actual instant; never assume a timezone for a naive value."""
    text = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid declared instant {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"declared instant has no timezone: {value!r}")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def canonical_value(value: object, schema: dict[str, object]) -> object:
    if isinstance(value, str) and is_instant_schema(schema):
        return canonical_instant(value)
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise TypeError("object schema properties must be an object")
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            child = properties.get(key, {})
            if not isinstance(child, dict):
                raise TypeError(f"schema for {key!r} must be an object")
            result[key] = canonical_value(item, child)
        return result
    if isinstance(value, list):
        child = schema.get("items", {})
        if not isinstance(child, dict):
            # Tuple/union item schemas do not establish one semantic time type.
            return deepcopy(value)
        return [canonical_value(item, child) for item in value]
    return deepcopy(value)


def tool_schemas(tools: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    schemas: dict[str, dict[str, object]] = {}
    for tool in tools:
        function = tool.get("function")
        if not isinstance(function, dict):
            raise TypeError("tool needs a function object")
        name, parameters = function.get("name"), function.get("parameters")
        if not isinstance(name, str) or not isinstance(parameters, dict):
            raise TypeError("tool needs a string name and parameter schema")
        if name in schemas:
            raise ValueError(f"duplicate tool identity: {name}")
        jsonschema.Draft202012Validator.check_schema(parameters)
        schemas[name] = parameters
    return schemas


def validate_calls(calls: list[ToolCall], tools: list[dict[str, object]]) -> None:
    """Check actual argument values before attempting semantic normalization."""
    schemas = tool_schemas(tools)
    for call in calls:
        if call.name not in schemas:
            raise ValueError(f"tool absent from supplied catalogue: {call.name}")
        try:
            jsonschema.Draft202012Validator(schemas[call.name]).validate(call.arguments)
        except jsonschema.ValidationError as exc:
            raise ValueError(f"{call.name}: {exc.message}") from exc
        # Calendar validity and timezone requirements are semantic, not regex checks.
        canonical_value(call.arguments, schemas[call.name])


def _key(call: ToolCall, schema: dict[str, object], normalize: bool) -> str:
    arguments = canonical_value(call.arguments, schema) if normalize else call.arguments
    return json.dumps(
        {"name": call.name, "arguments": arguments},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def compare_calls(
    expected: list[ToolCall], actual: list[ToolCall], tools: list[dict[str, object]]
) -> CallComparison:
    """Compare valid independent calls, preserving all non-time values exactly."""
    validate_calls(expected, tools)
    validate_calls(actual, tools)
    schemas = tool_schemas(tools)
    raw_expected = Counter(_key(call, schemas[call.name], False) for call in expected)
    raw_actual = Counter(_key(call, schemas[call.name], False) for call in actual)
    if raw_expected == raw_actual:
        return CallComparison("match")
    normalized_expected = Counter(
        _key(call, schemas[call.name], True) for call in expected
    )
    normalized_actual = Counter(_key(call, schemas[call.name], True) for call in actual)
    if normalized_expected == normalized_actual:
        return CallComparison("equivalent")
    return CallComparison(
        "different",
        tuple((normalized_expected - normalized_actual).elements()),
        tuple((normalized_actual - normalized_expected).elements()),
    )
