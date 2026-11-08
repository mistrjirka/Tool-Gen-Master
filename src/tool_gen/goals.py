"""Seeded goal generator: port of ``gen_bias_fixed_v3.py`` (bias-fixed pilot v4).

Sampling behavior is intentionally preserved verbatim: Zipf(0.8) domain weights
over the catalog insertion order, the [1,2,2,3,3,3,4,4,5] call-count mix, the
[3..8] catalog sizes, the 0.75 family-tool bias, the 0.30 optional-argument rate,
the 0.15 chaining rate (``API_call_<i>`` placeholders), the 0.30 call shuffle and
the 0.10 no-call rate. ``tool_weight`` keeps the v3 bias fixes: pure id-lookup
tools down-weighted to 0.30, zero-required-argument list tools up-weighted to
1.50, plus the ``near_duplicate`` rejection (fields/limit tweaks and strict
argument-subset pairs are never emitted twice for the same tool).

Known quirks preserved for reproducibility (not misrepresented as fixed):
- ``group_id`` is ``sha256(str(calls))`` over the Python repr of the call list,
  not over canonical JSON, so it is interpreter-repr-sensitive.
- Chained ``API_call_<i>`` values are forward-unresolved plain strings; there is
  no output schema or typed reference behind them. Semantic chaining is NOT
  solved here. Run ``tool-gen audit`` to surface unknown tools, bad enums/types
  and forward references as mechanical goal errors, distinct from reader noise.
- Each sampled argument draws from a freshly generated fixture-id pool, so
  id arguments across calls never co-refer by construction.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import string

from tool_gen.catalogs import DOMAINS, load_catalogs

Tool = dict[str, object]

CALL_COUNT_CHOICES = [1, 2, 2, 3, 3, 3, 4, 4, 5]
CATALOG_SIZE_CHOICES = [3, 4, 5, 6, 7, 8]
STYLES = [
    "conversational",
    "short_message",
    "checklist",
    "informal_command",
    "formal_command",
    "terse",
]
CONTEXT_MODES = ["api_only", "grounded"]
FAMILY_TOOL_BIAS = 0.75
OPTIONAL_RATE = 0.3
CHAIN_RATE = 0.15
SHUFFLE_RATE = 0.30
NO_CALL_RATE = 0.10

OPTIONAL_TWEAKABLE = {"fields", "limit"}


def _domain_weights() -> list[float]:
    raw = [1.0 / (i + 1) ** 0.8 for i in range(len(DOMAINS))]
    total = sum(raw)
    return [w / total for w in raw]


DOMAIN_WEIGHTS = _domain_weights()


def id_like(name: str) -> bool:
    n = name.lower()
    return n.endswith(("id", "code")) or "sku" in n


def tool_weight(tool: Tool) -> float:
    function = tool["function"]
    assert isinstance(function, dict)
    parameters = function["parameters"]
    assert isinstance(parameters, dict)
    required = parameters.get("required", [])
    assert isinstance(required, list)
    if required and all(id_like(str(k)) for k in required):
        return 0.30
    if not required:
        return 1.50
    return 1.00


def random_id(rng: random.Random, n: int = 10) -> str:
    return "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(n))


def _schema_int(prop: dict[str, object], key: str, default: int) -> int:
    """Integer schema bound; catalogs are validated, so anything else is a defect."""
    value = prop.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"schema bound {key!r} must be an integer, got {value!r}")
    return value


def _schema_float(prop: dict[str, object], key: str, default: float) -> float:
    value = prop.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"schema bound {key!r} must be a number, got {value!r}")
    return float(value)


def sample_value(
    rng: random.Random,
    prop: dict[str, object],
    param_name: str = "",
    fixture_ids: list[str] | None = None,
) -> object:
    ptype = str(prop.get("type", "string"))
    desc = str(prop.get("description", "")).lower()
    pname = param_name.lower()
    if "id" in pname or "code" in pname or "sku" in pname:
        if ptype == "integer":
            lo_id = _schema_int(prop, "minimum", 1)
            hi_id = min(_schema_int(prop, "maximum", 999), 999)
            return rng.randint(lo_id, max(lo_id, hi_id))
        if fixture_ids:
            return rng.choice(fixture_ids)
        return random_id(rng)
    if pname == "limit":
        return rng.choice([5, 10, 20, 50])
    if "enum" in prop:
        enum = prop["enum"]
        assert isinstance(enum, list) and enum
        return rng.choice(enum)
    if ptype == "integer":
        mn_int = _schema_int(prop, "minimum", 0)
        mx_int = min(_schema_int(prop, "maximum", 100), 100)
        if mn_int > mx_int:
            mn_int = 0
        return rng.randint(mn_int, mx_int)
    if ptype == "number":
        lo_num = _schema_float(prop, "minimum", 0.0)
        hi_num = min(_schema_float(prop, "maximum", 100.0), 100.0)
        return round(rng.uniform(lo_num, hi_num), 2)
    if ptype == "boolean":
        return rng.choice([True, False])
    if ptype == "string":
        if "instant" in desc or "date" in desc:
            d = rng.choice(["2024-01-15", "2024-02-20", "2024-03-10", "2025-06-01"])
            t = rng.choice(["09:00", "14:30", "17:00", "23:59"])
            if "instant" in desc:
                return f"{d}T{t}:00+02:00"
            return d
        if "one of" in desc:
            m = re.search(r"one of: (.+)", str(prop.get("description", "")))
            if m:
                return rng.choice([v.strip() for v in m.group(1).split(",")])
        return rng.choice(
            ["active", "pending", "sample", "main", "test", "open", "closed"]
        )
    return None


def near_duplicate(
    calls: list[dict[str, object]], name: str, args: dict[str, object]
) -> bool:
    for c in calls:
        if c["name"] != name:
            continue
        existing = c["arguments"]
        assert isinstance(existing, dict)
        ka, kb = set(existing), set(args)
        if ka ^ kb and (ka ^ kb) <= OPTIONAL_TWEAKABLE:
            return True
        if ka <= kb or kb <= ka:
            return True
    return False


def _function_of(tool: Tool) -> dict[str, object]:
    function = tool["function"]
    assert isinstance(function, dict)
    return function


def gen_goals(n: int, seed: int) -> list[dict[str, object]]:
    catalogs = load_catalogs()
    families = list(DOMAINS)
    by_family: dict[str, list[Tool]] = {d: list(catalogs[d]) for d in families}
    other_tools: dict[str, list[Tool]] = {}
    for d in families:
        pooled: list[Tool] = []
        for e, tl in by_family.items():
            if e != d:
                pooled.extend(tl)
        other_tools[d] = pooled

    rng = random.Random(seed)
    goals: list[dict[str, object]] = []
    for i in range(n):
        family = rng.choices(families, weights=DOMAIN_WEIGHTS, k=1)[0]
        tools = list(by_family[family])
        weights = [tool_weight(t) for t in tools]
        call_count = rng.choice(CALL_COUNT_CHOICES)
        catalog_size = rng.choice(CATALOG_SIZE_CHOICES)
        if catalog_size <= len(tools):
            catalog_tools = rng.sample(tools, catalog_size)
        else:
            distractors = rng.sample(
                other_tools[family],
                min(catalog_size - len(tools), len(other_tools[family])),
            )
            catalog_tools = tools + distractors
        rng.shuffle(catalog_tools)
        catalog_tools = catalog_tools[:catalog_size]

        calls: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for _ in range(call_count * 6):
            if len(calls) >= call_count:
                break
            tool = (
                rng.choices(tools, weights=weights, k=1)[0]
                if rng.random() < FAMILY_TOOL_BIAS
                else rng.choice(catalog_tools)
            )
            function = _function_of(tool)
            parameters = function["parameters"]
            assert isinstance(parameters, dict)
            props = parameters["properties"]
            assert isinstance(props, dict)
            required = parameters.get("required", [])
            assert isinstance(required, list)
            args: dict[str, object] = {}
            for key in required:
                if key in props:
                    prop = props[key]
                    assert isinstance(prop, dict)
                    val = sample_value(
                        rng, prop, str(key), [random_id(rng) for _ in range(5)]
                    )
                    if val is not None:
                        args[str(key)] = val
            for key in props:
                if (
                    key not in required
                    and key not in args
                    and rng.random() < OPTIONAL_RATE
                ):
                    prop = props[key]
                    assert isinstance(prop, dict)
                    val = sample_value(
                        rng, prop, str(key), [random_id(rng) for _ in range(5)]
                    )
                    if val is not None:
                        args[str(key)] = val
            if calls and args and rng.random() < CHAIN_RATE:
                args[rng.choice(list(args))] = f"API_call_{rng.randrange(len(calls))}"
            name = str(function["name"])
            if near_duplicate(calls, name, args):
                continue
            sig = (name, json.dumps(args, sort_keys=True))
            if sig not in seen:
                seen.add(sig)
                calls.append({"name": name, "arguments": args})

        if rng.random() < SHUFFLE_RATE and len(calls) > 1:
            rng.shuffle(calls)

        no_call = rng.random() < NO_CALL_RATE
        goals.append(
            {
                "id": f"cohv5-{seed}-{i:04d}",
                "group_id": hashlib.sha256(str(calls).encode()).hexdigest(),
                "split": "train",
                "family_id": family,
                "style": rng.choice(STYLES),
                "no_call": no_call,
                "context_mode": rng.choice(CONTEXT_MODES),
                "tools": catalog_tools,
                "witness": [] if no_call else calls,
                "fixtures": {},
                "observations": [],
            }
        )
    return goals
