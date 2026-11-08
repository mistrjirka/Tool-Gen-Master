"""Seeded goal generator: port of ``gen_bias_fixed_v3.py`` (bias-fixed pilot v4).

Sampling behavior intentionally preserves the pilot mixes: Zipf(0.8) domain weights
over the catalog insertion order, the [1,2,2,3,3,3,4,4,5] call-count mix, the
[3..8] catalog sizes, the 0.75 family-tool bias, the 0.30 optional-argument rate, the 0.30 call shuffle and
the 0.10 no-call rate. Default sampled goals are independent: the legacy
``API_call_<i>`` placeholder injection is removed, so new goals never chain by
construction (imported legacy goals carrying such references are still rejected
by ``tool-gen audit``). Witness tools are sampled ONLY from the per-goal catalog
actually supplied with that goal; within that subset the prior relative weights
(``tool_weight``: pure id-lookup tools 0.30, zero-required-argument list tools
1.50) and the 0.75 family-tool bias are preserved. IDs/lists remain allowed;

Value sampling obeys the supplied schemas and recurses into bundled
array/object arguments: projection arrays sample a unique subset of the
declared enum items within min/maxItems, and nested filter objects sample
their required properties always and a varying subset of optional ones
(``searchBooks.filter`` author/genre/year each drawn from its own schema).
Declared ``enum`` wins over
id/code heuristics (e.g. ``tariffCode``), numeric arguments honor their declared
min/max exactly (never clamped into out-of-schema values), and generic
name/place/keyword strings come from small explicit fictional pools keyed by
meaning/declared description (exact IDs and legal enums preserved). The
``near_duplicate`` rejection compares actual shared values: exact duplicate
calls and same core args differing only in projection/limit are never emitted
twice for the same tool, while different books/dates/filters (even with the
same key sets) and general-plus-genuinely-different-filter pairs are allowed.

Known quirks preserved for reproducibility (not misrepresented as fixed):
- ``group_id`` is ``sha256(str(calls))`` over the Python repr of the call list,
  not over canonical JSON, so it is interpreter-repr-sensitive.
- Each sampled argument draws from a freshly generated fixture-id pool, so
  id arguments across calls never co-refer by construction.
- ``listReadings`` windows are sampled end-to-end (fromInstant <= toInstant,
  inclusive); an imported goal with a reversed window is an invalid goal.
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
NESTED_OPTIONAL_RATE = 0.5
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


def _schema_range_int(prop: dict[str, object]) -> tuple[int, int]:
    """Declared integer bounds exactly; a min>max schema is a catalog defect."""
    lo = _schema_int(prop, "minimum", 0) if "minimum" in prop else 0
    hi = _schema_int(prop, "maximum", 100) if "maximum" in prop else 100
    if lo > hi:
        raise ValueError(f"schema range invalid: minimum {lo} > maximum {hi}")
    return lo, hi


def _schema_range_float(prop: dict[str, object]) -> tuple[float, float]:
    """Declared number bounds exactly; a min>max schema is a catalog defect."""
    lo = _schema_float(prop, "minimum", 0.0) if "minimum" in prop else 0.0
    hi = _schema_float(prop, "maximum", 100.0) if "maximum" in prop else 100.0
    if lo > hi:
        raise ValueError(f"schema range invalid: minimum {lo} > maximum {hi}")
    return lo, hi


PERSON_NAMES = [
    "Amara Okafor",
    "Jonas Lindqvist",
    "Priya Raman",
    "Tomas Herrera",
    "Nadia Haddad",
    "Elias Novak",
    "Mei Tanaka",
    "Sara Lindgren",
]

PLACES = [
    "Riverside Market",
    "Northgate Library",
    "Harborview Station",
    "Cedar Park",
    "Lakeside Pavilion",
    "Old Mill District",
]

KEYWORDS = [
    "harbor tides",
    "solar lanterns",
    "city bees",
    "quiet gardens",
    "river maps",
    "night trains",
]

BRANCHES = [
    "main",
    "north-branch",
    "release-2x",
    "feature-harbor",
]

NEUTRAL_TEXTS = [
    "harbor record",
    "general entry",
    "reference note",
    "sample item",
]

_PERSON_KEYS = (
    "author",
    "username",
    "guest",
    "student",
    "borrower",
    "customer",
    "contact",
    "person",
    "member",
)
_PLACE_KEYS = ("city", "origin", "destination", "location", "place", "store")
_KEYWORD_KEYS = ("keyword", "query", "title", "subject", "product", "name")


def _semantic_string(rng: random.Random, param_name: str, description: str) -> object:
    """Fictional value keyed by parameter meaning/declared description."""
    pname = param_name.lower()
    desc = description.lower()
    if "branch" in pname:
        return rng.choice(BRANCHES)
    if any(k in pname for k in _PERSON_KEYS) or any(
        k in desc for k in ("username", "display name", "guest name", "student")
    ):
        return rng.choice(PERSON_NAMES)
    if any(k in pname for k in _PLACE_KEYS) or any(
        k in desc for k in ("location name", "city name", "store display name")
    ):
        return rng.choice(PLACES)
    if any(k in pname for k in _KEYWORD_KEYS) or "keyword" in desc:
        return rng.choice(KEYWORDS)
    return rng.choice(NEUTRAL_TEXTS)


def json_key(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def sample_value(
    rng: random.Random,
    prop: dict[str, object],
    param_name: str = "",
    fixture_ids: list[str] | None = None,
) -> object:
    ptype = str(prop.get("type", "string"))
    raw_desc = str(prop.get("description", ""))
    desc = raw_desc.lower()
    pname = param_name.lower()
    if "enum" in prop:
        enum = prop["enum"]
        assert isinstance(enum, list) and enum
        return rng.choice(enum)
    if "id" in pname or "code" in pname or "sku" in pname:
        if ptype == "integer":
            lo_id = _schema_int(prop, "minimum", 1) if "minimum" in prop else 1
            hi_id = _schema_int(prop, "maximum", 999) if "maximum" in prop else 999
            if lo_id > hi_id:
                raise ValueError(
                    f"schema range invalid: minimum {lo_id} > maximum {hi_id}"
                )
            return rng.randint(lo_id, hi_id)
        if fixture_ids:
            return rng.choice(fixture_ids)
        return random_id(rng)
    if pname == "limit":
        lo_lim = _schema_int(prop, "minimum", 0) if "minimum" in prop else 0
        hi_lim = _schema_int(prop, "maximum", 50) if "maximum" in prop else 50
        if lo_lim > hi_lim:
            raise ValueError(
                f"schema range invalid: minimum {lo_lim} > maximum {hi_lim}"
            )
        fitting = [v for v in (5, 10, 20, 50) if lo_lim <= v <= hi_lim]
        if fitting:
            return rng.choice(fitting)
        return rng.randint(lo_lim, hi_lim)
    if ptype == "integer":
        mn_int, mx_int = _schema_range_int(prop)
        return rng.randint(mn_int, mx_int)
    if ptype == "number":
        lo_num, hi_num = _schema_range_float(prop)
        sampled = round(rng.uniform(lo_num, hi_num), 2)
        # Rounding to 2dp can escape narrow fractional bounds (e.g. .005-.006),
        # so clamp the rounded result back into the declared bounds.
        return max(lo_num, min(hi_num, sampled))
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
            m = re.search(r"one of: (.+)", raw_desc)
            if m:
                return rng.choice([v.strip() for v in m.group(1).split(",")])
        return _semantic_string(rng, param_name, raw_desc)
    if ptype == "array":
        items = prop.get("items", {})
        if not isinstance(items, dict):
            raise TypeError(
                f"array schema for {param_name!r} has non-object items: {items!r}"
            )
        min_items = _schema_int(prop, "minItems", 1) if "minItems" in prop else 1
        max_items = _schema_int(prop, "maxItems", 6) if "maxItems" in prop else 6
        if min_items < 0 or max_items < 0:
            raise ValueError(
                f"array schema for {param_name!r} has negative item bounds"
            )
        if min_items > max_items:
            raise ValueError(
                f"schema range invalid: minItems {min_items} > maxItems {max_items}"
            )
        item_enum = items.get("enum")
        if isinstance(item_enum, list) and item_enum:
            if min_items > len(item_enum):
                raise ValueError(
                    f"array schema for {param_name!r} needs {min_items} unique"
                    f" items from {len(item_enum)} enum values"
                )
            count = rng.randint(min_items, min(max_items, len(item_enum)))
            return rng.sample(list(item_enum), count)
        count = rng.randint(min_items, max_items)
        items_sampled: list[object] = [
            sample_value(rng, items, param_name, fixture_ids) for _ in range(count)
        ]
        if prop.get("uniqueItems") is True:
            for index in range(len(items_sampled)):
                for _ in range(10):
                    if json_key(items_sampled[index]) not in {
                        json_key(v) for j, v in enumerate(items_sampled) if j != index
                    }:
                        break
                    items_sampled[index] = sample_value(
                        rng, items, param_name, fixture_ids
                    )
            if len({json_key(value) for value in items_sampled}) != len(items_sampled):
                raise ValueError(
                    f"cannot sample {count} unique array items for {param_name!r}"
                )
        return items_sampled
    if ptype == "object":
        properties = prop.get("properties", {})
        if not isinstance(properties, dict):
            raise TypeError(
                f"object schema for {param_name!r} has non-object properties"
            )
        required = prop.get("required", [])
        if not isinstance(required, list):
            raise TypeError(f"object schema for {param_name!r} has non-list required")
        sampled_obj: dict[str, object] = {}
        for key in required:
            child = properties.get(str(key))
            if not isinstance(child, dict):
                raise TypeError(
                    f"object schema for {param_name!r} requires"
                    f" undeclared property {key!r}"
                )
            sampled_obj[str(key)] = sample_value(rng, child, str(key), fixture_ids)
        optional_keys = [
            k for k in properties if k not in required and isinstance(k, str)
        ]
        for key in optional_keys:
            if rng.random() < NESTED_OPTIONAL_RATE:
                child = properties[key]
                assert isinstance(child, dict)
                sampled_obj[str(key)] = sample_value(rng, child, str(key), fixture_ids)
        if not sampled_obj and optional_keys:
            key = rng.choice(optional_keys)
            child = properties[key]
            assert isinstance(child, dict)
            sampled_obj[str(key)] = sample_value(rng, child, str(key), fixture_ids)
        return sampled_obj
    raise TypeError(f"unsupported schema type {ptype!r} for {param_name!r}: {prop!r}")


def near_duplicate(
    calls: list[dict[str, object]], name: str, args: dict[str, object]
) -> bool:
    """Reject equal cores differing only in projection/limit. The argument
    dicts are compared with ``fields``/``limit`` removed on BOTH sides, so
    differing projection/limit values alone never distinguish calls; exact
    duplicates are covered. Different dates/IDs/filter values and
    unfiltered-plus-genuinely-filtered pairs remain allowed."""
    for c in calls:
        if c["name"] != name:
            continue
        existing = c["arguments"]
        assert isinstance(existing, dict)
        core_existing = {
            k: v for k, v in existing.items() if k not in OPTIONAL_TWEAKABLE
        }
        core_args = {k: v for k, v in args.items() if k not in OPTIONAL_TWEAKABLE}
        if core_existing == core_args:
            return True
    return False


def _function_of(tool: Tool) -> dict[str, object]:
    function = tool["function"]
    assert isinstance(function, dict)
    return function


def _order_readings_window(args: dict[str, object]) -> None:
    """Order this tool's declared instant window in place, start inclusive.

    Only the declared ``listReadings`` fromInstant/toInstant contract is
    handled here; no generic key-guessing over unrelated tools."""
    start = args.get("fromInstant")
    end = args.get("toInstant")
    if not isinstance(start, str) or not isinstance(end, str):
        return
    from tool_gen.comparison import canonical_instant

    if canonical_instant(start) > canonical_instant(end):
        args["fromInstant"], args["toInstant"] = end, start


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
        family_names = {str(_function_of(t)["name"]) for t in tools}
        family_in_catalog = [
            t for t in catalog_tools if str(_function_of(t)["name"]) in family_names
        ]
        for _ in range(call_count * 6):
            if len(calls) >= call_count:
                break
            # Supported witness tools come only from the supplied catalog;
            # the family bias picks among family members within that catalog,
            # keeping the prior relative weights.
            if rng.random() < FAMILY_TOOL_BIAS and family_in_catalog:
                tool = rng.choices(
                    family_in_catalog,
                    weights=[tool_weight(t) for t in family_in_catalog],
                    k=1,
                )[0]
            else:
                tool = rng.choice(catalog_tools)
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
                    args[str(key)] = sample_value(
                        rng, prop, str(key), [random_id(rng) for _ in range(5)]
                    )
            for key in props:
                if (
                    key not in required
                    and key not in args
                    and rng.random() < OPTIONAL_RATE
                ):
                    prop = props[key]
                    assert isinstance(prop, dict)
                    args[str(key)] = sample_value(
                        rng, prop, str(key), [random_id(rng) for _ in range(5)]
                    )
            name = str(function["name"])
            if name == "listReadings":
                _order_readings_window(args)
            if near_duplicate(calls, name, args):
                continue
            sig = (name, json.dumps(args, sort_keys=True))
            if sig not in seen:
                seen.add(sig)
                calls.append({"name": name, "arguments": args})

        if rng.random() < SHUFFLE_RATE and len(calls) > 1:
            rng.shuffle(calls)

        no_call = rng.random() < NO_CALL_RATE or not calls
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
