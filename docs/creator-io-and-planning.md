# Creator I/O ambiguity, judge low reasoning, and goal-first planning

## Outcome and scope

User authorized a low-reasoning judge test, an audit of ambiguous creator controls,
and analysis of a goal/final-state → automatic-solver approach. User later topped
up OpenRouter and allowed further bounded useful experiments.

Completed:
- A fresh off/low comparison on 14 retained cases, same model/prompt/data/schema,
  temperature0 and 3072 completion tokens. Every request was checked against its
  retained baseline: only reasoning differed.
- A separate 4096-token low-reasoning follow-up on the six unusable low outputs.
- A single-attempt current-vs-clean-creator I/O probe on seven identical specs.
- Source audit of current controls and historical execution/planning machinery.

No production creator/judge prompt was replaced, dataset call-count/shape controls were not relaxed, no
solver was implemented, and no training, bulk run, checkpoint promotion or frozen
consumer change occurred. The runtime code addition is opt-in per-invocation low reasoning in BudgetedClient,
with an explicit8192-token ceiling for that opt-in only. Default requests remain
reasoning-off with the original4096 ceiling; actual spend is reserved as before.

## Why the current creator I/O is difficult

The creator simultaneously chooses the task, values, tool plan and natural
request while satisfying a wire format plus count/type constraints. It receives
both public ORIGINAL parameter schemas and a different slot-based OUTPUT schema.
The trained model later receives request/context/tools, not the creator's intent,
technical coverage controls or cue. This purpose deserves clearer treatment.

### Competing meanings

| Term | Meanings that must not be conflated |
| --- | --- |
| call_count=4 | Four tool invocations; NOT four records, four prose clauses or four different APIs. |
| object | Original parameter object, argument container, or optional wire slot—all are JSON objects, only the first evidences this shape. |
| unfiltered / all | No supplied parameters versus all matching a selected machine/status/date; the latter is not empty canonical arguments. |
| {} | Omitted optional slot, supplied original empty object (wrapped in value), or empty canonical argument map. |
| no_call | Factory request to create an unsupported example, not inability to create an example. |
| cannot_create | Creator declines the constraints, not an unsupported user request. |
| intent | Candidate's information need, or a decline reason. Declines do NOT reach the critic, so this is an interface overload, not demonstrated judge contamination. |
| only / fields | Exact requested API projection versus what to show in the eventual answer. A valid retrieval plan may fetch extra metadata; canonical-label preferences must not be mistaken for universal semantic necessity. |
| empty context | No facts supplied, NOT proof the database is empty or prohibition on new fictional literals. |
| cap / limit | Exact plan count, upper planning bound, API row quantity, completion-token budget and monetary spend cap are different controls. |

The final production creator prompt already explicitly states exact call count and
post-decoding shape semantics. Adding another sentence saying exact is not a new
fix. The 30-item pilot used earlier wire wording; the current-vs-clean probe used
the current post-clarification prompt.

The same wire symbol is reused at multiple levels:

```text
wire filter: {}                 → filter omitted
wire filter: {value: {}}        → supplied original filter={}, an object value
all optional wire slots omitted → canonical arguments={}
```

The second can satisfy object coverage while still being semantically unfiltered.
Thus structural coverage is not the same as meaningful task diversity.

### Observed confusion, not just a hypothesis

In the clean arm, a spec requiring FOUR tool calls produced:

> Next 4 departures from STP-201.

It emitted one listDepartures call with limit4 and an unstated after timestamp.
The clean brief explicitly said exact number of tool calls, not a distinct-tool
count. Nevertheless, the model used the number as row quantity. It also invented
a reference instant and relied on unpromised next/earliest ordering.

The clean 0055 and 0060 examples were otherwise readable query batches but still
failed the zero-supplied-values requirement. Current 0065 omitted the required
original object value. These are failed technical profiles, not automatically
bad human requests.

This supports moving mechanical representation/planning work out of the creator,
not claiming one extra admonition will guarantee compliance.

## Judge reasoning comparison

Requested setting:

```json
{"reasoning":{"effort":"low","exclude":true}}
```

Reasoning text was not requested or inspected. Actual usage reported nonzero
reasoning tokens, confirming more than merely a changed local label.

