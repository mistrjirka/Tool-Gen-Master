# tool-gen — standalone current-generation pipeline

Port of the `mobile-rl-pilot/tool_composition_v3` current generator (goal
sampler `gen_bias_fixed_v3.py`, writer `run_bias_fixed_writer_v3.py` /
`bulk_writer_v4.py`, blind reader `blind_reader_v3.py`, paraphrases
`bulk_paraphrases_v4.py`, export `convert_to_sft.py`). Generates candidate
tool-calling requests: seeded goals → writer → blind reader → paraphrases →
SFT export. Pattern reports describe the data; neither a writer acceptance nor
a reader match proves that a request is natural or its goal is feasible.

## Layout

```text
src/tool_gen/
  goals.py                  seeded sampling (compatibility baseline)
  writer.py / reader.py     request creation and independent interpretation
  paraphrase.py / export.py augmentation and SFT conversion
  analysis.py / validate.py descriptive patterns and mechanical goal audit
  models.py / store.py      checked records, JSONL, run state and provenance
  client.py / cli.py        accounted API calls and command-line entry point
  catalogs/data/            16 domains, 64 tool declarations, one JSON per domain
  prompts/                 separate writer/, reader/ and paraphraser/ Markdown
docs/                      prompt-cause analysis and bias measurement guide
```

## Install

```sh
pip install .
# or editable
pip install -e .
```

Requires Python ≥ 3.10 and a Unix-like system (the client uses `fcntl` file
locks). Dependencies are declared in `pyproject.toml`. No path hacks or network
calls at import time; prompts and catalogs ship as package resources, so the
installed wheel does not depend on the original project or its filesystem.

Set `OPENROUTER_API_KEY` in the calling process environment for paid stages.
Offline goals, audit, export and analysis commands need no credentials. Raw data,
run evidence and `.env` files are ignored by Git.

## Pipeline

Every paid stage owns one shard directory, `<root>/shard-N`, holding the
budget ledger, a stage `manifest.json` and the stage output rows. The manifest
pins input content hashes, prompt text and config (temperature, model, budget,
shard settings); resuming with any changed pin is refused — use a fresh root
instead. Already-recorded ids are skipped only when the pins match. Budget caps
are **per shard**, not a shared global cap.

The sampler is intentionally a reproducible migration baseline with known defects,
not a claim that new bulk data is ready. Inspect the goal audit before spending
on a generation batch. The example below uses one worker per stage.

```sh
# 1. Seeded goals (reproducible: same seed → same goals.jsonl)
tool-gen goals -n 30 --seed 21 -o goals.jsonl

# 2. Mechanical goal audit: unknown tools, bad enums/types, forward
#    API_call_<i> refs. Fix generator defects here — never blame the reader.
tool-gen audit --input goals.jsonl

# 3. Writer: natural requests (temp 0.9 default). --out is a stage root;
#    this shard owns <root>/shard-N (ledger + manifest + results.jsonl).
tool-gen writer --goals goals.jsonl --out runs/writer \
  --temperature 0.9 --max-usd 1.00
# resume: re-run the same command; recorded goal ids are skipped when pins match.
# --max-usd none selects the separately authorized uncapped full build.

# 4. Blind reader: verify requests against complete tool schemas (temp 0.0).
#    --input accepts one writer results.jsonl or a stage root holding every
#    shard's results.jsonl; all rows are combined first, then sharded here,
#    so writer shards are never double-sharded. Each accepted verdict stores
#    a content fingerprint (id+request+tools+full visible context+
#    witness/no_call) binding it to its exact source; the fingerprint is
#    never sent to the reader.
tool-gen reader --input runs/writer --out runs/reader --temperature 0.0

# 5. Paraphrases: exactly 3 distinct registers per accepted request.
tool-gen paraphrase --writer runs/writer --out runs/para

# 6. Export to SFT rows (no-call literal '<no_call/>' preserved).
#    Without --verification rows are writer-only; with a reader results file
#    or root, only goals whose content fingerprint matches an accepted
#    verdict are kept (stale ids without matching proof abort with an
#    explicit error). The manifest says writer-only vs verified.
tool-gen export --input runs/writer --output sft/train.jsonl
tool-gen export --input runs/writer --verification runs/reader \
  --output sft/train.verified.jsonl
tool-gen export --paraphrases runs/para --output sft/para.jsonl

# 7. Pattern/bias report over JSONL files (implemented in tool_gen/analysis.py).
tool-gen analyze --input runs/writer/shard-0/results.jsonl --output report.json
```

For parallel work, run distinct `--shard N --shards K` invocations for every
`N` from `0` through `K-1`, using the same stage root. Each owns its own
`shard-N` ledger. Combine the full writer root before sharding the next stage;
do not shard an already-isolated writer subset a second time.

