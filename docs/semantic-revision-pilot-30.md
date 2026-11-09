# Semantic revision: 12-case calibration and matched 30-item pilot

## Conclusion

**Implemented the approved narrow revision; this experiment does not demonstrate
an overall quality improvement or readiness for unattended scale-up.**

The critic now accepts two previously false-rejected candidates and catches four
concrete missing-effect/condition cases, but it still accepts the known exclusive
projection mismatch. In new generation it accepted an unsupported next-12
ordering claim and rationalized a zero-row query as an existence check.
Parameter variety improved modestly; broad task quality did not clearly improve.
No examples were silently corrected, no readable weak slot was rerolled outside
its original two-attempt bound, and no training/bulk generation/promotion occurred.

## Changes and boundaries

- `quality.py` sends the actual user request and asserted context first in a
  readable brief, followed by public contracts and explicitly untrusted candidate
  intent/calls. Canonical syntax is not authority for user-selected values.
- Projection observations separate proposed input argument values from selected
  output key names. Asking for a name is not already knowing its value. Linked
  metadata remains relevant; these observations are hints, not automatic verdicts.
- Quality instructions distinguish source support from mere plan presence,
  explicit output exclusions from harmless identification, and user intent from
  API syntax or a personally preferred alternative plan. No keyword-based
  semantic checks or new normality restrictions were added.
- `CreationSpec` has an optional schema-derived exploration cue. A deterministic
  selected subset receives a scalar-enum option from its own catalogue; a local
  counter spreads planned cues across available choices. This is not a claim
  about human frequencies or observed-corpus exposure and is never a hard gate.
  Existing cues survive; absent cues parse compatibly. No new scheduler or
  hand-authored story/value pool was introduced.
- The creator's shapes refer to original argument values after wire decoding;
  `unfiltered` means empty canonical arguments. Wire objects still list every
  declared key, each optional slot omitted as `{}`. Legal explicit zero limits are not banned. Reusing the same
  API for distinct requests and leaving distractor APIs unused remain allowed.
- Catalogue membership, exact count/shape requirements, near-duplicate checks,
  non-chaining, context/identity ownership and frozen consumers are unchanged.
  CLI contracts are now semantic-creation-v2 / quality-operations-v3, refusing
  changed-input/prompt/config resumes instead of rewriting old rows.

## Execution and evidence

Command from repository root:

```sh
timeout --signal=TERM --kill-after=15s 1200s python3 -u \
  runs/semantic-revision-pilot-30-v1/run_experiment.py
```

Actual application `review_candidate` and `run_creation` paths ran through the
existing BudgetedClient against the model service. The one-off driver supplies
retained matched specs instead of resampling via CLI; CLI help and contract pins
were checked separately. This is real model-service execution on synthetic source
requests, not execution of fictional store/lab/etc. backends.

One shared ledger bounded **both phases together to $1**:
- **$0.052543** reported and accounted; no pending/retained unresolved spend.
- **85 fresh requests**, **0 cache hits**: 12 calibration, 42 creator, 31 pilot judge.
- Same requested model, deepseek/deepseek-v4.1-flash; creator 0.9, critic 0.0.
- Actual recorded provider routing varied. This is not a provider-controlled
  causal study or a claim about hidden model weights.
- Exit 0; all 12 calibration cases and 30 pilot identities reconciled exactly.

Evidence root: `runs/semantic-revision-pilot-30-v1/`. The driver, implementation
diff, immutable inputs, manifests, raw request/response evidence, original failed
attempts, receipt and descriptive analyzer outputs are retained there.

No automated tests were added. Existing checks: Ruff over src, strict mypy over
all 18 modules, compileall, and CLI help passed. Independent source review found
no blocking implementation defect; that is not proof of LLM quality.

### Final wire-contract clarification (after the live run)

Final audit found ambiguity in our pilot wording: it said literally arguments={}
for the zero-argument control, but the shared reader/creator wire requires every
declared argument key, with empty optional slots. The final prompt now explicitly
separates decoded argument VALUES from wire containers/slots, and says to omit
every optional value while retaining the wire keys. This also avoids counting
slot wrappers as original object-valued arguments.

