# 100-item semantic-generation review

## What ran

User authorized 100 new examples, all read directly by the parent and independently
by a subagent. Generator code stayed fixed at **6276781** throughout the run:
create -n 100 --seed 927, four shards, two bounded attempts, creator temperature
0.9 and judge 0.0, deepseek/deepseek-v4.1-flash. No training, reader invocation,
benchmark rerun or generator fix was performed during this assessment.

The initial 100 slots produced **86 accepted and 14 unresolved** terminal records.
Two unresolved slots (0070 and 0091) had no readable request: one only empty
completions, the other an empty completion followed by a malformed decline.
Exactly those two received one bounded fresh-root recovery with the same
structural-spec hash. Rough but readable examples were not replaced.

The result is **100 primary candidate texts**, not 100 approved training rows:
88 machine-accepted and 12 unresolved. Unvalidated candidates are shown deliberately
for review, not silently admitted. All original records and failed attempts survive.

All four source shards reconcile to 100 unique IDs, 25 per shard; input-spec hashes
agree across shards and both recoveries. Reported generation API spend, including
recoveries: **$0.105090**, 224 fresh requests, zero local response-cache hits,
no pending reservations. The initial run cost $0.103735. Each actual Python
process was bounded by a 1200-second timeout (recoveries: 420 seconds).

## What was read

The parent read all 100 requests and their canonical calls plus all 17 earlier
textual candidates. Potential issues were checked against exact tool contracts.
The independent subagent **@noa** separately read the same 100, the 17 earlier
candidates and all 64 contracts; it received no machine verdicts or parent grades.
Both per-ID assessment files cover exactly the same 100 unique identities.
Parent per-item grading was completed before opening the subagent's per-item report.

These are manual qualitative categories, not automated pass rates or population
accuracy estimates. We disagree mainly about how natural the technical batches feel.

| Assessment | Parent | Subagent |
| --- | ---: | ---: |
| Good/plausible human request | 58 | 85 |
| Usable technical/synthetic example | 35 | 11 |
| Needs revision | 5 | 4 |
| Uncertain contract equivalence | 2 | 0 |

The subagent also explicitly identified the fifth fidelity issue (0077), but
graded it usable_technical; I treat an explicit output-exclusivity violation as
label noise needing correction. The two parent uncertainties (0063/0081) concern
whether an exhaustive list of projectable fields is guaranteed equivalent to
the tool's omit-for-full-record behavior. They are not proven defects.

## Concrete fidelity problems

| ID suffix | Problem | Machine admission |
| --- | --- | --- |
| 0012 | Request says loans open on 2025-11-03; listLoans omits openOn. | unresolved |
| 0021 | Request includes alert 7082 severity/buildId; getAlert is missing. | unresolved |
| 0026 | Four requested media/social reads; sole call is an unrequested searchPosts with no arguments. | unresolved |
| 0072 | Statute search omitted; both list calls use limit 0 despite asking to show records. The contract says max rows, omit for all—not zero for all. | unresolved |
| 0077 | Request says just sample type and site; projection additionally returns sampleId. | accepted |

The first four are already quarantined by the pipeline. Their same raw model
response contains the inconsistent request and calls; this is not evidence that
storage combined text from one attempt with calls from another. The fifth is a
real judge false-accept. Known IDs alongside new fields are generally fine, but
not when they violate an explicitly exclusive requested output.

There are false rejections too. The earlier 0025 candidate projected borrower ID
and name: the judge claimed there was no new information, confusing requested
field names with values already supplied. Name was not known. Later wording
added an unnecessary existence-check justification. The final 0098 candidate was
rejected solely for lacking a shared story across outage/tariff/hotel lookups,
contrary to the approved independent-batch policy. These are reasons not to treat
the judge's explanations as authoritative.

## The important quality result: implicit templates remain

The set is mostly usable API-call practice, but it still reads much more like
one model producing back-office queries than 100 independently authored humans.

### Strongest repeated patterns

- **15 of 17 book searches are poetry**; one is reference and one has no genre.
  Restricting to the 88 machine-accepted candidates still yields **14 of 15 book
  searches as poetry**, with one reference search. None use novel, essays or comics.
- All 12 explicit book-publication-year filters use only **1954, 1987, 1994 or 1998**.
  Year 2021 occurs in an earlier candidate, not the primary set.
- Borrower **742 appears seven times**, borrower 412 four times. Schema examples
  and the old sampled placeholder values were not user facts supplied to the
  creator, so this is model-default concentration rather than a manually authored
  scenario bank.
- Limits **20 and 12 account for 46 of 87 explicit limit arguments**.
- There are 23 empty-argument calls, including 21 list calls. Such queries are
  individually legitimate; their repeated use as filler/full-overview patterns
  is a distribution concern, not an automatic per-row defect.
- Several four/five-call messages are broad shopping lists with polite connective
  tissue. These can be useful training, as the user explicitly noted, but should
  not substitute for broad human-purpose diversity.

The many poetry/borrower/record-projection variants are not many new reasoning
types. Values and surface wording change while the underlying recipe stays close.
All 100 packets also have empty visible context. With mostly ID-based read/list
tools, the model is pushed toward a fully informed operator who already supplies
identifiers, dates and filter values. That is a valid training slice, but not a
broad sample of ordinary human needs with contextual references. More realistic
visible context and wider capabilities would add a different kind of diversity;
surface paraphrasing alone cannot supply them.

Some examples are genuinely stronger: warehouse shortage/surplus views (0050/0075),
sample-attribute verification using retrieved fields (0034), coherent case/hearing
checks (0003), ordinary simple lookups (0035/0049/0057/0080), and realistic
unsupported actions or missing-data questions.

### Likely contributing mechanisms—not proven causes

Most readable creator responses emit the calls before intent/request:
101 of 118 parseable creator completions start with the calls property;
17 start with decision. Thirteen additional creator completions were empty or
unparseable. Observable emission order is not access to hidden planning, but it
may encourage API-call-first composition followed by prose rationalization.
A goal-first response layout is a bounded hypothesis to evaluate, not a claimed fix.

The current structural controls cover counts and broad types, not categorical
value coverage. Leaving all enum choices to the model allows an implicit default
such as poetry to dominate. A next experiment can use schema-derived categorical
coverage constraints without creating per-domain hand-written scenarios or
banning legitimate poetry/IDs/lists.

## Reliability versus semantic quality

Most unresolved inputs failed the required zero-argument shape: the model often
writes a semantically unfiltered list with a limit, while the structural contract
requires an actually empty argument object. Several such requests are otherwise
reasonable; structural-control failure must not be mislabeled as bad human text.
The current term unfiltered conflates those two ideas for the generator.
The no-text attempt in 0091 also claimed it could not invent concrete filters
without user facts, despite this stage's explicit permission to propose fictional
values. That is creator/reader-role confusion, not evidence the catalogue lacked
a meaningful possible request.

Conversely, semantic defects can pass every schema check. All primary calls can
be unwrapped and satisfy the original parameter schemas, yet 0012 omits a stated
date and 0077 adds an excluded output field. This task did not run a blind reader.

I do not endorse two statements in the independent narrative: an unfiltered loan
listing is not zero-information merely because it lists everything; and the ten
unsupported examples are not all write actions. 0074 is a weather read request
with getWeather absent from its offered catalogue; 0099 is an on-call roster read
whose data are unavailable. Both are reasonable no-call examples. The subagent's
per-item notes recognize their capability gaps; its broad summary overstates the
write-action pattern. Independent review is evidence to check, not a vote to obey.

## Conclusion / next priorities

Do not train on this collection unchanged. Four clear failures are already
unadmitted, one fidelity error escaped, two full-record/projection cases need
contract clarification, and the distribution is too repetitive to call broadly
human-like solely from row count.

