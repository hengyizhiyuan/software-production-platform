# SPG State Foundation Closure and Human–Machine Governance

- **Record date:** 2026-08-26
- **Status:** A. State Foundation — CLOSED; A1 / A2 — CLOSED; A3 Closure Review — PASSED
- **Governing architecture:** [Architecture Baseline v0.1](system-architecture-baseline-v0.1.md) and [SPG Lite domain / contract baseline](spg-lite-domain-contract-baseline.md)
- **Review and agenda:** [Runtime Findings Review](spg-runtime-findings-review.md)
- **Scope:** Confirmed logical architecture semantics; not an implementation specification or a new Architecture Baseline

This document preserves the supplied A closure conclusions and remains governed by Architecture Baseline **v0.1**. The subsequent [B Reconciliation & Recovery](spg-reconciliation-recovery.md), [C Completion & Trust](spg-completion-trust.md), and [D Side-effect Governance](spg-side-effect-governance.md) layers are CLOSED. The [Final Closure and Readiness Review](spg-runtime-architecture-readiness.md) is PASSED; Runtime Architecture Refinement is CLOSED and Runtime Architecture Readiness is PASS.

## 1. Confirmed Logical State Architecture

```text
Trusted Production Baseline
        │
        ▼
Working Production State
        ├── Plan Revision
        ├── Production Work Units
        ├── Execution Attempts
        ├── Work Product Artifacts
        ├── Production Issues
        └── State Transitions
        │
        ▼
Baseline Candidate
        ├── Commit Eligibility
        ├── Authority Decision
        └── Commit
        │
        ▼
New Trusted Production Baseline
```

This is a logical state model, not a database schema or physical-service topology. Referencing an artifact, issue, evidence, or decision here does not transfer its domain ownership or freeze its detailed model.

## 2. Trusted Production Baseline and Working Production State

### Trusted Production Baseline

> Trusted Production Baseline is an immutable reference set representing the currently accepted and trusted software production reality at a specific point in time.

It may reference Decision / Intent baselines, Architecture / Design Artifact revisions, Contract revisions, code and documentation revisions, configuration, Verification / Assurance references, and Human Decision Records.

The Baseline conceptually references authoritative artifacts rather than copying all artifact content. **Trusted Production Baselines are immutable:** a change creates a new Baseline, not a mutation of an existing one.

### Working Production State

> Working Production State represents governed production activity attempting to transform one Trusted Production Baseline into a possible next Trusted Production Baseline.

Its identity remains stable while its current projection evolves. Its history must be preserved.

**Trusted Production Reality ≠ Working Production Reality.** Physically existing code or artifacts in Working Production State do not automatically become Trusted Production Reality.

## 3. Plan Revision and Executable PWU Stability

A material change to executable production semantics creates a new **Production Plan Revision**. Material changes include:

- Scope.
- Dependencies.
- Execution path.
- Required capability.
- Expected output.
- Completion conditions.
- Verification obligations.
- Authority / risk boundary.

Non-semantic annotations and presentation-only changes do not necessarily require a new Plan Revision. Every executable PWU binds to an explicit **source Baseline and Plan Revision**, never an ambiguous reference to “the current plan”.

Once a PWU has been used to create an Execution Attempt, its executable semantics must not be silently rewritten. Material changes to production intent require explicit revision, replacement, or supersession rather than mutation of historical executable meaning. The final PWU revision implementation mechanism is **not frozen**.

## 4. Execution Attempt — Confirmed Runtime Concept

> Execution Attempt represents one concrete attempt by a specific Executor / Capability Provider to satisfy a Production Work Unit under a specific production reality.

An attempt conceptually binds to the PWU, Plan Revision, source Baseline, relevant Context, Executor / Capability Provider, and execution result.

Execution Attempts are immutable historical production facts and must not overwrite one another. Later success does not erase earlier failure. The concept supports retry / resume, model/provider decoupling, reliability measurement, production economics, recovery, and auditability; their detailed behavior is not designed here.