| Initial comparison, max_tokens=3072 | Off | Low |
| --- | ---: | ---: |
| Cases attempted | 14 | 14 |
| Usable schema-valid assessments | 14 | 8 |
| Truncated/unusable assessments | 0 | 6 |

Low used 29,733 reported reasoning tokens across the 14 cases. In four of the
first five length failures, all3072 tokens were reasoning and visible content
was empty; another had partial visible JSON. The sixth was the retained0014
case after continuation.

The explicit low effort is not a separate hard token budget. Reasoning and visible
JSON share max_tokens. The six length failures were then tested at the existing
4096-token client ceiling, with no prompt/model/input change. Four produced usable
reviews; two again spent all4096 tokens reasoning and returned no visible answer.
These are token-exhaustion failures, not evidence of semantic refusal.

After the user allowed further bounded experiments, the remaining two were each
tried once at8192 tokens. Both completed:0012 used5037 total completion tokens
(4566 reasoning), and0026 used2134 (1776 reasoning). They correctly flagged the
missing date and missing four actions. This adds two invocations, not a fresh
uniform8192-token run over all14. The usable low reviews were obtained across
14 initial +6 at4096 +2 at8192 token-limit invocations; do not report this as
14/14 first-attempt reliability. The lower consumption on the latter0026 draw
also illustrates routing/generation variability rather than deterministic budget needs.

At4096, low identified the missing alert in0021 and extra projection field in0077
under our intended exclusive-projection annotation, and accepted the valid mixed
ID/name lookup. That does not resolve when projection minimality is a label
convention rather than a strict condition on all valid assistant strategies. But0014 was rejected
for the zero-row call's lack of information while its request_fidelity still
approved next12 from an un-ordered capped subset. Overall rejection alone must
not be counted as detecting the intended defect.

Fresh off judgments also varied:0021 was newly accepted despite its missing alert,
whereas0077 was newly rejected. Same requested model/temperature0 does not establish
deterministic results across provider routing. This small probe does not isolate
a stable accuracy gain from reasoning.

### Credit interruption and cost boundaries

The first probe stopped on HTTP402 after20 HTTP attempts:19 result rows plus the
credit failure. The original ledger stayed stopped; it was not reset/refilled.
After the user's top-up instruction, a separately pinned continuation completed
the remaining nine rows under a cap equal to the original $0.15 minus the already
accounted bound. Prior truncated outputs were not rerun in that continuation.

The later 4096/creator experiment used its own explicit $0.30 cap:
- Paired comparison: $0.052978 reported plus $0.010833 pessimistically retained
  for the interrupted402 attempt.
- Separate six-judge/fourteen-creator follow-up: $0.024393 reported.
- Final two8k probes: $0.005766 reported, under a separate explicit$0.10 cap.
- Total: **$0.083137 reported; $0.093970 accounted including retained bound**.
- 51 HTTP attempts including the402, zero local cache hits, no pending reservations.

The 4096/8192 follow-ups are adaptive output-budget probes on unusable outputs,
not unchanged-parameter accuracy comparisons or repeated judging until green.

## Creator input-format experiment

The alternative prompt explains the training objective first, names only active
decoded-value requirements, distinguishes empty context from absent records, and
separates wire syntax from task meaning. It does not supply hand-authored stories
or relax the original catalogue/count/shape checks. Exploration cues were the same.

One attempt per arm on seven matched specs:
- Current production I/O: **3/7 hard-valid**; one profile failure and three empty
  completions (cause unknown with reasoning off).
- Experimental cleaner I/O: **4/7 hard-valid**; three profile failures.
- No semantic quality judge was used to declare these a success. All fourteen
  slots were inspected directly; eleven had readable requests.
- A clean-arm hard-valid request lost instant precision: after June1,2025 became
  exact midnightUTC in calls without that time/zone being stated. The shorter
  experimental date rule did not fully preserve the prior distinction between
  date-only and instant. That draft is not ready for promotion.

Seven pairs, different newly invented tasks and provider routing are insufficient
to establish an overall quality improvement. The experiment shows both the benefit
of clearer roles in some cases and the danger of merely shortening a prompt.