Priority follow-up is: clarify zero-argument structural controls; exercise
schema-derived enum/parameter coverage so model defaults do not dominate; and
improve projection/known-value role fidelity plus critic calibration on independent
batches. A goal-first creator-wire experiment may also be worthwhile. No such
generator changes were made during this review.

## All 100 primary candidates

For an unresolved entry below, the text/calls are a retained raw candidate for
inspection, not a pipeline-approved training example.

### semantic-927-0000

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Two quick checklist items for CS-101: first pull up the course record for CS-101, and second list up to 20 sessions for CS-101 that take place on 2024-11-05.

Calls: `getCourse({"courseCode":"CS-101"})`; `listSessions({"courseCode":"CS-101","limit":20,"onDate":"2024-11-05"})`.

Parent assessment: Coherent course record plus dated sessions; same known course, no output dependency.

### semantic-927-0001

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> ok grab me the sku and price for SKU-8842-TRAIL, confirm the store "Fern Hollow Outfitters", then list approved refunds of at least 45.50 processed after 2024-03-05T08:30Z (cap at 12) and up to 20 departures for route RT-558-Q from 2024-03-06T14:00Z onward

Calls: `getProduct({"fields":["sku","price"],"sku":"SKU-8842-TRAIL"})`; `getStore({"storeName":"Fern Hollow Outfitters"})`; `listRefunds({"limit":12,"minAmount":45.5,"processedAfter":"2024-03-05T08:30Z","status":"approved"})`; `listDepartures({"after":"2024-03-06T14:00Z","limit":20,"routeId":"RT-558-Q"})`.

Parent assessment: Useful commerce batch plus unrelated departure query; technical, not inherently invalid.

### semantic-927-0002

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Get borrower 742 but just their name; search poetry books by Ilse Marchetti updated since 2026-02-03T08:45Z, cap at 12; list loans with status on_loan open on 2026-02-03, limit 20; and list every reservation.

Calls: `getBorrower({"borrowerId":742,"fields":["name"]})`; `searchBooks({"filter":{"author":"Ilse Marchetti","genre":"poetry"},"limit":12,"updatedAfter":"2026-02-03T08:45Z"})`; `listLoans({"limit":20,"openOn":"2026-02-03","status":"on_loan"})`; `listReservations({})`.

Parent assessment: Library queries plus unfiltered reservations; raw enum wording and weak shared purpose.

### semantic-927-0003

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull the caseId, title, and status fields for CASE-8841 and CASE-3097, and list hearings for CASE-8841 on 2024-03-15 (max 12 rows) and for CASE-3097 on 2024-04-02 (max 5 rows).

Calls: `getCase({"caseId":"CASE-8841","fields":["caseId","title","status"]})`; `getCase({"caseId":"CASE-3097","fields":["caseId","title","status"]})`; `listHearings({"caseId":"CASE-8841","date":"2024-03-15","limit":12})`; `listHearings({"caseId":"CASE-3097","date":"2024-04-02","limit":5})`.

Parent assessment: Two case profiles plus their dated hearing lists; earlier candidate omitted a requested second case lookup and added statutes.

### semantic-927-0004

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Show me passing assay runs since 2025-11-03T08:30Z with yield at least 0.75, max 12; field FLD-7734's id, crop and area; approved refunds from 250.5 processed after 2025-10-20T14:00+02:00, max 8; swab samples collected 2025-09-18, max 30; and assay PCR-ITS2.

Calls: `listAssayRuns({"completedAfter":"2025-11-03T08:30Z","limit":12,"minYield":0.75,"outcome":"pass"})`; `getField({"fieldId":"FLD-7734","fields":["fieldId","crop","area"]})`; `listRefunds({"limit":8,"minAmount":250.5,"processedAfter":"2025-10-20T14:00+02:00","status":"approved"})`; `listSamples({"collectedOn":"2025-09-18","limit":30,"sampleType":"swab"})`; `getAssay({"assayCode":"PCR-ITS2"})`.

Parent assessment: Role values plausible; five-way lab/farm/refund bundle remains technical and scattered.

### semantic-927-0005

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you pull up three things for me? First, grab media asset 47213 but I only need its assetId, kind, title, and publishedOn fields. Second, fetch claim CLM-9384 and just show me its claimId, amount, and status. And third, get me the article with the slug ART-harbor-lights.

Calls: `getAsset({"assetId":47213,"fields":["assetId","kind","title","publishedOn"]})`; `getClaim({"claimId":"CLM-9384","fields":["claimId","amount","status"]})`; `getArticle({"articleId":"ART-harbor-lights"})`.

Parent assessment: Media/insurance/article lookups are individually useful, loosely connected.

### semantic-927-0006

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> List up to 10 wheat crops harvested after 2025-05-01, and also list all farm equipment without filtering by type or status.

Calls: `listCrops({"cropType":"wheat","harvestedAfter":"2025-05-01","limit":10})`; `listEquipment({})`.

Parent assessment: Natural farm request; correct unfiltered equipment listing.

### semantic-927-0007

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Retrieve up to 20 planned outages with a start date on or after 2025-03-01, and fetch meter MTR-8842 showing only its meterId and site fields.

Calls: `listOutages({"afterDate":"2025-03-01","limit":20,"status":"planned"})`; `getMeter({"fields":["meterId","site"],"meterId":"MTR-8842"})`.

Parent assessment: Clear outage listing plus new site information for a meter.

### semantic-927-0008

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Please search the library catalogue for poetry books published in 1998 by Marta Velez. Checklist: use the author exactly as "Marta Velez"; restrict to the poetry genre; restrict to publication year 1998; do not add any update-time filter or row limit.

Calls: `searchBooks({"filter":{"author":"Marta Velez","genre":"poetry","year":1998}})`.

Parent assessment: Faithful filter, but explicit instructions not to add optional filters/limits expose generation scaffolding.

### semantic-927-0009

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Look up book BK-8842 for just title, author, and year; search poetry books by Ilse Brandt published in 1994, up to 20 rows; get borrower 412's profile with all linked loans; and list up to 15 overdue loans that were open on 2024-03-18.

Calls: `getBook({"bookId":"BK-8842","fields":["title","author","year"]})`; `searchBooks({"filter":{"author":"Ilse Brandt","genre":"poetry","year":1994},"limit":20})`; `getBorrower({"borrowerId":412})`; `listLoans({"limit":15,"openOn":"2024-03-18","status":"overdue"})`.

Parent assessment: Useful library record/search/profile/overdue views; no unsupported borrower-only loan filter implied.

### semantic-927-0010

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please pull up meters MTR-4417 and MTR-8820 with their site and tariff code, show me up to 20 active outages starting from 2025-03-01 and up to 10 planned outages starting from 2025-02-15, and get the day_night tariff definition.

Calls: `getMeter({"fields":["meterId","site","tariffCode"],"meterId":"MTR-4417"})`; `getMeter({"fields":["site","tariffCode"],"meterId":"MTR-8820"})`; `listOutages({"afterDate":"2025-03-01","limit":20,"status":"active"})`; `listOutages({"afterDate":"2025-02-15","limit":10,"status":"planned"})`; `getTariff({"tariffCode":"day_night"})`.

Parent assessment: Meaningful energy checks. Including meter ID as a display label alongside new fields is not a useless projection; earlier candidate invented limit0 for active outages.

### semantic-927-0011

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Check field FLD-8842 — just its name, crop, and area. Also, what's the forecast for Sacramento Valley North on 2026-03-14? And list rice crops harvested after 2026-09-01, cap at 20.

Calls: `getField({"fieldId":"FLD-8842","fields":["name","crop","area"]})`; `getWeather({"date":"2026-03-14","location":"Sacramento Valley North"})`; `listCrops({"cropType":"rice","harvestedAfter":"2026-09-01","limit":20})`.

Parent assessment: Plausible farm operations, explicit dates and useful projection.

### semantic-927-0012

Parent: **needs_revision**. Subagent: **needs_revision**.
Pipeline: unresolved.

