# Watt Self-Analysis Trace — implementation and qualification

## Delivery status

- Independent branch: `codex/watt-trace-self-analysis`.
- Stable starting point: `5de657f3cb65780adf50f6557b54171a6c3cfae5`.
- Implementation commit: `f9a0a8728ff57ef5737ac79586cd326b01e04449`.
- Live-model-qualified source: `f5383bc0a865c37d45dbd49c6c5dd0c9225b87c5`.
- Final source: `41196f70060be38027d7a29bcfdef937ee9ec471`.
- Code/mechanical regression: PASS, 115 Python/PostgreSQL tests and 29 Admin JS tests.
- Real historical investigation: COMPLETED, CITATIONS_AND_STRUCTURE_PASS.
- Independent semantic review: **PARTIAL; not full self-analysis qualification**.
- Human review/acceptance: PENDING. ECS deployment: NOT_DEPLOYED.
- Canonical checkout remains `ee5bd86`; its preexisting `.c3-holdout-reviewer/`
  remains untouched. C3 continues in its separate worktree. No qualification or
  production service was stopped or replaced.

The final source change recognizes exact index snippets as actually observed
evidence and exposes the class-to-handling mapping in the public schema. It does
not relax exact quotation, repository provenance, ownership or permission gates.
The saved real Native decisions were replayed against final source through the
same Native Kernel and real read-only evidence tools: ten recorded decisions,
zero new model calls, identical verified report. This is mechanical replay,
not another live-model qualification.

See [capability inventory, boundary and risks](work-trace-self-analysis-v1.md).
The implementation uses existing ContextOrchestrator, INVESTIGATION Task Contract,
NativeContextAssembler, configured Worker inference adapter, NativeExecutorKernel,
NativeToolRegistry, GitExactReality and ContentAddressedStorage. No new chat-model
client, production Work, database schema or second reasoning engine was added.
No registered ECF READY or production IRK admission is claimed.

## Real evidence basis

Work `3ee622b5-b816-5679-afdc-e5de51cd2702`: “在既有演示官网上新增服务介绍页与公司新闻页”.
This was a real-model P0/P1 qualification/dogfood Work, not an ordinary customer Work.
The full diagnostic export captured at `2026-10-11T01:59:43.088902+00:00` is
NON_ATOMIC_ACROSS_OWNERS. This check used frozen evidence and exact Git objects;
it did not create a live ECS production attempt or mutate original Owners.

| Evidence identity | Exact value |
| --- | --- |
| Full diagnostic ZIP SHA256 | `3df14f6430f47bd1a85d909d3a3e5c51e06fcf84d738e58eda90b0d4530c275c` |
| trace.json SHA256 | `a909a2d9b7541caf23597dee1a82fb4ffa09ab2d64ed0dc9987517069f97f2c9` |
| Historical Git pack SHA256 | `343bad5f715ee8a0412e2e5dd8238b3ebe6e54cedbde182effbef2d1aed76a69` |
| Source baseline | `d4ad65db95fa1bb3ad7ec951ea844fd4939c2a3d` |
| Produced Candidate revision | `b4280990d55ac9da36eaa0dd9644006df7e8762e` |
| Produced Candidate tree | `330eb480e850ba9e0a57506db084d9a94ac59562` |
| Comparison runtime source | `5de657f3cb65780adf50f6557b54171a6c3cfae5` |
| Historical Worker implementation revision | UNKNOWN |

Artifact directory: `C:/Users/yuchunbo/Downloads/Watt-Self-Analysis-20261011`.
`historical-work-report.json` is the unaltered verified model report.
`historical-work-analysis.json` includes resolved catalog, normalized model
decisions, tool receipts, checkpoints, drafts and bounded refinement feedback.
`qualification-source-files.json` fixes the actual mounted live-test source hashes.
`final-source-replay.json` fixes final adapter hashes and replay outcome.
The original diagnostic ZIP is included in the delivery bundle; no credentials
or ignored environment file are included.

## Live investigation and failures retained