A deterministic replay of all 26 accepted real model outputs through the original
schema and hard validator passed; six zero-argument calls have nonempty wire key
sets with every slot omitted. This is a contract clarification, not a changed
validator or a fresh model-quality proof. The live measurements below apply to
the captured pre-clarification prompt. No new paid reruns were made. Exact delta:
`postpilot-wire-clarification.diff`; replay receipt: `wire-replay.json`.

## Calibration: all 12 retained cases

These are source-bound probes, not an accuracy estimate. The four previously
unadmitted bad pairs had not all reached the old judge, so catching them now is
not evidence of improvement against measured old verdicts for those cases.

| Source case | Relevant observation |
| --- | --- |
| 0012 primary | Rejects omitted openOn date. |
| 0021 primary | Rejects missing getAlert action. |
| 0026 primary | Rejects four missing reads/unrequested empty searchPosts. |
| 0072 primary | Rejects missing statute read and unrequested zero-row bounds. |
| 0077 primary | **Still accepts extra sampleId despite just sample type and site.** |
| 0025 earlier | Now accepts ID/name lookup: name is newly retrieved, not supplied. |
| 0098 primary | Now accepts useful independent outage/tariff/hotel batch. |
| 0080 primary | Accepts ordinary complete unfiltered loan listing. |
| 0074 primary | Accepts unavailable weather-data no-call request. |
| 0034 primary | Accepts reasoning over retrieved sample fields without analytics API. |
| 0081 earlier | Zero limit is faithful and legal; call's lack of new information is flagged separately. |
| 0063 primary | Accepts all-known-field build projections; full-record equivalence is not thereby proved or normalized. |

The two former false-rejection examples now pass once, under the revised input.
The exclusivity miss remains. We did not add increasingly specific rules or keep
rejudging the same unchanged candidate until it passed.

## Matched generation: results and caveats

The 30 specs span all 16 supplied families and include four five-call targets.
Every original ID, catalogue, context, style, call count and required shape was
verified unchanged; only optional cues were added. This is a preselected coverage
probe, not a natural prevalence sample. Calibration cases are excluded from the
30. All 30 new primaries and all 11 earlier readable attempts were read directly;
there were no no-text primaries requiring additional recovery.

| Observation | Matched old 30 | New 30 |
| --- | ---: | ---: |
| Machine-accepted | 28 | 26 |
| Unresolved | 2 | 4 |
| Primary calls | 83 | 83 |
| Distinct called tools | 50 | 50 |
| Book searches | 5 | 4 |
| Book genre mix | poetry 5 | reference 2, poetry 2 |
| Accepted five-call slots / four planned | 3 | 2 |

Nine new specs had cues; seven primaries used the suggested choice. Others could
ignore a cue rather than force filler. The cue for book genre reference appears
in 0009; 0008 also generated reference without that cue. This suggests the
mechanism can steer parameters, not that it caused every difference.

The missing fifth object-filter case is 0065, which failed its unchanged hard
shape requirement. Its omission cannot be counted as improved diversity.
Borrower742 still appears twice. Narrow default motifs have not disappeared.

Both cohorts preserve the same raw call complexity. New 0090 is a positive
five-store, same-API batch instead of demonstrating several different APIs.
New 0035 is a normal returned-loan query; 0008 is a concise reference/year search.
These are useful cases, not evidence that unique-value counts equal new reasoning
types. Much of the corpus still consists of record projections and list filters.

### Manual grades and independent challenge

| Category | Old matched parent | New parent | New independent first read |
| --- | ---: | ---: | ---: |
| good | 22 | 20 | 29 |
| usable_technical | 8 | 7 | 0 |
| needs_revision | 0 | 2 | 1 |
| uncertain | 0 | 1 | 0 |

These are subjective judgments, not accuracy scores. The separately configured
reviewer read the new packet without machine verdicts or parent grades and first
identified the missing-build problem. After challenge, it acknowledged the
ordering and movement-scope concerns below without changing its original grades.
We preserve disagreement instead of claiming independent all-green validation.

### Concrete remaining findings

