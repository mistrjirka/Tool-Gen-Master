# Independent-call pilot: 15 fresh goals

## Scope and selection

User requested 15 examples sampled as differently as practical, with chaining deferred.
This is a **coverage-focused pilot, not a random corpus accuracy estimate**.

An in-memory pool of 600 candidates (seed 420) supplied 15 selected goals.
Only these 15 went to the paid writer. Selection preceded all writer/reader outcomes;
no failed goal was replaced. Anchors covered a multi-key nested filter, inclusive
instant window, single unfiltered call, decimal threshold and unsupported request.
Remaining choices favored new domains, tools, types, styles and call counts.

- Actual witness calls cover **16 domains and 41 distinct tools**; offered catalogues contain 58 distinct tools.
- Call counts: one zero-call, one one-call, one two-call, six three-call, three four-call and three five-call goals.
- All six style hints appear. Arguments include strings, integers, numbers, arrays and a nested object.
- The current catalogues have no boolean arguments; none were invented for this pilot.
- No generated world state: fictional IDs/names test call construction, not record existence.

## Repairs exercised

Default generation is independent-only; imported legacy references still fail audit.
Projection arrays and nested filters are now sampled rather than silently omitted.
Declared listReadings windows are ordered by actual instant; reversed imported
windows fail audit. Unsatisfiable unique-item sampling raises rather than emitting
duplicates. Frozen datasets, consumers, scorers and benchmarks were untouched.
No automated tests were added.

## Actual results

| Stage | Result |
| --- | --- |
| Goal audit | 15/15 mechanically valid |
| Writer, temperature 0.9 | 15 accepted; 15 fresh requests, zero local cache hits |
| Blind reader, temperature 0.0, maximum 2 attempts | 13 accepted, 2 unresolved, 0 invalid; 19 fresh requests, zero local cache hits |
| Offline triage | 13 match, 1 reader output error, 1 different; zero fresh model requests |
| Content-bound verified export | 13 rows; both unresolved rows excluded |
| Existing XML renderer/parser, all 15 candidate targets | 15 typed round trips match; all assistant supervision spans nonempty |
| Actual local tokenizer, all 15 | All encode; 1018–1490 tokens, median 1296 |

Model: deepseek/deepseek-v4.1-flash via OpenRouter.
Reported accounted cost: writer $0.002488 + reader $0.006439 = **$0.008927**.
No pending reservations. Provider prompt-prefix caching is distinct from the
zero local response-cache hits above.

Four reader attempts returned empty output, all through DigitalOcean; two cases
recovered on Wafer and one remained empty twice. This does not establish the
underlying provider failure cause. The other unresolved case repeatedly mixed
up a limit on Wafer. Unresolved is not a bad-data label.

Consumer inspection used Python 3.12.16, tokenizers 0.23.3 and the existing
/srv/shared-ml/tokenizer/xml_tools.py plus tokenizer.json.
It checks rendering/parsing/tokenization, **not trained-model performance or real
tool execution**. All 15 candidate targets were inspected in memory; only the
13 reader-approved rows were persisted in the verified export.

## All 15 requests, including failures

### 1. cohv5-420-0267 — accepted

Tools: `listLoans`, `getBorrower`, `getStudent`, `searchBooks`, `getBorrower`.

> Returned loans. Borrower 327 — borrowerId, name. Student named Sara Lindgren. Books by Priya Raman, genre novel, year 1914. Borrower 5641.

Inspection: Exact readback, including the three-key nested book filter, numeric borrower IDs and projection.

### 2. cohv5-420-0171 — unresolved

Tools: `listReadings`, `listReadings`, `listReadings`.

> - List the readings for meter ID "VUNcRhq3zP" with to instant "2025-06-01T09:00:00+02:00" and min kwh 447.36.
> - List the readings for meter ID "yoXVAt5PNP" with from instant "2024-01-15T23:59:00+02:00" and to instant "2025-06-01T14:30:00+02:00".
> - List the readings for meter ID "Je7D9fd4fW".