The successful live request was `bdb7893a-6140-4acf-9ad0-cc69d61bafc3`, using the
existing configured DeepSeek Native adapter with `deepseek-flash` and exact source
repositories. It ran from `04:42:58.713256Z` to `04:46:30.457622Z` (211.74 seconds),
with ten inference submissions and 35 tools. Two report verification failures
were corrected in the same contract before RESULT_READY named digest
`0c924828806bca55d824214c0e8a48f2bcb253d19d5bc212d3a122d08e0afff9`.
This proves the actual model/tool/refinement/report path runs; it does not certify
all report semantics.

Earlier failures remain part of the evidence, not discarded retries:

| Request | Observation | Follow-up |
| --- | --- | --- |
| `cf89c8b4-9547-4a90-8ac2-d8f57047add1` | Before inference, Native SourceMember rejected root `.` scope | Expanded admitted top-level source paths; retained failure |
| `669d736a-aaef-4c26-b9cd-3c641dd85fc5` | Model emitted extra `recommendation_note`; schema rejected; timeout | Explicit exact schema instructions and retained drafts |
| `75e7d061-69ec-41cc-8f58-283c36406ca0` | Model shortened finding references; rejected; timeout | Exact reference feedback and bounded same-draft edits |
| `55977b5a-a33d-4026-9ebb-fc951397e015` | Placeholder report, sequential quote failures, unreadable draft UUID; timeout | Readable proposal-only drafts, batched quote feedback, original incident coverage |
| `bdb7893a-6140-4acf-9ad0-cc69d61bafc3` | Handling mismatch and unobserved references; same-contract correction succeeded | Schema now states mapping; actual index snippets are observable |

The first three live failures are saved as `attempt-1/2/3-analysis.json`.
The pre-inference failure is retained in the scoped CAS request records.
No expected answers were inserted into the model report to manufacture a PASS.

## Independent semantic assessment

The following assessment was performed separately against original Owner rows
and repository implementation after generation. It is not the model's report
and does not imply Human acceptance.

| Validation question | Assessment | Evidence / remaining defect |
| --- | --- | --- |
| What happened? | Main reconstruction PASS | Two new pages, three PWUs, recovered incidents, sealed Candidate and Human ACCEPT; reads exact produced diff |
| Where did execution deviate? | PASS for three recorded incidents | SCOPE_INFLATION, rejected `ls`, rejected JOIN decision; correctly distinguishes recovered failures from current blockers |
| Model variance or system limitation? | PARTIAL | Suggests variance while preserving hypotheses; invalid response bytes and rejected scope candidate remain missing, so model/provider/parser or candidate/validator blame cannot be settled |
| What should be fixed? | PARTIAL | Bounded rejected-candidate/raw-decision evidence and safe alternative-tool guidance are relevant; preview and mapping recommendations overstate missing evidence |
| What supports the conclusion? | Citation integrity PASS; causal sufficiency PARTIAL | Quotes/source identities match returned evidence; omitted contradictory Guardian and session evidence invalidate some deductions |

### OBSERVED FACT: actual historical incidents

1. Self-Refine `4d2b9a75-4f45-4e3f-87aa-335b18ad5216` records
   CANDIDATE_INCONSISTENT/SCOPE_INFLATION and LOCAL_OBLIGATION_RECOVERED.
   Exact initial rejected candidate contents are absent: candidate fault versus
   an overstrict validator remains UNKNOWN.
2. Failed receipt `47c852a9…` states `process executable is not allowlisted: ls`,
   `ValueError`, `effect_observed=false`. Matching comparison code in
   `src/spg/executor/tools.py` rejects nonallowlisted executable before launch.
   Safe rejection is observed; motivation for choosing `ls` remains a hypothesis.
3. JOIN step `b4d11a60-af4d-4c54-a7dd-9067c69f7629` records
   INVALID_MODEL_RESPONSE / NATIVE_DECISION_SCHEMA_REJECTED / json_invalid.
   Self-Refine `9325939c-5ac7-461f-925a-0b4cbae03bad` recovered it.
   The raw invalid response is absent: truncation/escaping/parser blame is UNKNOWN.

