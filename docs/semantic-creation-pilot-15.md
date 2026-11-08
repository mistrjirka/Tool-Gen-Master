# Semantic creation: implementation and 15-item manual pilot

## Implemented boundary

The program samples allowed catalogues and structural controls. It reuses the
seeded sampler for those controls, but **discards its sampled parameter values and
chosen calls** before model invocation. The creator jointly chooses a new
information need, fictional parameter values, independent calls and natural text.
No per-domain production scenarios, value whitelists or story templates were added.

Hard checks enforce catalogue membership, original schemas, selected call count,
argument shapes, window ordering, value-aware duplicate handling and no chaining.
A separate judge assesses whole-item usefulness/value roles/fidelity/language and
each indexed operation's new information and parameter fit. Server code owns
IDs, splits, hashes, context and acceptance. Judgments never silently edit targets.

Canonical creation.jsonl retains attempts and quality/error evidence; accepted
WriterResult-compatible results.jsonl is derived atomically. Errors and ambiguity
remain visible. Existing writer/reader/export formats, original datasets and
frozen consumers/scorers are unchanged. Quality acceptance is not a reader proof.

## Evidence and failed hypotheses

All calls used deepseek/deepseek-v4.1-flash through the actual BudgetedClient:
creator 0.9, judge 0.0. No reader invocations, training or benchmark reruns occurred.

- Initial whole-item judge calibration rubber-stamped all five old controls.
- Indexed per-operation review caught the known-only alert projection, but early
  calibrations also wrongly penalized unrelated batches, useful mixed projections
  and a valid unsupported request. Those failed results were preserved.
- Focused final calibration accepted the unsupported stock-price case and a
  projection with both known ID and new name, and flagged an ID-only projection
  with no existence-check intent.
- A final role check **still accepted** the old holder value "reference note".
  This is a known judge blind spot. We do not claim automatic role judgment is
  reliable merely because it produces detailed explanations.
- A separate schema-role generation probe offered searchPolicies/searchHotels,
  without hand-written values or requests. It generated hotels in Lisbon with
  rating at least 4 and health policies for holder Marta Silva. This is evidence
  the new generator can fill these roles without the old small pools, not a
  universal role-quality guarantee. It is separate from the 15-item cohort.

## Main run and manual correction

The pre-outcome structural selection used seed 426 and 15 slots, spanning twelve
primary families and all six style hints, including object/array/unfiltered
requirements. This was a coverage-focused pilot, not a random quality estimate.

The actual CLI run completed with 15 machine-accepted terminal records, 35 fresh
model requests and $0.016525 reported spend. It exercised:

- hard-invalid near-duplicate rejection followed by new generation;
- recovery from two empty creator outputs;
- a real quality rejection for an extra requested action without a target call,
  followed by a new candidate;
- typed canonical records and accepted-compatible output.

**The machine's 15/15 was not the manual quality verdict.** Reading every item
against its actual contracts found two additional issues the judge missed:

1. semantic-426-0009 asked for the "most recent" alerts/outages while using limited
   list calls whose contracts promise no ordering.
2. semantic-426-0012 justified no_call by absent analytics APIs. An assistant may
   compare/analyze retrieved data; lack of an analysis function alone is not a
   capability gap. Missing court/state details made the example less defensible.

Generic capability rules were clarified in creator and judge prompts: limits are
not ordering, retrieve enough data for subsequent reasoning, analysis need not be
an API, missing details alone do not establish unsupported capability, and dated
canonical calls require an absolute or context-grounded date.

Only those two structural slots were regenerated, using shards 9 and 12 of the
same 15-spec input. Both replacement inputs have the exact original spec-file
hash. Original outputs and failures remain immutable. Targeted runs added five
fresh requests and $0.004235; one empty creator output recovered.

The reviewed set retains all 15 source identities, with those two explicitly
versioned replacements. It uses 27 distinct tools across 13 actual call domains;
two items are unsupported requests. Fifteen groups are distinct. It has a mix of
zero through five calls. No result was replaced merely for having an unfamiliar
name, independent tasks, terse wording or a list.

## Manual inspection of all 15 final candidates

### 1. semantic-426-0000

> Please do these three things for me: 1) read the book record with identifier BK-4827; 2) read borrower number 764 and show only the name field; 3) search books where the author is exactly "Mirella Vance", the genre is poetry, and the publication year is 1994, returning at most 12 results.

Calls: `getBook`, `getBorrower`, `searchBooks`.

Assessment: Useful library batch: a book lookup, a borrower name lookup and a poetry search. The nested filter has role-appropriate author/genre/year values. More like an operator's task list than a single story, which is allowed.

### 2. semantic-426-0001

> Hey, could you do a few quick lookups for me? First, search for posts by marisol.vane that mention "ferry timetable", and cap it at 12 results. Then pull up the article with slug ART-harbor-lanterns-7. Finally, for item WH-7714, just show me the sku and binCode.

Calls: `searchPosts`, `getArticle`, `getItem`.

Assessment: A deliberately independent batch across posts/article/inventory. The username now looks like a handle, and the inventory projection returns a new bin location, not just its known SKU. Coherence remains weaker than the single-domain items.