> Get borrower 742's name only, and list up to 20 loans still open on 2025-11-03.

Calls: `getBorrower({"borrowerId":742,"fields":["name"]})`; `listLoans({"limit":20})`.

Parent assessment: Request specifies loans open on2025-11-03; listLoans arguments omit openOn entirely.

### semantic-927-0013

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Cancel my registered service contract CNT-4482 for machine MCH-1001, effective immediately, and send written confirmation to the registered account holder.

Calls: none (unsupported).

Parent assessment: Clearly unsupported contract cancellation/confirmation action against read-only capabilities.

### semantic-927-0014

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Find up to 5 routes from Hillcrest to Riverside. Also pull RT-77's name, stops and frequency, full details for stop STP-14, and up to 10 departures for route RT-77 from stop STP-14 at or after 2025-03-04T08:30Z.

Calls: `searchRoutes({"destination":"Riverside","limit":5,"origin":"Hillcrest"})`; `getRoute({"fields":["name","stops","frequency"],"routeId":"RT-77"})`; `getStop({"stopId":"STP-14"})`; `listDepartures({"after":"2025-03-04T08:30Z","limit":10,"routeId":"RT-77","stopId":"STP-14"})`.

Parent assessment: Coherent transit queries with explicit known route/stop identifiers, no chaining.

### semantic-927-0015

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Please do two quick checks for me:
> - Look up course MATH-207 and tell me about it.
> - Pull up product SKU-8842, showing only its sku and price.

Calls: `getCourse({"courseCode":"MATH-207"})`; `getProduct({"fields":["sku","price"],"sku":"SKU-8842"})`.

Parent assessment: Possible independent course/product checklist; little common purpose but allowed.

### semantic-927-0016

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Please do both of these in one go: (1) list swab samples collected on 2023-11-08, limit 25; (2) list assay runs with outcome pass, completed at/after 2023-11-01T09:30Z, minYield 0.75, limit 10.

Calls: `listSamples({"collectedOn":"2023-11-08","limit":25,"sampleType":"swab"})`; `listAssayRuns({"completedAfter":"2023-11-01T09:30Z","limit":10,"minYield":0.75,"outcome":"pass"})`.

Parent assessment: Useful lab queries, mostly parameter-shaped wording.

### semantic-927-0017

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Retrieve the complete list of refunds with no status, amount, or processing-time filters, and search statutes for the keyword "data retention" across all jurisdictions.

Calls: `listRefunds({})`; `searchStatutes({"keyword":"data retention"})`.

Parent assessment: Clear two-task operator request; all-jurisdiction statute search correctly leaves jurisdiction unset.

### semantic-927-0018

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Search posts about 'irrigation' by rkbennett, pull up field FLD-74213, list every harvester in maintenance, and show me all crops.

Calls: `searchPosts({"author":"rkbennett","keyword":"irrigation"})`; `getField({"fieldId":"FLD-74213"})`; `listEquipment({"status":"maintenance","type":"harvester"})`; `listCrops({})`.

Parent assessment: Recognizable farm batch, including irrigation posts and maintenance equipment.

### semantic-927-0019

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Show me bin B-07's contents, the PCR-16S assay definition, up to 25 water samples collected on 2024-03-12, and up to 50 critical alerts since 2024-03-10T00:00Z.

Calls: `getBin({"binCode":"B-07"})`; `getAssay({"assayCode":"PCR-16S"})`; `listSamples({"collectedOn":"2024-03-12","limit":25,"sampleType":"water"})`; `listAlerts({"limit":50,"severity":"critical","since":"2024-03-10T00:00Z"})`.

Parent assessment: Useful but scattered bin/lab/build-alert checklist.

### semantic-927-0020

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Can you cancel the production run that's scheduled for the Pinewood line tomorrow morning? We've had a material shortage and it can't go ahead.

Calls: none (unsupported).

Parent assessment: Natural unsupported production cancellation; external mutation absent.

### semantic-927-0021

Parent: **needs_revision**. Subagent: **needs_revision**.
Pipeline: unresolved.

> Please run these three checks for me: pull borrower 412's profile showing just their name; get the storage info for item WH-4471 including name and bin code; look up alert 7082 showing severity and build id; and also give me a full unfiltered list of all loans.

Calls: `getBorrower({"borrowerId":412,"fields":["name"]})`; `getItem({"sku":"WH-4471","fields":["name","binCode"]})`; `listLoans({})`.

Parent assessment: Request explicitly includes alert7082 severity/buildId but calls omit getAlert; says three checks yet lists four operations. Earlier request appears meaningful but not all structural controls.

### semantic-927-0022

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull the title, author and year for BK-4471, and search for up to 12 poetry books from 1994 updated on or after 2024-03-01T08:30Z.

Calls: `getBook({"bookId":"BK-4471","fields":["title","author","year"]})`; `searchBooks({"filter":{"genre":"poetry","year":1994},"limit":12,"updatedAfter":"2024-03-01T08:30Z"})`.

Parent assessment: Clear book projection and genre/year/update search.

### semantic-927-0023

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Please retrieve the media asset with id 47215, retrieve the claim CLM-88231, and list all revisions with the editorial decision approved that were reviewed on or after 2025-03-01T09:30Z.

Calls: `getAsset({"assetId":47215})`; `getClaim({"claimId":"CLM-88231"})`; `listRevisions({"decision":"approved","reviewedAfter":"2025-03-01T09:30Z"})`.

Parent assessment: Individually useful media/claim/revision reads; unrelated but permissible operator batch.

### semantic-927-0024

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Retrieve machine MCH-4820 and return only its machineId, status, and location fields.

Calls: `getMachine({"fields":["machineId","status","location"],"machineId":"MCH-4820"})`.

Parent assessment: Useful machine status/location projection; known ID alongside new fields is fine.

### semantic-927-0025

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, could you do a few things for me? I want to confirm borrower 418 is in the system and just see their ID and name. Then pull the title, author, genre, and year for book BK-2071. And finally, search for poetry by Imogen Hartley from 1987 that's been updated since 2024-03-12 09:45 UTC, but only show me up to 12 of them.

Calls: `getBorrower({"borrowerId":418,"fields":["borrowerId","name"]})`; `getBook({"bookId":"BK-2071","fields":["title","author","genre","year"]})`; `searchBooks({"filter":{"author":"Imogen Hartley","genre":"poetry","year":1987},"limit":12,"updatedAfter":"2024-03-12T09:45Z"})`.

Parent assessment: Natural library batch with explicit existence wording and useful name/title data; earlier candidate also looks semantically reasonable.

### semantic-927-0026

Parent: **needs_revision**. Subagent: **needs_revision**.
Pipeline: unresolved.

> Please list all revisions with decision changes_requested, list comments for post POST-4821, read the full record of post POST-4821, and read the profile of user mira_writes.

Calls: `searchPosts({})`.

Parent assessment: Request specifies four media/social operations; canonical calls contain only an unfiltered searchPosts, none of the requested actions.

### semantic-927-0027

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull book BK-7734 (just title, author, year), borrower 812's name, up to 20 poetry books from 1954, and all loans with no filters.

Calls: `getBook({"bookId":"BK-7734","fields":["title","author","year"]})`; `getBorrower({"borrowerId":812,"fields":["name"]})`; `searchBooks({"filter":{"genre":"poetry","year":1954},"limit":20})`; `listLoans({})`.

Parent assessment: Clear library batch with a genuinely unfiltered loan view.

### semantic-927-0028

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> List all refunds without any filtering, then report the daily sales total for the west region on 2026-03-14, retrieve the sku, name and price of product SKU-7742-QX, and read the store named “Larkspur Crossing Outlet”.

Calls: `listRefunds({})`; `getDailySales({"date":"2026-03-14","region":"west"})`; `getProduct({"fields":["sku","name","price"],"sku":"SKU-7742-QX"})`; `getStore({"storeName":"Larkspur Crossing Outlet"})`.

