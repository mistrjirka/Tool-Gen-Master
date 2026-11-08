"""Mechanical goal audit: internal consistency of supplied goals, not reader noise.

Checks every witness call against the tool catalog supplied with that goal:
unknown or duplicate tool identities, arguments that violate the tool's JSON
Schema (bad scalar types/enums/ranges checked on the actual argument values),
and calendar/time semantics via ``comparison.canonical_value``. Name-to-ID
semantics need live context, so unknown literal names are never classified as
invalid here.

``API_call_<i>`` legacy references are ungrounded until the user
dependency-contract decision (legacy whole-result vs typed field refs) lands:
they are reported explicitly as unsupported/invalid goals (generator-side, never
reader errors), without disabling generation chaining. A goal that fails here
is a generator defect; it must be fixed or dropped before writing/reading,
never silently attributed to the blind reader.
"""

from __future__ import annotations

import re
from copy import deepcopy

import jsonschema

from tool_gen.comparison import canonical_value

_CHAIN_RE = re.compile(r"^API_call_(\d+)$")

_MISSING: object = object()


def _split_refs(value: object, path: str, refs: list[tuple[str, str]]) -> object:
    """Collect ungrounded legacy refs at any nesting; scrub them from a copy.

    Returns the scrubbed value, or the ``_MISSING`` sentinel when the value
    itself is a legacy reference (callers omit such entries). Paths read like
    ``arguments.filter.memberIds[2]``."""
    if isinstance(value, str) and _CHAIN_RE.fullmatch(value):
        refs.append((path, value))
        return _MISSING
    if isinstance(value, dict):
        scrubbed: dict[str, object] = {}
        for key, item in value.items():
            cleaned = _split_refs(item, f"{path}.{key}", refs)
            if cleaned is not _MISSING:
                scrubbed[key] = cleaned
        return scrubbed
    if isinstance(value, list):
        cleaned_items: list[object] = []
        for index, item in enumerate(value):
            cleaned = _split_refs(item, f"{path}[{index}]", refs)
            if cleaned is not _MISSING:
                cleaned_items.append(cleaned)
        return cleaned_items
    return value


def audit_goal(goal: dict[str, object]) -> list[str]:
    problems: list[str] = []
    tools = goal.get("tools")
    witness = goal.get("witness", [])
    if not isinstance(tools, list):
        return [f"goal {goal.get('id')}: 'tools' catalog is not a list"]
    if not isinstance(witness, list):
        return [f"goal {goal.get('id')}: 'witness' is not a list"]
    schemas: dict[str, dict[str, object]] = {}
    for entry in tools:
        if not isinstance(entry, dict):
            problems.append(f"goal {goal.get('id')}: catalog entry is not an object")
            continue
        function = entry.get("function")
        if not isinstance(function, dict):
            problems.append(f"goal {goal.get('id')}: catalog entry lacks 'function'")
            continue
        name = function.get("name")
        parameters = function.get("parameters")
        if isinstance(name, str) and isinstance(parameters, dict):
            try:
                jsonschema.Draft202012Validator.check_schema(parameters)
            except jsonschema.SchemaError as exc:
                problems.append(
                    f"goal {goal.get('id')}: invalid parameter schema for {name!r}: "
                    + exc.message
                )
                continue
            if name in schemas:
                problems.append(
                    f"goal {goal.get('id')}: duplicate tool identity {name!r}"
                    + " in supplied catalogue"
                )
            else:
                schemas[name] = deepcopy(parameters)
        else:
            problems.append(
                f"goal {goal.get('id')}: catalog entry lacks a string name"
                + " or parameter schema"
            )
    for index, call in enumerate(witness):
        if not isinstance(call, dict):
            problems.append(f"goal {goal.get('id')} call {index}: not an object")
            continue
        name = call.get("name")
        args = call.get("arguments")
        if not isinstance(name, str) or name not in schemas:
            problems.append(
                f"goal {goal.get('id')} call {index}: unknown tool {name!r}"
            )
            continue
        if not isinstance(args, dict):
            problems.append(
                f"goal {goal.get('id')} call {index}: arguments not an object"
            )
            continue
        found_refs: list[tuple[str, str]] = []
        checkable = _split_refs(args, "arguments", found_refs)
        assert isinstance(checkable, dict)
        for path, value in found_refs:
            problems.append(
                f"goal {goal.get('id')} call {index}: unsupported legacy"
                + f" reference {value!r} at {path} (dependency contract"
                + " pending; invalid goal, not a reader error)"
            )
        try:
            jsonschema.Draft202012Validator(schemas[name]).validate(checkable)
        except jsonschema.ValidationError as exc:
            trail = "/".join(str(p) for p in list(exc.absolute_path)[:4]) or "root"
            problems.append(
                f"goal {goal.get('id')} call {index} ({name}): schema violation "
                + f"at {trail}: {exc.message}"
            )
            continue
        try:
            canonical_value(checkable, schemas[name])
        except (ValueError, TypeError) as exc:
            problems.append(
                f"goal {goal.get('id')} call {index} ({name}): invalid"
                + f" calendar/time semantics: {exc}"
            )
    if goal.get("no_call") and witness:
        problems.append(f"goal {goal.get('id')}: no_call goal carries witness calls")
    if not goal.get("no_call") and not witness:
        problems.append(
            f"goal {goal.get('id')}: call goal carries an empty witness;"
            + " supported no_call=false goals need a nonempty witness"
        )
    return problems


def audit_goals(goals: list[dict[str, object]]) -> dict[str, object]:
    """Summarize internal consistency over the supplied goals only."""
    families: set[str] = set()
    supplied_tools: set[str] = set()
    for goal in goals:
        if not isinstance(goal, dict):
            continue
        family = goal.get("family_id")
        if isinstance(family, str):
            families.add(family)
        tools = goal.get("tools", goal.get("catalog", []))
        if isinstance(tools, list):
            for entry in tools:
                if not isinstance(entry, dict):
                    continue
                function = entry.get("function")
                name = function.get("name") if isinstance(function, dict) else None
                if isinstance(name, str):
                    supplied_tools.add(name)
    all_problems: list[str] = []
    bad_goals = 0
    for goal in goals:
        if not isinstance(goal, dict):
            all_problems.append("goal record must be a JSON object")
            bad_goals += 1
            continue
        found = audit_goal(goal)
        if found:
            bad_goals += 1
            all_problems.extend(found)
    return {
        "goals": len(goals),
        "families": sorted(families),
        "tools": sorted(supplied_tools),
        "bad_goals": bad_goals,
        "problems": all_problems,
    }
