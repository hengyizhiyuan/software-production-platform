# Maturity Model

## Current Architecture Review State

Architecture Baseline remains **v0.1**. [Runtime Architecture Final Closure and Readiness](../architecture/spg-runtime-architecture-readiness.md) is PASS, and the [SPG Lite Runtime Implementation Contract](../architecture/spg-lite-runtime-implementation-contract.md) remains CLOSED. The [FVS-1 Implementation Contract](../architecture/spg-fvs-1-implementation-contract.md) is ADMITTED, F3-D is CLOSED, and FVS-1 is authorized for controlled implementation. S1 Runtime Foundation & Persistent Spine and S2 Governed Artifact Production are CLOSED / PASS. S3 is IN PROGRESS and S3-A remains CLOSED / PASS. S3-B is IMPLEMENTED — LOCAL VALIDATION PASS and pending Architecture Lead Reality Review with the full suite at 132/132 PASS. S3-C remains BLOCKED BY S3-B / NOT STARTED.

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
| S3 — Completion, Verification & Candidate Governance | IN PROGRESS |
| S3-A — Completion Evaluation & Produced Semantics | CLOSED / PASS |
| S3-B — Verification Qualification & Satisfaction | IMPLEMENTED — LOCAL VALIDATION PASS / PENDING ARCHITECTURE LEAD REALITY REVIEW |
| S3-C — Candidate Sealing & Human Governance | BLOCKED BY S3-B / NOT STARTED |
| S4 — Repository Integration & Runtime Commit | NOT STARTED |

S3-B preserves the exact non-authoritative proposed snapshot, provider-neutral Verification seam, relational applicability/freshness, SPG production admissibility, and atomic optimistic-concurrency-protected `PRODUCED → SATISFIED` transition. It introduces no Candidate, Authorization, Repository Integration, Runtime Commit, Trusted Baseline advancement, Trust Score, or Guardian ownership collapse. S3-B is not yet CLOSED and S3-C is not authorized. The exact next governed step is **Architecture Lead S3-B Reality Review → if PASS, close S3-B and authorize S3-C Candidate Sealing & Human Governance**.

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