### 3. semantic-426-0002

> Get book BK-4471 with title, author, and year only. Also get customer CUST-9032 with customerId, name, and tier only. Then list maintenance for machine MCH-2207 after 2025-10-01T08:00Z, max 3 rows. Then readings for meter MTR-7742 from 2026-02-01T00:00+01:00 to 2026-02-28T23:59+01:00, minKwh 12.5, max 25 rows. Finally search electronics products named wireless keyboard KX-8, max 10 rows.

Calls: `getBook`, `getCustomer`, `listMaintenance`, `listReadings`, `searchProducts`.

Assessment: One of the weaker broad batches: book/customer/maintenance/meter/products. Values are plausible, but some raw minKwh/field terminology remains. Keep as a technical stress example, not a model of ordinary conversation.

### 4. semantic-426-0003

> Hey, could you pull a few things for me? First, list all active outages that started on or after 2024-03-15. Second, grab the meter info for MTR-4482 but just give me the meterId and tariffCode fields. Third, show me the readings for MTR-4482 between 2024-04-01T00:00Z and 2024-04-30T23:59Z, but only ones with a minimum of 12.5 kWh. And finally, list wheat crops harvested after 2024-07-01.

Calls: `listOutages`, `getMeter`, `listReadings`, `listCrops`.

Assessment: Three energy queries share a meter identifier, without depending on tool output; the crop query is an extra independent task. Boundaries and the 12.5 kWh threshold are clear.

### 5. semantic-426-0004

> Please pull together three things: (1) the soil samples collected on 2025-03-14, capped at 12 rows; (2) the passing assay runs completed at or after 2025-02-01T08:30Z with a yield of at least 0.82, capped at 20 rows; and (3) the record for sample SMP-7314, showing only sampleId, collectedOn, and site.

Calls: `listSamples`, `listAssayRuns`, `getSample`.

Assessment: A plausible laboratory retrieval batch with a collection date, yield threshold and useful sample projection. No source fallback entity names.

### 6. semantic-426-0005

> hey, pull up build BLD-7781 but just the branch, status and start date; also grab alert 41207 in full; then show me every failed build no matter the branch or day; and finally the first 12 critical alerts from 2024-11-05T22:15Z onwards

Calls: `getBuild`, `getAlert`, `listBuilds`, `listAlerts`.

Assessment: A plausible build-operations message. Omitted branch/date filters are explicitly unconstrained; selected fields include new information.

### 7. semantic-426-0006

> Show me every production run and tell me the name and status of machine MCH-4407.

Calls: `listProduction`, `getMachine`.

Assessment: A particularly natural short request: production runs plus a named machine's name/status.

### 8. semantic-426-0007

> Search for up to 12 poetry books from 2019.

Calls: `searchBooks`.

Assessment: A simple human-like book search. Publication year and row cap are unambiguous.

### 9. semantic-426-0008

> Show me the attendance records for student Maya Ortiz.

Calls: `getStudent`.

Assessment: Natural attendance request resolved through getStudent's documented linked attendance records. The first candidate additionally asked for a global absent list without its call; the judge caught that and a genuinely new candidate replaced it.

### 10. semantic-426-0009

> Please pull alert 40721 with alertId, severity and raisedAt; alert 512 with alertId and buildId; build BLD-7331 with buildId, branch, status and startedOn; the failed builds on branch release/9.3 started on 2024-06-18, up to 12 rows; and restored outages from 2024-05-01 onward, up to 25 rows.

Calls: `getAlert`, `getAlert`, `getBuild`, `listBuilds`, `listOutages`.

Assessment: Regenerated after the initial request overclaimed newest-first ordering. The new request asks only for documented lookups/filters/limits. Still technical and multi-part, but no unsupported ranking claim.

### 11. semantic-426-0010

> List all departures for route RT-804 at or after 2025-06-01T00:00Z. Also list all departures. Finally, search for routes from Larkspur Crossing to Ravenwood Harbor and return at most 25 results.

Calls: `listDepartures`, `listDepartures`, `searchRoutes`.

Assessment: A plausible transit batch. General and route-filtered departure views remain allowed; they were not banned as duplicates merely for overlap.

### 12. semantic-426-0011

> Pull borrower 4271 with just the borrower id and name, the west region daily sales for 2026-03-14, and up to 20 revisions for article ART-harbor-tides that got changes_requested and were reviewed on or after 2026-01-08T09:30Z.

Calls: `getBorrower`, `getDailySales`, `listRevisions`.

Assessment: A looser borrower/sales/article-revision batch. It is useful call practice but not a convincing unified workflow; no fake story was invented to connect it.

### 13. semantic-426-0012

> I need to file a motion to compel discovery in my case CASE-8842 and have it served on opposing counsel by this Friday. Please submit the filing and arrange the service for me.

Calls: none (unsupported).

Assessment: Regenerated: now a clear unsupported filing-and-service action against read-only tools. The earlier comparison/analysis request was questionable as a no_call label and is retained in the initial run.