- **0014 — machine accepted:** asks for the next12 departures, but listDepartures
  promises a matching-row list and quantity cap, not chronological ordering.
  Capping at12 cannot guarantee the earliest12. The judge also claims the
  explicitly zero-row route search can confirm existence; no such count/existence
  metadata is established by that contract.
- **0076 — unresolved:** request includes full build BLD-4002 but its call is
  absent. The revised critic correctly catches this despite five calls satisfying
  the numeric target. The first attempt had seven calls under a five-call spec.
- **0050 — unresolved/parent uncertain:** movements are filtered by SKU WH-2210
  although the wording says all outbound movements. Prior item context might
  imply that scope, so this is ambiguous, not definitively invalid. The critic
  instead invents a bin-scoping obligation involving B-07, which the request did
  not establish. Role-separated formatting has not eliminated relational guesses.
- **0060 — unresolved:** a faithful request for a named machine's maintenance
  still supplies machineId, so it does not meet empty-argument coverage.
- **0065 — unresolved:** no required object-valued argument appears. One prior
  completion was empty, cause unknown—not a proven refusal.

Earlier attempts show additional real failures: using limit0 to count policies,
test sample/equipment existence, or get comment counts without promised total
metadata. Those failures were retained, not substituted for primaries.

## What this supports—and does not

The implementation is in place and some specific calibration cases improved.
The mechanism can influence selected categorical values without banning valid
alternatives. It did **not** establish a broad naturalness/semantic-quality gain,
improved admission yield, or a reliable autonomous quality gate. All source
contexts are empty, so contradictory populated-context behavior was not exercised.

Next evidence should test critic/model capability before accumulating more rules.
Context generation, softening exact count/shape requirements, and extra model
stages remain untested proposals, not changes made here. No additional paid
attempts were made after inspecting these failures. The final wire wording has
only deterministic replay evidence, not a second live generation measurement.

## Every new primary candidate

Unresolved entries are retained for assessment, not approved training examples.

### semantic-927-0000

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Two things, please: (1) pull up the course record for CS-205, and (2) list the taught sessions for that course on 2026-03-17.

Calls: `getCourse({"courseCode":"CS-205"})`; `listSessions({"courseCode":"CS-205","onDate":"2026-03-17"})`.

Assessment: Coherent course lookup plus its dated taught sessions; no invented API details.

### semantic-927-0001

Parent: **usable_technical**. Independent initial grade: **good**.
Machine admission: accepted.

> Grab me the sku, name, and price for product SKU-9042, the daily sales for 2024-11-07 in the east region, approved refunds of at least 150.5 processed since 2024-10-01T00:00Z (cap at 20 rows), and up to 12 departures on route RT-408 from 2024-11-07T08:30Z onward.

Calls: `getProduct({"fields":["sku","name","price"],"sku":"SKU-9042"})`; `getDailySales({"date":"2024-11-07","region":"east"})`; `listRefunds({"limit":20,"minAmount":150.5,"processedAfter":"2024-10-01T00:00Z","status":"approved"})`; `listDepartures({"after":"2024-11-07T08:30Z","limit":12,"routeId":"RT-408"})`.

Assessment: Faithful commerce/transit checklist with useful projected data; broad operator batch rather than one natural shared task.

### semantic-927-0003

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Grab case CASE-8841 with its id, title, status and filed date; grab CASE-2297 but just title and status; list CASE-2297's hearings for 2024-11-14, max 4; and search state statutes for "wrongful termination", up to 10 hits.

Calls: `getCase({"caseId":"CASE-8841","fields":["caseId","title","status","filedDate"]})`; `getCase({"caseId":"CASE-2297","fields":["title","status"]})`; `listHearings({"caseId":"CASE-2297","date":"2024-11-14","limit":4})`; `searchStatutes({"jurisdiction":"state","keyword":"wrongful termination","limit":10})`.

Assessment: Coherent legal records, case-specific hearings and statute search; exclusivity and caps match.

### semantic-927-0004

Parent: **usable_technical**. Independent initial grade: **good**.
Machine admission: accepted.

> Please pull up: approved refunds of $49.99 or more processed since 2024-11-01T09:00Z, max 25; field FLD-8842 showing id, name and crop; assay PCR-ITS2; item WH-3374 with sku, name and binCode; and up to 12 water samples collected on 2025-01-14.

