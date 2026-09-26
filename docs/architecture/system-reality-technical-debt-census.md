# Watt Systemic Reality and Technical Debt Census

Original audit date: 2026-09-26. The body below this update records the
**historical pre-P0 inspection** of the working tree of
`feature/production-environment-foundation` at HEAD
`3953f0cb0240559bd2d6b92a216f9becfbb54253`. This is a read-only audit of
implementation, active wiring, tests and recorded Human observations. It is
not a new architecture decision or an authorization to implement the items.

**Baseline caveat.** At inspection, 79 tracked files were modified and 23
files were untracked. The recent Self-Refine, Search and Multi-PWU work is
therefore working-tree Reality, **not** reproducible from HEAD alone. The last
completed working-tree regression collected 1,403 backend tests (1,400 passed,
three environment skips, no failures) and passed 75/75 JavaScript tests. That
supports the tested tree, not a committed release or Human acceptance. See the
[Multi-PWU qualification](../evidence/watt-multi-pwu-production-qualification-20260926.md).
The working-tree Alembic head is `20260926_51`; migrations
[`48`](../../migrations/versions/20260925_48_refinement_semantics.py) through
[`51`](../../migrations/versions/20260926_51_baseline_tree_identity.py) are
among the untracked files. The prior qualification exercised migration/schema
consistency; this audit did not run a new database migration.

## P0 batch reconciliation (2026-09-26)

The historical finding rows and recommendation below remain as the original
audit, rather than being silently rewritten. The **current** status of each
affected P0 ID is maintained here with the qualification limits. See the
[P0 closure evidence](../evidence/watt-p0-full-system-closure-20260926.md)
for exact revision, migration and test results.

| ID | Current status | Current Reality and remaining condition |
| --- | --- | --- |
| TD-BASE-001 | CLOSED | Self-Refine, Search and Multi-PWU were frozen in committed, pushed baseline `364f40fde5a22dbb2738b436f887cd7ad1e76ea5` (tree `f61ae4ba330aaa96b117f886ddbf1be028f27e93`, migration `20260926_51`). The P0 result revision is recorded in closure evidence. |
| TD-IDENT-001 | CLOSED for single-owner profile | HTTP now authenticates the operator, derives `human:owner` server-side, checks persisted membership/resource access and ignores forged caller identity. This is not shared enterprise IAM. Migration `52`; authenticated API and CSRF tests. |
| TD-REPO-002 | BLOCKED_EXTERNAL for live remote proof | GitHub READ/WRITE grant, credential references, exact Human delivery authorization, observed non-force push and optional PR paths are implemented and test-isolated. No approved live read/write token was supplied; Guardian owner decision gate is also absent for the full profile. No remote effect is claimed. Migration `54`. |
| TD-REPO-003 | PARTIALLY_CLOSED | Git history is captured as a checked Git bundle in PostgreSQL, recovered into another worker checkout and exportable; migration `53` and real local Git/PostgreSQL recovery test. Off-host PostgreSQL durability, restore and machine-loss proof require infrastructure activation. |
| TD-CONT-001 | BLOCKED_EXTERNAL for independent-host proof | Durable queue/lease/checkpoint code remains in the original owner paths; independent-host Compose overlay and qualification runbook are supplied. Desktop sleep and host replacement have not been observed on an independent host. |
| TD-PREV-001 | CLOSED for supported Watt topology | Real Docker preview qualified an exact Watt Candidate with frontend, backend and PostgreSQL. A complete-application delivery target routes Human review to this exact preview. Declared Redis support is bounded; unsupported topologies fail explicitly. The final-revision proof and limits are in closure evidence. |
| TD-VERIFY-001 | CLOSED for supported Watt scenario | Preview READY now requires observed served revision/tree, reachable frontend and backend, database health, and a goal write/read round trip; evidence is persisted and required for complete-application acceptance. This does not certify arbitrary feature correctness. |
| TD-ECF-001 | PARTIALLY_CLOSED | Required owner mode wires ECF into the normal Watt Work service, checks owner Reality before each new governed attempt, and consumes revisioned, fresh/superseding repository Reality across sessions. Full Journey A/B convergence with all upstream owners is not yet proven. |
| TD-GUARD-001 | BLOCKED_EXTERNAL | Required owner mode wires attributable Guardian intake. Inspected Guardian owner runtime only exposes `admit`/`get`, not findings, challenge or assurance decision/gate; Watt cannot truthfully substitute its own PASS. |
| TD-SCOPE-001 | CLOSED | Human approved Journey A/B and the bounded frontend/backend/PostgreSQL plus declared-support-service topology in this batch request. Human Acceptance remains pending. |