## What a goal-first solver would change

For the current read-only tools, a final physical world state is usually unchanged.
The goal should normally describe **required information/observations or an
explicit requested operation**, not demand that unknown database facts become true.

Illustrative distinction:

```text
Wrong read-only state target: make book X a poetry book.
Information goal: learn whether book X is poetry.
```

A non-production goal example could specify:
- learn borrower742's name;
- obtain every overdue loan open on an absolute date.

The model would not have to spell out slot envelopes or count query calls.
A compiler/planner with actual tool semantics derives a sufficient call plan.

```text
Synthetic world + visible context + modeled capabilities
                         |
                         v
              Model proposes a structured goal
                  (no API call JSON)
                         |
                         v
              Automatic planner / query compiler
              + execution/coverage validation
                         |
                         v
              Classify/check actual plan complexity
                         |
                         v
              Existing fixed-goal writer
                         |
                         v
              Narrow text↔goal fidelity review
              + separate corpus-quality review
```

Money is reserved before every model request as today, not after this graph.

### Reuse actually present

- Historical tool_composition_v2/catalogs.py has build_fixtures and apply
  implementations for eight families /32 APIs. Their32 names overlap the current
  catalogue and their structural parameter schemas match after descriptions/titles
  are removed. They model filters, projections, linked metadata and limited totals.
  An offline smoke (seed1907, one candidate draw per tool using current contracts)
  executed all32 names across the eight families and verified fixtures unchanged.
  Receipt: historical-mechanics.json. This is real local toy execution, not a
  goal planner or execution of external services.
- tool_composition_v2/candidates.py can enumerate executable candidate queries.
- tool_composition_v2/tasks.py samples sets of calls first and verifies exact
  witness-call identity. That is NOT a goal-first solver; reusing its whole sampler
  would reintroduce the call-first approach we wanted to improve. It also limits
  counts to1–4 and samples distinct tool names; those are sampler restrictions,
  not API invariants. Reusing it wholesale would lose legitimate five-call,
  same-API/different-record cases and undo the earlier cardinality repair.
- tool_composition_v1/environments.py provides execute/achieves and checks proper
  subsequences. Those are execution/goal-validation components, not a generic
  planner or proof that no other shorter plan exists.
- natural_rl_v2/goal_contract.py explicitly says it is not a generic planner.
- The standalone catalogue itself has input schemas/descriptions, not effect
  declarations. The other32 tools are not covered by the old v2 executor. A legacy
  extended-domain path returns generic random success for new domains; that is
  not a credible semantic execution model.

Therefore a useful next prototype can reuse the32 real read-tool mechanics, but
needs a declarative information-goal representation and a real plan-synthesis
step. It is not an existing toggle. API mechanics are not hand-written scenario
templates: one faithful tool model can support many generated tasks.

### Important safeguards

1. **No hidden-state cheating.** A planner may inspect private fixtures to validate,
   but cannot choose secret IDs/values the trained model could not derive from its
   request/context. Result-dependent inputs would require chaining, still deferred.
2. **Sufficiency, not coincidental output equality.** A wrong filter may happen to
   return the right rows in one fixture. A plan should cover the requested predicate,
   not exploit unknown fixture cardinalities or answer values.
3. **Writing can still drift.** A solver validates the formal goal, not the later
   English request. A narrower fidelity check remains useful.
4. **Not every legitimate task retrieves novel records.** Explicit validation,
   technical queries and requested zero-row operations need appropriate goal kinds;
   a universal new-information veto would remain overrestrictive.
5. **Solver failure is not automatically no_call.** Distinguish unsupported
   capability, missing visible inputs, search timeout, and exceeding a plan budget.
6. **Do not silently relax complexity.** Derive actual plan length first; if a
   controlled profile needs five calls, select a goal genuinely fitting it or
   put the task in another bucket. Never pad/truncate calls to make the count.

### Which cap changes?

- Current call_count is **exact cardinality**, not an upper cap.
- A planner can have a separate max_calls search budget; profile_target_calls
  remains a dataset-coverage objective checked against the resulting plan.
- API limit arguments remain row-quantity controls, not plan-count controls.
- Completion tokens must accommodate both reasoning and answer when enabled.
- The hard monetary ledger stays in force before every API request.