Calls: `listRefunds({"limit":25,"minAmount":49.99,"processedAfter":"2024-11-01T09:00Z","status":"approved"})`; `getField({"fieldId":"FLD-8842","fields":["fieldId","name","crop"]})`; `getAssay({"assayCode":"PCR-ITS2"})`; `getItem({"fields":["sku","name","binCode"],"sku":"WH-3374"})`; `listSamples({"collectedOn":"2025-01-14","limit":12,"sampleType":"water"})`.

Assessment: Useful but scattered five-way finance/farm/lab/warehouse batch. Currency symbol assumes local monetary convention not documented; not a proven contradiction.

### semantic-927-0005

Parent: **usable_technical**. Independent initial grade: **good**.
Machine admission: accepted.

> Hey, could you grab the asset with ID 4821 but just show me the assetId and title? Also, for session SES-44, I want the excused attendance marks that came in at or after 2025-03-02T08:30Z, up to 25 of them. And pull claim CLM-7788 but only return its claimId, amount and status.

Calls: `getAsset({"assetId":4821,"fields":["assetId","title"]})`; `listAttendance({"limit":25,"markedAfter":"2025-03-02T08:30Z","sessionId":"SES-44","status":"excused"})`; `getClaim({"claimId":"CLM-7788","fields":["claimId","amount","status"]})`.

Assessment: Clear media/attendance/insurance batch, preserves projections and instant; broad independent errands allowed.

### semantic-927-0006

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Please pull the complete equipment inventory with no filters at all, and also give me the weather forecast for Cedar Hollow Orchard on 2025-06-14.

Calls: `listEquipment({})`; `getWeather({"date":"2025-06-14","location":"Cedar Hollow Orchard"})`.

Assessment: Natural farm inventory overview and location/date forecast. Earlier filtered sensor/alert views were plausible requests but not zero-argument coverage.

### semantic-927-0007

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Please look up meter MTR-4820 and return only its meterId, site, and tariffCode, and also list up to 25 planned outages that start on or after 2025-03-01.

Calls: `getMeter({"fields":["meterId","site","tariffCode"],"meterId":"MTR-4820"})`; `listOutages({"afterDate":"2025-03-01","limit":25,"status":"planned"})`.

Assessment: Straightforward meter metadata and dated planned-outage views; exact requested projection.

### semantic-927-0008

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Please search the library catalogue for reference books published in 1994.

Calls: `searchBooks({"filter":{"genre":"reference","year":1994}})`.

Assessment: Simple reference-book/year search; new genre without unnecessary author/limit slots. Earlier outage query did not meet required object shape.

### semantic-927-0009

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> I'm doing a quick audit — can you pull reference books published in 2011 that were updated since 2023-05-01T00:00Z (up to 12), the title/author/year for book BK-70421, just the name for borrower 4187, and any overdue loans open on 2024-09-03, capped at 20?

Calls: `searchBooks({"filter":{"genre":"reference","year":2011},"limit":12,"updatedAfter":"2023-05-01T00:00Z"})`; `getBook({"bookId":"BK-70421","fields":["title","author","year"]})`; `getBorrower({"borrowerId":4187,"fields":["name"]})`; `listLoans({"limit":20,"openOn":"2024-09-03","status":"overdue"})`.

Assessment: Coherent library audit views with reference genre/year2011 rather than only poetry/old-year recipes; still a familiar multi-view skeleton.

### semantic-927-0011

Parent: **usable_technical**. Independent initial grade: **good**.
Machine admission: accepted.

> Get me the forecast for Osaka on 2026-04-15 and for Lisbon on 2026-04-15, and list wheat crops.

Calls: `getWeather({"date":"2026-04-15","location":"Osaka"})`; `getWeather({"date":"2026-04-15","location":"Lisbon"})`; `listCrops({"cropType":"wheat"})`.

Assessment: Two useful same-API forecasts plus wheat crops; loosely connected batch, not a fidelity defect.

### semantic-927-0014

Parent: **needs_revision**. Independent initial grade: **good**.
Machine admission: accepted.