### 14. semantic-426-0013

> Book a maintenance visit for tractor TR-88 next Tuesday.

Calls: none (unsupported).

Assessment: A plausible unsupported scheduling request. Relative next Tuesday needs no binding because no dated canonical call is produced.

### 15. semantic-426-0014

> Pull up meter MTR-3145 but just the meter ID and tariff code, and also list the first 10 planned outages from 2024-06-01 onward.

Calls: `getMeter`, `listOutages`.

Assessment: A useful meter/tariff lookup and planned-outage list. The projection includes a known meter ID alongside a genuinely new tariff code, which is legitimate.

## Consumer and accounting checks

The reviewed candidate export contains 15 rows with verification: none, explicitly
not reader-verified. All 15 passed existing XML render/parse typed round trips and
encoded with the actual local tokenizer; all assistant spans were nonempty.
Python 3.12.16 / tokenizers 0.23.3: full lengths 506–1794 tokens, median 983;
largest assistant span 394 tokens. This does not test trained-model performance,
inference output caps or real fictional-tool execution.

A no-op resume of targeted shard 12 retained its one accepted row and unchanged
two-request/$0.001722 ledger, with no additional model invocation.
Full strict typing, Ruff format/lint and compile checks pass; installed-wheel
create CLI, offline specs and both packaged prompt resources load correctly.

Across judge calibrations, the initial 15 run, two targeted reruns and the separate
role-generation probe: **63 fresh model requests, $0.039249 reported spend**,
zero local response-cache hits and no pending reservations. Provider prefix
caching is not a local cached response. No bulk generation or training occurred.

## Review disposition

Independent code review covered behavior (@evan), contracts (@blair), design
(@mara), runtime (@koa) at staged tree
8f35852917565a50bc776701a6a7875ac2089621 (base 1ff9707).
Reported reviewer models were not supplied; raw reports remain in their Pi
transcripts. No verified blocking code defect remained.

Runtime F1 (cannot_create dead path) was disproved: run_creation handles the
decline and breaks before _hard_validate. The live-evidence gap was closed by
the actual run and manual inspection above. The final role-calibration gap was
checked and remains a documented semantic-judge limitation, not silently passed.
A focused contracts follow-up (@ana) reviewed only the two prompt capability
clarifications at tree 5f20096885e9b179dc13ce45d9c8cbc219a53cba; prior code coverage
was not invalidated and no new blocking contract defect was found.

These reviews are code/contract evidence, not proof of human-likeness. Parent
manual inspection found semantic misses despite the initial all-green judgment.

## Remaining limits and assessment

This is a working implementation of the approved design, with noticeably more
plausible entity values and several natural, useful requests than the old
field-pool/transcript approach. This small, differently selected pilot does not
establish a corpus-wide improvement rate.

Some wide independent bundles and technical field-heavy wording remain; they can
be useful training but should not dominate. The model has its own naming/number
priors, and the toy catalogue still favors read-only lookups. The judge remains
fallible, particularly on subtle role plausibility and capability assumptions.
Larger unattended generation is not justified by its acceptance alone.

No natural/human-source data was imported, no new automated tests were created,
and no saved training sets, benchmarks, checkpoints or real external records were
modified. The reviewed 15 are candidate artifacts only.

## Commands and retained evidence

```sh
PYTHONPATH=src python -m tool_gen.cli create -n 15 --seed 426 --out runs/semantic-pilot-15-v1/create --max-attempts 2 --temperature 0.9 --max-usd 0.50
# After the documented generic prompt correction, only the two affected slots:
PYTHONPATH=src python -m tool_gen.cli create -n 15 --seed 426 --out runs/semantic-pilot-15-v2/create --shard 9 --shards 15 --max-attempts 2 --temperature 0.9 --max-usd 0.10
PYTHONPATH=src python -m tool_gen.cli create -n 15 --seed 426 --out runs/semantic-pilot-15-v2/create --shard 12 --shards 15 --max-attempts 2 --temperature 0.9 --max-usd 0.10
PYTHONPATH=src python -m tool_gen.cli export --input runs/semantic-pilot-15-reviewed/results.jsonl --output runs/semantic-pilot-15-reviewed/export/train.jsonl
```

Paid Python processes were bounded by actual 900-second (main run) / 420-second
(targeted runs) timeouts, with a ten-second kill grace.

Ignored local evidence:
- runs/semantic-quality-calibration-v1..v4/shard-0/{reviews.jsonl,manifest.json,budget.json,requests/}
- runs/semantic-quality-role-check-v1/shard-0/
- runs/semantic-role-generation-probe-v1/shard-0/
- runs/semantic-pilot-15-v1/create/shard-0/{specs.jsonl,creation.jsonl,results.jsonl,manifest.json,budget.json,requests/}
- runs/semantic-pilot-15-v2/create/shard-{9,12}/ with the same artifacts
- runs/semantic-pilot-15-reviewed/{review-manifest.json,results.jsonl,consumer-check.json,export/}

The review-manifest records selected source hashes and replacement IDs. No raw
failed attempts were overwritten; API credentials are not persisted.
