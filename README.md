# Tool-Gen-Master

Standalone generation and verification of candidate tool-calling data. The
pipeline samples goals, writes human-like requests, independently interprets
them, and exports SFT records. Descriptive reports reveal patterns without
turning every bias into a defect.

**Independent calls by default:** the sampler emits independent calls only; the
legacy `API_call_N` placeholder injection is removed. Imported legacy goals that
still carry such references are not grounded in declared outputs: they are
flagged as invalid goals and are not certified by the reader. Choosing a future
reference contract remains out of scope; see [prompt analysis](docs/prompt-analysis.md).
Do not treat this as authorization to start bulk generation or training.

## Install

```sh
pip install -e .
```

Python >=3.10 and a Unix-like system (`fcntl` protects cost ledgers). Dependencies
are in `pyproject.toml`; catalogues and prompts ship in the wheel. No original
project checkout or absolute filesystem paths are needed. Set
`OPENROUTER_API_KEY` in the process environment for paid stages. Offline commands
need no credentials. Raw data, run evidence and `.env` files are Git-ignored.

## Layout

```text
src/tool_gen/
  goals.py                  seeded structural sampling / legacy fixed goals
  creation.py / quality.py semantic creator and separate quality judge
  writer.py / paraphrase.py readable briefs for fixed goals and request generation
  reader.py                 blind interpretation and bounded recovery
  comparison.py             schema-aware call equivalence
  triage.py / analysis.py   failure diagnosis and descriptive patterns
  validate.py / models.py   mechanical audits and checked records
  store.py / client.py      provenance, JSONL, accounting and API transport
  cli.py                    command-line interface
  catalogs/data/            16 domains / 64 tools, one JSON per domain
  prompts/                  packaged creation/, quality/, writer/, reader/, paraphraser/
docs/                       original audit, repair evidence and measurement guide
```

## Semantic creation (preferred for new human-like candidates)

```sh
tool-gen create -n 15 --seed 426 --out runs/semantic --max-usd 0.50
# Optional later blind reconstruction; it is not the semantic quality judge.
tool-gen reader --input runs/semantic --out runs/semantic-reader
```

The program samples an allowed catalogue, call count and schema-derived argument
shapes. It discards the old draft's sampled values and chosen calls. A model then
chooses a new useful goal, fictional values, independent calls and natural request.
There are no manually written production scenarios or per-domain story templates.

```text
catalogue + structural controls -> creator -> hard validation -> quality judge
                                      ^                            |
                                      +--- bounded new candidate --+ problem
                                                                  |
                                                     accepted / unresolved
```

The separate judge evaluates the whole item and each operation's information
gain/value roles. It sees the candidate goal deliberately; it is not a blind
reader. Known-only projections are warnings to assess, not a universal ID ban.
Independent batches remain allowed. Limits do not imply sorting; assistant
reasoning over retrieved data does not require a dedicated analytics tool.

One capped ledger covers creator (0.9) and judge (0.0) requests per shard.
`--max-attempts 2` bounds recovery; judge output errors re-judge the retained
candidate, quality problems can generate a new one, uncertainty stays unresolved.
Operational errors abort with evidence and leave later inputs unwritten.

Each shard contains immutable `specs.jsonl`, canonical `creation.jsonl` with all
attempts/assessments, and an atomically derived accepted-only `results.jsonl`
compatible with existing export/reader/paraphrase commands. IDs/splits/group hashes
are server-owned. Changed specs/prompts/config refuse resume; accepted rows are
not regenerated on a no-op resume. The judge is fallible: see the
[15-item semantic pilot and manual corrections](docs/semantic-creation-pilot-15.md)
and the [100-item direct and independent review, with every example](docs/semantic-review-100.md).
The latter retains 12 unresolved candidates for inspection; it is not 100 approved
training rows and documents both judge false accepts and false rejects.

Quality acceptance is **not reader verification**. Export without reader proofs
retains `verification: none`; it never fabricates a blind-reader proof.