### VERIFIED FINDING: model report errors and limits

**Preview evidence conflation (finding-4).**
The report uses `served_delivery.client_received=UNAVAILABLE` to discuss preview
HTTP status/digest gaps. `src/spg/evaluation/production_trace.py:550` obtains
`served_delivery` from DeliveryObservationService. Its DeliveryAction enum in
`src/spg/application/delivery_observation.py:24` describes downloads; this is a
different owner/evidence surface from Guardian's preview.

Original `/lifecycle/guardian/0` has result
`d71f2935-02ea-4289-a2d4-d363a1783f1e`, exact Candidate revision `b4280990…`,
and actual GET observations for **both** `/news.html` and `/services.html`,
HTTP 200, observed timestamps, response SHA256 and candidate-preview identity.
Thus the assertion that this export lacks independently checkable preview status
or response digests is false. Human browser rendering/client persistence is still
not proved by those GET receipts. They must be kept distinct from server preview
observations and download audits. Any earlier summary saying only index.html had
an HTTP receipt is corrected by these full Guardian records.

**Missed available lineage (finding-5).**
The report says PWU-to-session mapping is missing. Original
`/lifecycle/advanced/owners/execution_sessions` includes `pwu_id`, and
`execution_attempts` includes `work_unit_id`. For example session
`296ef921-e388-54e4-a268-09af4ecbae0d` and attempt
`dea9d9c9-31c9-4feb-91bc-a5995c9edd2f` both identify PWU
`b394e64d-d7d3-5fab-abe3-3c5744497533`.
Not reading the available rows does not make their information unavailable.

**Causal attribution and regression suggestions.**
findings 1 and 3 contain stronger prose than their uncertainty permits. Treat
classification as provisional; a current source match alone cannot prove the
historical parser/runtime caused or did not cause the defect. The recommendation
that changed_paths must *equal* the allowed set is a Work-specific completion
suggestion, not a new generic Watt verifier rule. Do not apply it as platform policy.

**Timeline and coverage.**
Eight stage entries are a stage reconstruction, not a timestamp-sorted event log.
Some timestamps aggregate several incidents and are not validated against their
quoted record. The report focuses on PATH_SCOPE and does not fully inventory the
six original PATH_SCOPE/GIT_DIFF_CHECK records. No claim of a browser content
acceptance test should be derived from those Git checks.

## What this teaches about the current substrate

The existing Native substrate can investigate exact Work sources, consume Owner
evidence, generate structured recommendations and correct a rejected report within
its original contract. Model failures and attempted repairs are now observable.

The current verifier cannot prove absence claims, require contradiction searches,
verify time attribution or certify causal implications. Selective evidence reading
still leads to plausible but incorrect “missing log” conclusions. These are
documented qualification gaps, rather than hidden by a structural PASS.

Minimum next review direction: require a general evidence-coverage/contradiction
check before absence claims, preserving source types and UNKNOWN; assess additional
real failed Work and governance incidents before broader qualification. This is a
review recommendation, not automatic Evolution Work or an expanded C3/C4 task.

## Deployment and remaining risks

Deployment has not been performed. Before enabling this on ECS, configure the
existing Native provider in the API process, fix readable exact runtime Git objects
and managed Work repository object access, persist the analysis CAS, and confirm
the existing gateway permits the bounded request duration. The current API POST
executes a bounded investigation inline; persisted progress/history survives a
lost browser response, but request disconnect is not a durable job guarantee.
Outer cancellation cannot prove the existing adapter's provider HTTP thread ended.
Crash locks require analysis-only operator reconciliation; no automatic production
resume, source fetch, code mutation, promotion or deployment is enabled.

A useful report should remain ADVISORY_ONLY and HUMAN_REVIEW_REQUIRED. Neither
this feature nor its report may qualify C3, authorize a Candidate or update a
production Work. Broader semantic qualification and deployment are separate gates.
