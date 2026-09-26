# Watt P1 Core Readiness — technical qualification

Date: 2026-09-26. Branch: `feature/production-environment-foundation`.
This is a repository and automated/runtime qualification record. It is **not**
Human Acceptance of the new production experience.

## A. Reproducible baseline

- P0 starting revision and pushed baseline:
  `9bc4b65a8d07f14c6031d3bd7a098bc010a307ec`.
- P1 implementation revision:
  `5625ede3f4af5fb4173ede3c9bcb35382ac7a37f`; implementation tree:
  `f71e0bb60166695cf1bd6707051a5e8d55c96761`. The closure evidence is
  the subsequent documentation commit containing this file. Migration head:
  `20260926_57` (forward migrations 55–57).
- Full backend regression: **PASS**, 1,427 passed, three explicit skips, zero
  failures, four deprecation warnings in 56m22s. Full frontend regression:
  **PASS**, 76 passed, zero failed (`node --test tests/js/*.cjs`). P0,
  Multi-PWU, Self-Refine, Search, WIC, Native Executor and governance tests
  are included in the backend run. Skips are not treated as passes.
- The first full run found an old Steering test that shared one three-second
  deadline across failure observation and retry observation; after giving
  each bounded phase its own deadline, that exact test passed in the next
  full run. The next complete run found an old UI static assertion that
  mistook a Git URL input placeholder for a remote script dependency; the
  assertion now checks asset-bearing script/link tags. Both corrections
  passed focused validation and the final zero-failure full run.
- `alembic check`: **PASS** on PostgreSQL upgraded through 57; the P0-to-P1
  upgrade test preserves an existing unbound Work. No applied migration was
  rewritten. The previous drift was SQLAlchemy metadata names for already
  deployed legacy constraints, now aligned with the deployed schema.
- An isolated PostgreSQL database was migrated from empty through 57, then a
  real authenticated Uvicorn HTTP smoke observed sign-in 200, Product creation
  201, Product-bound Work creation 201, Work/Product history and operations 200,
  connector/summary APIs 200, P1 JavaScript 200 and `/app` 200. The temporary
  server and database were removed after the check. This verifies the served
  entry path; it is not Human product acceptance.

## B. Product / Software Asset

`software_products` owns durable identity, owner, name and lifecycle;
`software_product_assets` links admitted repository Engineering Resources and
other relevant asset references. A Work has a nullable `product_id`, so old
Works remain unbound until a Human binds them. Product and Work retain separate
identities. The Product read model lists its Works and governed history; its
current repository revision advances from an authorized Runtime Commit, not
from a new Work's mere request. The Product navigator exposes exact repository
ref/revision and other asset references. P1-Q1 qualifies three distinct Finance
Management Works with one Product identity and persistent source continuity.

## C. Multi-PWU production economics

`ProductionMeasurementService.graph_economics` reads each PWU and Attempt once,
attributes provider/model, observed tokens, resource units, queue wait,
execution and outcome, then projects the Work graph and Product aggregate.
P1-Q2 projects persisted facts for a parallel A/B fan-in J graph, including
retry/recovery; the test checks that accumulated execution differs from parallel wall time and the
critical path, and that Candidate lineage contains all satisfied units.
Unreported provider spend is explicitly `UNREPORTED`/`PARTIAL`, never zero.
This is observed cost/resource accounting, not price inference or billing.

## D. Connector and credential operations

The existing Connector catalog gains owner-controlled enable/disable,
deprecation and evidence-backed health observations with audit history;
resolution excludes disabled or unhealthy entries. Operator inventory
distinguishes capability, credential and authority. GitHub READ and WRITE
grants expose secret references and verification/expiry/rotation/revocation
metadata without exposing tokens; stale or revoked credentials fail closed.
P1-Q3 qualifies disable, health failure/recovery, grant invalidation, rotation
and preserved audit history. Connector invocation counts and last execution
success are `NOT_INSTRUMENTED`; health observations are not misreported as use.
Observed failure count is explicitly scoped to health observations.
The existing operator panel exposes the Connector and grant details and loads
their audit history on demand.