Changing that planning/coverage contract would be an explicit architecture
revision. It was analyzed here, not silently applied to the existing pipeline.

## Assessment and next direction

The audit supports the user's concern: creator inputs mix task design, planning,
coverage vocabulary and wire compilation. Our experiments do not prove that all
failures are prompting, but neither justify blaming model size first.

A bounded information-goal/planner prototype over the already modeled tools is
more substantive than adding another reminder to the current creator. It should
be evaluated before replacing the full64-tool pipeline, and must preserve useful
multi-call coverage, valid unusual requests and the non-chaining visibility boundary.

## Every creator probe

### semantic-927-0014 / current

Hard outcome: hard_valid. Manual observation: consistent.

> Find routes from Brookfield to Cedar Point, then pull route RT-77 with just its name and stops, route RT-204 in full, and stop STP-58 with only its location.

Calls: `searchRoutes({"destination":"Cedar Point","origin":"Brookfield"})`; `getRoute({"fields":["name","stops"],"routeId":"RT-77"})`; `getRoute({"routeId":"RT-204"})`; `getStop({"fields":["location"],"stopId":"STP-58"})`.

Four useful transit reads match the request, exact call count; no unsupported ranking claim.

### semantic-927-0014 / clean

Hard outcome: invalid_output. Manual observation: semantic_problem_and_profile_failure.

> Next 4 departures from STP-201.

Calls: `listDepartures({"after":"2025-06-01T08:00Z","limit":4,"stopId":"STP-201"})`.

Required4 tool calls became one call with limit4 and text 'Next4 departures'. Also supplies an unmentioned after instant without a reference clock, and next/earliest ordering is not promised. This directly exhibits confusion between call count and row count, despite explicit wording.

### semantic-927-0055 / clean

Hard outcome: invalid_output. Manual observation: profile_failure_only.

> Books: poetry updated after 2024-01-01T00:00Z. Loans open on 2024-03-15, max 10. Borrower 301 name.

Calls: `searchBooks({"filter":{"genre":"poetry"},"updatedAfter":"2024-01-01T00:00Z"})`; `listLoans({"limit":10,"openOn":"2024-03-15"})`; `getBorrower({"borrowerId":301,"fields":["name"]})`.

Readable and faithful library triple, but no decoded empty-argument call; all-loans-for-a-date is not zero supplied values.

### semantic-927-0055 / current

Hard outcome: invalid_output. Manual observation: unreadable.

No readable user request.

Calls: unavailable.

Empty completion with reasoning disabled; cause unknown, not a proven refusal.

### semantic-927-0060 / current

Hard outcome: hard_valid. Manual observation: usable_technical.

> Two things for the case review checklist: first, pull the complete hearing schedule with no filters at all — every case and every date. Second, get all attendance rows marked "present", again without narrowing by session, marked-after time, or row count. Please don't trim either list.

Calls: `listHearings({})`; `listAttendance({"status":"present"})`.

Hearing overview and present attendance are individually supported; 'case review checklist' is weak connective tissue, not proof of a shared relationship.

### semantic-927-0060 / clean

Hard outcome: invalid_output. Manual observation: profile_failure_only.

> Please check two things for me today: first, list all completed production runs dated 2026-09-17; second, list attendance rows with status present, but only return up to 25 rows.

Calls: `listProduction({"date":"2026-09-17","status":"completed"})`; `listAttendance({"limit":25,"status":"present"})`.

Production and attendance reads match the message, but both have supplied values so zero-argument control is missed. Today concerns doing the task, not the explicitly absolute production-date filter.

### semantic-927-0065 / clean

Hard outcome: hard_valid. Manual observation: usable_technical.

> Pull borrower 4127's name; water samples collected 2024-03-18; up to 12 poetry books by Iris Falkner from 2019; and all orders.

Calls: `getBorrower({"borrowerId":4127,"fields":["name"]})`; `listSamples({"collectedOn":"2024-03-18","sampleType":"water"})`; `searchBooks({"filter":{"author":"Iris Falkner","genre":"poetry","year":2019},"limit":12})`; `listOrders({})`.