> Search routes from Marrowfield Depot to Kestrel Harbor with a zero-row limit, then pull route RT-7742's routeId, name and frequency, plus stop STP-3310's stopId, location and routes, and finally the next 12 departures for route RT-7742 at stop STP-3310 from 2026-04-18T06:45Z onward.

Calls: `searchRoutes({"destination":"Kestrel Harbor","limit":0,"origin":"Marrowfield Depot"})`; `getRoute({"fields":["routeId","name","frequency"],"routeId":"RT-7742"})`; `getStop({"fields":["stopId","location","routes"],"stopId":"STP-3310"})`; `listDepartures({"after":"2026-04-18T06:45Z","limit":12,"routeId":"RT-7742","stopId":"STP-3310"})`.

Assessment: Request asks for the next12 departures but tool promises no ordering, only matching rows and a quantity cap. A capped arbitrary subset cannot ensure earliest12. Explicit zero-row route search is faithful but low-utility/debug-like, not schema-invalid.

### semantic-927-0017

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Please pull the complete refunds list with no filters applied, and search local statutes for the keyword "refund" with no result cap.

Calls: `listRefunds({})`; `searchStatutes({"jurisdiction":"local","keyword":"refund"})`.

Assessment: Refund records plus local refund legislation is a plausible related need. Earlier store/statute reads were also plausible but lacked required zero-argument shape.

### semantic-927-0020

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Could you flip the editorial decision on the revision for the article "ART-harbor-lights" from changes_requested to approved, and leave a note saying the headline fix looks good now?

Calls: none (unsupported).

Assessment: Realistic unsupported revision edit/note action against read-only catalogue.

### semantic-927-0024

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Fetch the part PRT-4820 and return only its stock and supplier fields.

Calls: `getPart({"fields":["stock","supplier"],"partId":"PRT-4820"})`.

Assessment: Useful simple stock/supplier query with only requested output fields.

### semantic-927-0027

Parent: **usable_technical**. Independent initial grade: **good**.
Machine admission: accepted.

> Can you grab me: books by Miriam Osei-Bonsu in poetry from 1988; the complete loan list with no status or date filters; borrower 742's id and name only; and every pending refund processed on or after 2024-11-05T09:30Z?

Calls: `searchBooks({"filter":{"author":"Miriam Osei-Bonsu","genre":"poetry","year":1988}})`; `listLoans({})`; `getBorrower({"borrowerId":742,"fields":["borrowerId","name"]})`; `listRefunds({"processedAfter":"2024-11-05T09:30Z","status":"pending"})`.

Assessment: Clear library/refund batch; poetry/year/borrower742 pattern remains. Earlier comics batch requested5 calls under a4-call control, so do not substitute it as the primary.

### semantic-927-0032

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Go ahead and switch on the irrigation system for the north greenhouse right now, and let me know once the water's running.

Calls: none (unsupported).

Assessment: Plausible unsupported irrigation control; read-only catalogue cannot switch equipment on.

### semantic-927-0033

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Grab alert 20771 but only show me its severity and raisedAt. Also list every failed build on branch release/2.4 that started on 2024-11-05. And for build BLD-4417, just give me the branch, status and durationMin.

Calls: `getAlert({"alertId":20771,"fields":["severity","raisedAt"]})`; `listBuilds({"branch":"release/2.4","startedOn":"2024-11-05","status":"failed"})`; `getBuild({"buildId":"BLD-4417","fields":["branch","status","durationMin"]})`.

Assessment: Coherent build/alert operations with precise projections. Earlier candidate adds unrequested limit25 to failed-build listing; final omits it correctly.

### semantic-927-0035

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Show me up to 15 returned loans.

Calls: `listLoans({"limit":15,"status":"returned"})`.

Assessment: Ordinary returned-loan list with explicit cap15; simple requests are valid.

### semantic-927-0036

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Hey, grab me the title, author, and year for book BK-88713, and while you're at it pull up just the name for borrower 4142.

Calls: `getBook({"bookId":"BK-88713","fields":["title","author","year"]})`; `getBorrower({"borrowerId":4142,"fields":["name"]})`.