## Fixed-goal and verification commands

The existing `goals` + `writer` path remains available for reproducible mechanical
sampling or supplied, already-bound goals. It does not gain semantic value
creation merely because the writer rephrases it.

```sh
# Offline goal sampling and mechanical audit. Inspect audit problems before API spend.
tool-gen goals -n 30 --seed 21 --output goals.jsonl
tool-gen audit --input goals.jsonl

# Paid writer: actual user-message content is a readable, deterministic brief.
tool-gen writer --goals goals.jsonl --out runs/writer --temperature 0.9 --max-usd 1.00

# Paid blind reader: full public schemas/context, no gold values in its prompt.
# At most two attempts per valid goal by default; no transport/budget retries.
tool-gen reader --input runs/writer --out runs/reader --max-attempts 2 --temperature 0.0

# Offline diagnosis: not a fresh reader verdict and never an export proof.
tool-gen triage --input runs/writer --results runs/reader --output triage.jsonl

# Explicit paid replay of unresolved IDs, including repaired formerly-invalid goals.
# The fresh output root must be outside the original reader-results root.
tool-gen reader --input runs/writer --replay-from runs/reader --out runs/replay

# Paid augmentation: exactly three usable, distinct-register rewrites.
tool-gen paraphrase --writer runs/writer --out runs/paraphrases

# Export writer-only originals, or filter to matching reader-accepted source proofs.
tool-gen export --input runs/writer --output sft/writer-only.jsonl
tool-gen export --input runs/writer --verification runs/reader --output sft/verified.jsonl

# Parent verification does not certify rewritten paraphrase strings.
tool-gen export --paraphrases runs/paraphrases --verification runs/reader --output sft/paraphrases.jsonl

# Offline distributions, recurrent phrases/templates, IDs/names and ordering.
tool-gen analyze --input runs/writer/shard-*/results.jsonl --output patterns.json
```

Reader/paraphrase/export inputs accept a result file or a stage root containing
shard files. `analyze` accepts explicit JSONL files, including shell-expanded
shards. `triage` supports current reader output and the original
`results-shardN.jsonl` artifacts. Conflicting/duplicate IDs fail explicitly;
missing artifacts and incomplete historical evidence are not guessed away.

## Writer inputs and creative variation

The system instructions and readable-brief template are separate Markdown
resources. Literal strings are quoted, numbers retain their types, and all
visible context is preserved. Each need carries its operation description
plus the schema meanings of its supplied choices (inclusive endpoints,
units, bounds, projection roles) without echoing parameter labels; schema
illustrations are not facts. Template substitution
is one-pass: names or records containing template-looking text stay unchanged.
The client sends the rendered text itself, not JSON containing escaped newlines.
Structured input remains useful internally; this is not a claim that Markdown
universally outperforms JSON.

Writer/paraphraser temperature is 0.9; reader temperature defaults to 0.0. Style
hints are not lexical quotas. IDs, names, terse requests, lists and formal language
remain allowed. The writer must preserve intent, literals, scope and genuine
sequence/dependencies; it must not invent links between independent requests.

## Reader contract and outcomes

The reader never receives target calls, writer judgments, expected values or a
source fingerprint. Its wire contract makes one value decision per argument:

```json
{
  "sampleType": {"value": "water"},
  "collectedOn": {"value": "2025-06-01"},
  "limit": {}
}
```

Every declared argument key has a slot. Required arguments must have a value;
optional `{}` means omitted. `{"value": null}` is distinct and allowed only when
the tool's own schema allows null. There are no redundant presence booleans.
The application unwraps this to ordinary arguments and validates the original
full tool schema. The slot envelope never reaches SFT output. Calls are uncapped.

```text
source preflight -> blind reading -> unwrap + schema/source checks -> compare
       |                                      |                       |
   invalid_goal                          reader error          match/equivalent
                                              |                       |
                                   bounded blind recovery          accepted
                                              |
                                          unresolved
```

