# Maturity Model

## Current Architecture Review State

Architecture Baseline remains **v0.1**. [Runtime Architecture Final Closure and Readiness](../architecture/spg-runtime-architecture-readiness.md) is PASS, and the [SPG Lite Runtime Implementation Contract](../architecture/spg-lite-runtime-implementation-contract.md) remains CLOSED. The [FVS-1 Implementation Contract](../architecture/spg-fvs-1-implementation-contract.md) is ADMITTED, F3-D is CLOSED, and FVS-1 is authorized for controlled implementation. S1 through S5 remain **CLOSED / PASS**. S6-C2 Authorization #4 created one immutable generation-1 Attempt whose Executor transport failed before Provider binding; Provider Outcome remains UNKNOWN, Production Reality remains NONE, and the PWU remains PROPOSED. S6-C2-R1, S6-C2-R2, S6-C2-R3, S6-C2-R4-A, and S6-C2-R4-B are **CLOSED / PASS**. The Windows S6-C2-R4-C full-regression Attempt remains **INTERRUPTED — FINAL RESULT UNKNOWN / NOT RETAINED**. Complete R4 qualification/execution is **DEFERRED_BY_MVP**, with the historical Recovery Barrier preserved.

[MVP Scope Calibration and Phase-2 Hardening Backlog](mvp-scope-calibration.md) is the current delivery-priority authority. The governed production and Reality-driven Plan Steering core is **CLOSED / PASS** after Dogfood #9 machine-loop proof and Dogfood #10 Human-operated acceptance. [WIC-1 Work Interaction Closed-loop Refinement](../architecture/work-interaction-closed-loop-refinement.md) is **DEFINED / ADMITTED** and Slices 1–4 are **IMPLEMENTED / PASS**, closing the bounded WIC Core. The Watt Product MVP remains **NOT CLOSED** pending separately governed Human WIC Dogfood and closure reassessment. Deployment readiness and Linux promotion remain later separately admitted work.

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
| MVP-SCOPE-1 — Architecture Scope Calibration & Phase-2 Hardening Backlog | ADMITTED — CURRENT DEVELOPMENT PRIORITY |
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
| S6 — Real Codex Dogfood & FVS Closure | CLOSED / PASS — HISTORICAL DEFERRED R4 BARRIER PRESERVED |
| S6-B1 — Real Codex SDK Host Integration Spike | CLOSED / PARTIAL |
| S6-B1-R — Provider Terminal & Identity Correlation Spike | PARTIAL — LIFECYCLE CAPABILITY PROVEN / DURABLE REAL EVIDENCE INCOMPLETE |
| S6-B1-R2 — Durable Provider Evidence Capture Hardening | CLOSED / PASS |
| S6-B2 — Dedicated Executor & Real Provider Boundary | CLOSED / PASS |
| S6-B2-A — Dedicated Executor Boundary Deterministic Spike | CLOSED / PASS |
| S6-B2-B1 — Codex Adapter Binding & Authentication Boundary Preflight | CLOSED / PASS |
| S6-B2-B2 Historical Real Probe — Single Real Codex Through Dedicated Executor Boundary | COMPLETE / PARTIAL |
| S6-C — Real Governed Dogfood Loop | CLOSED / PASS — DOGFOOD #9/#10 |
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
| Reality-driven Plan Steering MVP | CLOSED / PASS — 1C THROUGH 1L |
| Long-lived Motive Dogfood #9 | PASS — COMPLETE MACHINE-SIDE PRODUCTION LOOP |
| Long-lived Motive Dogfood #10 | PASS — HUMAN-OPERATED END-TO-END ACCEPTANCE |
| Governed Production + Plan Steering Core | CLOSED / PASS — HISTORICAL MVP CORE CLOSURE SCOPE |
| WIC-1 Work Interaction Architecture | DEFINED / ADMITTED — SLICES 1–4 IMPLEMENTED / PASS; CORE CLOSED / PASS |
| Watt Product MVP | NOT CLOSED — HUMAN WIC DOGFOOD AND CLOSURE REASSESSMENT REMAIN |

