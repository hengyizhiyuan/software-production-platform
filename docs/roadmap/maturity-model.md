# Maturity Model

## Current Architecture Review State

Architecture Baseline remains **v0.1**. The [Runtime Findings Review](../architecture/spg-runtime-findings-review.md) records the agenda; the [State Foundation Closure](../architecture/spg-state-foundation.md) and [Reconciliation & Recovery Closure](../architecture/spg-reconciliation-recovery.md) record confirmed A/B logical semantics. The [Runtime Verification and Benchmark Strategy](../architecture/spg-runtime-verification-benchmarks.md) records future verification work only. This update does not change maturity stages or MVP scope below.

| Review item | Status |
|---|---|
| Runtime Flow Tabletop Exercise | CLOSED |
| Runtime Failure-Mode Discovery | CLOSED |
| Issue Discovery Scope | FROZEN |
| Runtime Architecture Refinement | IN PROGRESS |
| A. State Foundation | CLOSED |
| A1. Core State Semantics | CLOSED — reviewed |
| A2. Transition & Commit Semantics | CLOSED — reviewed |
| A3. State Foundation Closure Review | PASSED |
| B. Reconciliation & Recovery | CLOSED |
| B1. Divergence & Recovery Semantics | CLOSED |
| B2. Execution Recovery | CLOSED |
| B3. Reconciliation & Replanning | CLOSED |
| B4. Recovery Closure | PASSED |
| C. Completion & Trust | NEXT — NOT STARTED |
| D. Side-effect Governance | NOT STARTED |
| NEXT | C. Completion & Trust |

The exact next valid transition is **Runtime Architecture Refinement → C. Completion & Trust**. A generic "continue" follows that transition. C remains NOT STARTED and is not begun by this B-closure documentation task. This does not authorize coding, tests, benchmarks, API/schema design, runtime implementation, Runtime Flow expansion, or Coding Readiness Review.

The refinement order remains A → B → C → D. A and B are CLOSED; B1/B2/B3 are CLOSED; B4 PASSED; C is NEXT and NOT STARTED; D is NOT STARTED. All 12 discovery areas remain frozen. Only the supplied A/B closure conclusions are promoted to confirmed semantics; detailed completion, side-effect governance, remaining labeled candidates, and concrete implementation mechanisms stay open. Future Runtime benchmarks do not add a maturity-stage implementation commitment.

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

A lightweight Decision Intelligence Provider may be used to exercise the contract. This is a bootstrap option, not a commitment to build a complete Decision Engine or integrate YiJue in Stage 1.

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