These statuses distinguish code completion from runtime and Human acceptance.
The prior table's classifications describe the original audit snapshot, not
the status of this batch. P1/P2 findings remain open unless separately proven.
The P0 migration head is applied, but `alembic check` still detects pre-P0
index/check/unique-constraint naming drift on older tables. The sole new
authority-table discrepancy was removed in `9a74c19`; the older drift is a
separate non-blocking schema-maintenance finding, not evidence of a missing P0
table or a reason to rewrite unrelated migrations in this batch.

## Executive answer

**Genuinely proven within a bounded scope.** WIC's sampled entry interaction
has explicit Human acceptance. Governed semantic fact precedence/supersession,
local Git acquisition and branch creation, the native queue/lease/checkpoint
substrate, exact local Candidate/Commit, and bounded connector gap qualification
have implementation and automated/runtime evidence. Multi-PWU serial,
parallel, Join and re-plan paths have real Git/PostgreSQL qualification and full
regression, with Human acceptance pending. These are bounded claims; none
establishes an externally hosted, multi-tenant production service.

**P0 before a truthful full-system integration claim:**

1. Freeze a reproducible version of the currently uncommitted working tree
   (`TD-BASE-001`). This is a baseline/evidence task, not new product code.
2. Establish authenticated Human/worker identity at authority-bearing HTTP
   boundaries (`TD-IDENT-001`); a caller-supplied `authority_identity` is not
   authentication.
3. Qualify the actual full-application preview with a real backend/database
   Candidate and define the supported project topology (`TD-PREV-001`). Static
   or frontend preview is not proof of that path.
4. Close canonical source continuity for repository-optional Work and the
   remote Git delivery path for hosted-repository Work (`TD-REPO-003`,
   `TD-REPO-002`). Local execution Git is not a durable managed repository or
   remote push/PR.
5. Put execution capacity and its durable workspace beyond the Human's local
   desktop failure domain, then qualify sleep/disconnect/restart (`TD-CONT-001`).
6. If “full system” includes ECF and Guardian, connect their owner runtimes to
   the normal production path and prove the handoff, return evidence and gate
   (`TD-ECF-001`, `TD-GUARD-001`). Existing isolated integration tests do not
   make those calls the default runtime.

**P1 before a serious usable release:** production history and runtime
verification visibility, connector management/credential experience, generic
capability coverage, product/software-asset identity, brownfield handoff,
environment retention, multi-PWU measurement, operational diagnosis, and
Human evaluation of the newly qualified production paths. See the P1 rows.

**P2 that can wait:** a full adaptive Pattern/SOP/Context platform, complete
Platform Improvement Work/release governance, commercial billing and broad
scale connectors (CI/CD, SSH, object storage, mini-program upload, etc.) unless
a chosen first-release journey specifically requires one.

**Human decisions before construction:** select the first integration journeys
and supported preview topologies; choose the canonical repository home for
repository-optional Work and remote Git authority model; define actor/tenant
ownership and retention policy. `TD-SCOPE-001` records this dependency.

**External credentials/infrastructure:** `SPG_WEB_SEARCH_API_KEY` is absent,
so live Brave Web Search is unqualified; protected GitHub code search needs
`SPG_GITHUB_READ_TOKEN`. Remote Git write authorization and a durable
non-desktop worker/repository host need product/infrastructure setup as well
as implementation. These are separate from source-code defects.

## Reading the census

`COMPLETE_AND_PROVEN` means **the bounded capability named in that row**, not
the entire architectural layer. Every row has one primary Reality class. `—`
in Priority means no closure work for an already proven bounded capability;
all open findings use P0, P1 or P2. “Blocks” refers to the full integration
journey named in the row, not every possible local unit test. “A” is automated
test evidence, “R” is real provider/container/Git/PostgreSQL qualification,
and “H” is Human acceptance. An absent H is not a failure.

