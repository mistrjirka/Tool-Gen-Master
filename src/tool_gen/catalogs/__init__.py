"""Packaged tool catalogs for standalone `tool_gen`.

One JSON file per domain lives in ``tool_gen.catalogs.data`` (``<domain>.json``,
each a list of OpenAI-style ``{'type': 'function', 'function': {...}}`` tool
schemas). This loader reads those package resources with :mod:`importlib.resources`
and validates their shape: no fixture data, no execution logic, no dependency on
the original pilot projects.
"""

from __future__ import annotations

import json
from importlib import resources

DOMAINS = (
    # Explicit insertion order mirrors the original ALL_DOMAINS build order
    # (v2's eight domains, then the eight extended domains). Downstream Zipf
    # weights are index-sensitive, so this order is load-bearing: never sort it.
    "library",
    "commerce",
    "buildlog",
    "lab",
    "energy",
    "courses",
    "media",
    "warehouse",
    "transit",
    "hotel",
    "farm",
    "legal",
    "retail",
    "manufacturing",
    "social",
    "insurance",
)

__all__ = ["DOMAINS", "load_catalogs"]


def _read_domain(domain: str) -> list[dict[str, object]]:
    text = (resources.files(__package__) / "data" / f"{domain}.json").read_text(
        encoding="utf-8"
    )
    parsed: object = json.loads(text)
    if not isinstance(parsed, list):
        raise TypeError(f"catalog {domain!r} must be a JSON list of tools")
    tools: list[dict[str, object]] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            raise TypeError(f"catalog {domain!r} entries must be JSON objects")
        tools.append(entry)
    return tools


def _check_tool(domain: str, tool: dict[str, object]) -> str:
    if tool.get("type") != "function":
        raise ValueError(f"catalog {domain!r}: tool entry must have type 'function'")
    function = tool.get("function")
    if not isinstance(function, dict):
        raise TypeError(
            f"catalog {domain!r}: tool entry must define a 'function' object"
        )
    name = function.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"catalog {domain!r}: tool function must have a string 'name'")
    description = function.get("description")
    if not isinstance(description, str) or not description:
        raise ValueError(
            f"catalog {domain!r} tool {name!r}: 'description' must be a nonempty string"
        )
    parameters = function.get("parameters")
    if not isinstance(parameters, dict):
        raise TypeError(
            f"catalog {domain!r} tool {name!r}: 'parameters' must be "
            "a JSON Schema object"
        )
    if parameters.get("type") != "object":
        raise ValueError(
            f"catalog {domain!r} tool {name!r}: parameters schema must "
            "be a top-level object schema"
        )
    properties = parameters.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise ValueError(
            f"catalog {domain!r} tool {name!r}: parameters schema must "
            "declare nonempty properties"
        )
    required = parameters.get("required")
    if not isinstance(required, list) or not all(
        isinstance(item, str) for item in required
    ):
        raise ValueError(
            f"catalog {domain!r} tool {name!r}: parameters schema 'required' "
            "must be a list of strings"
        )
    unknown = [item for item in required if item not in properties]
    if unknown:
        raise ValueError(
            f"catalog {domain!r} tool {name!r}: 'required' names unknown "
            f"properties: {unknown}"
        )
    if parameters.get("additionalProperties") is not False:
        raise ValueError(
            f"catalog {domain!r} tool {name!r}: parameters schema must set "
            "'additionalProperties: false'"
        )
    return name


def load_catalogs() -> dict[str, list[dict[str, object]]]:
    """Load every packaged domain catalog: ``{domain: [tool, ...]}`` of raw JSON dicts.

    Each tool keeps the ``{'type': 'function', 'function': {'name', 'description',
    'parameters'}}`` shape the generation stages consume. Raises
    :class:`ValueError`/:class:`TypeError` (or :class:`FileNotFoundError`) when
    any catalog is absent, misshapen, or reuses a tool identity.
    """
    catalogs: dict[str, list[dict[str, object]]] = {}
    seen: dict[str, str] = {}
    for domain in DOMAINS:
        tools = _read_domain(domain)
        if not tools:
            raise ValueError(f"catalog {domain!r} must define at least one tool")
        names = [_check_tool(domain, tool) for tool in tools]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"catalog {domain!r} reuses tool names: {duplicates}")
        for name in names:
            if name in seen:
                raise ValueError(
                    f"tool {name!r} appears in both {seen[name]!r} and "
                    f"{domain!r}; tool identities must be unique"
                )
            seen[name] = domain
        catalogs[domain] = tools
    return catalogs