Inspection: Unresolved: both paid reader attempts returned empty output via DigitalOcean. Not evidence of a bad request.

### 3. cohv5-420-0099 — accepted

Tools: `listOrders`.

> List orders.

Inspection: Exact unfiltered one-call readback.

### 4. cohv5-420-0011 — accepted

Tools: `listHearings`, `listRefunds`, `getProduct`, `getStore`.

> Get hearings for case ID srZLPLYXoM. Refunds with min amount 78730.0. Product with sku RYvI0o9nin. Store with name Mei Tanaka.

Inspection: Exact four-call readback, including decimal threshold and fictional store name.

### 5. cohv5-420-0004 — accepted

Tools: none (unsupported).

> Retrieve the current stock price of Tesla.

Inspection: Correct unsupported decision: offered tools cannot retrieve stock prices.

### 6. cohv5-420-0215 — accepted

Tools: `listAlerts`, `searchPosts`, `searchRoutes`.

> List alerts with severity "info", limit 20. Search posts for "harbor tides" keyword. Search routes from "Harborview Station" to "Harborview Station".

Inspection: Exact readback. Same-origin/destination route is unusual; no actual route existence or loop behavior was checked.

### 7. cohv5-420-0043 — accepted

Tools: `getArticle`, `listSamples`, `listAssayRuns`.

> Grab the article hLjFxz7pid for me, then show me the water samples collected on 2024-02-20, and list any assay runs that failed with at least a 0.11 yield.

Inspection: Natural paraphrasing with exact ID, collection date and minimum yield. 'Then' sequences independent requests, not output dependencies.

### 8. cohv5-420-0126 — accepted

Tools: `getField`, `listMovements`.

> Get the field with ID "uQj1tiusiI". Also list all movements where the direction is "transfer".

Inspection: Empty first completion; second attempt recovered both calls.

### 9. cohv5-420-0007 — accepted

Tools: `listMaintenance`, `listProduction`, `getHotel`.

> Maintenance for c1Q2sRxZw9 after 2024-03-10T09:00:00+02:00, limit 5. Production. Hotel St3UVoWmbk with rating, name, hotelId, city.

Inspection: Exact readback. Bare 'Production.' remains very terse; no hard terse/length rule was imposed.

### 10. cohv5-420-0356 — unresolved

Tools: `getAsset`, `searchPolicies`, `searchPolicies`, `listClaims`.

> Can you pull up the asset with asset ID 40489 and show me its title, kind, and assetId? I'd also like to search policies with a limit of 50. And while you're at it, search policies where the holder is "reference note." Finally, list claims with a limit of 5.

Inspection: Unresolved: both attempts changed listClaims limit 5 to 50 and reordered the asset projection. Wrong limit is a genuine readback error; projection reordering alone need not change projection intent. Sentence punctuation inside the quoted holder also leaves exact-literal interpretation less explicit.

### 11. cohv5-420-0422 — accepted

Tools: `listEquipment`, `getUser`, `getWeather`, `listCrops`, `listCrops`.

> Can you pull up all the equipment where the type is "sensor", find the user with username "Sara Lindgren", and grab the weather for "Northgate Library" on "2024-03-10"? Also list the crops, plus the crops with crop type "wheat" harvested after "2024-02-20", limited to 50.

Inspection: Empty first completion; second attempt recovered all five calls. Fictional names/locations are not verified real entities.

### 12. cohv5-420-0505 — accepted

Tools: `listAttendance`, `getStudent`, `listSessions`, `getDocument`, `getCourse`.

> Can you pull up a few things for me? I'd like to see attendance records with status "absent", limited to 10. Then find the student named "Mei Tanaka". Also list sessions, limit 10. Grab the document with doc ID "D9Ny8NExq2" and just give me its title and filedDate fields. And look up the course with course code "n1jNzoFntJ".

Inspection: Exact five-call readback, including both limits and document projection.

