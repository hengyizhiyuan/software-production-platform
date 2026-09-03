# AI-Native Software Production Platform

## Project Identity

- **Project:** AI-Native Software Production Platform
- **Repository:** `software-production-platform`
- **Internal Program:** TNGA Program

TNGA is an internal strategic research and development program code. It is not the repository name, package name, or external product name.

## Project Purpose

This repository is the Source of Truth for the AI-Native Software Production Platform: a platform for the full lifecycle of AI-native software production.

The platform is an AI-native Software Production System, not an AI Coding tool, ChatGPT replacement, or Coding Agent integration platform. Its objective is to build an AI-native Software Production Loop in which AI can use goals, engineering context, and governance constraints to drive planning, execution coordination, verification, feedback analysis, iteration adjustment, and baseline evolution.

## Current Stage

**Runtime Architecture Refinement — CLOSED**

**MVP-SCOPE-1 — CLOSED / PASS**

**MVP-APP-1 — CLOSED / PASS**

**MVP-API-1 — CLOSED / PASS**

**MVP-UI-1 — CLOSED / PASS**

**MVP-DOCKER-1 — CLOSED / PASS**

**MVP-E2E-1A — BLOCKED / RECOVERABLE — HISTORICAL ATTEMPT PRESERVED**

**MVP-E2E-1B — CLOSED / PASS**

**MVP-E2E-1D — BLOCKED — PROVIDER SUCCESS / PRODUCTION REALITY NONE — HISTORICAL ATTEMPT PRESERVED**

**MVP-E2E-1E — CLOSED / PASS**

**MVP-E2E-1G — CLOSED / PASS**

**MVP-E2E-1H — CLOSED / PASS**

**FIRST COMPLETE WATT GOVERNED SOFTWARE PRODUCTION LOOP — PROVEN**

**MVP-E2E-1I — IMPLEMENTED — RESTART READINESS PASS / PENDING ARCHITECTURE LEAD REVIEW**

**MVP — IN PROGRESS**

Architecture Baseline remains **v0.1**. Runtime Architecture Refinement is CLOSED and Runtime Architecture Readiness is PASS. [SPG Lite Runtime Implementation Contract](docs/architecture/spg-lite-runtime-implementation-contract.md) records I1/I2/I3 CLOSED, I4 PASSED, and Coding Readiness PASS. The [FVS-1 Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md) is ADMITTED; F3-D is CLOSED and FVS-1 is **AUTHORIZED FOR CONTROLLED IMPLEMENTATION**. S1 Runtime Foundation & Persistent Spine, S2 Governed Artifact Production, S3 Completion, Verification & Candidate Governance, S4 Repository Integration & Runtime Commit, and S5 Failure / Recovery Hardening are **CLOSED / PASS**. S6 Real Codex Dogfood & FVS Closure is **IN PROGRESS**. S6-B1 remains **CLOSED / PARTIAL**. S6-B2 Dedicated Executor & Real Provider Boundary, S6-B2-A, and S6-B2-B1 are **CLOSED / PASS**. The S6-B2-B2 historical real probe remains **COMPLETE / PARTIAL** with `Provider SUCCESS + Production Reality NONE` preserved. S6-C1 and S6-C2-DB1 remain **CLOSED / PASS**. Authorization #4 created Attempt generation 1, whose Executor transport failed before any Provider Thread or Turn; Provider Outcome remains UNKNOWN and Production Reality remains NONE. S6-C2-R1, S6-C2-R2, S6-C2-R3, S6-C2-R4-A, and S6-C2-R4-B are **CLOSED / PASS**. The Windows S6-C2-R4-C full-regression Attempt remains **INTERRUPTED — FINAL RESULT UNKNOWN / NOT RETAINED**. Full-system R4 regression, R4-C, R4-D, and real maintenance-lineage recovery are **DEFERRED_BY_MVP**; they are not current MVP blockers. S6-C remains historically IN PROGRESS, with its Recovery Barrier preserved rather than advanced.

