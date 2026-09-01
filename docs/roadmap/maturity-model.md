# Maturity Model

## Current Architecture Review State

Architecture Baseline remains **v0.1**. [Runtime Architecture Final Closure and Readiness](../architecture/spg-runtime-architecture-readiness.md) is PASS, and the [SPG Lite Runtime Implementation Contract](../architecture/spg-lite-runtime-implementation-contract.md) remains CLOSED. The [FVS-1 Implementation Contract](../architecture/spg-fvs-1-implementation-contract.md) is ADMITTED, F3-D is CLOSED, and FVS-1 is authorized for controlled implementation. S1 Runtime Foundation & Persistent Spine, S2 Governed Artifact Production, S3 Completion, Verification & Candidate Governance, S4 Repository Integration & Runtime Commit, and S5 Failure / Recovery Hardening are **CLOSED / PASS**. S6 Real Codex Dogfood & FVS Closure is **IN PROGRESS**. S6-B1 remains **CLOSED / PARTIAL** and S6-B2 is **CLOSED / PASS** after final deterministic closure hardening. The S6-B2-B2 historical real probe remains **COMPLETE / PARTIAL** and preserves its exact `Provider SUCCESS + Production Reality NONE` benchmark; no additional real Turn occurred. S6-C1 is **CLOSED / PASS** with baseline-binding semantic calibration; S6-C2 is **PRE-EXECUTION BLOCKED / NO ATTEMPT CREATED**; S6-C is **IN PROGRESS**.

| Review item | Status |
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

S5 is CLOSED / PASS. Its FVS-level generic recovery model remains unchanged. S6-B1 is CLOSED / PARTIAL and no additional S6-B1 probe is authorized. S6-B2 is CLOSED / PASS after replacing the historical broad keyword scan with structural request-contract assertions. B2CLOSE-01–08 pass; the complete B2 deterministic module passes 38/38 with one real test deselected; affected S6-B1/R/R2 tests pass 45/45 with one real test deselected; the current-tree deterministic suite passes 428/428 with two real tests deselected. Migration head remains `20260829_12`; compilation/import and `git diff --check` pass. The historical B2-B2 probe remains COMPLETE / PARTIAL, retains exact Thread/Turn evidence and `Provider SUCCESS + Production Reality NONE`, and is not normalized into PASS. S6-C1 is CLOSED / PASS with one admitted bounded documentation dogfood contract and baseline-binding calibration; its target artifact, Attempt, and Provider Turn do not yet exist. S6-C remains in progress and S6-C2 is pre-execution blocked.

The refinement order A → B → C → D and Final Review is complete. All 12 discovery areas remain frozen. The closure confirms logical Runtime semantics, ownership boundaries, deferred-scope clarity, and SPG Lite feasibility without selecting physical mechanisms or expanding MVP.

## Stage 0 — Architecture Foundation

Establish the platform charter, problem definition, design principles, architecture boundaries, governance model, Source of Truth baseline, and provider-independent Capability Contracts.

## Stage 1 — AI Engineering Control Loop MVP

Includes:

- Project Bootstrap
- Lightweight Context Management
- Task Initiative
- Production Planner
- Role System
- Executor Integration
- Verification and Guardian Assurance Extension Point
- Decision Intelligence Contract validation through the internal production loop
- Provider-neutral Capability Contract, Executor adapter, and Runtime/Profile configuration boundaries
- Local-first validation with container-ready packaging; Docker and Docker Compose are the preferred FVS/local deployment direction

A lightweight Decision Intelligence Provider may be used to exercise the contract. This is a bootstrap option, not a commitment to build a complete Decision Engine or integrate YiJue in Stage 1.

One real provider path is sufficient for the first FVS. Dual Global/Mainland providers, provider-management UI, cross-region topology, residency policy automation, and Kubernetes are not Stage 1 prerequisites.

For FVS-1 specifically, S1-A implements the Python Modular Monolith package foundation, CLI-first startup, Pydantic Settings, dependency declarations, and pytest smoke tests. S1-B adds real PostgreSQL connectivity, SQLAlchemy engine/session and explicit Unit of Work infrastructure, optimistic version-aware updates, an empty Alembic environment, and real PostgreSQL integration evidence without adding Runtime domain tables. Git worktree integration and Codex CLI Executor Adapter remain unimplemented.

## Stage 2 — Mature Capability Provider Integration

- Replace or upgrade bootstrap providers without changing SPG responsibility
- Integrate a mature Decision Intelligence Provider, potentially the YiJue Decision Engine
- Integrate Guardian and ECF through their owned capability boundaries
- Preserve independent ownership, Source of Truth, and lifecycle

## Stage 3+

Future expansion areas:

- Multi Executor
- CI/CD
- Delivery Automation
- Runtime Feedback
- Production Economics
- Multiple Enterprise Decision Providers
- Runtime Profile management, provider/model adapters, and enterprise-private bindings
- Provider placement and data-residency governance
- Token / AI Capacity Governance — **FUTURE / DEFERRED; NOT REQUIRED FOR CURRENT DOGFOOD MVP; NOT AUTHORIZED FOR DESIGN OR IMPLEMENTATION**. Potential future concerns are limited here to token/quota observability, per-PWU capacity-consumption attribution, capacity-aware PWU scheduling, model/provider cost-performance comparison, budget/quota policies, and abnormal-consumption detection. Cost optimization must not weaken required software quality, trust, verification, assurance, recovery, or authority boundaries.

The governing evolution sequence is:

```text
Define Capability Contract
        ↓
Bootstrap Minimal Provider
        ↓
Build and Validate Internal Production Loop
        ↓
Integrate Mature Capability Provider
```

This maturity model intentionally does not expand implementation details.