Execution Attempt is no longer merely a Candidate Mechanism. No database schema or attempt lifecycle implementation is defined.

## 5. State Transition Journal — Confirmed Foundation Requirement

The State Transition Journal durably records material governance state transitions. Conceptual information may include subject, from state, to state, reason, actor, timestamp, evidence reference, and execution-attempt reference.

**Historical production facts must not be erased merely because the current state changed.**

The requirement is confirmed, not speculative. It does **not** imply full Event Sourcing. SPG Lite may maintain current-state fields for efficient querying while preserving transition history. These are logical requirements, not a journal schema or persistence protocol.

## 6. Production State Projection — Confirmed Core Responsibility

> Production State Projection turns persisted production facts into a current consumable view of production reality.

Potential consumers include Production Planner, Human Governor, Dashboard / UI, Governance Runtime, and future Assurance / Context integrations.

```text
Transition / Production Facts
        ↓
Production State Projection
        ↓
Current State View
```

The Projection is **not** the final production authority. It may be rebuilt from authoritative production facts. This responsibility does not require an event-sourced architecture or transfer SPG state ownership to ECF.

## 7. Baseline Candidate

**Baseline Candidate** replaces the earlier working term **Integration Candidate**.

> A Baseline Candidate is a sealed and exact production snapshot proposed to become the next Trusted Production Baseline.

It may reference:

- Source Trusted Baseline.
- Production Plan Revision.
- Work Product Artifacts.
- Design / Documentation artifacts.
- Verification / Assurance references.
- Lineage updates.
- Relevant Human Decision Records.

Commit and Acceptance target an **exact Baseline Candidate revision**. Once sealed for acceptance, materially changing its contents creates a new candidate revision. Prior acceptance must not silently authorize the changed candidate.

The logical concept is confirmed. Its database schema and full lifecycle are not defined.

## 8. Commit Semantics and Current Trusted Baseline Authority

### Three distinct responsibilities

| Concept | Question |
|---|---|
| Commit Eligibility | Is this exact Baseline Candidate structurally and governance-wise eligible to become a Trusted Production Baseline? |
| Commit Authorization | Has the required Authority / Policy authorized this exact candidate? |
| Commit Execution | Does the Production Governance Runtime officially make this candidate the new Trusted Production Baseline? |

Eligibility → Authorization → Execution must not be collapsed into one concept. Eligibility does not grant authority, and authorization alone does not perform the Commit.

### Current Trusted Baseline Pointer

A unique logical authority must answer: **Which Trusted Production Baseline currently represents authoritative production reality?**

The working term **Current Trusted Baseline Pointer** names this authority concept, not a required database field. Only successful Commit changes the Current Trusted Baseline authority.

Commit must validate its expected source Baseline:

| Expected current | Actual current | Source-baseline check |
|---|---|---|
| B37 | B37 | Allows Commit of B38, subject to eligibility and authorization |
| B37 | B39 | Rejects Commit of B38 |

This is the State Foundation for later stale-work and concurrency handling; it does not select a locking, transaction, or recovery protocol.

### Commit Failure Boundary

Artifact preparation and authoritative Baseline switching are distinct:

```text
Prepare immutable artifact references
        ↓
Create prepared Baseline Candidate / Baseline record
        ↓
Authoritative Baseline switch
```

- Failure **before** the authoritative switch leaves the previous Trusted Production Baseline authoritative.
- Failure **after** the authoritative switch does not undo the committed Trusted Baseline merely because UI, cache, dashboard, derived projection, or follow-up synchronization updates fail.

### Authority Before Convenience

Authoritative production reality is determined by governance authority state, not UI state, cache state, progress display, or the success of every derived projection.

These failure boundaries do not introduce distributed transactions or Event Sourcing. The subsequent [B closure](spg-reconciliation-recovery.md) defines logical recovery semantics on this foundation; concrete implementation mechanisms remain unselected.