MVP-DOCKER-1 Attempt #1 remains historical evidence: **BLOCKED — HOST_DOCKER_UNAVAILABLE**, implementation not started, file changes 0. Attempt #2 began only after Human confirmation that Docker Desktop / Linux Engine was available.

MVP-E2E-1A Attempt generation 1 remains immutable historical evidence: Attempt `b8992eb6-893d-40eb-a8a2-7c3fb008d4c0`, Dispatch `b433b2b3-230e-422d-a754-6990b289cf12`, Provider Outcome **UNKNOWN**, Provider Thread / Turn **0 / 0**, and independently observed Production Reality **NONE**. No Completion, Candidate, Integration, or Runtime Commit exists. The Codex process stopped before Thread creation because its SQLite state runtime could not initialize under the Windows bind-mounted `/home/spg/.codex`.

MVP-E2E-1B is CLOSED / PASS. It separates the exact authorized authentication cache from mutable runtime state. The E2E `CODEX_HOME` now uses a dedicated Linux-native Docker named volume; the exact authentication file is exposed read-only at the Executor infrastructure boundary. The no-Turn child preflight initialized the locked Codex 0.147.0 app-server and SQLite state with authentication **AVAILABLE**, a writable state root, and Provider Thread / Turn **0 / 0**. The historical Work now projects **BLOCKED / EXECUTION_STOPPED** with informational Architecture/Operator Attention and no retry, resume, or Completion-evaluation action. Real governed execution remains unproven.

MVP-E2E-1D remains immutable historical evidence: Attempt `72e89694-77d1-49d4-82ca-557f8433383f`, Dispatch `43f4a1b6-ebb7-452c-8b99-e8de7019be7c`, Provider Report `4a3599e6-324e-4385-855a-0916bee09d31`, and Repository Observation `b12558c9-af32-43f8-a64c-42659bd78c1b`. The real Provider Thread and Turn completed with Provider Outcome **SUCCESS**, but the independently observed Production Reality was **NONE**: the change manifest was empty, the required artifact was absent, and no Completion, Candidate, Integration, or Runtime Commit exists. Provider terminal evidence recorded the exact execution blocker `bwrap: No permissions to create a new namespace`. Provider success is not Production Truth.

MVP-E2E-1E is **CLOSED / PASS**. The E2E-only Dedicated Executor selects the locked Codex SDK's public `full-access` sandbox policy to avoid unsupported nested namespace isolation inside the already-isolated Docker boundary; the default non-E2E policy remains `workspace-write`. Docker isolation, the exact Attempt workspace, authoritative-repository separation, credential filtering, governed scope, and independent Production Reality observation remain mandatory. A zero-Turn child preflight proved public-SDK policy acceptance, writable isolated workspace, authentication readiness, and Provider Thread / Turn **0 / 0**. For a Completion Contract that requires production output or change, terminal Provider evidence plus Production Reality **NONE** now projects **BLOCKED / EXECUTION_STOPPED** without changing Provider Outcome or inventing Completion or recovery authority.

MVP-E2E-1G and MVP-E2E-1H are **CLOSED / PASS**. The first complete Watt governed software production loop is **PROVEN**: Human Intent progressed through Work, PWU, one real Codex execution, independent Observation, Completion, Verification, Candidate, Human Authorization, Repository Integration, Runtime Commit, Trusted Baseline advancement, and completed Work projection.

MVP-E2E-1I is **IMPLEMENTED — RESTART READINESS PASS / PENDING ARCHITECTURE LEAD REVIEW**. After the CONVERGED Repository Integration, startup now materializes the Watt-owned authoritative checkout only when the Current Trusted Baseline, Runtime Commit, Integration Effect, repository identity, authoritative ref/tree, and exact source-Baseline index all agree and no independent local changes exist. Unexpected changes stop with `REPOSITORY_CHECKOUT_DIVERGENCE`. The current `watt-e2e2` app restarted successfully and remained restart-idempotent, the checkout stayed clean at the unchanged Trusted Baseline, completed Work and `trusted_result=true` remained queryable, and no Provider or Runtime production history was added or rewritten.