## E. Brownfield journey

Supported intake is a local Git repository or public HTTPS Git repository;
unsupported protocols fail explicitly. Intake preserves exact ref/revision,
relevant context and admitted Engineering Resource. Product-bound Work
refinement selects its Product repository, requiring an explicit resource when
multiple repositories are attached. P1-Q4 qualifies real Git intake, Product
binding and Work source continuity. A separate real native-container Brownfield
test qualifies Work → production → Candidate/Preview/Verification → governed
delivery boundary and Product history. External GitHub push remains unobserved
without an approved write credential and Human-authorized Candidate.

## F. Reference-aware retention

Native workspace policy classifies active, referenced, review-retained,
archived, cleanup-eligible and released states. Active attempts, recovery,
Human review, pins and direct Evidence references block physical cleanup.
An eligible workspace is archived with a verified bundle before hot material
is removed; persisted action stages and idempotency support restart. The
retirement path preserves the last recovery bundle. P1-Q5 exercises pin and
Evidence protection, expiry, an interruption after verified archive, restart
through a new service instance, restore and repeated cleanup. Candidate
Preview runtime cleanup protects pending review and retains immutable evidence.

## G. Operator diagnosis

`ControlRoomService.diagnosis` correlates Product/Work, PWU, queue, worker
registration and lease, Connector gap, Preview probe, Self-Refine, Verification,
Candidate, Evidence references and graph economics into one root-cause
projection. P1-Q6 checks a capability-blocked Work and an unhealthy live
Candidate Preview probe. The operator summary includes worker/queue/lease
health, recent Work states, failed/escalated refinements and observed/unknown
provider spend. This is a bounded Watt-native control view, not enterprise
monitoring or a claim that every external provider is instrumented.

## H. Versioned evaluation

The `watt-p1-v1` corpus records domain, capability, origin, risk, invariant,
runtime requirement, estimated cost, baseline version and failure metadata.
Focused, milestone and representative release selection use the same governed
case model. `evaluation_runs` persists revision-bound reports and shared-case
qualified-baseline comparisons without a universal quality score. P1-Q7
qualifies persistence, trend/delta and four-domain result handling. Actual
representative [P0 baseline](watt-p1-evaluation-p0-baseline-20260926.json),
[P1 implementation](watt-p1-evaluation-current-20260926.json) and
[persisted trend](watt-p1-evaluation-trend-20260926.json) evidence use the
same four case IDs across Interaction, Production, Resilience and Assurance.
Both revisions passed **4/4**, with four first-pass successes and zero
failures/escalations. The shared-case delta is zero for outcomes; local test
timing increased by 4.257 seconds mean and 14.249 seconds P95. This timing
shift is an observation, not an inferred product-quality regression.
Refinement-attempt, token/compute and Work-cost metrics are unreported for
these four evaluation cases; there is no real-container case in this subset.
The reports are stored in `evaluation_runs` with distinct P0 and P1 revision
and baseline lineage. Automated evaluation is separate from Human Acceptance
and does not claim the whole release corpus was run as a single evaluation.

## I. Current-state and schema hygiene

Active architecture, integration, measurement, evaluation and production
environment docs were reconciled with bounded P1 runtime behavior. The debt
census retains historical P0 findings and adds a dated P1 reconciliation with
`CLOSED`/`PARTIALLY_CLOSED` and explicit bounded scope. The stale “Multi-PWU
deferred” Work message was corrected. Legacy constraint-name metadata now matches deployed PostgreSQL;
the forward upgrade from P0 revision 54 through 57 and `alembic check` pass.

The permanent P1 qualification set is repository-backed, not an ad hoc
checklist: Q1 and Q8 in `test_mvp_api.py` plus source-commit continuity in
`test_dcp2_production_measurement.py`; Q2 in that measurement module; Q3 in
`test_github_governed_delivery.py`; Q4 in
`test_p1_brownfield_product.py` and the real-container Brownfield flow; Q5 in
`test_native_executor_runtime.py` and `test_candidate_full_preview.py`; Q6 in
`test_mvp_api.py`; Q7 in `test_release_evaluation_gate.py`; and Q9 in
`test_p1_schema_hygiene.py`. These focused scenarios passed before the final
full regression. The Q5 test deliberately interrupts after durable bundle
verification and resumes through a fresh service instance.