### 13. cohv5-420-0189 — accepted

Tools: `listDepartures`, `getRoute`, `getAlert`.

> - List departures after 2024-01-15T09:00:00+02:00, limit 10.
> - Get route "Evq7Xi5C8v" with fields stops, routeId, name, and frequency.
> - Get alert 7342 with field alertId.

Inspection: Exact parameter readback. Prose says 'after' while schema says 'at/after'; parameter matching does not prove inclusive-boundary behavior on actual records.

### 14. cohv5-420-0348 — accepted

Tools: `listReservations`, `listRevisions`, `listReservations`, `searchHotels`.

> Hey, can you pull up the reservations list, plus revisions where the decision is "rejected" — cap that at 50. Also show me reservations for guest name "Nadia Haddad", limit 10, and search hotels in city "Lakeside Pavilion".

Inspection: Exact four-call readback. 'Lakeside Pavilion' as a city is an unusual sampled literal, not verified geography.

### 15. cohv5-420-0374 — accepted

Tools: `getTariff`, `getClaim`, `listOutages`.

> Get tariff code "day_night"; claim qKefu0YY1K; list restored outages after 2024-01-15, limit 5.

Inspection: Exact parameter readback. Natural 'after' versus declared 'on/after' again leaves boundary intent less explicit than the schema.

## Assessment and limits

The generator, paid writer, blind reader, source-bound export and existing
XML/tokenizer path operate end to end on this selected set. This is materially
stronger evidence than lint or selected reader controls alone, but not a claim
of full reliability or naturalness.

Manual inspection found no unequivocal missing writer operations or numeric-value
changes; the two reader failures do not justify discarding the source requests.
Inclusive/exclusive boundary intent and punctuation remain less explicit in some
prose than in schemas. Matching arguments cannot independently prove business
feasibility or behavior on boundary records. Several requests closely transcribe
field names; cross-domain bundles and small generic name/place pools are visible.
These are limitations, not blanket bans on IDs, unfamiliar names, terse wording
or lists.

Reader empty-output reliability and incorrect argument readback remain actionable
before scaling. No bulk generation, training, promotion, paraphrase validation or
frozen benchmark rerun was performed.

## Human-likeness review: separate from reader correctness

This later assessment deliberately ignores reader acceptance as a quality score.
All 15 requests above were re-read for plausible human intent, information value,
entity roles and language—not merely whether their arguments could be recovered.
The earlier inspection establishes call fidelity, not representative human quality.

### Main judgment

The set contains usable call-construction exercises, but it is not yet convincing
as a broadly human-like request distribution. Many individual sentences are
possible human utterances, especially in an internal dashboard. That is a weaker
standard than whether a person would naturally want the sampled combination.
Polite introductions and "also/finally" often disguise a bag of independent
API-shaped requests rather than a recognizable information need.

This pilot was explicitly selected for maximal coverage; it overemphasizes diverse
cross-domain combinations. Its frequency of artificial bundles cannot be treated
as a random estimate of the full generator. Nevertheless, the selection did not
invent the weak goals: the sampler produced them and the writer accepted them.

### All 15, judged without the reader labels

