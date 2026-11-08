# Why the saved prompts look this way

## Scope and evidence

The initial sections are a source-and-artifact audit of the migration baseline.
The later repair-validation section records bounded fresh service checks, not a
new bulk dataset or downstream training experiment. The original source is the
active bias-fixed pipeline formerly under
`mobile-rl-pilot/tool_composition_v3/`, not the superseded procedural generators.

Evidence inspected:

- The saved 30-goal pilot in `results/bias-fixed-pilot-v4/writer/results.jsonl`
  and its reader records in `results/br-v5pilot/results-shard0.jsonl`.
- The saved coherent-v4 SFT file, 4,976 rows. Descriptive measurements and exact
  denominators are in [bias-analysis.md](bias-analysis.md).
- The earlier random sample: seed `7548855091409031020`, 10 of the 20 reader
  matches without replacement, and all 10 failures shuffled. Both strata were
  examined; passing examples were not assumed good.
- Original writer, reader, paraphraser, goal sampler and tool declarations.

The initial migration performed no paid generation, training, promotion or
benchmark rerun. Subsequent repairs used the small live checks documented below;
there was still no bulk generation or training. These remain synthetic data, not
newly imported human-source requests.
“Writer accepted”, “reader matched”, “schema-valid” and “human-like” are different
claims.

## The intended outcome is broad human-like data

The user's examples are illustrations, not distribution laws. Identifiers,
ordinary names, terse fragments, questions, formal requests and useful lists can
all be appropriate. There is no justified target such as “zero lists” or “every
request must avoid the word ID”. We want diverse wording appropriate to the actual
intent, with correct scope and exact entity/value resolution.

For example, “get book vbYni72MnK” can naturally refer to the same opaque
identifier as “get the book with ID vbYni72MnK”. Neither wording establishes that
`vbYni72MnK` is a book title. For a genuine title-based request, the task needs a
tool that searches titles or visible records mapping that title to the ID.
The existing `searchBooks` filter covers author/genre/year, not title; inventing a
title and passing it to `bookId` would change the task, not improve its wording.

## Causes supported by the source

### 1. Lists are partly requested by the generator

The old sampler chooses uniformly from six style labels, including
`checklist`. The writer base explicitly permits paragraphs or bullets as
appropriate. Its naturalness addendum says to avoid field/value lists **unless**
the requested style is checklist. Lists are therefore an expected output, not
evidence that temperature was zero.

This does not explain every list. It does mean that banning bullets in the writer
while continuing to request checklist goals would be contradictory. Measure the
realized style mix and judge whether the format fits the intent.

### 2. The writer input itself resembles a field dump

The old `build_writer_payload` strips a verb from a function name and constructs
strings such as:

```text
get store where storeName is closed
list refunds where minAmount is 71.27
```

Its key-humanization helper only handles a few suffixes. Labels such as
`storeName`, `sampleType` and `minAmount` survive. The writer is also told to
preserve every literal, which makes copying this field-heavy wording an easy
strategy. A final instruction to “sound human” does not remove that input anchor.

A better payload would preserve typed constraints and their scope but describe
the information need in domain terms, rather than force a particular sentence
template. This is a proposed quality change, not a measured improvement.

### 3. Unnatural names originate upstream

The generic string sampler uses the same tiny pool:

```text
active, pending, sample, main, test, open, closed
```

That is how a store becomes named “pending” or route endpoints become “pending”
and “active”. Increasing writer temperature cannot safely invent replacement
names: it is required to retain the supplied values.

The latest sampler also checks ID/code-like parameter names before enum
membership. Thus a field such as `tariffCode` can receive a random identifier
instead of a legal enum value. This is a schema defect, not a language-style
preference.

### 4. The writer already used nonzero temperature

Both the pilot writer and bulk writer pass `temperature=0.9`. The paraphraser
also uses 0.9. The independent reader uses 0.0. The migration keeps those roles
separate; writer and reader settings are independently configurable.

Creative sampling can vary wording, but it cannot repair wrong tool availability,
incompatible values, missing context or a contradictory target. No new temperature
experiment or quality claim is implied by this extraction.

### 5. Some old diversity instructions were arbitrary gates

The old prompt says never to exceed a 15% opener share, while its code rejects
openers above 20% after a small batch. A single invocation cannot see the whole
batch. The bulk driver also forces extra terse requests when its short-request
share is low, even when several exact literals cannot fit in five words.

Those are assistant-imposed aesthetic quotas, not requirements for a correct
human request. The migration removes the hard opener gate and forced terse
cadence, retaining soft diversity guidance and descriptive measurements. Literal
fidelity and correct scope remain requirements; a prescribed opening word,
bullet count or length does not.

### 6. Chaining has an unresolved contract mismatch

The legacy sampler replaced an arbitrary argument with `API_call_N`, independently of
what the preceding tool returns. It could then shuffle calls without remapping the
indices. There are no declared output schemas or field selectors behind these
references. The writer converts the token to “the value returned by operation N”,
which hides the implementation token but does not make the dependency feasible.