All4 asks match calls; object/empty-argument controls met, but still a familiar library-and-unrelated-read batch rather than demonstrated new reasoning diversity.

### semantic-927-0065 / current

Hard outcome: invalid_output. Manual observation: profile_failure_only.

> Grab all rows of each: samples of type water, loans, orders, and library books — no filters on the last three.

Calls: `listSamples({"sampleType":"water"})`; `listLoans({})`; `listOrders({})`; `searchBooks({})`.

Faithful water-sample plus all-loans/orders/books views; object-valued original parameter is absent. A wire slot/container is not such a value.

### semantic-927-0076 / current

Hard outcome: invalid_output. Manual observation: unreadable.

No readable user request.

Calls: unavailable.

Empty completion with reasoning disabled; cause unknown.

### semantic-927-0076 / clean

Hard outcome: hard_valid. Manual observation: semantic_ambiguity.

> I’m reviewing some account issues from this summer. Can you pull up cancelled orders placed after June 1, 2025, up to 20 of them? Also check order ORD-1842, the customer CUST-733, and build BLD-4027. And while you’re at it, search products with no name or category filter so I can see the whole catalog.

Calls: `listOrders({"after":"2025-06-01T00:00Z","limit":20,"status":"cancelled"})`; `getOrder({"fields":["orderId","total","status"],"orderId":"ORD-1842"})`; `getCustomer({"customerId":"CUST-733","fields":["customerId","name","tier"]})`; `getBuild({"buildId":"BLD-4027"})`; `searchProducts({})`.

Call-count/shape valid, but user says after June1,2025 while the call chooses exact midnight UTC with no visible zone/time binding. The shortened experimental date rule did not adequately preserve date-only versus instant precision; do not promote this draft.

### semantic-927-0090 / clean

Hard outcome: hard_valid. Manual observation: consistent.

> Check price and name for SKU-8742, get price for SKU-2057, look up Harbor Point Market, and for 2024-06-14 show north-region sales plus the total across all regions.

Calls: `getProduct({"fields":["name","price"],"sku":"SKU-8742"})`; `getProduct({"fields":["sku","price"],"sku":"SKU-2057"})`; `getStore({"storeName":"Harbor Point Market"})`; `getDailySales({"date":"2024-06-14","region":"north"})`; `getDailySales({"date":"2024-06-14"})`.

Five coherent product/store/sales reads, including two same-date sales scopes. Extra SKU on nonexclusive price lookup is an identification choice, not automatically wrong.

### semantic-927-0090 / current

Hard outcome: invalid_output. Manual observation: unreadable.

No readable user request.

Calls: unavailable.

Empty completion with reasoning disabled; cause unknown.

### semantic-927-0099 / current

Hard outcome: hard_valid. Manual observation: consistent.

> Can you grab Sam's phone number and email for me? I need to pass them along to the vendor this afternoon.

Calls: .

Unavailable directory/contact-data access is a valid no-call request, not merely missing detail.

### semantic-927-0099 / clean

Hard outcome: hard_valid. Manual observation: consistent.

> set up a weekly report for critical alerts and send it to the on-call channel every Monday at 9am

Calls: .

Unavailable report scheduling/chat broadcast is a valid no-call request. No dated canonical call needs binding for this unsupported action.

## Local evidence and reproducibility

- runs/judge-low-reasoning-v1/: inputs, raw off/low wire+responses, stopped first
  ledger, separately authorized continuation,28 results and comparison.json.
- runs/judge-low-reasoning-8k-v1/: two final larger-budget probes, exact wire,
  usage, assessments and capped receipt.
- runs/creator-io-reasoning-followup-v1/: experimental creator-system.md,
  run_followup.py,20 fresh request records, six4096-token judge outcomes,
  fourteen creator outputs, manual assessments, historical-mechanics.json and receipt.
- Both retain manifests and the exact prompts. Neither changes saved targets,
  training mixtures, frozen scorers, checkpoints or production prompt defaults.
- OpenRouter reasoning documentation:
  https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
- Live model-capability metadata checked before the experiment:
  https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash/endpoints

No automated tests were created. Existing Ruff/strict-mypy checks passed after the
small client opt-in change; real requests verified both default-off and low bodies.
