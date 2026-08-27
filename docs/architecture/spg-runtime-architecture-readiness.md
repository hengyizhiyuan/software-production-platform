# SPG Runtime Architecture Final Closure and Readiness

## 1. Purpose and evidence boundary

This document is the authoritative final closure record for **Runtime Architecture Refinement** under Architecture Baseline **v0.1**. It consolidates the reviewed semantics from:

- [A. State Foundation](spg-state-foundation.md);
- [B. Reconciliation & Recovery](spg-reconciliation-recovery.md);
- [C. Completion & Trust](spg-completion-trust.md);
- [D. Side-effect Governance](spg-side-effect-governance.md).

The final cross-layer review confirms architectural readiness. It does not claim implemented Runtime behavior, executed Runtime tests, physical persistence design, APIs, service topology, full Guardian, full ECF, or production completion.

## 2. Final architecture workflow state

| Architecture work | Status |
| --- | --- |
| Runtime Architecture Refinement | **CLOSED** |
| A. State Foundation | **CLOSED** |
| B. Reconciliation & Recovery | **CLOSED** |
| C. Completion & Trust | **CLOSED** |
| D. Side-effect Governance | **CLOSED** |
| Final Closure / Architecture Readiness Review | **PASSED** |
| Runtime Architecture Readiness | **PASS** |
| Architecture Baseline | **v0.1** |

The refinement stage is no longer an active design agenda item. A/B/C/D remain closed and are not reopened by this review.

## 3. Runtime Architecture Readiness — PASS

> The Runtime's core state, recovery, completion/trust, and external side-effect governance semantics are sufficiently stable to enter SPG Lite implementation-contract / Runtime MVP design without depending on unresolved major Runtime architecture questions.

`Architecture Ready` does not mean:

- all future architecture questions are solved;
- no Reality Check may change the design;
- all deferred capabilities should now be implemented;
- production implementation is already complete.

It means:

> Enough architecture is stable to implement the next governed iteration safely.

The subsequently admitted [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) closes the next governed design stage with Coding Readiness PASS. The current next governed step is:

> **Architecture Lead Reality Review → reconcile the existing Pre-Implementation Repository Reality Check against the newly admitted Source of Truth → authorize the first controlled vertical implementation slice if no blocker remains.**

No specific implementation slice is authorized by either closure record.

## 4. Coherent A/B/C/D Runtime Governance Model

The four refinement areas form one Runtime Governance Model, not four independent systems.

### A. State Foundation

Answers:

> What production reality exists, and which reality is authoritative?

Its primary semantics include Trusted Production Baseline, Working Production State, Plan Revision, Production Work Unit, Execution Attempt, State Transition Journal, Production State Projection, Baseline Candidate, and Commit authority semantics.

### B. Reconciliation & Recovery

Answers:

> What happens when execution or production reality diverges?

Its primary semantics include Failure versus Divergence, Production Issue, Resume / Retry / Rework, fencing and isolation, Production Validity Basis, Revalidate / Reconcile / Replan, stale work, Recovery Barrier, recovering knowledge before execution, and idempotent recovery.

### C. Completion & Trust

Answers:

> When is production complete, sufficiently evidenced, and eligible to become Trusted Production Reality?

Its primary semantics include Output Obligation Manifest, Completion Contract, Produced versus Satisfied, Verification Basis, Evidence scope / provenance / freshness, Commit Eligibility, Commit Authorization, Trusted Completion, authority freshness, Risk Acceptance / Exception, and exact Baseline Candidate acceptance.

### D. Side-effect Governance

Answers:

> How may governed production safely change shared or external reality?

Its primary semantics include External Side Effect, Side-effect Intent, scoped Authorization / Permit, Effect Operation Identity, external preconditions, Effect fencing, Observed External Reality, Partial / Unknown convergence, External Reality Reconciliation, Compensation, and Governed Integration Atomicity.

### Cross-layer consistency result

**A/B/C/D Semantic Consistency — PASS.**

The final review confirms that:

- Production Validity and Evidence Freshness are distinct and both follow `Validity Is Relational`;
- Attempt Fencing and External Effect Fencing form a continuous Authority boundary;
- External Reality Reconciliation reuses B-level Reconciliation semantics;
- Completion, Evidence, and Authority remain separate;
- Commit Eligibility and Commit Authorization remain separate;
- Side-effect Authorization and Baseline Commit Authorization remain separate;
- Compensation is compatible with immutable history;
- no cross-layer semantic requires rewriting Trusted Baseline history.