Meanwhile, the reader prompt forbids inventing dependencies on unknown results,
and numeric/enum argument schemas cannot represent those string placeholders.
A reader can therefore object to an intended chain even when its prose is
understandable. Conversely, a writer can invent a dependency in an otherwise
independent goal and still obtain a matching call list.

Current behavior: default generation emits independent calls only (placeholder
injection removed for this phase); imported legacy goals carrying `API_call_N`
are still quarantined as invalid goals by `tool-gen audit`, not as reader errors.
Grounded chaining needs declared outputs, typed reference paths and
reference-safe ordering, which remain undecided and out of scope here.

### 7. Some goals request tools absent from their own catalogue

The sampler first subsamples the visible catalogue, but its 75% family-tool branch
can still choose from the **entire** family. A supported witness may therefore
contain a tool that was not shown. This is a concrete construction defect;
“unsupported” no-call goals are a separate intentional category with no witness.

The mechanical audit reports this independently of reader behavior. Migration is
not a silent regeneration or filtering of the existing dataset.

### 8. The near-duplicate rule is broader than its explanation

The current rule compares sets of argument keys, not the values of shared
arguments. Two calls with `bookId` but different books are rejected just because
their key sets match. This suppresses legitimate same-tool requests as well as
the redundant projection/limit patterns it was meant to target.

A narrower rule must consider values and whether the natural request distinguishes
two scopes. Neither “same tool twice” nor “one call has more filters” is, by itself,
proof of a bad task.

## What the sampled reader outcomes actually show

| Saved ID (prefix `cohv5-21-`) | Recorded outcome | Evidence-based interpretation |
| --- | --- | --- |
| `0014`, `0025` | Match | “closed”/“active” store names remain unnatural despite passing. |
| `0029` | Match | Writer added “using the borrower ID from those results”, but the target has a fixed borrower ID. A match missed this extra dependency. |
| `0006` | Failure | “Previous search” points to statutes, while the target reference points to the hearing operation. |
| `0008`, `0004` | Failure | Ungrounded store-result→limit and product-result→date assumptions; the reader additionally fabricated concrete values. |
| `0010` | Failure | Status words used as locations, plus a target `listDepartures` absent from the catalogue. |
| `0020` | Failure | Reader reconstructed the calls but wrongly demanded filters for an API whose filters are optional. |
| `0001` | Failure | Reader dropped explicitly supplied dates while claiming they were present. Not equivalent time formatting. |
| `0024` | Failure | Empty completion; alone this says nothing conclusive about request quality. |
| `0009` | Failure | Empty completion, but independently the target's severity reference violates its enum even though “info” is already supplied. |
| `0027` | Failure | “pending” is an implausible store name, but a literal name lookup remains schema-valid; unnaturalness is not automatically ambiguity. |

The old “six interpretation errors are mostly reader noise” categorization was
too coarse. An error may expose both a source defect and a reader-contract defect.
Likewise, writer/reader acceptance cannot serve as a complete naturalness check.

## Initial extraction (commit 64590b9)

Implemented at migration: standalone modules and resources; no old absolute imports; shared
JSONL/run handling; separate model settings; full declared schemas and visible
context for the reader; uncapped call arrays; clearer error provenance; descriptive
pattern reports; soft rather than enforced lexical diversity guidance.

At that commit, domain/call/style sampling, generic value pools, experimental
chaining and the overbroad duplicate rule were preserved for reproducibility.
The repairs below deliberately change the flawed sampling rules, not frozen data.
There is still no claim of a replacement high-quality dataset or better downstream
performance. Frozen datasets, renderers, scorers and benchmark outputs stay unchanged.

## Proposed improvements, not blanket rules

1. **Mechanical construction — repaired for new sampling:** schema-first enums,
   declared numeric bounds, visible-tool membership and value-aware duplicate
   detection. Clearly overlapping weather/direction no-call topics were removed;
   arbitrary custom-catalogue unsupported labels still need independent checking.
2. **Entities/values — partly improved:** meaningful generic fictional pools replace
   status words as names/places; full visible mappings are preserved. Automatic
   grounded world generation and human-source imports are not implemented.
3. **Dependency semantics — awaiting a user decision:** typed field references do
   not fit the frozen XML consumer; numeric symbolic references are also blocked
   by its scalar grammar. Grounded scalar-result lookup chains could retain the
   legacy interface; richer references require a new consumer/format. Do not drop
   chaining or silently project fields into whole-result tokens to claim success.
4. **Readable intent payload — implemented:** actual string briefs, quoted typed
   values, generic field humanization, full context and one-pass templates. This
   does not establish that one text format universally beats JSON.
5. **Conditional diversity review — reporting implemented:** distributions remain
   descriptive, not quotas. Broader naturalness/generalization needs real-data
   review and controlled experiments, not a fixed preferred prose style.
6. **Reader recovery/triage — implemented and bounded-live checked below:** keep
   ambiguity and operational errors separate from bad-source claims; inspect
   matches as well as failures. No judge is assumed infallible.
7. **Downstream experiments — still proposed:** preserve group-aware splits and
   compare improvements at fixed goals before any scale-up/training claim.

## Reader/writer repair validation

### Root cause and contract change