Parent assessment: Plausible commerce dashboard tasks; role-appropriate store name.

### semantic-927-0029

Parent: **good**. Subagent: **good**.
Pipeline: unresolved.

> Show me title, author and year for book BK-207. Also list first 20 books from the whole catalog, no filters.

Calls: `getBook({"bookId":"BK-207","fields":["title","author","year"]})`; `searchBooks({"limit":20})`.

Parent assessment: Meaningful unfiltered book search capped at20. Nonzero arguments do not make it semantically filtered, though zero-argument structural control may fail.

### semantic-927-0030

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Order me a hardcover copy of whatever the library has on the shelf and ship it to my place, thanks.

Calls: none (unsupported).

Parent assessment: Unsupported purchase/shipping action, but 'whatever on shelf' is vague and more contrived than a normal purchase.

### semantic-927-0031

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Show me all loans, the Lisbon forecast for 2025-06-15, and book BK-77.

Calls: `listLoans({})`; `getWeather({"location":"Lisbon","date":"2025-06-15"})`; `getBook({"bookId":"BK-77"})`.

Parent assessment: Clear small independent library/weather batch, little common purpose.

### semantic-927-0032

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> shoot a text over to my farmhand Danny at 555-0184 letting him know the north gate latch is busted and he should use the side entrance tomorrow morning

Calls: none (unsupported).

Parent assessment: Natural farmhand SMS request; no messaging capability.

### semantic-927-0033

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull alert 4821 showing just severity and raisedAt, then list up to 20 critical alerts since 2025-03-04T08:30Z, and up to 10 failed builds on branch release/7.2 started on 2025-03-03.

Calls: `getAlert({"alertId":4821,"fields":["severity","raisedAt"]})`; `listAlerts({"limit":20,"severity":"critical","since":"2025-03-04T08:30Z"})`; `listBuilds({"branch":"release/7.2","limit":10,"startedOn":"2025-03-03","status":"failed"})`.

Parent assessment: Good build/alert operations, exact filters and no ranking assumption.

### semantic-927-0034

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you check if sample SMP-7042 is a soil sample collected on 2024-03-11 and only show me the sample ID, type, collection date, and site? Also pull up the PCR-16S assay definition, and find up to 10 passing assay runs completed on or after 2024-03-10T08:00Z with a minimum yield of 0.75.

Calls: `getSample({"sampleId":"SMP-7042","fields":["sampleId","sampleType","collectedOn","site"]})`; `getAssay({"assayCode":"PCR-16S"})`; `listAssayRuns({"outcome":"pass","minYield":0.75,"completedAfter":"2024-03-10T08:00Z","limit":10})`.

Parent assessment: Useful verification of sample attributes; getSample returns needed fields and assistant can compare without a separate analysis tool.

### semantic-927-0035

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull the full record for book BK-8842.

Calls: `getBook({"bookId":"BK-8842"})`.

Parent assessment: Normal full-record lookup.

### semantic-927-0036

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, pull up just the title, author, and genre for book BK-77Q, and also grab the name for borrower 842.

Calls: `getBook({"bookId":"BK-77Q","fields":["title","author","genre"]})`; `getBorrower({"borrowerId":842,"fields":["name"]})`.

Parent assessment: Natural terse library pair returning new information.

### semantic-927-0037

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Show borrower 742's id and name, find up to 12 poetry books by Ivy Marsh, and list overdue loans open on 2024-11-03.

Calls: `getBorrower({"borrowerId":742,"fields":["borrowerId","name"]})`; `searchBooks({"filter":{"author":"Ivy Marsh","genre":"poetry"},"limit":12})`; `listLoans({"openOn":"2024-11-03","status":"overdue"})`.

Parent assessment: Clear library filters/projection; contributes to repeated poetry/borrower-pattern bias.

### semantic-927-0038

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you search products for me? I want books only, called exactly "The Cartographer's Lantern", and just show me up to 12 of them.

Calls: `searchProducts({"category":"books","limit":12,"name":"The Cartographer's Lantern"})`.

Parent assessment: Plausible exact-title product search.

### semantic-927-0039

Parent: **good**. Subagent: **usable_technical**.
Pipeline: accepted.

> Call the Blue Harbor Grill and move my Friday reservation to 8pm.

Calls: none (unsupported).

Parent assessment: Natural unsupported restaurant call/reservation modification.

### semantic-927-0040

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Show me all refunds with no filters, the sales total for 2024-03-12, the type and price of room RM-208, the price of SKU-8860, and the record for the store Harbor Point Outlet.

Calls: `listRefunds({})`; `getDailySales({"date":"2024-03-12"})`; `getRoom({"fields":["roomId","type","price"],"roomId":"RM-208"})`; `getProduct({"fields":["sku","price"],"sku":"SKU-8860"})`; `getStore({"storeName":"Harbor Point Outlet"})`.

Parent assessment: Useful commerce batch with an unrelated room lookup; return IDs alongside requested new fields are reasonable labels. Earlier version is semantically reasonable but lacks zero-arg coverage.

### semantic-927-0041

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you pull up post POST-90210 but just show me the post ID, author, and likes? Also fetch up to 12 comments on that same post, look up claim CLM-778899 with only its ID, amount, and status, and then just give me the whole farm equipment list with no type or status filter.

Calls: `getPost({"fields":["postId","author","likes"],"postId":"POST-90210"})`; `listComments({"limit":12,"postId":"POST-90210"})`; `getClaim({"claimId":"CLM-778899","fields":["claimId","amount","status"]})`; `listEquipment({})`.

Parent assessment: Social post/comments coherent, claims and all equipment are independent additions; possible technical batch.

### semantic-927-0042

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull up the comment thread for post POST-7742 — up to 40 comments — and also grab that post's author and content.

Calls: `listComments({"limit":40,"postId":"POST-7742"})`; `getPost({"fields":["author","content"],"postId":"POST-7742"})`.

Parent assessment: Natural post plus comment-thread request, same explicit post ID.

### semantic-927-0043

Parent: **usable_technical**. Subagent: **usable_technical**.
Pipeline: accepted.

> Pull borrower 742's name and meter MTR-8820's tariff code.

Calls: `getBorrower({"borrowerId":742,"fields":["borrowerId","name"]})`; `getMeter({"fields":["meterId","tariffCode"],"meterId":"MTR-8820"})`.

Parent assessment: Two clear independent lookups, no common purpose; each returns new information.

### semantic-927-0044

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you grab me the name and all linked loans for borrower 412, tell me the title, author, and year of book BK-8842, and also search for up to 20 poetry books by Marisol Ferrante that were updated at or after 2024-03-01T09:30Z?

Calls: `getBorrower({"borrowerId":412,"fields":["name"]})`; `getBook({"bookId":"BK-8842","fields":["title","author","year"]})`; `searchBooks({"filter":{"author":"Marisol Ferrante","genre":"poetry"},"limit":20,"updatedAfter":"2024-03-01T09:30Z"})`.

Parent assessment: Library request explicitly asks linked loans and projected profile name; getBorrower semantics support this.

### semantic-927-0045

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Run the following five lookups for me: (1) search routes from Kestrel Bay to Aldermoor Junction, returning at most 5 rows; (2) list assay runs with outcome pass, minimum yield 0.62, completed at or after 2024-03-01T08:30Z, returning at most 20 rows; (3) read product SKU-4711-TRN with only the sku, name, and price fields; (4) read post POST-8842-KX with only the postId, author, content, and likes fields; (5) list comments for post POST-8842-KX, returning at most 12 rows.

Calls: `searchRoutes({"destination":"Aldermoor Junction","limit":5,"origin":"Kestrel Bay"})`; `listAssayRuns({"completedAfter":"2024-03-01T08:30Z","limit":20,"minYield":0.62,"outcome":"pass"})`; `getProduct({"fields":["sku","name","price"],"sku":"SKU-4711-TRN"})`; `getPost({"fields":["postId","author","content","likes"],"postId":"POST-8842-KX"})`; `listComments({"limit":12,"postId":"POST-8842-KX"})`.