## 5. End-to-End Governed Production Flow

```text
Approved Production Intent
↓
Production Planner
↓
Production Plan / Revision
↓
Production Work Units
↓
Context Assembly
↓
Execution Attempt
↓
Work Product Artifacts
↓
Completion Contract Evaluation
↓
Verification / Evidence
↓
Baseline Candidate
↓
Commit Eligibility
↓
Commit Authorization
↓
Trusted Completion
↓
Commit
↓
Trusted Production Baseline
↓
Governed External Effects
↓
Observed External Reality
↓
Convergence / Reconciliation / Compensation
```

Divergence and recovery may occur at any relevant stage without rewriting historical production facts.

**End-to-End Runtime Governance Loop — PASS.**

## 6. Runtime Constitution: Eight Parent Governance Principles

The detailed A/B/C/D invariants are interpreted under these parent principles.

### Principle 1 — Facts Before Claims

> Participant claims do not substitute for observable, traceable production facts.

An Executor report of `SUCCESS` is not PWU completion. An API acknowledgement is not external convergence. A dashboard percentage is not authoritative production state. Governance relies on facts, artifacts, Evidence, and recorded state transitions.

### Principle 2 — Observed Does Not Mean Admitted

> Existing, generated, retrieved, or observed reality does not automatically become admitted Trusted Production Reality.

A generated artifact is not automatically trusted; existing output does not automatically satisfy a PWU; an observed production or external change does not automatically change the Trusted Baseline. Admission requires the governed path.

### Principle 3 — Validity Is Relational

> Validity is a governed relationship between an object and specific production reality, revisions, dependencies, context, policies, and authority conditions.

This applies to Production Work validity, Evidence freshness, Candidate freshness, Authority Decision validity, and Side-effect Permit validity. Avoid permanent labels such as `verified = true forever`, `approved = true forever`, or `valid = true forever`.

### Principle 4 — History Is Appended, Not Rewritten

> New production reality is represented through new governed history rather than rewriting prior material facts.

A Retry creates a new Execution Attempt; a Plan change creates a Revision; a Candidate change creates a Candidate revision; Compensation creates a new External Effect; Risk Acceptance does not erase a Finding; Supersession does not erase old work.

### Principle 5 — Authority Changes Permission, Not Facts

> Authority may change what the system is permitted to do, but it cannot rewrite observed production facts.

Human or automated Authority may change intent, accept risk, authorize an Exception, or authorize an External Effect. It cannot turn a failed test into PASS, erase an observed effect, fabricate completion, or fabricate Evidence.

### Principle 6 — No Actor Owns Production Truth Alone

> No individual Human, AI model, Planner, Executor, Guardian, Context Provider, plugin, or Runtime component unilaterally owns authoritative production truth.

Production truth is composed through facts, artifacts, Evidence, Authority Decisions, policy, Contracts, and governed state transitions. The Production Governance Runtime adjudicates authoritative transitions but does not create every underlying fact. This is not majority voting.

### Principle 7 — Recover Coherence, Not Appearance

> Recovery restores a truthful, consistent, and governable production state rather than merely making dashboards or task statuses appear successful again.

Classify before recovery, recover knowledge before execution, preserve maximum valid work, and keep Unknown or Partial reality explicit until reconciled. Compensation does not pretend history never happened.

### Principle 8 — Replaceable Intelligence, Durable Governance

> Intelligence providers may become stronger, cheaper, specialized, consolidated, or replaceable without redefining fundamental production-governance semantics.

Stronger models may receive larger PWUs, broader safe autonomy, fewer Human interventions, lighter Verification, or different routing. They do not automatically inherit unrestricted transition, self-verification, self-acceptance, or external-effect Authority. Contract, Responsibility, and Authority boundaries remain even when one provider supplies multiple capabilities.

## 7. Implementation Guidance: Preserve Semantic Separability Before Physical Separability

> Distinct architecture semantics must remain distinguishable even when the first implementation represents them using shared physical structures.

Production Validity Basis, Verification Basis, Authority Requirement, and Side-effect Permit need not each require a dedicated database, service, or table. Side-effect Intent, Permit, and Effect Operation may initially coexist in a thin External Effect Record while retaining distinct meanings.

