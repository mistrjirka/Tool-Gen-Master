"""Mechanical goal audit: internal consistency of supplied goals, not reader noise.

Checks every witness call against the tool catalog supplied with that goal:
unknown tool names, arguments that violate the tool's JSON Schema (bad
enums/types), and ``API_call_<i>`` forward references (index out of range for
the calls seen so far). Any tool domain works: the audit never restricts
goals to a bundled catalog, so generic tool data passes through unchanged.
A goal that fails here is a generator defect; it must be fixed or dropped
before writing/reading, never silently attributed to the blind reader.
"""

from __future__ import annotations

import re
from copy import deepcopy

import jsonschema

_CHAIN_RE = re.compile(r"^API_call_(\d+)$")


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
            schemas[name] = deepcopy(parameters)
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
        for value in args.values():
            if isinstance(value, str):
                m = _CHAIN_RE.fullmatch(value)
                if m and int(m.group(1)) >= index:
                    problems.append(
                        f"goal {goal.get('id')} call {index}: forward reference {value!r} "
                        + "to a call that does not precede it"
                    )
        checkable = {
            k: v
            for k, v in args.items()
            if not (isinstance(v, str) and _CHAIN_RE.fullmatch(v))
        }
        try:
            jsonschema.Draft202012Validator(schemas[name]).validate(checkable)
        except jsonschema.ValidationError as exc:
            trail = "/".join(str(p) for p in list(exc.absolute_path)[:4]) or "root"
            problems.append(
                f"goal {goal.get('id')} call {index} ({name}): schema violation "
                + f"at {trail}: {exc.message}"
            )
    if goal.get("no_call") and witness:
        problems.append(f"goal {goal.get('id')}: no_call goal carries witness calls")
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
