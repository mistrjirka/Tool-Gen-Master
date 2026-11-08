# Why the saved prompts look this way

## Scope and evidence

This is a source-and-artifact audit, not a new LLM-quality experiment. The source
is the active bias-fixed pipeline formerly under
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

No paid generation, training, promotion or benchmark rerun was performed for this
migration. These remain synthetic data, not newly imported human-source requests.
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

The sampler replaces an arbitrary argument with `API_call_N`, independently of
what the preceding tool returns. It can then shuffle calls without remapping the
indices. There are no declared output schemas or field selectors behind these
references. The writer converts the token to “the value returned by operation N”,
which hides the implementation token but does not make the dependency feasible.

Meanwhile, the reader prompt forbids inventing dependencies on unknown results,
and numeric/enum argument schemas cannot represent those string placeholders.
A reader can therefore object to an intended chain even when its prose is
understandable. Conversely, a writer can invent a dependency in an otherwise
independent goal and still obtain a matching call list.

Do not infer that all chains are bad or remove them merely to improve acceptance.
They need grounded outputs, typed reference paths and reference-safe ordering.
The migrated sampler retains this experimental behavior for reproducibility and
does not claim that semantic chaining has been solved.

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

## Changes made by extraction vs work still proposed

Implemented: standalone modules and resources; no old absolute imports; shared
JSONL/run handling; separate model settings; full declared schemas and visible
context for the reader; uncapped call arrays; clearer error provenance; descriptive
pattern reports; soft rather than enforced lexical diversity guidance.

Preserved as a reproducible baseline: domain/call/style sampling, opaque ID
generation, generic value pools, experimental chaining and the overbroad
near-duplicate rule. The port is not advertised as a new high-quality dataset.
Frozen datasets, training renderers/scorers and saved benchmark outputs are not
modified. Reader-prompt changes have not been validated with fresh inference here.

## Proposed improvements, not blanket rules

1. **Fix mechanical construction first:** visible-tool membership, schema-first
   enum/type/range sampling and correct no-call capability labels. These have
   concrete correctness evidence, unlike aesthetic preferences.
2. **Ground entities and values:** meaningful domain values and real visible
   name↔ID mappings where needed. Keep ID-only requests as part of the range.
3. **Make dependency semantics real:** output schemas, field/collection selectors,
   compatible argument types and stable references through any reordering.
4. **Improve the intent payload:** preserve typed constraints and their scope
   without priming a field-by-field transcript. Keep explicit independent needs
   independent; do not invent a story to connect them.
5. **Review diversity conditionally:** styles, lengths, openings and repeated
   patterns conditioned on call count/domain/intent, rather than a universal
   “good” distribution. Lists and concise technical requests may be appropriate.
6. **Evaluate semantic fidelity and naturalness separately:** randomly inspect
   reader matches as well as failures; keep operational errors separate from
   ambiguous requests. Recheck a representative pilot before any new bulk run.
7. **Use measured experiments:** compare prompt/payload changes at the same goals,
   record budget and settings, and retain group-aware splits for paraphrases.
   Do not claim better downstream performance without a corresponding run.

## Source fingerprints at extraction

Paths below are relative to the original `mobile-rl-pilot/` tree:

| Source | SHA256 |
| --- | --- |
| `tool_composition_v3/gen_bias_fixed_v3.py` | `b6ed9029b5db5b18bf6ea71a0482372e67da88bedcdedb3777b0f3ffc03a4949` |
| `tool_composition_v3/run_bias_fixed_writer_v3.py` | `72d55023bd633da7fd3907494e8f5ce85be7fdf4f9eb841b55ad748dac168691` |
| `tool_composition_v3/blind_reader_v3.py` | `94f4ea23157df2de1ccdae092841822c789bbac4b43851f099934c4bd88baaba` |
| `tool_composition_v3/bulk_paraphrases_v4.py` | `1c074f29fc7df99383d87270a1250d37a908e95cbe4cf56f771a21603b0583ff` |
| `tool_composition_v2/prompts.py` | `226afaf118b044e40fc5d9e9d5bad26167203c40737e6a34c3165292947b32bc` |