Do not implement one service, class, or table per architecture noun by default. This guidance preserves SPG Lite feasibility and is not a frozen physical design.

## 8. Authority and Ownership Review — PASS

### Human Authority

Human Authority governs Intent, scope, constraints, risk acceptance, Exception decisions, high-impact acceptance, and governance policy as appropriate. It is not an unrestricted Runtime superuser.

> Human Authority Does Not Imply Runtime Bypass.

### Production Planner

Production Planner owns production-path planning, decomposition, adaptive replanning proposals, and Production Plan / Revision semantics. It may change the path within Authority constraints but must not silently redefine the authorized destination.

### Executor

Executor provides execution capability, execution facts, and Work Product production. It does not own PWU Satisfaction, Verification truth, Trusted Completion, Baseline Commit, or unrestricted external-effect Authority.

### Guardian / Verification

Guardian / Verification owns Evidence interpretation, Findings, Qualification, Gate, Assurance Truth, and assurance confidence / coverage semantics. It does not own Product Intent, Production Plan, SPG authoritative transitions, Baseline Commit, or external production orchestration.

### ECF / Context Capability

ECF / Context Capability owns authoritative Engineering Context delivery, Context authority, Context projection, and Context lineage. It does not become Planner, Executor, Guardian, or Production Governance Runtime. SPG Lite may use Context Assembly Lite while preserving the future ECF interface boundary.

### Production Governance Runtime

Production Governance Runtime owns authoritative SPG state-transition decisions, lifecycle governance, transition consistency, recovery coordination, completion-state adjudication, Candidate / Commit governance, and external-effect governance coordination. It does not fabricate execution facts, Evidence, Context truth, or Human Authority decisions.

The Human / Planner / Executor / Guardian / ECF / Runtime ownership model is consistent across A/B/C/D.

## 9. Provider Consolidation Review — PASS

> A single powerful model/provider may supply multiple Production Capabilities without collapsing logical governance boundaries.

Planning, implementation, analysis, and verification outputs from one provider remain subject to their respective Contracts, provenance, responsibilities, policy, and Authority boundaries.

> Provider Consolidation Does Not Collapse Authority Boundaries.

Strategic consequence:

> No single intelligence should be able to capture the production system merely by becoming more capable.

This consequence does not introduce a new Authority mechanism.

## 10. Frozen Runtime Failure Findings Coverage — PASS

Runtime Failure Discovery remains **CLOSED**. The final review found no evidence requiring a new finding beyond the frozen scope. Existing architecture covers:

- unrelated-task `SUCCESS` reports;
- missing expected artifacts;
- execution timeout with unknown actual state;
- duplicate or zombie Executors;
- stale work after Baseline advancement;
- semantic incompatibility without textual Git conflict;
- stale Verification and stale Candidate Acceptance;
- Runtime crash during Commit or active execution;
- duplicate or unknown external-effect results;
- partial external convergence;
- stale external authorization;
- Compensation failure;
- External Reality Divergence.

> Runtime Failure Discovery remains CLOSED unless future implementation, dogfood, or Reality Check produces new evidence requiring reopening.

### Real Codex incident regression candidate

The existing incident remains a future benchmark candidate:

```text
Authorized task: documentation update
Observed Executor work: repository reads only
Expected artifact delta: missing
Executor report: SUCCESS
Reported task identity: unrelated older task
```

Expected governed behavior is to record the Attempt result, detect task-identity mismatch, reject PWU Satisfaction because the output obligation is unsatisfied, keep the Trusted Baseline unchanged, and require recovery or re-execution. The benchmark is not claimed as implemented or executed.

## 11. SPG Lite Feasibility — PASS

> The confirmed Runtime semantics can be implemented initially without heavyweight distributed infrastructure.

A first implementation may use an ordinary backend, relational persistence, Git, a Codex / Executor adapter, simple explicit Contracts, transition history, a thin Verification interface, and a thin External Effect interface.

It does not require Event Sourcing, microservice decomposition, distributed transactions, a graph database, full Guardian, full ECF, or a generalized orchestration platform.

### Core semantics ready for implementation-contract design

The following concepts are sufficiently stable to enter the next implementation-contract stage without freezing a physical schema:

