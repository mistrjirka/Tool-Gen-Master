# Measuring patterns without turning them into rules

## Run the report

```sh
tool-gen analyze --input path/to/train.jsonl --output patterns.json
tool-gen analyze --input runs/writer/shard-*/results.jsonl --output writer-patterns.json
```

This is offline: no credentials, API calls or model inference. The command accepts
raw goals, writer records, reader records, single/batched paraphrases and the SFT
message/tool-call format. A batched paraphrase record contributes one sample per
generated variant. SFT user messages and assistant calls are concatenated within
their row; this is a row-level report, not a multi-turn dialogue evaluator.

Invalid JSON objects fail with file/line context. Unsupported record shapes are
counted with bounded diagnostic examples; they are not quietly interpreted as
no-call examples. Reports always disclose input coverage and relevant
denominators. Missing eligible observations yield `share: null`, not a fictitious
0%. A report does not return a failing exit status merely because a distribution
is uneven.

Analyze one artifact layer at a time for comparison. Feeding both goals and their
writer outputs counts the same underlying task twice for structural statistics;
the tool does not silently deduplicate requested inputs. Group-size distributions
help reveal augmentation/repeated parents.

## What is measured

| Family | Measurements and interpretation |
| --- | --- |
| Openings and wording | Top first words and opening phrases, entropy, sample-incidence 2–5-grams, exact repeated requests and value-masked templates, with counts/examples. Common phrases are not automatically wrong. |
| Format and length | Leading bullet/number markers, separate “Checklist” prefixes, word-count range/median and ≤5-word share. This does not detect every prose list. |
| Implementation-shaped text | Literal camelCase/snake_case argument names and `API_call_N` in requests. Inspect context before inferring leakage: technical wording or quoted literals can be legitimate. |
| Names/IDs | Explicit “ID/identifier/SKU/code” wording, ID-like/name-like argument leaves, ID prefix distributions, per-key value frequencies. These are labeled heuristics, not inferred entity identity. |
| Call/catalogue structure | Call-count/catalogue-size distributions, separately called vs available tool frequencies, observed-category entropy/Gini, target calls absent from their catalogue. |
| Ordering | Alphabetical argument order on multi-argument calls only; schema-relative order of the supplied key subset; alphabetical and catalogue-relative call order only where at least two distinct tools are present. |
| References and values | Reference-token incidence, scalar leaf types, repeated values by leaf key. Token incidence does not establish feasible chaining. |
| Repetition/provenance | Repeated target-call multisets plus catalogue names, declared domains/styles/splits/augmentation, parent-group sizes and recorded outcomes. Intentional paraphrases should repeat targets. |

### Avoid known measurement mistakes

- Single-argument calls are trivially alphabetical; including them inflates the
  apparent argument-order bias.
- Schema order must compare the supplied subset, not demand equality with every
  optional property in the schema.
- An ID metric must examine ID-like argument keys, not classify every long string
  (including timestamps) as an identifier.
- Zero-call requests with different unsupported intents are not all one duplicate
  task; they are excluded from repeated target-call measurements.
- Repeated n-grams count a phrase at most once per sample, not once per occurrence.
  Value masking can still merge different intents: it is a template candidate,
  not a semantic duplicate detector.
- JSON key order may be imposed by serialization. It is not necessarily a model
  preference, and it need not be harmful.
- Gini covers observed categories only. It does not measure how many tools from a
  larger intended universe are entirely missing.
- Per-key value frequencies pool matching leaf names across tools. For example,
  different tools' `status` enums are not guaranteed to mean the same thing.
- A reader failure is a recorded outcome, not a synonym for a genuinely bad goal.

## First real-data report

Sources are the saved `tool-data/coherent-v4-sft/train.jsonl` and the saved
30-example bias-fixed pilot writer records. No inference was rerun. Full local
outputs are under ignored `runs/analysis/coherent-v4-patterns.json` and
`runs/analysis/pilot-30-patterns.json`; input datasets are not bundled/published.

| Measurement | Saved coherent v4 | Saved pilot |
| --- | ---: | ---: |
| Rows/text samples | 4,976 / 4,976 | 30 / 30 |
| Bullet/number markers | 739/4,976 = **14.9%** | 5/30 = **16.7%** |
| “Checklist” prefix, separately measured | 57/4,976 = 1.1% | 1/30 = 3.3% |
| Literal camelCase/snake_case argument names | 538/4,976 = **10.8%** | 6/30 = **20.0%** |
| Explicit ID/identifier/SKU/code wording | 2,207/4,976 = 44.4% | 18/30 = 60.0% |
| ID-like argument samples, heuristic | 3,389/4,976 = 68.1% | 18/30 = 60.0% |
| Name-like argument samples, heuristic | 859/4,976 = 17.3% | 8/30 = 26.7% |
| Alphabetical argument order, ≥2 arguments | 604/2,488 = 24.3% | 3/12 = 25.0% |
| Schema-relative argument order, eligible ≥2 arguments | 2,430/2,430 = **100%** | 12/12 = **100%** |
| Target calls absent from row's catalogue | **333/12,115 calls** | **1/70 calls** |
| Additional rows sharing a value-masked template | 354/4,976 = 7.1% | 0/30 |
| Word-count median | 14.5 | 18.5 |

ID/name categories can overlap within a row and include no-call rows in the row
denominator. Bullet markers and “Checklist” prefixes can overlap too; do not add
their shares as disjoint categories. The template figure counts extra rows beyond
each first occurrence, not the fraction of all rows in repeated groups.

Interpretation:

- Schema-relative ordering is a real construction pattern. It is not proof of
  downstream harm; counterbalancing it is an experiment, not an automatic fix.
- List prevalence alone cannot tell whether lists are appropriate for these
  tasks. Inspect examples by intent and call count before changing style weights.
- Literal field wording and tiny value pools explain why some requests feel
  artificial. Both should be considered alongside valid technical-user styles.
- Calls absent from their own catalogue are a correctness issue, unlike an
  aesthetic preference. Diagnose and fix the sampler before scaling.
- The 30-row pilot is too small to establish stable distribution changes versus
  v4, and the samplers differ. These are descriptions, not a controlled A/B result.

## Using the measurements

1. Keep the target use case explicit; no corpus has to be uniform over all tools,
   names, styles or opening words.
2. Compare compatible data layers, preferably holding goals constant when changing
   wording prompts. Domain/call-count changes can explain a surface-pattern change.
3. Inspect both common patterns and random cases. Do not look only at reader
   failures or declare every uncommon phrase desirable.
4. Decide whether an observed pattern is useful, harmless, an unwanted shortcut,
   or a genuine correctness defect; record the evidence for that decision.
5. Only then change a sampler/prompt and run a bounded quality experiment. Do not
   filter existing data using arbitrary “bias thresholds”.

This report is not a human-likeness classifier, semantic feasibility verifier,
privacy/leakage audit, or proof of downstream generalization. Those require
different evidence. The next improvement proposals are in
[prompt-analysis.md](prompt-analysis.md#proposed-improvements-not-blanket-rules).
