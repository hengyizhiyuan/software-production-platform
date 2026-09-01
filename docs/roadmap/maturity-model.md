# Maturity Model

## Current Architecture Review State

Architecture Baseline remains **v0.1**. [Runtime Architecture Final Closure and Readiness](../architecture/spg-runtime-architecture-readiness.md) is PASS, and the [SPG Lite Runtime Implementation Contract](../architecture/spg-lite-runtime-implementation-contract.md) remains CLOSED. The [FVS-1 Implementation Contract](../architecture/spg-fvs-1-implementation-contract.md) is ADMITTED, F3-D is CLOSED, and FVS-1 is authorized for controlled implementation. S1 through S5 remain **CLOSED / PASS**. S6 is **IN PROGRESS**. S6-C2 Authorization #4 created one immutable generation-1 Attempt whose Executor transport failed before Provider binding; Provider Outcome remains UNKNOWN, Production Reality remains NONE, and the PWU remains PROPOSED. S6-C2-R1 and S6-C2-R2 are **CLOSED / PASS**. S6-C2 remains **IN PROGRESS / RECOVERY BARRIER ACTIVE**.

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
| S6-C2-HR1R — Bounded Environment Sync Recovery | CLOSED / PASS |
| S6-C2-HR1 — Windows Execution-Host Repair | CLOSED / PASS |
| S6-C2-DB1 — Local Dogfood Runtime Database Isolation | CLOSED / PASS |
| S6-C2-R1 — Attempt Recovery Assessment & Encoding Diagnosis | CLOSED / PASS |
| S6-C2-R2 — Explicit UTF-8 Dedicated Executor Transport Repair | CLOSED / PASS |
| S6-C2 — First Real Governed Dogfood Execution & Observation | IN PROGRESS / RECOVERY BARRIER ACTIVE |

S6-C2-HR1R, S6-C2-HR1, and S6-C2-DB1 remain CLOSED / PASS historical prerequisites. Authorization #4 subsequently created the first governed dogfood Attempt and exposed a Windows parent/child encoding mismatch before Provider binding. R1 persisted the admitted `UNKNOWN / REOBSERVE` Recovery Assessment with an active barrier. R2 replaces locale-dependent text transport with an explicit UTF-8/strict bytes wire for request, response, and diagnostic streams. Its 15 evidence obligations comprise 14 executable UTF8 pytest functions plus one external production Runtime immutability assertion. Synthetic R2 tests pass 14/14, affected B2-A/B2-B1 pass 30/30, and HOST tests pass 18/18. The serial full regression collected 462 tests, selected and passed 460, failed 0, skipped 0, and deselected two real Provider tests in 5440.85 seconds; the production Runtime snapshot remained identical. Provider Threads and Turns remain zero; the target artifact remains absent.

S5 is CLOSED / PASS and its generic recovery model remains unchanged. S6-B1 is CLOSED / PARTIAL and no additional S6-B1 probe is authorized. The historical B2-B2 probe remains COMPLETE / PARTIAL with `Provider SUCCESS + Production Reality NONE`. S6-C2-R2 changes only Dedicated Executor transport infrastructure and tests; it creates no Provider authority, Runtime recovery action, completion, verification, candidate, integration, or baseline commitment. The resulting clean repository checkpoint is eligible only as an S6-C2 platform-repair checkpoint pending production-lineage recovery review; it is not an admitted Production Source Baseline.

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