| Row | Qualitative assessment |
| --- | --- |
| 1 | Possible librarian/admin scratchpad, but "borrowerId, name" and the exact parameter inventory look transcribed from a schema. Not convincing ordinary conversation. |
| 2 | The three-meter information need is plausible. "With to instant" and "min kwh" are particularly unnatural schema-derived language. Exact timestamps and IDs themselves are not the defect. |
| 3 | "List orders." is plainly plausible. Short and underspecified in the everyday sense, but valid for an unfiltered listing; adding a story would not improve it necessarily. |
| 4 | One of the weakest: hearings, high-threshold refunds, a product and a store have no established shared purpose. Each subrequest is possible; the combination looks randomly assembled. |
| 5 | A normal, plausible request. Unsupported by this catalogue does not mean unnatural. |
| 6 | Alerts, posts and routes are stitched together. Same-origin/destination search could be a genuine loop-route request, but that purpose is not established; repeated pool values can create it accidentally. |
| 7 | Fluent phrasing and a believable laboratory subtask. The article lookup is loosely connected at best without context. Better prose than the terse cases, not proof of a coherent whole. |
| 8 | A possible technical operator request. "Where the direction is transfer" sounds more like a query predicate than everyday warehouse language, but is not inherently bad. |
| 9 | Strong schema/scratchpad feel: "Production." and camelCase hotel fields, plus an unmotivated hotel lookup beside maintenance. A human could write fragments; their sampled combination is the issue. |
| 10 | Conversational wrapping, but the holder "reference note" exposes the generic fallback pool. Asset/policy/claims work could share a purpose, but none is established. Fluent is not the same as natural content. |
| 11 | A farm-operations batch is mostly plausible. Full-name-as-username and generic venue names show weak entity-role modeling; these are not universal prohibitions on such literals. |
| 12 | Among the more plausible multi-call requests: attendance, a student, sessions and a course fit education administration. Still a parameter-complete task inventory rather than a clearly stated purpose. |
| 13 | Departures and route details fit together. Asking for alert 7342 with only its already-known alertId adds little information. An existence check could justify it, but that intent is absent. |
| 14 | Smooth language masks unrelated revisions/hotel work. Using "Lakeside Pavilion" as a city illustrates a venue/city role mismatch in a shared place pool, not a ban on unfamiliar fictional place names. |
| 15 | Possible terse technical work. A tariff, claim and outage list might belong to one workflow, but no such relationship was sampled. Underscore enum spelling is another schema-transcription cue. |

The strongest problems are upstream, not merely stylistic:

- **Combination without motivation:** a conjunction of individually legal calls
  is not automatically a plausible request. Independent calls need not be chained
  to share a purpose.
- **Field names instead of intent:** readable formatting did not change that the
  brief is generated from operation/argument names. The writer is often translating
  a field inventory into sentences rather than expressing a person's goal.
- **Entity-role leakage:** the same six place names serve cities, stations and
  venues; the same eight people serve several roles. The policy-holder fallback
  becomes "reference note". These are systematic priors, not isolated spelling
  mistakes. A human can supply unusual names; a generator constantly choosing
  semantically generic ones is a different issue.
- **Low-information operations:** projection can request only a known lookup key.
  Schema validation cannot tell whether the user learned anything useful.
- **Copying more than interpreting:** raw timestamps, literal thresholds, enum
  spellings and field lists dominate. Some are realistic technical inputs, but
  this alone does not exercise natural dates, units or semantic reformulation.
- **Narrow work types despite domain variety:** most tools remain record lookups,
  filtered lists and projections. Sixteen domain labels do not provide sixteen
  different kinds of reasoning or action.

These are review questions, not new opener/ID/list/length quotas. The writer is
already instructed to reject contrived/redundant goals and avoid field dumps;
adding another "sound natural" sentence is unlikely to repair the sampling model.

### Comparison with actual local Seal examples

For this review, 18 non-chaining examples were inspected from the exact local Seal
train/in-domain/out-domain files, using seed 420 and a small call-count-stratified
sample plus two additional random items per split. This is a qualitative reference,
not a quality-rate estimate and not a claim that Seal examples are human-authored.
No inference, benchmark rerun, annotation change or training was performed.

**Where the inspected Seal examples are stronger:**

- `test_out_domain-easy-83`: "Find books about Middle Eastern culture and history."
  It states an information need rather than repeating filter/property names.
- `test_out_domain-difficult-548`: creating an IT project, submitting a named job
  with file paths and checking an Azure account has a recognizable operational
  setting. It uses natural date expressions mapped to ISO dates in the target.
- `train-difficult-6633`: a walk-test description uses 10 minutes 30 seconds while
  the API argument is 10.5 minutes. That illustrates semantic/unit interpretation
  absent from the mostly literal-copying pilot—not an endorsement of that row's
  unrelated additional requests or every aspect of its annotation.