Assessment: Natural two-record library lookup with useful title/author/year and borrower name, no ID padding.

### semantic-927-0041

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Hey, can you pull up everything from the social feed — no filters, just all the posts — and also grab post POST-9087 with just the postId, author, and content, plus all its comments? Oh, and while you're at it, could you get me the profile for mira_vale too?

Calls: `searchPosts({})`; `getPost({"fields":["postId","author","content"],"postId":"POST-9087"})`; `listComments({"postId":"POST-9087"})`; `getUser({"username":"mira_vale"})`.

Assessment: Coherent feed/post/comments/profile read. Earlier zero-limited comments/equipment calls cannot establish total count/existence unless undocumented metadata is assumed.

### semantic-927-0047

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Pull the PCR-16S assay definition, then give me the sampleType and collectedOn for SMP-6001, and list up to 10 swab and 10 water samples collected on 2024-03-14.

Calls: `getAssay({"assayCode":"PCR-16S"})`; `getSample({"fields":["sampleType","collectedOn"],"sampleId":"SMP-6001"})`; `listSamples({"collectedOn":"2024-03-14","limit":10,"sampleType":"swab"})`; `listSamples({"collectedOn":"2024-03-14","limit":10,"sampleType":"water"})`.

Assessment: Coherent assay/sample details and10-per-type lab lists; same-API reuse is appropriate. Earlier zero-limit swab call cannot answer existence from returned rows.

### semantic-927-0050

Parent: **uncertain**. Independent initial grade: **good**.
Machine admission: unresolved.

> Show me bin B-07, the item WH-2210 with just sku and bin, all outbound movements after 2025-02-10T08:00Z, shortage stocktakes counted on 2025-02-14, and surplus stocktakes counted on 2025-02-14.

Calls: `getBin({"binCode":"B-07"})`; `getItem({"fields":["sku","binCode"],"sku":"WH-2210"})`; `listMovements({"afterInstant":"2025-02-10T08:00Z","direction":"outbound","sku":"WH-2210"})`; `listStocktakes({"countedOn":"2025-02-14","result":"shortage"})`; `listStocktakes({"countedOn":"2025-02-14","result":"surplus"})`.

Assessment: SKU WH2210 is applied to movements, while wording says all outbound movements after the instant. Prior item mention might imply item scope, but it is not explicit; ambiguity affects row selection. Do not call this definitively wrong merely for using an implicit relation.

### semantic-927-0053

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Hey, can you grab claim CLM-88204 but just the claim ID, amount, and status for me? Also search for home policies under Marisol Okafor, capped at 12 results. And finally, list all claims with no filters at all.

Calls: `getClaim({"claimId":"CLM-88204","fields":["claimId","amount","status"]})`; `searchPolicies({"holder":"Marisol Okafor","limit":12,"type":"home"})`; `listClaims({})`.

Assessment: Plausible insurance claim/home-policy/claims overview. Earlier count-with-limit0 wrongly assumes an unpromised total-count result.

### semantic-927-0055

Parent: **usable_technical**. Independent initial grade: **good**.
Machine admission: accepted.

> Pull borrower 742's name only. Also search books by Nell R. Coyne, poetry, 1998, updated at/after 2024-11-03T09:30Z, max 12. And list all loans.

Calls: `getBorrower({"borrowerId":742,"fields":["name"]})`; `searchBooks({"filter":{"author":"Nell R. Coyne","genre":"poetry","year":1998},"limit":12,"updatedAfter":"2024-11-03T09:30Z"})`; `listLoans({})`.

Assessment: Faithful library triple but same borrower742/poetry1998/update-time/full-loans recipe; useful schema composition, not a new kind of work.

### semantic-927-0057

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Show me the city of hotel HTL-742.

Calls: `getHotel({"fields":["city"],"hotelId":"HTL-742"})`.

Assessment: Simple useful hotel-city lookup, no unnecessary story or raw API syntax.

### semantic-927-0060

Parent: **good**. Independent initial grade: **good**.
Machine admission: unresolved.

> Please do two things: 1) retrieve part PRT-7781 and show me only its partId, name and stock. 2) list all maintenance records for machine MCH-3245 with no limit and no after filter.