Parent assessment: Five individually supported queries; substantial cross-domain shopping-list character.

### semantic-927-0046

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please arrange for a technician to visit room RM-401 tomorrow morning and restore its electricity supply, then confirm the work order number to me.

Calls: none (unsupported).

Parent assessment: Clear unsupported physical technician/work-order action.

### semantic-927-0047

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull assay ASSAY-NITRATE-7, sample SMP-9042 (just sampleId and site), and up to 12 water plus 5 soil samples collected on 2025-03-14.

Calls: `getAssay({"assayCode":"ASSAY-NITRATE-7"})`; `getSample({"fields":["sampleId","site"],"sampleId":"SMP-9042"})`; `listSamples({"collectedOn":"2025-03-14","limit":12,"sampleType":"water"})`; `listSamples({"collectedOn":"2025-03-14","limit":5,"sampleType":"soil"})`.

Parent assessment: Plausible lab batch, separate water/soil views with distinct caps and useful sample site.

### semantic-927-0048

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Show up to 20 overdue loans that were still open on 2024-11-05; also list up to 10 poetry books by Marisol Quintero published in 1998 and updated at or after 2024-09-01T08:30Z; and get borrower 742's borrowerId and name only.

Calls: `listLoans({"limit":20,"openOn":"2024-11-05","status":"overdue"})`; `searchBooks({"filter":{"author":"Marisol Quintero","genre":"poetry","year":1998},"limit":10,"updatedAfter":"2024-09-01T08:30Z"})`; `getBorrower({"borrowerId":742,"fields":["borrowerId","name"]})`.

Parent assessment: Faithful library batch, but repeats poetry/borrower742/1998 recipe.

### semantic-927-0049

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> List up to 20 active outages starting on or after 2024-03-01.

Calls: `listOutages({"afterDate":"2024-03-01","limit":20,"status":"active"})`.

Parent assessment: Simple useful outage query with inclusive bound.

### semantic-927-0050

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Show me what's in bin R-07, the sku and name for TX-4410, its inbound movements from 2023-11-14 08:30 UTC (up to 20), and the shortage and surplus stocktakes counted on 2023-11-10 (5 each).

Calls: `getBin({"binCode":"R-07"})`; `getItem({"fields":["sku","name"],"sku":"TX-4410"})`; `listMovements({"afterInstant":"2023-11-14T08:30Z","direction":"inbound","limit":20,"sku":"TX-4410"})`; `listStocktakes({"countedOn":"2023-11-10","limit":5,"result":"shortage"})`; `listStocktakes({"countedOn":"2023-11-10","limit":5,"result":"surplus"})`.

Parent assessment: Coherent warehouse inventory/movement/stocktake views, same known SKU rather than output chaining.

### semantic-927-0051

Parent: **good**. Subagent: **good**.
Pipeline: unresolved.

> Hey, grab me book BK-742's title, author, and year, then show me up to 8 overdue loans that were still open on 2024-11-18, and pull borrower 4128's profile with all their linked loan records.

Calls: `getBook({"bookId":"BK-742","fields":["title","author","year"]})`; `listLoans({"limit":8,"openOn":"2024-11-18","status":"overdue"})`; `getBorrower({"borrowerId":4128})`.

Parent assessment: Meaningful library batch even though structural zero-argument target is unmet; earlier all-loans request incorrectly capped at20.

### semantic-927-0052

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Pull up asset 41207 with assetId, kind, title and publishedOn; show me changes_requested revisions for article ART-green-roofs-2024 reviewed since 2024-11-01T00:00Z, max 25; and read the PCR-16S assay.

Calls: `getAsset({"assetId":41207,"fields":["assetId","kind","title","publishedOn"]})`; `listRevisions({"articleId":"ART-green-roofs-2024","decision":"changes_requested","limit":25,"reviewedAfter":"2024-11-01T00:00Z"})`; `getAssay({"assayCode":"PCR-16S"})`.

Parent assessment: Media/revision/assay batch is technically usable but weakly connected.

### semantic-927-0053

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, could you pull up the whole policy catalogue for me first, then show me everything on policy POL-8842 and all the claims tied to that policy?

Calls: `searchPolicies({})`; `getPolicy({"policyId":"POL-8842"})`; `listClaims({"policyId":"POL-8842"})`.

Parent assessment: Verified getPolicy describes only a policy record, not linked claims; separate listClaims is useful. Natural full catalogue plus specific policy/claim view.

### semantic-927-0054

Parent: **usable_technical**. Subagent: **good**.
Pipeline: unresolved.

> Hey, can you pull a few things for me? Get the east region's daily sales for 2025-09-14, grab the article ART-urban-rooftop-gardens, show me the caseId, title, and status for CASE-884, find Lisbon to Porto routes with a 12-row cap, and list approved refunds of at least 250.5 that were processed after 2025-09-01T09:30+02:00, capped at 10.

Calls: `getDailySales({"date":"2025-09-14","region":"east"})`; `getArticle({"articleId":"ART-urban-rooftop-gardens"})`; `getCase({"caseId":"CASE-884","fields":["caseId","title","status"]})`; `searchRoutes({"destination":"Porto","limit":12,"origin":"Lisbon"})`; `listRefunds({"limit":10,"minAmount":250.5,"processedAfter":"2025-09-01T09:30+02:00","status":"approved"})`.

Parent assessment: Very broad cross-domain batch; values/queries meaningful but synthetic coverage-list feel. Earlier version also appears semantically plausible.

### semantic-927-0055

Parent: **good**. Subagent: **good**.
Pipeline: unresolved.

> Pull borrower 742's id and name, search up to 5 poetry books from 1954, and list up to 20 loans (any status, any dates).

Calls: `getBorrower({"borrowerId":742,"fields":["borrowerId","name"]})`; `searchBooks({"filter":{"genre":"poetry","year":1954},"limit":5})`; `listLoans({"limit":20})`.

Parent assessment: Clear library views; capped all-status/all-date loans are semantically unfiltered, though not zero-argument.

### semantic-927-0056

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you pull four things for me? I want the revisions for the article with slug ART-harbor-wind that were marked approved, then asset number 4412 but only show me the assetId, kind, title and publishedOn fields, then the outbound stock movements for sku WH-4417 from 2024-05-01T08:30Z onward, and finally the water samples collected on 2024-05-02.

Calls: `listRevisions({"decision":"approved","articleId":"ART-harbor-wind"})`; `getAsset({"assetId":4412,"fields":["assetId","kind","title","publishedOn"]})`; `listMovements({"direction":"outbound","sku":"WH-4417","afterInstant":"2024-05-01T08:30Z"})`; `listSamples({"sampleType":"water","collectedOn":"2024-05-02"})`.

Parent assessment: Natural wrapper around largely unrelated media/warehouse/lab queries.

### semantic-927-0057

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Search Kyoto hotels with min rating 4.

Calls: `searchHotels({"city":"Kyoto","minRating":4})`.

Parent assessment: Normal short hotel search with a clear minimum rating.

### semantic-927-0058

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Can you go ahead and order 30 more ergonomic desk chairs from our office-supply vendor and have them delivered to the downtown branch by next Friday?

Calls: none (unsupported).

Parent assessment: Natural unsupported purchase/delivery action.

### semantic-927-0059

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Search for poetry books by Nadia Verrill published in 1994, up to 12 results, and also list all loans without any filters.

Calls: `searchBooks({"filter":{"author":"Nadia Verrill","genre":"poetry","year":1994},"limit":12})`; `listLoans({})`.

Parent assessment: Simple library batch; earlier date-only wording bound to midnightUTC instant without explicit zone is ambiguous.

### semantic-927-0060

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Please give me two complete overviews, unfiltered: (1) all production runs regardless of status or date, and (2) all hearings regardless of case or date.