- Seal work also includes create/modify/analyze/calculate intents. The pilot's
  CRUD-style read selection is narrower even when it spans many named domains.

**Where Seal has the same problems or worse:**

- `train-difficult-8287` combines greenhouse CO2, a library usability test, a car
  odometer and audience demographics. This is also a contrived shopping list.
  Its target additionally supplies a required test ID not given in the request.
- `test_out_domain-difficult-587` combines a cash payment, hospitality safety,
  an SSL certificate and pharmacy information. Smooth connectors do not supply
  a realistic shared purpose.
- `test_in_domain-difficult-592` asks for a press release, but its gold additionally
  calls Greek-alphabet, Zulu-translation and order-detail tools. The full task and
  tool descriptions were checked: those extra requests are not in the instruction.
  This is a concrete annotation issue, not an aesthetic criticism.
- Random-looking pasted IDs, verbose assistant-style politeness and multi-call
  bundles occur in Seal too. They are not unique to this generator. Three-call
  examples dominate the actual Seal splits, so "multiple calls" alone is not a
  meaningful criticism of our pilot.

Inspected sample IDs (full prefixes retained):

- train-easy-107, train-difficult-9768, train-difficult-6633,
  train-difficult-8287, train-easy-1567, train-difficult-11335.
- test_in_domain-easy-173, test_in_domain-difficult-251,
  test_in_domain-difficult-220, test_in_domain-difficult-592,
  test_in_domain-difficult-343, test_in_domain-difficult-515.
- test_out_domain-easy-83, test_out_domain-difficult-214,
  test_out_domain-difficult-548, test_out_domain-difficult-180,
  test_out_domain-difficult-587, test_out_domain-difficult-350.

Sources: /srv/shared-ml/tool-data/seal-tools/dataset_for_finetune/{train.json,
test_in_domain.json,test_out_domain.json}. Benchmark rows were neither changed
nor imported into a new training dataset.

**Conclusion:** the pilot resembles Seal's API-selection exercises, including
some of Seal's artificiality. The better Seal examples more often express a
recognizable task and meaningful domain concepts. Matching Seal's weakest bundles
is not the right target for broad human-like data. Improve jointly plausible
intents/entities and meaningful information needs before relying on surface
paraphrasing or mechanical acceptance. No implementation change is implied by
this assessment.

## Evidence and commands

Ignored local artifacts under runs/independent-pilot-15-v1/:
selection.json, input/goals.jsonl, writer/shard-0/{manifest.json,budget.json,
results.jsonl,requests/}, reader/shard-0/{manifest.json,budget.json,results.jsonl,
requests/}, triage.jsonl, consumer-check.json and export/{manifest.json,train.jsonl}.
Raw responses, input hashes and charged attempts remain retained; API credentials
are not stored.

Commands from Tool-Gen-Master with PYTHONPATH=src:

```sh
python -m tool_gen.cli audit --input runs/independent-pilot-15-v1/input/goals.jsonl
# Actual paid processes were each bounded by timeout --signal=TERM --kill-after=10s 600s.
python -m tool_gen.cli writer --goals runs/independent-pilot-15-v1/input/goals.jsonl --out runs/independent-pilot-15-v1/writer --temperature 0.9 --max-usd 0.15
python -m tool_gen.cli reader --input runs/independent-pilot-15-v1/writer --out runs/independent-pilot-15-v1/reader --temperature 0.0 --max-attempts 2 --max-usd 0.25
python -m tool_gen.cli triage --input runs/independent-pilot-15-v1/writer --results runs/independent-pilot-15-v1/reader --output runs/independent-pilot-15-v1/triage.jsonl
python -m tool_gen.cli export --input runs/independent-pilot-15-v1/writer --verification runs/independent-pilot-15-v1/reader --output runs/independent-pilot-15-v1/export/train.jsonl
```