- Trusted Production Baseline;
- Working Production State;
- Production Plan / Revision;
- Production Work Unit;
- Execution Attempt;
- Work Product / Artifact Reference;
- Completion Contract;
- Baseline Candidate;
- Verification / Evidence Reference semantics;
- Production Issue;
- Governance / Human Decision Record;
- External Effect Record semantics;
- Transition History.

No table, API, service, or physical persistence choice is defined here.

## 12. Deferred and Non-first-class Concepts

The following concepts must not be forced into first-class implementation entities solely because architecture discussion named them:

- Production Completion Candidate;
- first-class Effect Group;
- Trust Score;
- full Evidence ontology;
- automatic Materiality engine;
- Production State Platform extraction;
- Policy DSL;
- Capability Marketplace;
- Autonomy Engine;
- universal Side-effect Gateway;
- Compensation Engine;
- Saga framework;
- Semantic Conflict Engine.

Their semantics may be represented initially through simpler structures.

Major capabilities remaining outside SPG Lite MVP unless separately approved include full ECF, full Guardian, independent Production State Platform, Event Sourcing, Production State Branching, complex multi-user / multi-agent production, Capability Marketplace, advanced adaptive model routing, full autonomy, Trust Graph, Trust Score, full Evidence ontology, Policy DSL, complex multi-authority approval, automatic Semantic Conflict Engine, universal Side-effect Gateway, Saga / 2PC / distributed transactions, universal exactly-once infrastructure, automatic Compensation Planner, complete deployment platform, and a generalized production-pattern / Effect Protocol engine.

## 13. Architecture Baseline v0.1

Architecture Baseline remains **v0.1**. Runtime Refinement deepened Runtime semantics without replacing the core architecture:

- the Five Capability Plane model remains valid;
- SPG, Guardian, and ECF ownership remain valid;
- the Decision Intelligence boundary remains valid;
- Human Governance remains valid;
- the MVP boundary remains valid.

A future Baseline revision requires Material Architecture Change supported by implementation / Reality Check evidence or an explicit architecture decision.

## 14. Final Architecture Readiness Gate

| Review dimension | Result |
| --- | --- |
| A/B/C/D semantic consistency | PASS |
| End-to-end Runtime lifecycle | PASS |
| State authority model | PASS |
| Reconciliation / Recovery model | PASS |
| Completion semantics | PASS |
| Verification / Trust semantics | PASS |
| Side-effect safety | PASS |
| Governed Integration Atomicity | PASS |
| Frozen failure-mode coverage | PASS |
| Human Authority consistency | PASS |
| No Actor Owns Production Truth Alone | PASS |
| Guardian boundary | PASS |
| ECF boundary | PASS |
| Decision Intelligence boundary | PASS |
| Model/provider decoupling | PASS |
| Governed Autonomy compatibility | PASS |
| History / lineage / auditability | PASS |
| MVP complexity containment | PASS |
| Core domain semantic stability | PASS |
| Deferred-scope clarity | PASS |
| Architecture Baseline v0.1 compatibility | PASS |

**Runtime Architecture Readiness — PASS.**

## 15. Reality-driven evolution

Readiness moves the project from asking what Runtime should mean to asking for the minimum implementable Contract and design that preserve these semantics. It does not freeze future learning.

```text
Reality / Evidence
↓
Architecture Review
↓
Governed Decision
↓
possible Baseline Revision
```

Implementation, dogfooding, Guardian integration, ECF evolution, and real Runtime evidence may expose Material Architecture Evidence. The Governed AI Engineering Loop must respond to contradictory reality rather than preserve v0.1 mechanically.

## 16. Closure and next mainline transition

Runtime Architecture Refinement is **CLOSED**. Final Closure / Architecture Readiness Review is **PASSED**. Runtime Architecture Readiness is **PASS**. Architecture Baseline remains **v0.1**.

This Runtime Architecture closure did not itself produce an implementation contract. The subsequently admitted [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) now records Implementation Contract / Runtime MVP Design CLOSED and Coding Readiness PASS without changing the Runtime closure or Baseline v0.1.

The exact next valid mainline task is:

> **Architecture Lead Reality Review → reconcile the existing Pre-Implementation Repository Reality Check against the newly admitted Source of Truth → authorize the first controlled vertical implementation slice if no blocker remains.**