Calls: `getPart({"fields":["partId","name","stock"],"partId":"PRT-7781"})`; `listMaintenance({"machineId":"MCH-3245"})`.

Assessment: Faithful part data plus all maintenance for a named machine; semantically valid even though machineId means it is not an empty-argument structural example.

### semantic-927-0065

Parent: **usable_technical**. Independent initial grade: **good**.
Machine admission: unresolved.

> Pull policy POL-88214 (holder and premium only), borrower 4772 with just the name, and give me the full unfiltered order list plus the full unfiltered loan list.

Calls: `getPolicy({"fields":["holder","premium"],"policyId":"POL-88214"})`; `getBorrower({"borrowerId":4772,"fields":["name"]})`; `listOrders({})`; `listLoans({})`.

Assessment: Useful but broad insurance/library/order overview batch; no book-filter object appears, so it cannot count as object-shape coverage.

### semantic-927-0076

Parent: **needs_revision**. Independent initial grade: **needs_revision**.
Machine admission: unresolved.

> Hi, could you pull up order ORD-801 with just the orderId, customer and status fields, and also grab customer CUST-901's name and email? I also want to see the cancelled orders list, and separately read build BLD-4001 with branch and status only and build BLD-4002 in full. Finally, give me an unfiltered product search with no name, category or limit.

Calls: `getOrder({"fields":["orderId","customer","status"],"orderId":"ORD-801"})`; `getCustomer({"customerId":"CUST-901","fields":["name","email"]})`; `listOrders({"status":"cancelled"})`; `getBuild({"buildId":"BLD-4001","fields":["branch","status"]})`; `searchProducts({})`.

Assessment: Six explicit requested reads but only five calls: full build BLD4002 is never retrieved. No listBuilds/bulk-build alternative in offered catalogue; cannot excuse missing effect as a different valid plan. Several IDs echo schema illustrations; this is descriptive, not itself a ban-worthy defect.

### semantic-927-0090

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Look up these five stores by name for me: Harbor Point Books, Cedar & Pine Outfitters, Moonrise Bakery, Ironwood Hardware, and Blue Lantern Cafe.

Calls: `getStore({"storeName":"Harbor Point Books"})`; `getStore({"storeName":"Cedar & Pine Outfitters"})`; `getStore({"storeName":"Moonrise Bakery"})`; `getStore({"storeName":"Ironwood Hardware"})`; `getStore({"storeName":"Blue Lantern Cafe"})`.

Assessment: Natural five-store lookup, repeating one API for genuinely distinct records rather than forced one-of-every-tool demonstration.

### semantic-927-0099

Parent: **good**. Independent initial grade: **good**.
Machine admission: accepted.

> Restart the failed build for the release-2.3 branch and post the result to our team chat.

Calls: none (unsupported).

Assessment: Plausible unsupported build restart/team-chat broadcast; catalogue contains only reads.

## Local reproducibility

- `run_experiment.py`: exact source selection and shared capped client. Existing
  runs pin captured prompt bytes; the final wording intentionally cannot resume
  into the old manifest. Reproduction of the live trial needs its captured
  pre-clarification prompt/implementation and a fresh output root.
- `pilot/specs.jsonl`, `matched-baseline.jsonl`, `calibration/inputs.jsonl`:
  immutable inputs and source pointers.
- `service/budget.json`, `service/requests/`, `receipt.json`, `run.log`:
  actual billing, wire/output evidence and process result.
- `pilot/creation.jsonl`: all terminal records/attempts;
  `pilot/results.jsonl`: machine-accepted compatibility view only.
- `review/blind-packets.jsonl`, `catalogue.json`, separate `provenance.jsonl`:
  30 blinded primaries, 11 earlier texts, 61 exact relevant contracts.
- `review/parent-assessments.jsonl`, `subagent-assessments.jsonl`,
  `subagent-review.md`: complete direct/independent judgments and disagreements.
- `summarize.py`, `metrics.json`, `analysis-*.json`: existing descriptive
  analyzer reused on review views, not training exports or quality thresholds.

The original 100-item run, saved targets, training mixes, benchmarks, scorers and
checkpoints were not modified.
