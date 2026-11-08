"""Describe data patterns without prescribing a preferred distribution.

Supports goal, writer, reader, paraphrase and SFT JSONL artifacts. Text metrics
use only samples with a nonempty request; structural metrics have their own
explicit eligibility counts. Nothing in this module accepts or rejects data.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from pydantic import JsonValue, TypeAdapter, ValidationError

JsonObject = dict[str, JsonValue]
_OBJECT = TypeAdapter(JsonObject)
_WORD = re.compile(r"\b\w+(?:['’\-]\w+)*\b", re.UNICODE)
_LIST_LINE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
_REFERENCE = re.compile(r"API_call_\d+")
_ID_KEY = re.compile(r"(?:id|code)$|^sku$", re.IGNORECASE)
_NAME_KEY = re.compile(
    r"name$|^(?:title|author|holder|city|location|origin|destination)$", re.IGNORECASE
)


@dataclass(frozen=True)
class CallView:
    name: str
    arguments: JsonObject


@dataclass(frozen=True)
class ToolView:
    name: str
    properties: tuple[str, ...]


@dataclass(frozen=True)
class Sample:
    identity: str
    request: str | None
    calls: tuple[CallView, ...] | None
    tools: tuple[ToolView, ...] | None
    style: str | None
    outcome: str | None
    group: str | None
    domain: str | None = None
    split: str | None = None
    augmentation: str | None = None


def _object(value: JsonValue) -> JsonObject | None:
    return value if isinstance(value, dict) else None


def _string(value: JsonValue) -> str | None:
    return value if isinstance(value, str) else None


def _calls(value: JsonValue) -> tuple[CallView, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise TypeError("calls must be an array")
    calls = []
    for item in value:
        call = _object(item)
        if call is None:
            raise ValueError("call must be an object")
        function = _object(call.get("function")) or call
        name = _string(function.get("name"))
        arguments = _object(function.get("arguments"))
        if not name or arguments is None:
            raise ValueError("call needs a name and object-valued arguments")
        calls.append(CallView(name, arguments))
    return tuple(calls)


def _tools(value: JsonValue) -> tuple[ToolView, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise TypeError("tools must be an array")
    tools = []
    for item in value:
        tool = _object(item)
        function = _object(tool.get("function")) if tool is not None else None
        if function is None:
            raise ValueError("tool needs a function definition")
        name = _string(function.get("name"))
        parameters = _object(function.get("parameters"))
        properties = (
            _object(parameters.get("properties")) if parameters is not None else None
        )
        if not name or properties is None:
            raise ValueError("tool needs a name and parameter properties")
        tools.append(ToolView(name, tuple(properties)))
    return tuple(tools)


def _normalize(record: JsonObject, index: int) -> list[Sample]:
    goal = _object(record.get("goal"))
    source = goal if goal is not None else record
    identity = _string(source.get("id")) or _string(record.get("id")) or f"row-{index}"
    group = _string(source.get("group_id")) or _string(source.get("parent_group"))
    tools = _tools(source.get("tools", source.get("catalog")))
    calls = _calls(source.get("witness", source.get("calls")))
    style = _string(source.get("style"))
    outcome = _string(record.get("outcome")) or _string(record.get("decision"))
    accepted = record.get("accepted")
    if outcome is None and isinstance(accepted, bool):
        outcome = "reader_pass" if accepted else "legacy_reader_unmatched"
    request = _string(record.get("request"))
    messages = record.get("messages")
    if isinstance(messages, list):
        user_text = []
        message_calls: list[CallView] = []
        has_assistant = False
        for value in messages:
            message = _object(value)
            if message is None:
                raise ValueError("message must be an object")
            if message.get("role") == "user":
                content = _string(message.get("content"))
                if content:
                    user_text.append(content)
            if message.get("role") == "assistant":
                has_assistant = True
                parsed = _calls(message.get("tool_calls"))
                if parsed is not None:
                    message_calls.extend(parsed)
        if request is None and user_text:
            request = "\n".join(user_text)
        if calls is None and has_assistant:
            calls = tuple(message_calls)
    if "paraphrases" in record:
        variants = record["paraphrases"]
        if not isinstance(variants, list):
            raise ValueError("paraphrases must be an array")
        samples = []
        for number, value in enumerate(variants):
            variant = _object(value)
            if variant is None:
                raise ValueError("paraphrase must be an object")
            text = _string(variant.get("text"))
            if text and text.strip():
                samples.append(
                    Sample(
                        f"{identity}/paraphrase-{number}",
                        text,
                        calls,
                        tools,
                        _string(variant.get("register")),
                        outcome,
                        group,
                        domain=_string(source.get("family_id")),
                        split=_string(source.get("split")),
                        augmentation=_string(record.get("augmentation")),
                    )
                )
        return samples
    if "paraphrase" in record:
        request = _string(record.get("paraphrase"))
        style = _string(record.get("register"))
        if not request or not request.strip():
            return []
    if request is None and calls is None and tools is None:
        raise ValueError("unrecognized artifact: no request, calls or tool catalogue")
    return [
        Sample(
            identity,
            request if request and request.strip() else None,
            calls,
            tools,
            style,
            outcome,
            group,
            domain=_string(source.get("family_id")),
            split=_string(source.get("split")),
            augmentation=_string(record.get("augmentation")),
        )
    ]


def _rate(count: int, eligible: int) -> dict[str, int | float | None]:
    return {
        "count": count,
        "eligible": eligible,
        "share": count / eligible if eligible else None,
    }


def _distribution(
    counts: Counter[str], examples: dict[str, list[str]] | None = None, limit: int = 20
) -> dict[str, object]:
    total = sum(counts.values())
    top = []
    for value, count in counts.most_common(limit):
        entry: dict[str, object] = {
            "value": value,
            "count": count,
            "share": count / total if total else None,
        }
        if examples is not None:
            entry["example_ids"] = examples.get(value, [])[:3]
        top.append(entry)
    entropy = (
        -sum((count / total) * math.log2(count / total) for count in counts.values())
        if total
        else None
    )
    ordered = sorted(counts.values())
    size = len(ordered)
    gini = (
        (
            2 * sum((i + 1) * c for i, c in enumerate(ordered)) / (size * total)
            - (size + 1) / size
        )
        if total
        else None
    )
    return {
        "observations": total,
        "distinct": len(counts),
        "entropy_bits": entropy,
        "gini_observed_categories": gini,
        "top": top,
    }


def _leaves(arguments: JsonObject) -> Iterable[tuple[str, JsonValue]]:
    for key, value in arguments.items():
        if isinstance(value, dict):
            yield from _leaves(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield from _leaves(item)
                elif not isinstance(item, list):
                    yield key, item
                else:
                    yield from _leaves({key: item})
        else:
            yield key, value


def _skeleton(sample: Sample) -> str:
    replacements = {}
    for call in sample.calls or ():
        for key, value in _leaves(call.arguments):
            if value is None or isinstance(value, bool):
                continue
            literal = (
                value if isinstance(value, str) else json.dumps(value, allow_nan=False)
            )
            if not literal:
                continue
            kind = (
                "id"
                if _ID_KEY.search(key)
                else "name"
                if _NAME_KEY.search(key)
                else "value"
            )
            replacements[literal] = f"<{kind}>"
    text = sample.request or ""
    if replacements:
        pattern = re.compile(
            r"(?<!\w)(?:"
            + "|".join(
                re.escape(value)
                for value in sorted(replacements, key=len, reverse=True)
            )
            + r")(?!\w)"
        )
        text = pattern.sub(lambda match: replacements[match.group()], text)
    return " ".join(text.casefold().split())


def _repetitions(groups: dict[str, list[str]], eligible: int) -> dict[str, object]:
    repeated = [(key, ids) for key, ids in groups.items() if len(ids) > 1]
    repeated.sort(key=lambda item: (-len(item[1]), item[0]))
    return {
        **_rate(sum(len(ids) - 1 for _, ids in repeated), eligible),
        "repeated_groups": len(repeated),
        "examples": [
            {"pattern": key, "count": len(ids), "example_ids": ids[:5]}
            for key, ids in repeated[:10]
        ],
    }


def _wording_metrics(text_samples: list[Sample]) -> dict[str, object]:
    openers: Counter[str] = Counter()
    prefixes: Counter[str] = Counter()
    opener_examples: dict[str, list[str]] = defaultdict(list)
    ngrams: dict[int, Counter[str]] = {n: Counter() for n in (2, 3, 4, 5)}
    exact: dict[str, list[str]] = defaultdict(list)
    skeletons: dict[str, list[str]] = defaultdict(list)
    word_counts = []
    list_requests = checklist_prefixes = id_wording = field_wording = internal_refs = 0
    for sample in text_samples:
        text = sample.request or ""
        words = [word.casefold() for word in _WORD.findall(text)]
        word_counts.append(len(words))
        if words:
            openers[words[0]] += 1
            opener_examples[words[0]].append(sample.identity)
            prefixes[" ".join(words[:3])] += 1
        for size, counts in ngrams.items():
            counts.update(
                {" ".join(words[i : i + size]) for i in range(len(words) - size + 1)}
            )
        list_requests += bool(_LIST_LINE.search(text))
        internal_refs += bool(_REFERENCE.search(text))
        checklist_prefixes += bool(re.match(r"\s*checklist\b", text, re.IGNORECASE))
        id_wording += bool(
            re.search(r"\b(?:id|identifier|sku|code)\b", text, re.IGNORECASE)
        )
        fields = {
            key
            for call in sample.calls or ()
            for key in call.arguments
            if re.search(r"[a-z][A-Z]|_", key)
        }
        field_wording += any(
            re.search(r"\b" + re.escape(key) + r"\b", text, re.IGNORECASE)
            for key in fields
        )
        exact[text].append(sample.identity)
        skeletons[_skeleton(sample)].append(sample.identity)

    return {
        "openers": _distribution(openers, opener_examples),
        "opening_up_to_three_words": _distribution(prefixes),
        "list_form_requests": _rate(list_requests, len(text_samples)),
        "checklist_prefix_requests": _rate(checklist_prefixes, len(text_samples)),
        "explicit_id_sku_code_wording": _rate(id_wording, len(text_samples)),
        "internal_reference_tokens_in_requests": _rate(
            internal_refs, len(text_samples)
        ),
        "literal_camel_or_snake_argument_names": _rate(
            field_wording, len(text_samples)
        ),
        "word_count": {
            "min": min(word_counts) if word_counts else None,
            "median": median(word_counts) if word_counts else None,
            "max": max(word_counts) if word_counts else None,
        },
        "short_requests_up_to_five_words": _rate(
            sum(n <= 5 for n in word_counts), len(text_samples)
        ),
        "exact_duplicate_requests": _repetitions(exact, len(text_samples)),
        "value_masked_templates": _repetitions(skeletons, len(text_samples)),
        "recurring_ngrams": {
            str(size): {
                "eligible_text_samples": len(text_samples),
                "distinct": len(counts),
                "top": [
                    {
                        "phrase": phrase,
                        "sample_count": count,
                        "sample_share": count / len(text_samples)
                        if text_samples
                        else None,
                    }
                    for phrase, count in counts.most_common(20)
                ],
            }
            for size, counts in ngrams.items()
        },
    }


def _structure_metrics(samples: list[Sample]) -> dict[str, object]:
    call_samples = [sample for sample in samples if sample.calls is not None]
    called: Counter[str] = Counter()
    available: Counter[str] = Counter()
    call_counts: Counter[str] = Counter()
    catalog_sizes: Counter[str] = Counter()
    types: Counter[str] = Counter()
    identities: Counter[str] = Counter()
    id_prefixes: Counter[str] = Counter()
    value_frequencies: dict[str, Counter[str]] = defaultdict(Counter)
    call_graphs: dict[str, list[str]] = defaultdict(list)
    graph_eligible = multi_args = alphabetical_args = schema_args = schema_eligible = 0
    ordered_rows = alphabetical_tools = catalogue_order = 0
    known_call_rows = missing_tools = chained_rows = id_rows = name_rows = id_values = (
        prefixed_ids
    ) = 0
    for sample in samples:
        schemas = {tool.name: tool.properties for tool in sample.tools or ()}
        if sample.tools is not None:
            available.update(tool.name for tool in sample.tools)
            catalog_sizes[str(len(sample.tools))] += 1
        if sample.calls is None:
            continue
        calls = sample.calls
        call_counts[str(len(calls))] += 1
        called.update(call.name for call in calls)
        leaves = [
            (key, value) for call in calls for key, value in _leaves(call.arguments)
        ]
        chained_rows += any(
            isinstance(value, str) and _REFERENCE.search(value) for _, value in leaves
        )
        has_id = has_name = False
        for key, value in leaves:
            value_frequencies[key][
                json.dumps(value, ensure_ascii=False, allow_nan=False)
            ] += 1
            types[
                "null"
                if value is None
                else "boolean"
                if isinstance(value, bool)
                else "integer"
                if isinstance(value, int)
                else "number"
                if isinstance(value, float)
                else "string"
            ] += 1
            if _ID_KEY.search(key) and not (
                isinstance(value, str) and _REFERENCE.fullmatch(value)
            ):
                identities["id_like_leaves"] += 1
                has_id = True
                if isinstance(value, str):
                    id_values += 1
                    prefix = re.match(r"^([A-Za-z]{2,8})[-_]", value)
                    if prefix:
                        prefixed_ids += 1
                        id_prefixes[prefix.group(1)] += 1
            elif _NAME_KEY.search(key):
                identities["name_like_leaves"] += 1
                has_name = True
        id_rows += has_id
        name_rows += has_name
        for call in calls:
            keys = list(call.arguments)
            if len(keys) >= 2:
                multi_args += 1
                alphabetical_args += keys == sorted(keys)
                if call.name in schemas and set(keys) <= set(schemas[call.name]):
                    schema_eligible += 1
                    schema_args += keys == [
                        key for key in schemas[call.name] if key in call.arguments
                    ]
        if sample.tools is not None:
            known_call_rows += 1
            missing_tools += sum(call.name not in schemas for call in calls)
            names = [call.name for call in calls]
            if len(set(names)) >= 2 and all(name in schemas for name in names):
                ordered_rows += 1
                alphabetical_tools += names == sorted(names)
                positions = {tool.name: i for i, tool in enumerate(sample.tools)}
                catalogue_order += names == sorted(names, key=positions.__getitem__)
            if calls:
                graph_eligible += 1
                signature = json.dumps(
                    {
                        "catalogue": sorted(schemas),
                        "calls": sorted(
                            json.dumps(
                                {"name": call.name, "arguments": call.arguments},
                                sort_keys=True,
                                ensure_ascii=False,
                                allow_nan=False,
                            )
                            for call in calls
                        ),
                    },
                    sort_keys=True,
                )
                call_graphs[signature].append(sample.identity)
    total_calls = sum(called.values())
    return {
        "call_counts": dict(sorted(call_counts.items(), key=lambda item: int(item[0]))),
        "catalogue_sizes": dict(
            sorted(catalog_sizes.items(), key=lambda item: int(item[0]))
        ),
        "no_call_samples": _rate(call_counts["0"], len(call_samples)),
        "called_tools": _distribution(called),
        "available_tools": _distribution(available),
        "alphabetical_argument_order_multi_arg": _rate(alphabetical_args, multi_args),
        "schema_relative_argument_order_multi_arg": _rate(schema_args, schema_eligible),
        "alphabetical_call_order": _rate(alphabetical_tools, ordered_rows),
        "catalogue_relative_call_order": _rate(catalogue_order, ordered_rows),
        "calls_missing_from_catalogue": {
            "count": missing_tools,
            "eligible_samples_with_calls_and_catalogue": known_call_rows,
            "eligible_calls": sum(
                len(s.calls or ())
                for s in samples
                if s.calls is not None and s.tools is not None
            ),
        },
        "reference_token_samples": _rate(chained_rows, len(call_samples)),
        "leaf_argument_types": dict(types),
        "leaf_value_frequencies_by_key": {
            key: _distribution(counts, limit=5)
            for key, counts in sorted(value_frequencies.items())
        },
        "id_like_argument_samples_heuristic": _rate(id_rows, len(call_samples)),
        "name_like_argument_samples_heuristic": _rate(name_rows, len(call_samples)),
        "identity_leaf_counts_heuristic": dict(identities),
        "prefixed_id_strings_heuristic": _rate(prefixed_ids, id_values),
        "id_prefixes_heuristic": _distribution(id_prefixes),
        "repeated_call_targets_and_catalogue_names": _repetitions(
            call_graphs, graph_eligible
        ),
        "total_calls": total_calls,
    }


def analyze_records(records: Iterable[JsonObject]) -> dict[str, object]:
    """Report distributions and candidate patterns; never apply quality thresholds."""
    samples = []
    skipped = []
    records_seen = 0
    empty_variant_records = 0
    for records_seen, record in enumerate(records, 1):
        try:
            normalized = _normalize(record, records_seen)
        except (ValueError, TypeError) as exc:
            skipped.append({"row": records_seen, "reason": str(exc)})
            continue
        empty_variant_records += int(not normalized)
        samples.extend(normalized)
    text_samples = [sample for sample in samples if sample.request is not None]
    call_samples = [sample for sample in samples if sample.calls is not None]
    catalog_samples = [sample for sample in samples if sample.tools is not None]
    return {
        "interpretation": "Descriptive patterns, not quality judgments or pass/fail gates. Correlation is not evidence of harm.",
        "coverage": {
            "records_seen": records_seen,
            "normalized_samples": len(samples),
            "text_samples": len(text_samples),
            "samples_with_calls": len(call_samples),
            "samples_with_catalogue": len(catalog_samples),
            "skipped_records": len(skipped),
            "skipped_examples": skipped[:10],
            "empty_paraphrase_records": empty_variant_records,
        },
        "wording": _wording_metrics(text_samples),
        "structure": _structure_metrics(samples),
        "declared_styles": _distribution(
            Counter(s.style for s in samples if s.style is not None)
        ),
        "recorded_outcomes": _distribution(
            Counter(s.outcome for s in samples if s.outcome is not None)
        ),
        "declared_domains": _distribution(
            Counter(s.domain for s in samples if s.domain is not None)
        ),
        "declared_splits": _distribution(
            Counter(s.split for s in samples if s.split is not None)
        ),
        "declared_augmentations": _distribution(
            Counter(s.augmentation for s in samples if s.augmentation is not None)
        ),
        "parent_group_size_distribution": dict(
            sorted(
                Counter(
                    str(size)
                    for size in Counter(
                        s.group for s in samples if s.group is not None
                    ).values()
                ).items(),
                key=lambda item: int(item[0]),
            )
        ),
        "notes": [
            "Lists, repeated wording, identifier copying, and uneven tool frequencies can be appropriate.",
            "Reader unresolved/error outcomes are not evidence that the source request is bad.",
            "List detection uses leading bullet/number markers; checklist prefixes are measured separately, not all prose lists are detected.",
            "Leaf value counts pool identical leaf keys across tools; values are displayed as JSON to retain their types.",
            "Mixing pipeline stages can count the same underlying goal more than once; parent-group sizes expose but do not remove this.",
            "ID/name categories use argument-name heuristics; an arbitrary identifier is not established as a display name.",
            "Reference tokens measure representation, not whether a dependency is feasible or correctly indexed.",
            "Argument order is measured only on multi-argument calls; schema order compares the supplied subset of keys.",
            "Call order excludes samples with fewer than two distinct called tools or missing catalogue entries.",
            "Value-masked templates can merge different intents; repeated targets can be intentional paraphrases.",
            "No-call rows are excluded from repeated call-target measurements, not conflated as duplicate tasks.",
            "Gini covers observed categories only; absent tools require comparison against the intended catalogue universe.",
            "Paraphrases count individually; SFT user messages and assistant calls are concatenated within a row.",
            "JSON key order may reflect serialization, not model or generator preference. Small samples are unstable.",
        ],
    }


def analyze_paths(paths: list[Path]) -> dict[str, object]:
    """Analyze explicit JSONL inputs. Invalid JSON is an input error, not missing data."""

    def records() -> Iterable[JsonObject]:
        for path in paths:
            if not path.is_file():
                raise ValueError(
                    f"{path}: expected an existing JSONL file; expand shard files explicitly"
                )
            with path.open(encoding="utf-8") as stream:
                for number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        yield _OBJECT.validate_json(line)
                    except ValidationError as exc:
                        raise ValueError(
                            f"{path}:{number}: invalid JSON object: {exc}"
                        ) from exc

    return {"inputs": [str(path) for path in paths], **analyze_records(records())}