The current delivery priority is governed by [MVP Scope Calibration and Phase-2 Hardening Backlog](docs/roadmap/mvp-scope-calibration.md): review the implemented local Docker MVP, then validate one real local governed Codex production loop before Linux deployment and systematic self-dogfood. ChatGPT + Codex remains the development workflow; a CLI-only Runtime is not the MVP product.

For the MVP product model, **Work is the user-facing organization unit**. Engineering Resources are bound to Work through an explicit Engineering Scope, while Goal remains an optional weak aggregation. MVP execution uses exactly one Engineering Resource and one-PWU-first planning as bounded delivery policies, without encoding either restriction as a permanent architecture limit.

| Architecture workflow item | Status |
|---|---|
| Runtime Flow Tabletop Exercise | CLOSED |
| Runtime Failure-Mode Discovery | CLOSED |
| Issue Discovery Scope | FROZEN |
| Runtime Architecture Refinement | CLOSED |
| A. State Foundation | CLOSED |
| A1. Core State Semantics | CLOSED — reviewed |
| A2. Transition & Commit Semantics | CLOSED — reviewed |
| A3. State Foundation Closure Review | PASSED |
| B. Reconciliation & Recovery | CLOSED |
| B1. Divergence & Recovery Semantics | CLOSED |
| B2. Execution Recovery | CLOSED |
| B3. Reconciliation & Replanning | CLOSED |
| B4. Recovery Closure | PASSED |
| C. Completion & Trust | CLOSED |
| C1. Completion Semantics | CLOSED — reviewed |
| C2. Verification & Trust Freshness | CLOSED — reviewed |
| C3. Acceptance & Trusted Completion | CLOSED — reviewed |
| C4. Completion & Trust Closure | PASSED |
| D. Side-effect Governance | CLOSED |
| D1. Side-effect Semantics & Boundary | CLOSED — reviewed |
| D2. Side-effect Authority & Execution Safety | CLOSED — reviewed |
| D3. Compensation & External Reality | CLOSED — reviewed |
| D4. Side-effect Governance Closure | PASSED |
| Final Closure / Architecture Readiness Review | PASSED |
| Runtime Architecture Readiness | PASS |
| SPG Lite Runtime — Implementation Contract / Runtime MVP Design | CLOSED |
| I1. Minimal Runtime Contract & Domain Spine | CLOSED |
| I2. State Transition & Persistence Design | CLOSED |
| I3. Capability Interfaces & End-to-End MVP Loop | CLOSED |
| I4. Coding Readiness Closure | PASSED |
| Coding Readiness | PASS |
| Implementation Governance | AUTHORIZED FOR CONTROLLED IMPLEMENTATION |
| FVS-1 Implementation Contract | ADMITTED |
| MVP-SCOPE-1 — Architecture Scope Calibration & Phase-2 Hardening Backlog | CLOSED / PASS |
| MVP-APP-1 — Goal-Centric Governed Work Application Flow | CLOSED / PASS |
| MVP-API-1 — Minimal Goal / Work Product HTTP API | CLOSED / PASS |
| MVP-UI-1 — Functional Goal / Work Control Room Web UI | CLOSED / PASS |
| MVP-DOCKER-1 — Local Integrated Product Runtime | CLOSED / PASS |
| MVP-E2E-1A — Real Local Governed Codex Execution to Human Candidate Attention | BLOCKED / RECOVERABLE — HISTORICAL ATTEMPT PRESERVED |
| MVP-E2E-1B — Container-Native Codex State Repair & Blocked-Reality Projection | CLOSED / PASS |
| MVP-E2E-1D — Fresh Work Real Governed Codex Production Attempt | BLOCKED — PROVIDER SUCCESS / PRODUCTION REALITY NONE — HISTORICAL ATTEMPT PRESERVED |
| MVP-E2E-1E — Container Codex Sandbox Compatibility & Terminal-NONE Projection | CLOSED / PASS |
| MVP-E2E-1G — Fresh E2E Runtime & First Real Watt Production Artifact | CLOSED / PASS |
| MVP-E2E-1H — Human-Authorized Repository Integration & Trusted Baseline Commit | CLOSED / PASS |
| First Complete Watt Governed Software Production Loop | PROVEN |
| MVP-E2E-1I — Post-Integration Checkout Synchronization & Restart Readiness | CLOSED / PASS |
| MVP-E2E Proof — Two Complete Governed Watt Production Loops | CLOSED / PASS |
| MVP-ORCH-1 — Production Orchestration Lite | CLOSED / PASS |
| F1. Slice Goal & Governance Contract | REVIEWED / ADMITTED |
| F2. Minimal Technical Foundation | REVIEWED / ADMITTED |
| F3-A. Runtime Slice Boundary & Physical Spine | REVIEWED / ADMITTED |
| F3-B. Repository Integration / Commit Semantics | REVIEWED / ADMITTED |
| F3-C. Executable Test & Failure Contract | REVIEWED / ADMITTED |
| F3-D. FVS Coding Authorization Closure | CLOSED — FVS-1 AUTHORIZED FOR CONTROLLED IMPLEMENTATION |
| S1 — Runtime Foundation & Persistent Spine | CLOSED / PASS |
| S1-A. Runtime Project Foundation | CLOSED / PASS |
| S1-B. Persistent Runtime Foundation | CLOSED / PASS |
| S1-C. Bootstrap Baseline & Minimal Durable Runtime Spine | CLOSED / PASS |
| S2 — Governed Artifact Production | CLOSED / PASS |
| S2-A — Context & Execution Preparation Foundation | CLOSED / PASS |
| S2-B — Isolated Execution & Independent Artifact Observation | CLOSED / PASS |
| S3 — Completion, Verification & Candidate Governance | CLOSED / PASS |
| S3-A — Completion Evaluation & Produced Semantics | CLOSED / PASS |
| S3-B — Verification Qualification & Satisfaction | CLOSED / PASS |
| S3-C — Candidate Sealing & Human Governance | CLOSED / PASS |
| S4 — Repository Integration & Runtime Commit | CLOSED / PASS |
| S4-A — Authorized Repository Integration | CLOSED / PASS |
| S4-B — Runtime Commit | CLOSED / PASS |
| S5 — Failure / Recovery Hardening | CLOSED / PASS |
| S5-A — Recovery Classification & Reconciliation Foundation | CLOSED / PASS |
| S5-B — Repository Integration & Runtime Commit Reconciliation | CLOSED / PASS |
| S5-C — Execution Attempt & Workspace Recovery Hardening | CLOSED / PASS |
| S6 — Real Codex Dogfood & FVS Closure | IN PROGRESS |
| S6-B1 — Real Codex SDK Host Integration Spike | CLOSED / PARTIAL |
| S6-B1-R — Provider Terminal & Identity Correlation Spike | PARTIAL — LIFECYCLE CAPABILITY PROVEN / DURABLE REAL EVIDENCE INCOMPLETE |
| S6-B1-R2 — Durable Provider Evidence Capture Hardening | CLOSED / PASS |
| S6-B2 — Dedicated Executor & Real Provider Boundary | CLOSED / PASS |
| S6-B2-A — Dedicated Executor Boundary Deterministic Spike | CLOSED / PASS |
| S6-B2-B1 — Codex Adapter Binding & Authentication Boundary Preflight | CLOSED / PASS |
| S6-B2-B2 Historical Real Probe — Single Real Codex Through Dedicated Executor Boundary | COMPLETE / PARTIAL |
| S6-C — Real Governed Dogfood Loop | IN PROGRESS |
| S6-C1 — Real Governed Dogfood Requirement & Contract Admission | CLOSED / PASS |
| S6-C2-HR1R — Bounded Environment Sync Recovery | CLOSED / PASS |
| S6-C2-HR1 — Windows Execution-Host Repair | CLOSED / PASS |
| S6-C2-DB1 — Local Dogfood Runtime Database Isolation | CLOSED / PASS |
| S6-C2-R1 — Attempt Recovery Assessment & Encoding Diagnosis | CLOSED / PASS |
| S6-C2-R2 — Explicit UTF-8 Dedicated Executor Transport Repair | CLOSED / PASS |
| S6-C2-R3 — Production-Lineage Recovery Reality Check | CLOSED / PASS |
| S6-C2-R4 — Verified Maintenance Baseline & Production-Lineage Recovery | DEFERRED_BY_MVP after R4-B |
| S6-C2-R4-A — Recovery Contract Admission | CLOSED / PASS |
| S6-C2-R4-B — Controlled Implementation & Focused Validation | CLOSED / PASS |
| S6-C2-R4-C — Windows Full Deterministic Regression Attempt | INTERRUPTED HISTORICAL ATTEMPT; DEFERRED_BY_MVP |
| S6-C2-R4-D — Real Maintenance Recovery Execution | DEFERRED_BY_MVP / NOT EXECUTED |
| Linux MVP Deployment & Promotion Gate | AFTER LOCAL USABLE MVP / NOT STARTED |
| S6-C2 — First Real Governed Dogfood Execution & Observation | HISTORICAL RECOVERY BARRIER PRESERVED; DEFERRED_BY_MVP |