| ID | Capability | Owner | Promised Reality | Current Reality | Evidence | Gap | Classification | Priority | Blocks Integration | Recommended Closure |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TD-BASE-001 | Reproducible baseline | engineering | Exact source and evidence lineage | Current tree has 79 modified + 23 untracked files; HEAD predates recent work. [qualification](../evidence/watt-multi-pwu-production-qualification-20260926.md) (A/R) | A/R | A clean checkout of HEAD cannot reproduce the qualified tree | HIDDEN_RUNTIME_DEBT | P0 | Yes, release/integration baseline | Review and commit a coherent qualified tree, then rerun only checks invalidated by that act and record exact revision |
| CAP-WIC-001 | WIC/Response Contract | Interaction | Intent, mode, high-value clarification, question budget, capability alignment, corrections, response stages | [WIC closure](../evidence/wic-interaction-intelligence-phase-closure.md), [response realization](../../src/spg/application/wic_response.py), [Interaction runtime](../../src/spg/application/interaction.py) (A/R/H sampled) | A/R/H sampled | No gap for the accepted sampled entry scope | COMPLETE_AND_PROVEN | — | No | Preserve sampled acceptance boundary and scenario-driven evolution |
| TD-WIC-002 | Long-horizon Interaction | WIC | Durable coherent multi-turn behavior | Restart and exact-turn retry exist in [Interaction](../../src/spg/application/interaction.py); closure explicitly limits Human evaluation (A) | A | Long-horizon multi-turn stability and post-completion history need real use | EXPLICIT_TECHNICAL_DEBT | P1 | No, bounded integration | Dogfood long conversations and retain an inspectable execution timeline |
| CAP-SEM-001 | Engineering Semantic Truth | Semantic layer | Neutral extraction, contextual binding, canonical facts, Human precedence, correction/supersession | [fact binder](../../src/spg/application/engineering_semantics.py), [typed wire](../../src/spg/providers/semantic_wire.py), [semantic tests](../../tests/test_engineering_semantic_truth.py), [WIC closure](../evidence/wic-interaction-intelligence-phase-closure.md) (A/R) | A/R | No arbitrary provider-field guessing found in the inspected active semantic wire; broader Human production validation is not implied | COMPLETE_AND_PROVEN | — | No | Keep raw provider output outside authority and retain semantic regression |
| CAP-STEER-001 | Steering | WHAT NEXT | Reality-grounded re-entry, revision and ownership distinct from Scheduler/Executor | [Steering driver](../../src/spg/application/steering_driver.py), [semantic steps](../../src/spg/application/semantic_steps.py), [plan tests](../../tests/integration/test_mvp_plan_steering_truth.py) (A/R) | A/R | Human has not deeply evaluated real-production plan usefulness/replanning | IMPLEMENTED_BUT_HUMAN_ACCEPTANCE_PENDING | P1 | No, automation integration | Evaluate representative failure/refinement/re-plan journeys with Human |
| CAP-PLAN-001 | Multi-PWU | Planning and Runtime | Semantic hierarchy, DAG, exact baselines, parallel roots, Join, verified checkpoint, auto-continue/re-plan | [plan graph](../../src/spg/domain/planning.py), [runtime](../../src/spg/application/runtime.py), [qualification Q1–Q14](../evidence/watt-multi-pwu-production-qualification-20260926.md) (A/R) | A/R | Human has not accepted the new production experience | IMPLEMENTED_BUT_HUMAN_ACCEPTANCE_PENDING | P1 | No, bounded runtime integration | Human dogfood serial/parallel/Join visibility and recovery |
| TD-PLAN-002 | Production measurement | DCP-2 | Attributable measurements across production | [candidate creation](../../src/spg/application/governance.py) stores all graph PWUs, but [measurement](../../src/spg/application/measurement.py) rejects `len(satisfied_work_unit_ids) != 1` (code inspection; A covers older one-PWU cases) | Code/docs inspection | Multi-PWU Candidate economics/latency projection is still single-PWU shaped | HIDDEN_RUNTIME_DEBT | P1 | Yes, measurement journey | Make Candidate/Work measurement graph-aware and qualify multi-PWU values; do not alter trusted production lineage |
| CAP-NATIVE-001 | Native Executor and 8+1 | Executor | Self-Orient/Check/Execute/Observe/Refine/Converge/Resume/Evaluate and Human governance | [runtime](../../src/spg/application/executor_runtime.py), [technical closure](../evidence/watt-native-executor-technical-closure.md), [qualification](../evidence/watt-native-executor-qualification-closure-20260912.md) (A/R) | A/R | Final Human product acceptance remains deferred | IMPLEMENTED_BUT_HUMAN_ACCEPTANCE_PENDING | P1 | No, technical integration | Human-run exact Candidate, controls, preview and delivery journey |
| CAP-REFINE-001 | Self-Refine | Interaction, Steering, Executor | Candidate is not truth; routine/recurring/systemic classes, budgets, deterministic gate, low Human noise | [classification](../../src/spg/domain/refinement_contract.py), [Executor loop](../../src/spg/application/executor_runtime.py), [calibration evidence](../evidence/watt-self-refine-calibration-qualification-20260925.md) (A/R) | A/R | Combined Human evaluation pending; Platform Improvement is separate | IMPLEMENTED_BUT_HUMAN_ACCEPTANCE_PENDING | P1 | No, bounded integration | Human-evaluate recovery and escalation, preserve current bounded budgets |
| CAP-SEARCH-001 | Public GitHub retrieval | External Research | Explicit/model-initiated search, refinement, inspect, provenance, budget, truthful failure | [research runtime](../../src/spg/application/external_research.py), [provider](../../src/spg/providers/external_search.py), [live qualification](../evidence/watt-external-search-qualification-20260925.md) (A/R) | A/R | Human product acceptance pending | IMPLEMENTED_BUT_HUMAN_ACCEPTANCE_PENDING | P1 | No, GitHub search path | Human-evaluate result relevance and source presentation |
| TD-SEARCH-002 | Web/protected search | External Research | Real Web Search and protected GitHub code search | Providers and credential gates exist in [manifest](../../src/spg/application/connector_manifest.py); live Web qualification is blocked in [evidence](../evidence/watt-external-search-qualification-20260925.md) (A, R for public GitHub only) | Code/docs inspection | Missing `SPG_WEB_SEARCH_API_KEY`; optional code-search token absent | REQUIRES_EXTERNAL_CREDENTIAL_OR_INFRASTRUCTURE | P1 | Yes, Web/code search scenarios only | Configure read credentials, run live qualification, retain fail-closed behavior |
| CAP-CONN-001 | Core connectors | Capability Reality | Truthful executable inventory; filesystem, shell, Git, dependency/build/test, container, preview/artifact | [manifest](../../src/spg/application/connector_manifest.py), [native tools](../../src/spg/executor/tools.py), [connector tests](../../tests/test_connector_manifest.py) (A/R for bounded native paths) | Code/docs inspection | Catalog entries without a provider are explicitly non-executable | COMPLETE_AND_PROVEN | — | No | Keep catalog/provider/qualification distinct |
| TD-CONN-002 | Extended connectors | Connector owners | HTTP/API, browser, DB/migration, SSH, CI/CD, deployment, object storage, issue, mini-program | [manifest](../../src/spg/application/connector_manifest.py) has no provider for HTTP, browser, secret, SSH, CI, deployment, object storage, issue or upload; DB/migration/quality/mini build are generic-process adapter-ready, not family-specific qualified (code/A) | code/A | Broad catalog is not a broad executable platform | PARTIALLY_IMPLEMENTED | P2 | Conditional on chosen journey | Select journey-required families; promote a required family to P1 only after the Human selects that journey, then qualify provider and authority |
| CAP-GAP-001 | Capability Gap Recovery | ConnectorResolver | Detect gap, bounded generic candidate, native qualification, WORK and USER persistence/reuse | [resolver](../../src/spg/application/connectors.py), [qualification](../../src/spg/application/native_connector_qualification.py), [PostgreSQL tests](../../tests/integration/test_connector_capabilities.py) (A/R) | A/R | Generic process adapter scope, not arbitrary self-created providers or external authority | COMPLETE_AND_PROVEN | — | No | Preserve WORK/USER scope and independent qualification gate |
| TD-CONN-003 | Connector Management | Product | Human/Admin inspection, disable/rotate/credential/scope control | Future requirement in [architecture](watt-ai-native-software-production-architecture.md); only Work gap API and stored overlays exist in [resolver](../../src/spg/application/connectors.py) (code) | code | No management product or credential lifecycle | DOCUMENTED_ONLY | P1 | Yes, reusable connector/credential release | Define minimal authorized management and rotation flow after identity model |
| CAP-PE-001 | Work Production Environment | Watt | Work-bound isolated workspace/container, multi-repo revision, record, recovery | [native environment](../../src/spg/application/native_production_environment.py), [provider](../../src/spg/infrastructure/production_environment.py), [cross-repo qualification](../../tests/integration/test_brownfield_native_production_flow.py) (A/R with two local-image skips in latest full suite) | Code/docs inspection | Default product Human experience not accepted; external owner runtime differs from harness | IMPLEMENTED_BUT_HUMAN_ACCEPTANCE_PENDING | P1 | No, bounded local environment | Repeat real-container qualification with required image and Human dogfood |
| TD-PE-002 | Environment lifecycle/retention | Watt | Reference-aware cleanup and durable recovery | [architecture](watt-production-environment-architecture.md) explicitly defers graph/reachability/collector; [lifecycle](../../src/spg/application/production_environment.py) creates reference edges only (code) | code | Cleanup eligibility/retention policy not implemented | EXPLICIT_TECHNICAL_DEBT | P1 | No, short bounded integration | Choose retention policy and qualify cleanup/restart without deleting referenced evidence |
| TD-PREV-001 | Full Application Preview | Preview runtime | Exact Candidate frontend/backend/database/supporting services, health, isolation, failure evidence | [mode selection](../../src/spg/application/candidate_preview.py) and [Docker provider](../../src/spg/infrastructure/candidate_preview_runtime.py) implement a Watt-specific Python/Postgres topology. [tests](../../tests/test_candidate_full_preview.py) exercise a real frontend endpoint, but full-app cases use simulated provider; no real full-app Docker qualification found (A, limited R) | A, limited R | FULL_APPLICATION_RUNTIME is not yet real-qualified; arbitrary app/supporting-service graph unsupported | PARTIALLY_IMPLEMENTED | P0 | Yes, functional full-app review | Run a real exact-Candidate backend+DB preview through API/UI; state supported topology and fail explicitly outside it |
| CAP-REPO-001 | Repository Acquisition/local Git | Asset+Executor | Public HTTPS/local intake, exact branch/revision/tree, full reachable history, branch create/retry | [intake](../../src/spg/application/assets.py), [branch operation](../../src/spg/application/native_git_operations.py), [reliability tests](../../tests/test_repository_acquisition_reliability.py) (A/R) | A/R | Local qualification does not grant remote write authority | COMPLETE_AND_PROVEN | — | No, local Git path | Retain exact source gate and branch observability |
| TD-REPO-002 | Hosted Git delivery | Git provider | Authenticated read/write grant, push, PR/MR and delivery Reality | [manifest](../../src/spg/application/connector_manifest.py) lists GitHub/GitLab/Gitee push/PR without providers; [Control Room](../../src/spg/application/control_room.py) reports no GitHub App/OAuth (code) | code | No remote write credential integration or governed push/PR runtime | PARTIALLY_IMPLEMENTED | P0 | Yes, hosted-repository end-to-end journey | Decide provider/Access Grant, implement and qualify observed remote effects after identity boundary |
| TD-REPO-003 | Managed Repository | source SOT | Durable canonical Git for users without external host | [managed execution workspace](../../src/spg/application/assets.py) creates local Git substrate; [architecture](repository-asset-and-managed-execution-workspace.md) explicitly excludes managed hosting (code/docs) | Code/docs inspection | Canonical code can remain only in host-local Workspace/volume | DOCUMENTED_ONLY | P0 | Yes, repository-optional durable journey | Choose durable managed Git or authorized export target; prove restart/machine-loss recovery and exact history |
| TD-ASSET-001 | Product/Software Asset | Product owner | Product portfolio and long-lived Software Asset changed by Works | [product schema](../../src/spg/infrastructure/persistence/product_schema.py) has Goal/Work/Asset scope but no Product/Portfolio lifecycle; [Work model](../../src/spg/domain/product.py) is Work-centric (code) | code | Long-lived asset ownership, evolution and portfolio continuity are not first-class | DOCUMENTED_ONLY | P1 | No, single-Work integration | Decide minimal Product identity and Work→Product relation before repeated-Work dogfood |
| TD-IDENT-001 | Identity/tenant/authorization | Governance | Authenticated actor, organization, membership, resource visibility and role authority | [HTTP routes](../../src/spg/api/http.py) accept client-supplied `authority_identity`; [product schema](../../src/spg/infrastructure/persistence/product_schema.py) has no tenant/membership tables; local Compose binds to loopback (code) | code | Human authority is attributed but not authenticated or tenant-scoped | HIDDEN_RUNTIME_DEBT | P0 | Yes, trustworthy Human authorization / shared runtime | Add actor/session authentication and server-derived authority before exposing shared production controls |
| TD-IMPORT-001 | Brownfield onboarding | Asset+Context | Repo, docs/context, credentials and developer handoff | [repository intake](../../src/spg/application/assets.py), [brownfield bridge](../../src/spg/application/brownfield_delivery.py), [local delivery](../../src/spg/application/delivery.py) (A/R bounded) | Code/docs inspection | External credential setup and imported non-repo asset/context lifecycle remain incomplete | PARTIALLY_IMPLEMENTED | P1 | Conditional, richer brownfield journey | Test one supported import→production→export path; narrow unsupported sources explicitly |
| TD-ECF-001 | ECF integration | Engineering Reality | Fresh, revisioned, attributable ECF intake/projection across sessions | [boundary payloads](../../src/spg/application/production_environment_contracts.py) and [cross-repo harness](../../tests/integration/test_brownfield_native_production_flow.py) exist; [default context](../../src/spg/application/conversation.py) is native and [bootstrap](../../src/spg/application/bootstrap.py) does not wire ECF runtime (A/R isolated) | A/R isolated | Normal production does not consume ECF-owned freshness/supersession runtime | PARTIALLY_IMPLEMENTED | P0 | Yes, full ECF integration claim | Add explicit Watt-side runtime gateway/configuration and test repeated-session stale/superseded Reality; do not reimplement ECF |
| TD-GUARD-001 | Guardian integration | Assurance | Evidence handoff, findings/challenge/gate, release assurance | [intake payload](../../src/spg/application/native_production_record.py), [cross-repo harness](../../tests/integration/test_brownfield_native_production_flow.py) exist; [default Verification](../../src/spg/application/bootstrap.py) intentionally runs without Guardian (A/R isolated) | A/R isolated | Intake is not a default Guardian decision/gate or repeated-failure challenge | PARTIALLY_IMPLEMENTED | P0 | Yes, full Guardian integration claim | Wire attributable intake/result/failure gate in selected journey and qualify real owner runtime |
| TD-PLATFORM-001 | Platform Improvement | internal production | Cluster failures → mitigation → improvement Work → governed release | [Self-Refine store](../../src/spg/infrastructure/executor_runtime/postgres_store.py) clusters signatures and projects candidates; no Internal Improvement Work/release path found (code/A) | code/A | Telemetry exists, closed improvement loop does not | PARTIALLY_IMPLEMENTED | P2 | No | Admit separately after core dogfood, using observed clusters |
| TD-CONT-001 | Scheduler/worker continuity | Execution ops | Durable fair queue, independent worker leases/recovery, unattended long-running production | [scheduler/lease recovery](../../src/spg/application/executor_runtime.py), [worker](../../src/spg/executor_worker.py), [local Compose](../../compose.native-executor.yaml) (A/R for lease recovery) | Code/docs inspection | Local worker/volumes still share the desktop host failure domain; a folder permission prompt plus machine sleep/remote-control loss can stop all capacity until that host returns | HIDDEN_RUNTIME_DEBT | P0 | Yes, unattended dogfood | Run worker+durable state on independent host; prove prompt-denial, sleep/disconnect, lease reclaim and exact workspace recovery |
| CAP-GOV-001 | Human governance | Work+Candidate | Attention, explicit final Candidate/Delivery authorization; Human is not next-PWU button | [Work](../../src/spg/application/work.py), [governance](../../src/spg/application/governance.py), [Multi-PWU Q11](../evidence/watt-multi-pwu-production-qualification-20260926.md) (A/R) | A/R | Human experience beyond sampled WIC remains pending; authenticated actor is separate `TD-IDENT-001` | IMPLEMENTED_BUT_HUMAN_ACCEPTANCE_PENDING | P1 | No, local technical path | Human-test attention, exact review and release decisions after identity foundation |
| TD-OPS-001 | Admin/observability | Operations | System/Work/worker/connector health, costs, diagnostic failures | [health and queue APIs](../../src/spg/api/http.py), [Self-Refine metrics](../../src/spg/infrastructure/executor_runtime/postgres_store.py), [Control Room](../../src/spg/web/control-room.js) (A) | A | No unified operator view/alerting across worker, connector, preview and source retention | PARTIALLY_IMPLEMENTED | P1 | No, bounded integration | Add minimal operational diagnosis after independent worker runtime is chosen |
| TD-COST-001 | Production economics | Measurement | Exact token/compute/resource cost with unknown spend preserved | [usage models](../../src/spg/domain/native_execution.py), [resource settlement](../../src/spg/infrastructure/executor_runtime/postgres_store.py), [measurement](../../src/spg/application/measurement.py) (A) | A | Provider cost may be `UNREPORTED`; multi-PWU aggregation is incomplete (`TD-PLAN-002`) | PARTIALLY_IMPLEMENTED | P1 | No, functional path | Make observed/unknown spend explicit per Work graph before economic claims |
| TD-BILL-001 | Commercial billing | Product | Prices, invoices, organization billing | [future capabilities](future-capabilities.md) separates strategy/economics from product billing; no billing runtime found | Code/docs inspection | Legitimate later commercial scope | FUTURE_COMMERCIAL_OR_SCALE_CAPABILITY | P2 | No | Revisit after reliable production economics and tenant identity |
| TD-INTEL-001 | Domain Grounding/SOP/Context | Intelligence owners | Adaptive patterns, activity SOP and context selection | [foundation contracts and defaults](../../src/spg/application/production_intelligence.py), [architecture](watt-ai-native-software-production-architecture.md) explicitly says foundation (A) | A | Full adaptive catalog, retrieval/index/cache and enterprise SOP precedence are not built | PARTIALLY_IMPLEMENTED | P2 | No, current bounded path | Extend only from scenario evidence; keep guidance outside authority |
| TD-EVAL-001 | Production Evaluation Framework | Evaluation | Balanced, versioned intent/production/assurance evaluation | [release gate](../../src/spg/evaluation/release_gate.py) has scenario selectors and [WIC closure](../evidence/wic-interaction-intelligence-phase-closure.md) retains the full framework as unimplemented (A for current corpus) | Code/docs inspection | Existing regression corpus is not a complete evaluation framework or Human acceptance substitute | PARTIALLY_IMPLEMENTED | P1 | No, bounded integration | Establish minimum representative release scenarios and trend evidence after integration scope is fixed |
| CAP-UI-001 | Formal UI visual language | Product experience | Accepted industrial-cyan workspace composition | [Formal UI evidence](../evidence/formal-ui-phase-1/README.md), [web implementation](../../src/spg/web/app.js) (A/H visual) | Code/docs inspection | Visual fidelity acceptance does not certify production usability or every action | COMPLETE_AND_PROVEN | — | No | Preserve the bounded visual acceptance claim |
| TD-DEC-001 | Independent Decision Intelligence | external owner | Replaceable Decision Artifact provider, not an embedded YiJue engine | [program decisions](program-architecture-decisions.md) explicitly place concrete provider integration in the future; current WIC/Steering does not instantiate YiJue (docs/code) | Code/docs inspection | No independent Decision Intelligence runtime integration | DOCUMENTED_ONLY | P2 | No, current core | Revisit only when a selected journey needs this provider |
| TD-DEPLOY-001 | Autonomous governed deployment | Delivery | Governed promotion to externally hosted runtime | [phase-2 product direction](../product/watt-autonomous-governed-deployment-phase-2.md); [connector manifest](../../src/spg/application/connector_manifest.py) has no deployment provider (docs/code) | Code/docs inspection | Remote deployment is not a current production action | FUTURE_COMMERCIAL_OR_SCALE_CAPABILITY | P2 | No, local delivery integration | Admit a deployment scenario separately with external-effect authority and observed rollback/compensation |
| TD-VERIFY-001 | Runtime Verification | Assurance | Functional behavior of served result independently checked | [Dogfood #10](../evidence/dogfood/long-lived-motive-dogfood-10-human-acceptance.md) retains `VERIFICATION_RUNTIME_COVERAGE_GAP`; [Verification](../../src/spg/application/verification.py) validates source obligations (A/R) | A/R | Source-level PASS does not by itself prove browser-served runtime behavior | EXPLICIT_TECHNICAL_DEBT | P1 | Yes, functional preview/release claim | Add scenario-specific served-runtime obligations after real full-app preview qualification |
| TD-DOC-001 | Current-state wording | Architecture docs | Current docs distinguish bounded implementation from future layer | [integration boundary](integration-boundary.md) still says MVP does not implement ECF/Guardian while Watt-side boundary payloads/harness exist; [Work status](../../src/spg/application/work.py) still says multi-PWU deferred on a refinement branch. Older dated evidence is historical and must remain untouched (docs/code) | Code/docs inspection | Readers can mistake transitional wording for current capability or vice versa | STALE_DOCUMENTATION | P1 | No | Correct current wording in a separate scoped task; leave historical evidence immutable |
| TD-SCOPE-001 | Integration scope | Human architecture | One explicit first integration profile and acceptance bar | [first-release journey](../product/watt-first-release-human-journey.md) and [roadmap](../roadmap/watt-development-roadmap-and-progress.md) contain broader directions than the qualified local runtime | Code/docs inspection | Which journeys/topologies/owners are in the next “full system” gate is not fixed | REQUIRES_HUMAN_PRODUCT_OR_ARCHITECTURE_DECISION | P0 | Yes, gate definition | Human select scenarios and authority/infrastructure boundary before P0 build sequencing |

## Connector family reality, without catalog inflation

| Family | Current executable reality | Qualification / limit |
| --- | --- | --- |
| Filesystem, process, Git local | Native tool providers; exact workspace/authority boundaries | Native Executor runtime and connector tests; external Git push is separate |
| Dependency, build, test, lint/format/type-check | Named dependency/build/test providers; quality via generic process adapter | Native tool tests; each command still requires Work scope and observed result |
| Container, preview, artifact, observability logs | Production Environment and Preview providers; artifact references, runtime logs | Docker/local bounded scope; full-app preview caveat `TD-PREV-001` |
| GitHub public search/fetch | Real public REST retrieval | Live GitHub qualification; code search needs read token |
| GitHub/GitLab/Gitee write, HTTP general, browser automation, secret injection, SSH, CI/CD, deployment, object storage, issue update, mini-program upload | Catalog/authority description only; no production provider in manifest | Not executable by catalog membership |
| Database query/mutate, migration, quality, mini-program build | Generic `process.run` or build adapter eligible | Adapter readiness is not dedicated connector qualification or broad authorization |

## Human acceptance and evidence boundary

| Area | Implementation | Automated test | Runtime qualification | Human acceptance |
| --- | --- | --- | --- | --- |
| WIC entry/Interaction Intelligence | Bounded complete | PASS | Sampled provider/UI evidence | **PASS for sampled WIC scope only** |
| Semantic Truth and Steering | Implemented bounded foundation | PASS | Provider and Work path evidence | Production plan/Steering **NOT_EVALUATED** in WIC closure |
| Multi-PWU | Implemented | 1,400/1,403 backend total, three skips; Q1–Q14 PASS | Real Git/PostgreSQL serial/parallel/Join | PENDING |
| Native Executor/8+1 and Self-Refine | Technically qualified | PASS | Real provider/container evidence | PENDING for combined current journey |
| GitHub Search | Implemented | PASS | Real public search/fetch | PENDING |
| Web Search | Implemented behind key | PASS for contract/failure | BLOCKED by missing key | PENDING |
| Production Environment/Preview | Bounded implementations | PASS for covered cases | Native PE and frontend preview; real full-app preview **not proven** | PENDING |
| ECF/Guardian | Watt boundary/harness | Cross-repo tests for available contracts | Isolated harness, not default runtime | PENDING |
| Remote Git/Managed Repository/identity | Partial or absent | Local Git only | No end-to-end hosted/managed evidence | PENDING |

The latest full suite's three skips are two unavailable qualified local-image
cases and one sibling ECF preview-contract mismatch, not passes. No full
regression was rerun for this read-only audit.

## Architecture Promise / Runtime Reality Drift

The strongest current examples are: (1) `TD-PREV-001`, where a real frontend
preview and full-app implementation can be mistaken for full-app runtime
qualification; (2) `TD-ECF-001`/`TD-GUARD-001`, where contract payloads and an
isolated harness can be mistaken for default owner-runtime integration;
(3) `TD-PLAN-002`, where a new multi-PWU Candidate feeds an older one-PWU
measurement assumption; (4) `TD-REPO-003`, where a local execution workspace can
be mistaken for managed canonical Git; and (5) `TD-IDENT-001`, where persisted
authority attribution can be mistaken for actor authentication. These findings
come from comparing active call paths and evidence, not from TODO markers.

## Recommended construction order (proposal only)

1. Human fixes the integration profile (`TD-SCOPE-001`): one local self-dogfood
   and one external/brownfield repository journey, with supported preview
   topologies, ECF/Guardian inclusion and source home stated explicitly.
2. Establish a reproducible baseline (`TD-BASE-001`) and authenticated actor /
   resource authority (`TD-IDENT-001`). This prevents later gates and evidence
   from binding to ambiguous source or identity.
3. Decide and build source continuity (`TD-REPO-003`) and remote Git Access
   Grant/delivery (`TD-REPO-002`) on that authority model; qualify exact
   branch/revision, push/PR and machine-loss recovery without changing Work
   ownership.
4. Move worker/storage outside the desktop failure domain (`TD-CONT-001`),
   then integrate ECF and Guardian owner runtimes (`TD-ECF-001`,
   `TD-GUARD-001`) in the chosen Work path. Keep their ownership separate.
5. Prove actual full-app Candidate preview and served-runtime Verification
   (`TD-PREV-001`, `TD-VERIFY-001`); only then run the selected full-system
   integration and Human dogfood.
6. Close P1 usability/operations in dependency order: multi-PWU measurement,
   product asset continuity, connector/credential management, brownfield
   import/export, retention, diagnostics and Human acceptance. Defer P2 until
   observed scenarios justify them.

No debt item was implemented or historical evidence rewritten during this
census. The document itself is the only intended audit change.

```text
ALL_MAJOR_ARCHITECTURE_PROMISES_ARE_ACCOUNTED_FOR = PASS
DOCS_AND_RUNTIME_REALITY_ARE_RECONCILED = PASS
PARTIAL_IMPLEMENTATIONS_ARE_EXPLICIT = PASS
ARCHITECTURE_PROMISE_RUNTIME_DRIFT_IS_IDENTIFIED = PASS
CURRENT_P0_DEBT_IS_EXPLICIT = PASS
CURRENT_P1_DEBT_IS_EXPLICIT = PASS
LEGITIMATE_P2_FUTURE_SCOPE_IS_SEPARATED = PASS
HUMAN_DECISION_ITEMS_ARE_SEPARATED = PASS
EXTERNAL_CREDENTIAL_BLOCKERS_ARE_SEPARATED = PASS
HUMAN_ACCEPTANCE_STATUS_IS_TRUTHFUL = PASS
NO_DEBT_ITEM_WAS_SILENTLY_IMPLEMENTED_DURING_AUDIT = PASS
NEXT_IMPLEMENTATION_SEQUENCE_IS_PROPOSED = PASS
```