## J. Human and external gates

- `HUMAN_ACCEPTANCE = PENDING` for this P1 batch. Prior WIC-only sampled Human
  acceptance must not be generalized to end-to-end production.
- Live GitHub push/PR needs an approved scoped WRITE credential, an accepted
  exact Candidate and separate Delivery Authorization.
- Independent-host/host-loss recovery needs off-host infrastructure. Guardian
  owner currently exposes intake but no owner decision gate API, so that gate
  remains externally blocked. Web search live qualification needs its key.

## K. Bounded future scope

Broader provider credential integrations, organization promotion, complete
cross-provider retention graphs, commercial pricing/billing, enterprise
alerting and long-horizon Human dogfood remain outside this P1 batch. No P2
scope is claimed closed by an automated test.

## Final technical decision

```text
PRODUCT_IS_FIRST_CLASS_LONG_LIVED_ASSET = PASS
WORK_CHANGES_PRODUCT_WITHOUT_BECOMING_PRODUCT = PASS
PRODUCT_ENGINEERING_ASSETS_ARE_TRACEABLE = PASS
MULTI_PWU_MEASUREMENT_IS_GRAPH_AWARE = PASS
WORK_ECONOMICS_DO_NOT_DOUBLE_COUNT_PARALLEL_PWUS = PASS
UNKNOWN_PROVIDER_COST_IS_NOT_REPORTED_AS_ZERO = PASS
CONNECTORS_ARE_HUMAN_MANAGEABLE = PASS
CREDENTIAL_LIFECYCLE_IS_GOVERNED = PASS
CONNECTOR_AUTHORITY_DOES_NOT_AUTO_EXPAND = PASS
BROWNFIELD_IMPORT_TO_PRODUCTION_PATH = PASS
BROWNFIELD_EXPORT_OR_DELIVERY_BOUNDARY = PASS (governed boundary; live push blocked)
ENVIRONMENT_RETENTION_IS_REFERENCE_AWARE = PASS
CLEANUP_DOES_NOT_DESTROY_REQUIRED_EVIDENCE = PASS
OPERATOR_CAN_DIAGNOSE_WORK_BLOCKER = PASS
PRODUCTION_COST_AND_HEALTH_ARE_VISIBLE = PASS (observed/unknown separated)
EVALUATION_CORPUS_IS_VERSIONED = PASS
FOCUSED_EVALUATION_WORKS = PASS
MILESTONE_EVALUATION_WORKS = PASS
RELEASE_EVALUATION_WORKS = PASS (representative four-domain comparison)
CURRENT_VERSION_CAN_BE_COMPARED_TO_QUALIFIED_BASELINE = PASS
PRODUCTION_HISTORY_IS_INSPECTABLE_WITHOUT_RAW_COT = PASS
ACTIVE_DOCS_MATCH_CURRENT_RUNTIME_REALITY = PASS
MIGRATION_HISTORY_REMAINS_TRUTHFUL = PASS
ALEMBIC_CHECK = PASS
P0_REGRESSION = PASS (covered by full backend regression)
MULTI_PWU_REGRESSION = PASS
SELF_REFINE_REGRESSION = PASS
SEARCH_REGRESSION = PASS (contract/failure paths; live Web Search key unavailable)
FULL_BACKEND_REGRESSION = PASS (1427 passed; 3 skipped)
FULL_FRONTEND_REGRESSION = PASS (76 passed)
P1_CODE_COMPLETABLE_BATCH = PASS (bounded external gates listed above)
FINAL_WORKING_TREE_IS_CLEAN_AND_REPRODUCIBLE = PASS (verified after push)
HUMAN_ACCEPTANCE = PENDING
```