## 9. Git / Production Reality Boundary

Git/code reality and Trusted Production Reality are related but not identical. Git remains authoritative for code revision and history. SPG's Trusted Production Baseline is a higher-level governed composition referencing Git revision, Design revision, Contract revision, Documentation revision, Verification / Assurance references, and Human authority records.

SPG does not redefine Git ownership or become the authoritative content store for these artifacts. A new Trusted Production Baseline is a new production-reality reference set, **not** a new version of this repository's Architecture Baseline.

## 10. SPG Core Logical Responsibility Model

The former Architecture Hypothesis is now a **confirmed logical responsibility decomposition only**:

```text
SPG Core

Production Planner
        ↓
Production Governance Runtime
        ↓
Production State Projection
```

| Logical responsibility | Question and responsibility |
|---|---|
| Production Planner | How should production proceed? Owns production planning and adaptive plan evolution. |
| Production Governance Runtime | What production transitions are allowed, what actually happened, and what authoritative state transitions may occur? Validates, admits, and performs governed transitions. |
| Production State Projection | What is the current understandable production reality? Builds consumable views from recorded facts. |

These are not separate deployable services, microservices, or required runtime modules.

### Production Governance Runtime as Logical Transition Authority

**Production Governance Runtime is the only logical authority through which authoritative SPG production-state transitions occur.**

| Participant | Contribution to governed transitions |
|---|---|
| Production Planner | Proposes plans / production changes |
| Executor | Reports execution facts and produced artifacts |
| Verification / Guardian | Reports verification / assurance facts |
| Human Governor | Issues authority decisions |
| Production Governance Runtime | Validates, admits, and performs governed state transitions |

Components do not directly mutate authoritative production reality. Runtime owns governed state-transition semantics, not business decision intelligence, artifact content, Assurance Truth, or Human Authority. Admission of reported facts does not transfer their domain ownership.

## 11. Human–Machine Governance Positioning

### Human Authority Does Not Imply Runtime Bypass

> Human participants may possess higher-level authority over intent, direction, constraints, risk acceptance and final production acceptance, but human authority does not grant unrestricted privilege to bypass production consistency, lineage, state-transition or commit rules.

Human authority is expressed through governed goal / direction decisions, constraint decisions, exception decisions, risk acceptance, and acceptance of an exact Baseline Candidate. Production Governance Runtime determines how those authorized decisions may consistently change production reality.

### Human Agency First Clarification

Human Agency First does not mean the human is an unrestricted production superuser.

Humans retain meaningful authority over intent, direction, organizational constraints, risk ownership, high-impact exceptions, and final acceptance where policy requires it. They do not directly mutate authoritative production state outside governance rules. Strategic judgment, accountability, and acceptance authority are not weakened by the transition boundary.

### Governed Participant Principle

Human, AI, Executor, Guardian, and other production actors are all governed participants. Each actor has Responsibility, Authority, Capability, Context, and a Policy Boundary.

> Equal submission to production governance does not imply equal responsibility or equal authority.

Human and Machine **do not have identical authority**. Their distinction is reflected through assigned responsibilities and authority, not an exemption from production governance.

- Humans retain governance authority where human judgment and accountability matter.
- AI / machines receive operational autonomy where policy permits.
- Neither may silently bypass authoritative state-transition rules.

## 12. PWU Acceptance Semantic Correction

Individual Human Final Acceptance is **not mandatory by default for every PWU**.

| Level | Governing question |
|---|---|
| PWU | Has this work unit satisfied its production obligations? Working semantic term: **Satisfied**. |
| Baseline Candidate | Should this exact set of production changes become Trusted Production Reality? Primary target of Human / Policy Final Acceptance. |

```text
PWU Produced
        ↓
Verified / Qualified
        ↓
Satisfied
        │
        ▼
Baseline Candidate
        ↓
Authority Acceptance
        ↓
Commit
        ↓
Trusted Production Baseline
```