On transport or budget failure the current row is recorded, the manifest is
marked aborted, unprocessed goals are left unwritten, and the command exits
nonzero. Failed transport rows are not retried in place. A fresh output root
reprocesses all selected rows, so use it deliberately rather than to conceal
previous failed or billable attempts.

## Prompts

Editable Markdown under `src/tool_gen/prompts/` (shipped in the wheel):

- `writer/base.md` — request contract (realistic requests, exact literals).
  Both stages receive the same actual full visible context object (all
  name-to-ID mappings and records, never truncated); only private
  fixtures/witness stay hidden.
- `writer/bias_fixes.md` — soft style preferences (register diversity,
  natural length, lists where a person would use them) plus hard
  requirements (fidelity/scope, exact literals, no `API_call_N` in
  user-visible text, no invented dependencies between independent
  operations). Literal identifiers need not always be introduced with
  "ID", without renaming opaque IDs into invented titles or changing
  name-to-ID semantics.
- `reader/base.md` — blind interpreter contract.
- `reader/targeted.md` — full student-visible prompt + `argument_presence`
  per declared argument, uncapped call count.
- `paraphraser/base.md` — 3-register rewrite contract.

`API_call_N` tokens never reach writer- or paraphraser-visible text (chained
arguments are verbalized as "the value returned by operation N"); the reader
schema has no call-count cap.

## Measurement, not moralizing

Reports describe measured patterns (register mix, opener concentration,
id-argument rates, chain rates) without hard rules: prompt suggestions stay
suggestions, lists and identifier styles are not banned, and "bias" is
reported as a distribution, never an automatic defect.

Intentional writer-policy delta: the pilot's hard opener-concentration
rejection quota and forced ~10% terse rewriting were aesthetic distribution
gates, not semantic invariants, and are removed here. Seeded goal sampling
remains byte-identical to the source at the checked seeds (21, 7 and 42 on
Python 3.14.9). Writer policy and the migration corrections documented here
are separate from that generator-parity claim. Prompt-quality gains from the rewritten
`writer/bias_fixes.md` have not been measured — no paid model calls were
made for this migration. See `docs/prompt-analysis.md` and
`docs/bias-analysis.md` for the analysis write-ups.

## SFT row and manifest labels

Each exported row:

- `messages` — an optional leading `system` message carrying the full
  visible context as JSON (only when the goal has nonempty context; empty
  context exports no system message and stays byte-identical to the legacy
  envelope), then the `user` request, then `assistant` with `tool_calls`
  (`[{type: function, function: {name, arguments}}]`, deep-copied witness
  calls) or the exact no-call literal `'<no_call/>\n'`.
- `tools` — the goal's full catalog snapshot used for that request.
- `source: coherent_v3`, `provenance: coherent_v3_bulk` — origin labels kept
  from the original converter.
- `augmentation: none` for writer rows, `paraphrase:<register>` for
  paraphrase rows.
- `parent_group` — the goal's `group_id` (groups SFT rows by source goal).
- `split` — preserved from the goal (the sampler currently emits `train`);
  `length` — kept `0` as in the original converter, not a token-length
  measurement; `id` — the goal id; `request` — the exported text.

Each export manifest: `status: coherent_v3_bulk` (origin label kept from the
original converter), `rows`, `source`, and `verification` — `none`
(writer-only, not reader-checked), `reader-verified` (every row's content
fingerprint matched an accepted reader verdict), or
`parent-verified-paraphrases-unverified` (paraphrase export: parent goals
carry matching reader proof, but the rewritten paraphrase strings themselves
were never reader-checked).

## Known quirks (preserved for parity, not fixed)

- `group_id` is `sha256(str(calls))` over the Python repr — repr-sensitive.
- Domain insertion order and parameter-property key order affect the seeded
  random stream. Sorting catalogue JSON keys is not a behavior-neutral change.
- Chained `API_call_<i>` values are unresolved plain strings; there is no
  output schema or typed reference behind them. Semantic chaining is not
  claimed as solved.
- Sampled ID arguments draw from fresh per-argument pools; shared-entity
  references are not intentionally constructed. A `grounded` label alone
  does not populate visible records or name-to-ID mappings.
- A witness call can name a family tool missing from the goal's sampled
  catalog (the 75% family-tool branch draws from all family tools, not just
  the sampled catalog subset). `tool-gen audit` flags these as unknown-tool
  goal errors; the source generator has the same defect.
- No-call topics are chosen deterministically per goal id
  (`Random('unsup:<id>')`), not from the shared RNG stream: repeated runs
  construct the same no-call intent payload and can reuse an identical cached
  request. Fresh model outputs are still stochastic at temperature 0.9.
  No-call payload selection is a documented delta, not a promise that fresh
  LLM generations are deterministic.