S6-C2-HR1R, S6-C2-HR1, and S6-C2-DB1 remain CLOSED / PASS historical prerequisites. Authorization #4 subsequently created the first governed dogfood Attempt and exposed a Windows parent/child encoding mismatch before Provider binding. R1 persisted the admitted `UNKNOWN / REOBSERVE` Recovery Assessment with an active barrier. R2 replaces locale-dependent text transport with an explicit UTF-8/strict bytes wire for request, response, and diagnostic streams. Its 15 evidence obligations comprise 14 executable UTF8 pytest functions plus one external production Runtime immutability assertion. Synthetic R2 tests pass 14/14, affected B2-A/B2-B1 pass 30/30, and HOST tests pass 18/18. The serial full regression collected 462 tests, selected and passed 460, failed 0, skipped 0, and deselected two real Provider tests in 5440.85 seconds; the production Runtime snapshot remained identical. Provider Threads and Turns remain zero; the target artifact remains absent.

S5 is CLOSED / PASS and its generic recovery model remains unchanged. S6-B1 is CLOSED / PARTIAL and no additional S6-B1 probe is authorized. The historical B2-B2 probe remains COMPLETE / PARTIAL with `Provider SUCCESS + Production Reality NONE`. S6-C2-R3 confirmed that retrying the old Source Baseline cannot lawfully integrate and classified the gap as `NARROW PRODUCTION-LINEAGE RECOVERY CAPABILITY REQUIRED`.

S6-C2-R4-A admits the Verified Maintenance Baseline & Production-Lineage Recovery contract. R4-B is CLOSED / PASS after Architecture Lead Reality Review and implements its generic typed capability, one immutable maintenance admission/resolution representation, read-only Git qualification, exact evidence and Authority fingerprints, Baseline pointer CAS, old-lineage `SUPERSEDED` terminal states, new Run/Plan/PWU admission, atomic rollback, idempotency, and concurrency. MR-01 through MR-34 focused evidence passes 23/23; unique affected regression cases pass 175/175; persistence foundation passes 6/6. The production Runtime remains byte/fact identical at Alembic `20260829_12`, with no real recovery or Provider execution. The Windows R4-C regression was interrupted at the last observed 59% progress with no known failure but no terminal result; no checkpoint was created. Complete R4 qualification, R4-D, and real maintenance recovery are DEFERRED_BY_MVP.

The Windows spg_runtime at Alembic 20260829_12 is archived as historical Dogfood evidence and is not the active Runtime to be continued or migrated to Linux. Backup C:\Users\yuchunbo\Documents\SPG-backups\spg_runtime_windows_bootstrap_20260902T061522Z.dump has SHA-256 64ebae40cbea8589f3b1c988422329d4f52e9b5200729ca67c19f31c1a0045b0 and passed restore-list validation. The next target is a usable local Docker MVP. Linux is the later deployment and promotion target for that completed MVP, not a reason to postpone the product surface. Real maintenance recovery remains unexecuted, the old lineage is not superseded, no new lineage exists, and the historical Recovery Barrier remains active.

## Immediate MVP Delivery Sequence

The detailed A/B/C classification, guardrails, verification levels, and Phase-2 triggers are authoritative in [MVP Scope Calibration and Phase-2 Hardening Backlog](mvp-scope-calibration.md). The shortest governed delivery path is:

1. single-project governed task application flow;
2. minimal HTTP API;
3. functional Web UI;
4. local Docker product integration;
5. one real local end-to-end task;
6. governed Work Interaction Core implementation and Human validation;
7. Watt Product MVP closure reassessment and promotion validation;
8. Linux deployment and promotion validation;
9. systematic self-dogfood;
10. evidence-triggered Phase-2 hardening.

The Stage 0–3 model below remains the long-term maturity model; it does not override this immediate delivery order.

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

For FVS-1, the original S1-A/S1-B foundation established the Python Modular Monolith, CLI-first startup, typed settings, PostgreSQL, SQLAlchemy, Alembic, and tests. Subsequent S1-C through S5 slices implemented the bounded Runtime, execution/observation, Completion/Verification, Candidate governance, Repository Integration, Runtime Commit, and recovery foundations. The CLI remains a development/operator surface; a functional Web UI is mandatory for the usable MVP product.

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