The [FVS-1 Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md#54-s6-b1-real-codex-sdk-host-integration-spike-reality) records the bounded S6-B1 Reality and its S6-B1-R/R2 follow-ups. Historical probes remain immutable. **No additional S6-B1 or S6-B2-B2 real Provider probe is authorized**. S6-B2 and S6-C2-R4-B are **CLOSED / PASS** after deterministic closure hardening and Architecture Lead Reality Review. The historical B2-B2 probe remains **COMPLETE / PARTIAL** and still records the exact benchmark `Provider SUCCESS + Production Reality NONE`; it is not relabeled. The historical S6-C2 Recovery Barrier remains preserved. The Windows R4-C regression was interrupted at the last observed 59% progress with no known failure, but no terminal pytest result was retained and no checkpoint was created. Complete R4 qualification and execution are DEFERRED_BY_MVP. No real Runtime recovery, dispatch, or Provider Turn is authorized or executed.

The completed refinement order is **A. State Foundation → B. Reconciliation & Recovery → C. Completion & Trust → D. Side-effect Governance → Final Readiness Review**.

S6-C1 admits one bounded documentation dogfood Production Intent and one PWU contract. Authorization #4 created one immutable generation-1 Attempt and one Dispatch, but the Windows locale-dependent parent/child JSON transport failed before Provider binding. No Provider Thread or Turn was created, the target artifact remains absent, and the PWU remains PROPOSED. Runtime Failure Discovery remains CLOSED and its 12-area scope remains frozen; reopen it only when implementation, dogfood, or Reality Check evidence requires it.

The [Runtime Findings Review](docs/architecture/spg-runtime-findings-review.md) preserves the frozen discovery scope. [State Foundation](docs/architecture/spg-state-foundation.md), [Reconciliation & Recovery](docs/architecture/spg-reconciliation-recovery.md), [Completion & Trust](docs/architecture/spg-completion-trust.md), and [Side-effect Governance](docs/architecture/spg-side-effect-governance.md) preserve the closed A/B/C/D semantics and their respective 20-invariant sets. The broader [Runtime Verification and Benchmark Strategy](docs/architecture/spg-runtime-verification-benchmarks.md) remains future work; FVS-1 now admits only its bounded T01–T18 and 12/12 executable obligations, which are not yet implemented or passed. Architecture readiness means enough semantics are stable for the next governed iteration, not that all future architecture or implementation is complete.

### S6-C2-HR1 Windows Execution-Host Repair Closure

S6-C2-HR1R and S6-C2-HR1 are CLOSED / PASS. The first environment sync failure remains historical evidence; the lock-preserving recovery sync, Windows state-root behavior, credential filtering, authentication readiness, Dedicated Executor no-Turn preflight, HOST 18/18, and affected B2-A/B2-B1 30/30 regression all passed at closure. Full Regression Attempt 1 remains UNKNOWN / NOT RETAINED after host interruption, while replacement Attempt 2 passed 446/446 selected deterministic tests with two real Provider tests deselected. These facts remain historical execution-host evidence; the later S6-C2 Authorization #4 Attempt and R1/R2 recovery path do not rewrite them.

### S6-C2-DB1 Local Dogfood Runtime Database Isolation

Authorization #3 remains a pre-execution block classified as `PRODUCTION_RUNTIME_DATABASE_NOT_CONFIGURED`: repository, Contract, and execution-host gates passed, but no Runtime object, Attempt, Provider Thread, Provider Turn, or production side effect was created. S6-C2-DB1 establishes one local PostgreSQL service and existing volume with two logically distinct databases: `spg_runtime` for real local Dogfood Runtime state and `spg_test` for pytest state. This is logical, not physical, isolation.

At S6-C2-DB1 closure, `spg_runtime` was migrated to Alembic `20260829_12` with empty Runtime authority tables. Test fixtures consume only `SPG_TEST_DATABASE_URL`, while Runtime consumes `SPG_DATABASE_URL`. That historical closure did not authorize execution; Authorization #4 later created the exact generation-1 Runtime lineage now governed by S6-C2-R1/R2.

### S6-C2-R1/R2 Recovery and Explicit UTF-8 Transport Repair

S6-C2-R1 is CLOSED / PASS. Recovery Assessment `18e1a39b-3133-591f-9364-50a5766fc8d2` classifies Attempt generation 1 as `UNKNOWN / REOBSERVE`, current but not safely recoverable, with Human Attention and Recovery Barrier active. It preserves Provider Outcome UNKNOWN and Production Reality NONE.

S6-C2-R2 is CLOSED / PASS. It makes the Dedicated Executor JSON wire explicitly UTF-8 with strict error handling in both directions. The parent encodes request bytes and strictly decodes child stdout/stderr bytes, independent of host locale or parent `PYTHONUTF8`. Malformed UTF-8 maps conservatively to transport `MALFORMED_RESPONSE` and Provider Outcome UNKNOWN. The evidence model contains 15 obligations: UTF8-01 through UTF8-14 are 14 executable pytest functions, while UTF8-15 is the external pre/post `spg_runtime` immutability assertion that deliberately does not expose production Runtime state to pytest. Synthetic UTF-8 transport tests pass 14/14; affected B2-A and B2-B1 tests pass 15/15 each; HOST tests pass 18/18. The serial full current-tree deterministic regression collected 462 tests, selected and passed 460, failed 0, skipped 0, and deselected the two `real_codex` tests in 5440.85 seconds. The exact production Runtime snapshot remained unchanged and no real Provider Thread or Turn was created. R2 closure does not resolve the Recovery Barrier or authorize another Attempt.

### S6-C2-R3/R4-A Production-Lineage Recovery Contract

S6-C2-R3 is CLOSED / PASS with classification `NARROW PRODUCTION-LINEAGE RECOVERY CAPABILITY REQUIRED`. The current blocked Run/Plan/PWU/Attempt lineage remains immutably bound to its old Trusted Baseline, while the authoritative self-hosted repository has advanced through an independently verified platform repair. Execution compatibility does not imply Repository Integration eligibility, and neither in-place rebinding nor destructive Runtime reset is lawful.

S6-C2-R4-A is CLOSED / PASS as contract admission. [Section 67 of the FVS-1 Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md#67-s6-c2-r3-closure-and-r4-a-verified-maintenance-baseline-and-production-lineage-recovery-contract) defines exact maintenance-checkpoint qualification, immutable verification evidence, Human Authority, read-only Git validation, maintenance Baseline admission, append-only old-lineage supersession and Recovery resolution, new Run/Plan/PWU admission, atomicity, idempotency, concurrency, eligibility, outcome boundaries, and future MR-01 through MR-34 executable obligations.

The current UTF-8 repair checkpoint is historical input evidence, not the future maintenance Baseline. The eventual recovery target can be observed only after Linux promotion-gate full-regression acceptance, then explicitly bound by a separately authorized Runtime recovery step. R4-A created no implementation or Runtime fact.

### S6-C2-R4-B Verified Maintenance Recovery Implementation

S6-C2-R4-B is **CLOSED / PASS** after Architecture Lead Reality Review. [Section 68 of the FVS-1 Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md#68-s6-c2-r4-b-verified-maintenance-recovery-implementation-and-focused-validation) records the provider-neutral typed request/result, immutable maintenance admission and resolution record, exact evidence and Human Authority fingerprints, read-only Git qualification, maintenance-provenance Trusted Baseline admission, pointer CAS, `SUPERSEDED` old-lineage terminal states, new Run/Plan/PWU admission, atomic rollback, idempotency, concurrency, and the MR-01 through MR-34 mapping.

Focused R4-B evidence passes 23/23; unique affected persistence, Runtime spine, S4-B, S5, and directly adjusted inventory cases pass 175/175; persistence foundation passes 6/6. Compile/import, migration downgrade/re-upgrade on `spg_test`, `uv lock --check`, and `git diff --check` pass. The pre/post `spg_runtime` whole-database fingerprint is identical, its schema remains `20260829_12`, and no real Baseline, pointer, lineage, Recovery Action, Attempt generation 2, Provider Thread, or Provider Turn was created.

### Windows Bootstrap Runtime Archive and MVP Delivery Replan

The Windows R4-C full-regression Attempt was intentionally abandoned after interruption. Its log retained progress through 59% with no known failure, but no terminal pytest result; it is **INTERRUPTED / FINAL RESULT UNKNOWN / NOT RETAINED**, and no R4-C checkpoint was created. Complete R4 qualification, R4-D, and real maintenance recovery are DEFERRED_BY_MVP. The next delivery target is the usable local Docker MVP; the Linux development server becomes the deployment and promotion target only after that product exists.

The unchanged spg_runtime at Alembic 20260829_12 is archived as **WINDOWS BOOTSTRAP DOGFOOD EVIDENCE — NOT AN ACTIVE SERVER RUNTIME TO BE CONTINUED**. Backup C:\Users\yuchunbo\Documents\SPG-backups\spg_runtime_windows_bootstrap_20260902T061522Z.dump has SHA-256 64ebae40cbea8589f3b1c988422329d4f52e9b5200729ca67c19f31c1a0045b0 and passed restore-list validation. It is not migrated into the future Linux Runtime. Real maintenance recovery remains unexecuted, the old lineage is not superseded, no new lineage exists, and the historical Recovery Barrier remains active.

### MVP-ORCH-1 Production Orchestration Lite

MVP-ORCH-1 is **CLOSED / PASS** after Architecture Lead Reality Review. It
introduces a bounded, in-process application driver over the
existing authoritative Work and governed Runtime transitions. After Human Work
Draft Approval, Watt automatically executes one currently legal non-Human
transition at a time, re-reading Runtime Reality after every committed step.
It stops at Human Attention, BLOCKED Reality, COMPLETED, ambiguity, unchanged
Reality, infrastructure failure, application shutdown, or the configured
finite transition bound. A process-local per-Work guard prevents obvious
duplicate scheduling; it does not create a second production state machine or
distributed authority.

Human Work Draft Approval and exact Candidate Authorization remain mandatory
for MVP. Candidate authorization is not inferred or automated. After the Human
authorizes an exact sealed Candidate, the same bounded driver may continue
Repository Integration, Runtime Commit, Trusted Baseline advancement, and Work
completion through the existing services. Human Attention is requested only
when Watt lacks lawful autonomous authority or cannot safely determine the next
production action. Human-in-the-loop does not mean Human-as-the-loop.

The implementation is single-process and uses ephemeral daemon scheduling.
Startup may reschedule only Works whose current projection permits ordinary
READY/RUNNING deterministic progression. Existing dispatch facts prevent
automatic Provider redispatch, so restart does not imply Provider retry,
Provider Resume, Attempt recovery, or manufactured Human Authority. Durable
recovery, distributed scheduling/Worker Fleet, message brokers, and
policy/risk-driven automatic Candidate integration are DEFERRED_BY_MVP.

## Program-level Architecture Source of Truth

The current system-level architecture baseline is:

- [AI Native Software Production System Architecture Baseline v0.1](docs/architecture/system-architecture-baseline-v0.1.md)
- [SPG Lite Domain Model and Contract Boundary Baseline](docs/architecture/spg-lite-domain-contract-baseline.md)
- [SPG Runtime Architecture Final Closure and Readiness](docs/architecture/spg-runtime-architecture-readiness.md)
- [SPG Lite Runtime Implementation Contract](docs/architecture/spg-lite-runtime-implementation-contract.md)
- [Runtime Profile, Provider Placement, and Containerized Deployment](docs/architecture/runtime-profile-provider-deployment.md)
- [SPG FVS-1 — Governed Documentation Production Loop Implementation Contract](docs/architecture/spg-fvs-1-implementation-contract.md)
- [MVP Scope Calibration and Phase-2 Hardening Backlog](docs/roadmap/mvp-scope-calibration.md)

The system baseline governs mission and system boundaries. The SPG Lite baseline consolidates the current SPG domain objects and capability contracts under those boundaries. Detailed documents refine their own scope without silently changing these program-level decisions.

## Core Principles

- Human Agency First — meaningful Human authority, not unrestricted runtime privilege
- Human Authority Does Not Imply Runtime Bypass
- Governed Participants — shared governance rules, different Responsibility / Authority
- No Actor Owns Production Truth Alone
- Distributed Responsibility, Governed Adjudication — not majority voting
- Provider Consolidation Does Not Collapse Authority Boundaries
- Replaceable Intelligence, Durable Governance
- One Product Architecture, Multiple Runtime Profiles
- Provider / Model Selection Is Configuration, Not Domain Logic
- Model Provider and Executor Provider Are Distinct
- Containerization Is Packaging / Infrastructure, Not Domain Semantics
- Context before Execution
- Evidence before Acceptance
- Completion Semantics Are Layered
- Validity Is Relational
- Trust Is Obligation Satisfaction Before It Is a Score
- Execution Capability Does Not Imply Side-effect Authority
- Observed External Reality Does Not Automatically Become Trusted Reality
- Governed Integration Atomicity over Assumed Physical Atomicity
- Role over Agent
- Executor Independence
- Platform Capability over Application Duplication
- Capability Contract Before Capability Implementation
- Dependency Direction Follows Capability Ownership
- Production Work Unit Generalization
- Ownership Before Integration
- Generated Does Not Equal Trusted
- Contract Before Implementation
- Source of Truth over Conversation History
- Conversation-to-Contract — raw conversation is never authoritative execution input
- Controlled Autonomy
- AI Capability Evolution Independence

## Current Major Components

The future platform will form a system with the following capabilities:

- Consumer Projects, for example 易决
- Guardian — Engineering Assurance System
- Engineering Context Fabric

This document describes their relationship only; it does not define their internal subsystem designs.


## Origin and MVP Goal

The current design originates from real ChatGPT + Codex collaboration practice. The MVP goal is not to copy that workflow into a new platform; it is to validate a minimum AI-native Software Production Loop for real projects.

The MVP prioritizes running the production loop, serving real projects, accumulating engineering data, and validating AI-driven research and development. The long-term direction may evolve toward an AI Software Production Operating System.


## Formal Platform Positioning

The platform is not an AI Coding tool, a ChatGPT replacement, or a simple model API integration layer. It is an AI-native Software Production System that treats AI as a core production capability and first-class production factor, while organizing human intent, engineering judgment, and machine intelligence into a governed, verifiable, and continuously evolving system.

The long-term challenge is to organize intelligence for complex software production, not merely to make AI smarter or call stronger models. The current MVP remains limited to rapid validation, real internal projects, small-step iteration, and experimentation.

## Core Positioning Principle

Human defines intent. AI amplifies capability. System ensures trust.

The platform's first-class abstraction is Role, not Agent. Its core concerns are Responsibility, Authority, Context, Artifact, and Gate.