Calls: `listProduction({})`; `listHearings({})`.

Parent assessment: Two complete independent list overviews; usable but formulaic emphasis on unfiltered/no-case/no-date.

### semantic-927-0061

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, could you pull up to 25 outbound stock movements recorded from 2024-05-01T00:00Z onward, and also grab the daily sales total for the west region on 2024-05-14?

Calls: `listMovements({"afterInstant":"2024-05-01T00:00Z","direction":"outbound","limit":25})`; `getDailySales({"date":"2024-05-14","region":"west"})`.

Parent assessment: Natural outbound inventory movements plus regional sales total.

### semantic-927-0062

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Retrieve the following, without altering any identifiers: the contents of bin B-47; course MATH-221; daily sales for 2024-11-05 in the east region; product SKU-7704 with only name and price; and every refund with no status, amount, or time filtering.

Calls: `getBin({"binCode":"B-47"})`; `getCourse({"courseCode":"MATH-221"})`; `getDailySales({"date":"2024-11-05","region":"east"})`; `getProduct({"fields":["name","price"],"sku":"SKU-7704"})`; `listRefunds({})`.

Parent assessment: Five-way coverage-style batch; 'without altering any identifiers' exposes fidelity scaffolding.

### semantic-927-0063

Parent: **uncertain**. Subagent: **usable_technical**.
Pipeline: accepted.

> Pull up the full records for builds BLD-8842, BLD-9103 and BLD-9377 — I want the branch, status, start date and duration for each.

Calls: `getBuild({"buildId":"BLD-8842","fields":["buildId","branch","status","startedOn","durationMin"]})`; `getBuild({"buildId":"BLD-9103","fields":["buildId","branch","status","startedOn","durationMin"]})`; `getBuild({"buildId":"BLD-9377","fields":["buildId","branch","status","startedOn","durationMin"]})`.

Parent assessment: Full build records encoded as exhaustive known-field projections; need establish equivalence to omit-for-full contract rather than assume response has no other fields.

### semantic-927-0064

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Please do three quick checks:
> 1. Get product SKU-7734 but only return its sku, name, and price.
> 2. List up to 45 failed builds that started on 2025-11-03, across all branches (don't filter by branch).
> 3. Get alert 812, and include all the fields: alertId, severity, buildId, and raisedAt.

Calls: `getProduct({"fields":["sku","name","price"],"sku":"SKU-7734"})`; `listBuilds({"limit":45,"startedOn":"2025-11-03","status":"failed"})`; `getAlert({"alertId":812,"fields":["alertId","severity","buildId","raisedAt"]})`.

Parent assessment: Useful product/build/alert batch but technical field-list phrasing.

### semantic-927-0065

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Pull overdue loans open on 2026-03-14 (max 12), just the name on borrower 412, poetry books with year 1987 updated from 2026-01-01T00:00Z (max 20), and then every loan you have.

Calls: `listLoans({"limit":12,"openOn":"2026-03-14","status":"overdue"})`; `getBorrower({"borrowerId":412,"fields":["name"]})`; `searchBooks({"filter":{"genre":"poetry","year":1987},"limit":20,"updatedAfter":"2026-01-01T00:00Z"})`; `listLoans({})`.

Parent assessment: Faithful library views; filtered and general loans together allowed, though repeated recipe is noticeable.

### semantic-927-0066

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please pull up part PRT-4472, but I only need its partId, name, and stock.

Calls: `getPart({"fields":["partId","name","stock"],"partId":"PRT-4472"})`.

Parent assessment: Natural part stock/name lookup with useful projected information.

### semantic-927-0067

Parent: **good**. Subagent: **usable_technical**.
Pipeline: accepted.

> Can you pull up case CASE-4471 and document DOC-3382, show me any hearings on 2025-03-14, and search federal statutes for "wire fraud"?

Calls: `getCase({"caseId":"CASE-4471"})`; `getDocument({"docId":"DOC-3382"})`; `listHearings({"date":"2025-03-14"})`; `searchStatutes({"keyword":"wire fraud","jurisdiction":"federal"})`.

Parent assessment: Reasonable legal records/hearings/statute request; 'any hearings' can naturally mean matching date list.

### semantic-927-0068

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please list up to 12 graphic assets published on or after 2024-03-01, and also retrieve asset 4821 with only the fields assetId, kind, title, and publishedOn.

Calls: `listAssets({"kind":"graphic","limit":12,"publishedAfter":"2024-03-01"})`; `getAsset({"assetId":4821,"fields":["assetId","kind","title","publishedOn"]})`.

Parent assessment: Verified publishedAfter explicitly means on/after in this tool, so the inclusive wording is faithful.

### semantic-927-0069

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please retrieve book BK-7421 with only the title, author, and genre fields returned, and retrieve borrower 1842 with only the name field returned.

Calls: `getBook({"bookId":"BK-7421","fields":["title","author","genre"]})`; `getBorrower({"borrowerId":1842,"fields":["name"]})`.

Parent assessment: Normal two-record library lookup.

### semantic-927-0070

Parent: **usable_technical**. Subagent: **usable_technical**.
Pipeline: accepted.

> Please pull the profile summary (borrower ID and name only) for borrower 4187; then search for up to 25 reference books published in 1987 that were updated at or after 2024-11-03T08:45Z; also retrieve the daily sales total for 2025-02-14 in the west region; and finally search for up to 12 routes from Lakeview Station to Port Meridian.

Calls: `getBorrower({"borrowerId":4187,"fields":["borrowerId","name"]})`; `searchBooks({"filter":{"genre":"reference","year":1987},"limit":25,"updatedAfter":"2024-11-03T08:45Z"})`; `getDailySales({"date":"2025-02-14","region":"west"})`; `searchRoutes({"destination":"Port Meridian","limit":12,"origin":"Lakeview Station"})`.

Parent assessment: Clear but stuffed four-domain batch; reference genre is useful variation from dominant poetry.

### semantic-927-0071

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Find up to 12 routes from Riverside Station to Northgate Market; list up to 10 failed builds on release/7.4 started 2026-03-02; show up to 20 critical alerts since 2026-03-01T06:30Z; and list up to 15 departures for route RT-880 after 2026-03-02T17:45+01:00.

Calls: `searchRoutes({"destination":"Northgate Market","limit":12,"origin":"Riverside Station"})`; `listBuilds({"branch":"release/7.4","limit":10,"startedOn":"2026-03-02","status":"failed"})`; `listAlerts({"limit":20,"severity":"critical","since":"2026-03-01T06:30Z"})`; `listDepartures({"after":"2026-03-02T17:45+01:00","limit":15,"routeId":"RT-880"})`.

Parent assessment: Technically clear transit/devops batch, loosely related.

### semantic-927-0072

Parent: **needs_revision**. Subagent: **needs_revision**.
Pipeline: unresolved.

> Show me the loan list, the hearings on 2023-11-07, and federal statutes about evidence.

Calls: `listLoans({"limit":0})`; `listHearings({"date":"2023-11-07","limit":0})`.

Parent assessment: Missing statute search entirely. listLoans/listHearings limit0 return no rows under max-rows contract, not 'all'.

### semantic-927-0073

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please do three things for me: 1) pull borrower 742's profile, showing only the borrower id and name; 2) fetch book BK-8842 but just its title, author, and year; 3) search for books by Marisol Vega in the poetry genre published in 1998 that were updated at or after 2024-03-15T09:30Z, and cap the results at 25 rows.

Calls: `getBorrower({"borrowerId":742,"fields":["borrowerId","name"]})`; `getBook({"bookId":"BK-8842","fields":["title","author","year"]})`; `searchBooks({"filter":{"author":"Marisol Vega","genre":"poetry","year":1998},"limit":25,"updatedAfter":"2024-03-15T09:30Z"})`.