- `accepted`: reconstructed status/calls match, including safe equivalence.
- `unresolved`: ambiguity, differences or reader failures remain after the bound.
  **This is not a declaration that the request is bad.**
- `invalid_goal`: the supplied target/catalogue violates the source contract;
  no model request is made. This concerns the artifact, not whether its prose
  sounds human.

Retries use only the same public request/schema/context plus public-contract
feedback, never hidden expected arguments. Each attempt is retained. `OutputError`
(model JSON/schema/empty-output failures) can recover; operational `ClientError`
and budget/transport failures abort with evidence, leaving later goals unwritten.

Safe equivalence is narrow: only explicitly declared instants (including the
exact legacy instant declaration) are normalized across timezone/precision
representations. No timezone is assumed. Dates, names, opaque IDs, null versus
omission and array order stay exact. Independent calls may reorder; multiplicity
is preserved. Unsupported dependency encodings are not treated as literal equality.

A narrow anti-hallucination check rejects opaque identifiers invented from schema
examples when absent from the request/visible context. It does not impose wording
rules on names, enums or numeric IDs; visible name-to-ID mappings remain usable.
It is not a complete semantic grounding proof.

Offline triage shares the audit/comparator, labels equivalent representations,
flags possible false ambiguity and separates missing evidence from model errors.
Historical fingerprint-less rows remain `legacy_unbound`. Reports cannot certify
exports. Replay performs fresh, accounted reader requests in a distinct run root.

## Sharding, accounting and provenance

`--out` is a stage root. For parallel work run `--shard N --shards K` for every
index from 0 to K-1. Each owns `<root>/shard-N`: ledger, manifest, immutable API
evidence and result rows. Budget caps are **per shard**, not a pooled global cap.
`--max-usd none` explicitly opts into account-credit-limited spending.

Manifests pin source-file hashes, prompts/templates, contract/config and shard
settings. Changed pins refuse in-place resume. Recorded results are preserved;
transport-failed rows are not silently resent. A deliberately fresh root retries
selected inputs at new cost. Reader proofs bind exact source content
(id/request/tools/context/target/no-call status), never just IDs. Stale accepted
IDs with different content cannot certify an export.

## SFT compatibility

Original datasets, renderers, scorers and saved benchmark outputs are untouched.
Exports retain the existing assistant `tool_calls` envelope and exact
`<no_call/>\n` literal. Nonempty visible context is a leading system message.
Source split/group identifiers are preserved; `length: 0` is legacy metadata,
not a token count. Legacy `source: coherent_v3` / `provenance: coherent_v3_bulk`
labels are retained from the converter.

Manifests distinguish `none` (writer-only), `reader-verified` (matching source
proof) and `parent-verified-paraphrases-unverified` (parent proof only). Uncovered
or reader-unresolved rows are skipped with counts; stale proofs abort.

## Sampling corrections and limitations

The initial migration (`64590b9`) preserved the old sampler. Subsequent repairs
change seeded outputs intentionally: enum/type/range correctness, visible-tool
membership, meaningful generic name/place values, recursive array/object sampling,
ordered reading windows and value-aware duplicate checks. The valid two-date sales
example is no longer rejected merely for sharing a tool.
Same-version seeded runs remain reproducible; cross-version byte parity is not
promised. Domain/property ordering still affects the random stream.

`group_id` remains a hash of the call-list representation. Fictional values and
visible-context support do not turn the sampler into a simulated world. Chaining
still awaits its explicit contract decision; no broad quality/performance gains
are claimed from a small reader smoke. No human-source dataset was imported.

See [the fresh 15-goal independent pilot, including all failures](docs/independent-pilot-15.md),
[prompt causes and repair evidence](docs/prompt-analysis.md) and
[bias measurements](docs/bias-analysis.md). No bulk generation, training,
checkpoint promotion or benchmark rerun is implied by these commands.