The old flat-argument reader still dropped explicit optional fields after generic
re-reading. Two focused source-literal-inventory prompts also failed: they did not
recover either the sample collection/completion dates or the alert limit.
The missing values were present in the actual transmitted request and schemas;
raw model output omitted them without hitting its token limit.

Those failures used Wafer routing. A successful five-call example used another
provider. Wafer's observed alphabetical output ordering was consistent with an
optional-key/decoding interaction, but this is not proof about the provider's
implementation. Pinning a provider was not needed for the smaller repair:

- All declared argument slots are now required on the reader wire.
- A requested value is a closed `{value: ...}` object; an unrequested optional is
  the closed empty object `{}`. Required arguments cannot use the empty branch.
- There are no contradictory presence booleans or a null omission sentinel.
- Canonical calls are reconstructed and checked against the full original schema.
  Neither the slot envelope nor reader retry machinery enters SFT targets.

Both previously failing cases then recovered their optional values in fresh Wafer
calls with the same source request/catalogue/model/temperature. General literal
inventory machinery was not retained after its negative result.

### Actual bounded runs (not cached baseline inference)

| Path under ignored `runs/` | What actually ran and was observed |
| --- | --- |
| `verification-fixes-smoke-v1/reader` | Initial flat contract: 6 accepted, 3 unresolved across 9 selected cases; two unresolved cases were clear requests with omitted optional arguments, one genuinely lacked an ID. |
| `verification-fixes-smoke-v1/literal-evidence-probe` | Two fresh source-only inventory probes; both still omitted fields. |
| `verification-fixes-smoke-v1/slot-schema-probe` | Two fresh slot-contract probes; both recovered on Wafer. |
| `verification-fixes-smoke-v1/reader-slots` | Actual CLI with slot contract: all 8 intended-positive cases accepted, including equivalent UTC notation and five calls; the missing-ID control stayed unresolved. 10 fresh requests, zero cache hits. |
| `readable-writer-smoke-v1/writer` | Three actual temperature-0.9 writer calls using raw readable briefs: scoped alerts/builds, the valid two-date sales pair and a named store. Manual inspection found the supplied values/scopes preserved. |
| `reader-grounding-controls-v1/reader` | Those 3 new requests, visible name-to-ID mapping and a number-word ID all accepted; 3 negative controls remained unresolved. 11 fresh requests, zero cache hits. |
| `verification-fixes-smoke-v1/targeted-replay` | Actual `--replay-from` selected only the 3 original unresolved IDs: 2 clear omissions recovered, genuinely missing ID still unresolved. 4 fresh requests, zero cache hits. |

The guard-control negatives include gold coinciding with a schema example and a
missing required severity. The latter still produced contradictory partial calls
with ambiguous status; these are retained as reader-contract errors/unresolved,
not certified and not labeled bad user requests. LLM output errors remain possible.

Fresh responses and usage are retained in each stage's accounted request evidence.
Together these bounded repair checks cost about one cent; there was no paid bulk
verification, baseline benchmark rerun or training. The cases deliberately target
known failure modes and controls, not a random estimate of corpus-wide accuracy.

### Acceptance and uncertainty

- Declared instants compare by actual timezone-aware time, not exact string form.
  Dates/IDs/names/null omission/array order are not fuzzily normalized.
- Unfiltered searches with optional filters and unfamiliar literal names are valid.
- A narrowly declared opaque-ID guard blocks invented schema examples, while mapped
  IDs and numeric values expressed in words remain supported.
- Retry feedback uses only public request/schema facts; hidden target values never
  enter a reader prompt. Operational failures abort rather than triggering opaque
  retries. Unresolved results are preserved for triage/replay.
- Offline triage reuses current source audits and equivalence checks, marks old
  unbound evidence, rejects duplicates, and never manufactures fresh export proofs.

These checks demonstrate the observed fixes, not perfect semantic judging or
improved downstream model accuracy. Grounded chaining is deferred while independent behavior is established, not
silently claimed from a higher reader pass rate. A subsequent fresh end-to-end
[15-goal independent pilot](independent-pilot-15.md) exercises the repaired nested
sampling, ordered windows and default non-chaining generation, with all failures
retained and separately inspected.

## Source fingerprints at extraction

Paths below are relative to the original `mobile-rl-pilot/` tree:

| Source | SHA256 |
| --- | --- |
| `tool_composition_v3/gen_bias_fixed_v3.py` | `b6ed9029b5db5b18bf6ea71a0482372e67da88bedcdedb3777b0f3ffc03a4949` |
| `tool_composition_v3/run_bias_fixed_writer_v3.py` | `72d55023bd633da7fd3907494e8f5ce85be7fdf4f9eb841b55ad748dac168691` |
| `tool_composition_v3/blind_reader_v3.py` | `94f4ea23157df2de1ccdae092841822c789bbac4b43851f099934c4bd88baaba` |
| `tool_composition_v3/bulk_paraphrases_v4.py` | `1c074f29fc7df99383d87270a1250d37a908e95cbe4cf56f771a21603b0583ff` |
| `tool_composition_v2/prompts.py` | `226afaf118b044e40fc5d9e9d5bad26167203c40737e6a34c3165292947b32bc` |