Parent assessment: Coherent library checklist but nearly repeats previous poetry/year/borrower742/BK8842 recipe.

### semantic-927-0074

Parent: **good**. Subagent: **usable_technical**.
Pipeline: accepted.

> Here is my checklist: 1) tell me the weather forecast for Reykjavik for the next three days; 2) include the expected high and low temperature for each day; 3) include whether rain or snow is expected. I don't need anything else.

Calls: none (unsupported).

Parent assessment: Verified offered catalogue has hotels/rooms/reservations/alerts/policies but no getWeather. This is a valid read-only unsupported weather question, not a write-action negative.

### semantic-927-0075

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please run this checklist for me: 1) show me everything in bin B-07; 2) list up to 20 shortage stocktakes counted on 2024-06-30; 3) list up to 30 inbound movements for SKU-4471 at or after 2024-06-01T08:00Z; 4) list up to 10 surplus stocktakes counted on 2024-06-30.

Calls: `getBin({"binCode":"B-07"})`; `listStocktakes({"countedOn":"2024-06-30","limit":20,"result":"shortage"})`; `listMovements({"afterInstant":"2024-06-01T08:00Z","direction":"inbound","limit":30,"sku":"SKU-4471"})`; `listStocktakes({"countedOn":"2024-06-30","limit":10,"result":"surplus"})`.

Parent assessment: Useful warehouse shortage/surplus/movement/bin views.

### semantic-927-0076

Parent: **usable_technical**. Subagent: **good**.
Pipeline: unresolved.

> Hey, could you pull up build BLD-7734, customer CUST-2046 (just their ID, name, and tier please), the day_night tariff definition, up to 12 books, and the shipped orders placed after 2024-06-01T00:00Z — cap that order list at 30. Thanks!

Calls: `getBuild({"buildId":"BLD-7734"})`; `getCustomer({"customerId":"CUST-2046","fields":["customerId","name","tier"]})`; `getTariff({"tariffCode":"day_night"})`; `searchProducts({"category":"books","limit":12})`; `listOrders({"after":"2024-06-01T00:00Z","limit":30,"status":"shipped"})`.

Parent assessment: Very wide technical batch; product category books may satisfy book ask in offered retail context, not necessarily wrong API.

### semantic-927-0077

Parent: **needs_revision**. Subagent: **usable_technical**.
Pipeline: accepted.

> Pull up assay MGX-ITS2-07 and give me just the sample type and site for sample SMP-4417-C.

Calls: `getAssay({"assayCode":"MGX-ITS2-07"})`; `getSample({"fields":["sampleId","sampleType","site"],"sampleId":"SMP-4417-C"})`.

Parent assessment: Explicit 'just sample type and site' conflicts with projection adding sampleId; unlike nonexclusive display labels this is a fidelity defect.

### semantic-927-0078

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Could you check off the passing assay runs for me: only those completed at or after 2024-03-15T08:30Z with a yield of at least 0.82, and cap the list at 25 rows?

Calls: `listAssayRuns({"completedAfter":"2024-03-15T08:30Z","limit":25,"minYield":0.82,"outcome":"pass"})`.

Parent assessment: Clear assay-run threshold/date/list cap; 'check off' is loose checklist phrasing, no explicit persistent mutation requested.

### semantic-927-0079

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> For my end-of-month checklist: please get the daily sales total for 2024-11-30 in the east region and get the price for SKU-8841.

Calls: `getDailySales({"date":"2024-11-30","region":"east"})`; `getProduct({"fields":["sku","price"],"sku":"SKU-8841"})`.

Parent assessment: Plausible end-of-month commerce checklist.

### semantic-927-0080

Parent: **good**. Subagent: **usable_technical**.
Pipeline: accepted.

> List every loan record currently on file.

Calls: `listLoans({})`.

Parent assessment: Plain full loan listing is a legitimate information request, not zero-information merely because unfiltered.

### semantic-927-0081

Parent: **uncertain**. Subagent: **usable_technical**.
Pipeline: unresolved.

> Please fetch full details for customer CUST-4471, then get the daily sales total for 2024-11-05 in the north region, and finally list up to 20 comments for post POST-2207.

Calls: `getCustomer({"customerId":"CUST-4471","fields":["customerId","name","email","tier"]})`; `getDailySales({"date":"2024-11-05","region":"north"})`; `listComments({"limit":20,"postId":"POST-2207"})`.

Parent assessment: Full customer details encoded as exhaustive known-profile projection; verify contract equivalence and linked metadata before calling exact.

### semantic-927-0082

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Hey, could you grab me a few things? First, the overall sales total for March 14, 2026 (all regions). Then look up SKU-7742 and just give me its name and price. Also, I want the complete list of refunds — no status or amount filters, just everything. And check what hotels in Reykjavik have at least a 4.5-star rating. Finally, find any posts that mention 'battery recall'.

Calls: `getDailySales({"date":"2026-03-14"})`; `getProduct({"sku":"SKU-7742","fields":["name","price"]})`; `listRefunds({})`; `searchHotels({"city":"Reykjavik","minRating":4.5})`; `searchPosts({"keyword":"battery recall"})`.

Parent assessment: Five clear but scattered commerce/hotel/social tasks; natural date wording is a positive.

### semantic-927-0083

Parent: **usable_technical**. Subagent: **usable_technical**.
Pipeline: accepted.

> Compile a reference bundle for me. First, list every taught session in the catalogue, unfiltered and without a row cap. Second, retrieve claim CLM-88231 with all four fields: claimId, policyId, amount, and status. Third, search for all home policies under the holder name Beatrix Lindqvist, with no row limit.

Calls: `listSessions({})`; `getClaim({"claimId":"CLM-88231","fields":["claimId","policyId","amount","status"]})`; `searchPolicies({"holder":"Beatrix Lindqvist","type":"home"})`.

Parent assessment: Reference-bundle wrapper does not create a shared purpose across education/insurance; individually useful queries and plausible holder name.

### semantic-927-0084

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Please pull the full assay definition for code ENV-QC-772, and also search the books category for products named "Coastal Field Notebook", returning at most 20 rows.

Calls: `getAssay({"assayCode":"ENV-QC-772"})`; `searchProducts({"category":"books","limit":20,"name":"Coastal Field Notebook"})`.

Parent assessment: Assay definition plus exact retail book-product title is a possible technical batch.

### semantic-927-0085

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Checklist, please pull these records for me: 1) alert 7421, showing only alertId, severity and raisedAt; 2) alert 7422, showing only alertId, severity and buildId; 3) build BLD-8813, showing only buildId, status and durationMin; 4) at most 12 critical alerts raised at or after 2025-03-04T08:00Z.

Calls: `getAlert({"alertId":7421,"fields":["alertId","severity","raisedAt"]})`; `getAlert({"alertId":7422,"fields":["alertId","severity","buildId"]})`; `getBuild({"buildId":"BLD-8813","fields":["buildId","status","durationMin"]})`; `listAlerts({"limit":12,"severity":"critical","since":"2025-03-04T08:00Z"})`.

Parent assessment: Coherent build/alert checklist; all projections include genuinely new information.

### semantic-927-0086

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Hey, could you pull up the day/night tariff details for me, check the status of case CASE-4402 (just the case ID, title, and status), and also grab document DOC-8813?

Calls: `getTariff({"tariffCode":"day_night"})`; `getCase({"caseId":"CASE-4402","fields":["caseId","title","status"]})`; `getDocument({"docId":"DOC-8813"})`.

Parent assessment: Useful legal reads plus unrelated tariff details; natural day/night maps correct enum.

### semantic-927-0087

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please pull two things for me: the company-wide daily sales total for 2024-11-05 (no region filter), and an unfiltered list of all refunds with no status, amount or date filtering.

Calls: `getDailySales({"date":"2024-11-05"})`; `listRefunds({})`.

Parent assessment: Natural commerce totals plus complete unfiltered refunds.