This is a semantic distinction, not a complete PWU state machine or frozen enum. The subsequent [C closure](spg-completion-trust.md) confirms layered Completion, Produced / Satisfied, PWU and Plan Completion Contracts, and Trusted Completion while deferring physical lifecycle representation.

**Integrated** is derived lineage/integration state associated with artifacts/PWUs included in a committed Baseline, not a mandatory primary PWU terminal state.

## 13. State Foundation Invariants — CLOSED

1. Trusted Production Baseline is immutable.
2. Working Production State and Trusted Production State are explicitly separated.
3. Working State never silently becomes Trusted State.
4. Every executable PWU binds to an explicit source Baseline and Plan Revision.
5. Material Plan changes create new Plan Revisions.
6. Executable PWU semantics cannot be silently rewritten after execution has begun.
7. Every concrete execution is represented by an immutable Execution Attempt.
8. Material governance transitions are durably recorded.
9. Current Production State is a Projection of recorded production reality, not its sole authority.
10. Commit operates on an exact sealed Baseline Candidate.
11. Human / AI / Executor / Guardian provide decisions, facts, or proposals; none directly mutate authoritative production reality.
12. Production Governance Runtime is the logical transition authority.
13. Human Authority does not imply Runtime bypass privilege.
14. Final production acceptance targets an exact Baseline Candidate rather than generic intent or individual PWUs by default.
15. Only successful Commit changes the Current Trusted Baseline authority.
16. Commit validates its expected source Baseline.
17. Failure before authoritative Baseline switch leaves the previous Trusted Baseline authoritative.
18. Failure after authoritative Baseline switch does not revert the Baseline merely because derived projections, caches, or follow-up synchronization fail.
19. Historical production facts are preserved rather than overwritten.
20. Git/code reality and Trusted Production Reality are related but not identical concepts.

## 14. MVP Complexity and Ownership Boundary

These confirmed semantics do **not** require SPG Lite to implement Event Sourcing, distributed transactions, a distributed state store, a complex workflow engine, a graph database, distributed locking, Production State Branching, or microservice decomposition.

SPG Lite may initially express them through ordinary persistent storage, explicit records / revisions, transition history, Git references, and simple controlled commit logic. This is a permitted low-complexity direction, not a selected schema, API, or implementation design.

> Architecture reserves future; product does not consume future.

Ownership remains unchanged:

- Decision Intelligence Domain owns decision semantics; YiJue remains an independent Consumer Product / possible Provider, not an SPG dependency.
- SPG owns production planning and governance state; its Runtime is transition authority, not business decision authority.
- Artifact producers retain content ownership; Git retains code history.
- Guardian retains Assurance Evidence, Findings, Gates, and qualification authority.
- ECF retains canonical Context / Context Projection authority, not SPG production-state authority.
- Human Governance retains strategic, risk, exception, and applicable final-acceptance authority.

Production Issue representation and Design Artifact taxonomy refinement remain unresolved. The subsequent [B closure](spg-reconciliation-recovery.md) confirms Lease and fencing as logical recovery semantics only. The [C closure](spg-completion-trust.md) confirms PWU / Plan Completion Contract and Output Obligation Manifest semantics while deferring schema, DSL, and physical representation. References to issues or design revisions do not freeze outstanding models. No new Feature ID, code, runtime module, schema, API, or MVP implementation commitment is introduced.

## 15. Current Architecture Workflow and Next Valid Step

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

The subsequently admitted [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) is CLOSED with Coding Readiness PASS. The [FVS-1 Contract](spg-fvs-1-implementation-contract.md) records F3-D CLOSED. S1-B implements generic persistence mechanics but no Runtime state object, transition, Baseline, Attempt, Transition History domain record, or invariant path; those remain for later explicitly authorized slices.

This document preserves A's closed semantics and all 20 invariants; its workflow view is synchronized through Coding Readiness. The original discovery scope remains frozen. This A-closure record did not itself perform implementation design or coding.