### semantic-927-0088

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you grab me a few things: pull CUST-4471's name and email; find hotels in Ljubljana rated 4.5 stars or higher, max 8; list BIO-204 sessions on 2025-03-11, up to 20; search books named "Coastal Field Guide", max 15; and list shipped orders placed after 2025-02-01T00:00Z, up to 30.

Calls: `getCustomer({"customerId":"CUST-4471","fields":["name","email"]})`; `searchHotels({"city":"Ljubljana","limit":8,"minRating":4.5})`; `listSessions({"courseCode":"BIO-204","limit":20,"onDate":"2025-03-11"})`; `searchProducts({"category":"books","limit":15,"name":"Coastal Field Guide"})`; `listOrders({"after":"2025-02-01T00:00Z","limit":30,"status":"shipped"})`.

Parent assessment: Five-domain operator batch; role values fit, book-product query is valid retail use when catalogue supports it.

### semantic-927-0089

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Get part PRT-4820 with just partId and stock, and stop STP-7734 with stopId, location and routes.

Calls: `getPart({"fields":["partId","stock"],"partId":"PRT-4820"})`; `getStop({"fields":["stopId","location","routes"],"stopId":"STP-7734"})`.

Parent assessment: Clear independent part-stock and stop-route lookups with useful projections.

### semantic-927-0090

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Can you pull up product SKU-7742 (just name and price) and SKU-9081 (full record), plus the store pages for "Maple & Main" and "Harbor Point Books", and the daily sales total for 2024-06-15 in the west region?

Calls: `getProduct({"sku":"SKU-7742","fields":["name","price"]})`; `getProduct({"sku":"SKU-9081"})`; `getStore({"storeName":"Maple & Main"})`; `getStore({"storeName":"Harbor Point Books"})`; `getDailySales({"date":"2024-06-15","region":"west"})`.

Parent assessment: Coherent retail/store/sales views, realistic store names including ampersand.

### semantic-927-0091

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Hey, can you pull up book BK-4471 and just show me its title, author, genre, and year? And while you're at it, find me poetry books by Nadia Ferreira, up to 20 of them.

Calls: `getBook({"bookId":"BK-4471","fields":["title","author","genre","year"]})`; `searchBooks({"filter":{"author":"Nadia Ferreira","genre":"poetry"},"limit":20})`.

Parent assessment: Natural library pair, but another author-poetry query and recurring BK4471 ID.

### semantic-927-0092

Parent: **usable_technical**. Subagent: **good**.
Pipeline: unresolved.

> Pull the maintenance log for MCH-4471 after 2026-02-15T08:30Z, up to 20 rows, grab the assay definition ELISA-A2, and list any failed production runs on 2026-02-14, max 25.

Calls: `listMaintenance({"after":"2026-02-15T08:30Z","limit":20,"machineId":"MCH-4471"})`; `getAssay({"assayCode":"ELISA-A2"})`; `listProduction({"date":"2026-02-14","limit":25,"status":"failed"})`.

Parent assessment: Manufacturing queries plus separate assay lookup; technical but useful.

### semantic-927-0093

Parent: **good**. Subagent: **usable_technical**.
Pipeline: accepted.

> Retrieve the catalog record for book BK-407, limited to its book ID, title, author, and last-updated fields; retrieve the catalog record for book NOV-88213, limited to its title, genre, and year fields; retrieve borrower profile 512, limited to borrower ID and name; and retrieve the full borrower profile for borrower 77.

Calls: `getBook({"bookId":"BK-407","fields":["bookId","title","author","updatedAt"]})`; `getBook({"bookId":"NOV-88213","fields":["title","genre","year"]})`; `getBorrower({"borrowerId":512,"fields":["borrowerId","name"]})`; `getBorrower({"borrowerId":77})`.

Parent assessment: Formal library records request; differing opaque ID shapes are allowed, aliases like last-updated map appropriately.

### semantic-927-0094

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> pull up whatever maintenance has been logged for machine MCH-4477 since 2026-02-01T08:00Z, cap it at 12 rows

Calls: `listMaintenance({"machineId":"MCH-4477","after":"2026-02-01T08:00Z","limit":12})`.

Parent assessment: Ordinary machine maintenance request, clear cap; since/after boundary language remains a general semantic caveat.

### semantic-927-0095

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> grab me a few things: search books with author "Ines Marchetti", genre poetry, year 1998, cap it at 3 rows; list swab samples collected on 2024-03-17, max 12; pull borrower 4127 but only the borrowerId and name; show overdue loans that were open on 2025-01-09; and also just dump the full loans list.

Calls: `searchBooks({"filter":{"author":"Ines Marchetti","genre":"poetry","year":1998},"limit":3})`; `listSamples({"collectedOn":"2024-03-17","limit":12,"sampleType":"swab"})`; `getBorrower({"borrowerId":4127,"fields":["borrowerId","name"]})`; `listLoans({"openOn":"2025-01-09","status":"overdue"})`; `listLoans({})`.

Parent assessment: Useful but field-like library/lab batch; repeats poetry/1998 pattern. Earlier candidate is semantically plausible despite structural rejection.

### semantic-927-0096

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> Please text all farm equipment operators an urgent alert that tractor TR-77 is down for maintenance and must not be dispatched today.

Calls: none (unsupported).

Parent assessment: Natural unsupported operator SMS broadcast.

### semantic-927-0097

Parent: **usable_technical**. Subagent: **good**.
Pipeline: accepted.

> Get order ORD-1188, showing only status. Get customer CUST-3320 with name and tier. Get field FLD-614 with crop and area. List all production runs, no filters. List readings for meter MTR-8842 from 2024-06-01T00:00Z to 2024-06-30T23:59Z.

Calls: `getOrder({"orderId":"ORD-1188","fields":["status"]})`; `getCustomer({"customerId":"CUST-3320","fields":["name","tier"]})`; `getField({"fieldId":"FLD-614","fields":["crop","area"]})`; `listProduction({})`; `listReadings({"meterId":"MTR-8842","fromInstant":"2024-06-01T00:00Z","toInstant":"2024-06-30T23:59Z"})`.

Parent assessment: Five independently useful but loosely connected technical tasks, preserves explicit meter window.

### semantic-927-0098

Parent: **usable_technical**. Subagent: **good**.
Pipeline: unresolved.

> Could you check which planned outages start on or after 2026-05-01, pull up the day_night tariff definition, and also read the full record for hotel HTL-812?

Calls: `listOutages({"status":"planned","afterDate":"2026-05-01"})`; `getTariff({"tariffCode":"day_night"})`; `getHotel({"hotelId":"HTL-812"})`.

Parent assessment: Energy queries plus hotel lookup; clear mixed batch. Earlier explicit limit0 is faithful but low-utility/debug-like, not automatically a wrong parameter.

### semantic-927-0099

Parent: **good**. Subagent: **good**.
Pipeline: accepted.

> can you pull up whoever's on call for the payments backend team tonight?

Calls: none (unsupported).

Parent assessment: Verified offered field/build/alert tools provide no on-call roster; a natural missing-data-access negative, not a write action.

## Retained local evidence

Under runs/semantic-review-100-v1/:
- create/shard-{0,1,2,3}/: immutable specs, canonical creation records, accepted
  compatible results, request evidence, ledgers and manifests.
- review/blind-packets.jsonl: all 100 primary candidates plus 17 earlier texts,
  with machine verdicts excluded.
- review/catalogue.json: exact 64 contracts, deduplicated and checked for conflicts.
- review/provenance.jsonl: source mapping and machine status, kept separate.
- review/parent-assessments.jsonl: all 100 direct parent judgments.
- review/subagent-assessments.jsonl and subagent-review.md: independent @noa review.

No-text recoveries are retained under semantic-review-100-empty-recovery-v1
(slot70) and -v2 (slot91), with identical structural-input hashes. Nothing was
overwritten, exported into an active training mix, trained or benchmarked.
