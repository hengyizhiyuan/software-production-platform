# SPG Reconciliation & Recovery Closure

- **Record date:** 2026-08-26
- **Status:** B. Reconciliation & Recovery — CLOSED; B1 / B2 / B3 — CLOSED; B4 Recovery Closure — PASSED
- **Governing architecture:** [Architecture Baseline v0.1](system-architecture-baseline-v0.1.md), [SPG Lite baseline](spg-lite-domain-contract-baseline.md), and [State Foundation Closure](spg-state-foundation.md)
- **Review agenda:** [Runtime Findings Review](spg-runtime-findings-review.md)
- **Scope:** Confirmed logical Runtime semantics and architecture principles, not implementation mechanisms

This document records the supplied B1 / B2 / B3 review conclusions and B4 PASSED closure result. It does not claim newly executed Runtime tests or a working recovery implementation. A remains CLOSED. Architecture Baseline remains **v0.1**.

| Classification | Meaning |
|---|---|
| Confirmed architecture principle | A constraint on future designs and governed behavior |
| Confirmed Runtime semantic | Accepted logical meaning, identity, validity, or authority rule; not an API, schema, or frozen storage representation |
| Future verification requirement | An obligation to verify an invariant or boundary later; not a test implemented here |
| Benchmark candidate | A proposed future executable/evaluated scenario; not a completed benchmark |
| Implementation mechanism | A concrete technical realization; none is selected by this closure |

The subsequent [C Completion & Trust](spg-completion-trust.md) and [D Side-effect Governance](spg-side-effect-governance.md) layers are CLOSED. D reuses B's reconciliation semantics for External Reality Divergence. The [Final Closure and Readiness Review](spg-runtime-architecture-readiness.md) is PASSED; Runtime Architecture Refinement is CLOSED and Runtime Architecture Readiness is PASS.

## 1. B1 — Divergence & Recovery Semantics: CLOSED

### Failure and Divergence

**Failure ≠ Divergence.** Failure means a particular operation did not complete as expected. Divergence means current production reality no longer conforms to the governed production path or assumptions.

An Execution Attempt may have both:

```text
Execution Result:    SUCCESS
Production Validity: STALE
```

**Execution success does not establish current production validity.** Validity and execution outcome must not be collapsed into one judgment.

### Divergence Classification

**Classify before recover.** The following categories are logical distinctions, not a database enum or mandatory routing algorithm.

| Divergence category | Meaning | Typical recovery direction |
|---|---|---|
| Execution Interruption | Intent and plan may remain valid, but a particular Attempt was interrupted | Resume / Retry |
| Production Defect | Output exists but does not satisfy required production obligations | Rework |
| Production Assumption Invalidated | Assumptions underlying the production path are no longer valid | Reconcile / Replan |
| Production Reality Diverged | Reality used by active work differs materially from current Trusted Production Reality | Revalidate / Reconcile / Supersede |
| Governance Intent Changed | Authority-owned intent, scope, constraints, or priorities changed | Cancel / Supersede / Replan / Authority escalation |

### Recovery Scope

**Recover at the lowest sufficient level.** The conceptual escalation ladder is:

```text
Resume
  ↓
Retry
  ↓
Rework
  ↓
Reconcile
  ↓
Replan
  ↓
Human / Decision Authority Escalation
```

This is **not a mandatory sequential workflow**. Recovery scope expands only when a narrower mechanism cannot restore coherent governed production state. An unsafe or inapplicable lower-level action must not be attempted merely to follow the ladder.

**Preserve the maximum amount of still-valid production work.** A local divergence does not by itself justify restarting the entire Production Plan.

## 2. B2 — Execution Recovery: CLOSED

### Observation Loss

**Loss of observation does not prove execution failure.** A timeout or lost connection may mean:

- The Executor failed.
- The Executor remains active.
- Execution completed but result delivery failed.
- Artifacts were partially produced.
- External side effects occurred.

Unknown execution reality must be represented explicitly rather than guessed. The subsequent [D closure](spg-side-effect-governance.md) confirms Unknown External Reality, stable Effect Operation Identity, observation, and reconciliation without changing this B principle.

### Resume and Retry

**Resume** continues the same Execution Attempt and preserves its identity. It requires sufficient continuity evidence, potentially including a valid continuation/checkpoint, the same execution identity, compatible Baseline / Context, and no newer conflicting Attempt.

**Retry** creates a new Execution Attempt for the same PWU. It must not rewrite or reset historical Attempt identity or facts:

```text
PWU-004
  EA-17 — INTERRUPTED
      ↓
  EA-18 — retry_of = EA-17
```

**Retry creates new production history rather than rewriting old history.** The example illustrates identity and lineage, not field names for a selected schema.

### Retry Under Uncertainty

**Never retry into unresolved execution uncertainty unless isolation and fencing make concurrent execution safe.** Before creating a new authoritative Attempt, Runtime must determine that the old Attempt is terminated, fenced, isolated, or otherwise unable to corrupt current authoritative work.

This is a safety condition, not a distributed-lock design. A timeout alone does not satisfy it.

### Execution Lease and Fencing

**Execution Lease and execution fencing are confirmed logical recovery semantics**, promoted from the earlier candidate status.

Execution Lease represents temporary execution authority for an Attempt. Lease expiry does **not** prove that the physical Executor stopped. It means Runtime no longer recognizes the Attempt as possessing current execution authority.

A fencing / generation concept must distinguish current authority from expired or superseded authority:

```text
EA-17 — generation = 3
EA-18 — generation = 4

EA-17 returns late:
  execution fact:               recorded as history
  execution authority:         FENCED
  authoritative state mutation: REJECTED
```

Late results remain observed historical facts, but late or zombie execution cannot regain authoritative production rights. Recording a fact does not admit its output into current production reality. No infrastructure-specific fencing primitive, lease store, clock protocol, or locking implementation is selected.

### Attempt Isolation

Different Execution Attempts must be sufficiently isolated so that a zombie or superseded Executor cannot corrupt the current authoritative working state. Rejecting a late result alone is insufficient if the old Executor can still corrupt that state.

Possible **future implementation mechanisms** include Git branches, Git worktrees, isolated workspaces, and sandbox/environment boundaries. No mechanism is frozen.

Parallel Attempts for the same PWU must be an explicit production strategy, not accidental duplicate execution.

## 3. B3 — Reconciliation & Replanning: CLOSED

### Production Validity Basis

Executable production work is evaluated against an explicit **Production Validity Basis**, potentially including:

- Source Trusted Baseline.
- Production Plan Revision.
- Context Revision.
- Contract Revision.
- Relevant design / architecture assumptions.
- Dependency artifacts.

These references are governance semantics, not merely informational metadata. They determine whether existing work still applies to current production reality.

### Logical Validity States

| Validity | Meaning |
|---|---|
| VALID | Work remains applicable to current production reality |
| REVALIDATION_REQUIRED | A relevant production fact changed and its impact cannot yet be safely determined |
| STALE | Material assumptions or dependencies are no longer valid |

**STALE ≠ FAILED.** A technically successful execution can still be stale. These are logical validity distinctions, not a complete PWU state machine or implementation enum.

### Baseline Advancement and Invalidation Propagation

**Advancing the Trusted Production Baseline triggers impact evaluation, not automatic global invalidation.** A source-Baseline mismatch indicates potentially stale work, not automatically invalid work.

Invalidation propagates through explicit production dependencies. Runtime distinguishes directly invalidated work, indirectly affected work, and unaffected work. It preserves unrelated still-valid work rather than globally restarting production.

### Revalidate, Reconcile, and Replan

| Semantic | Question | Authority boundary |
|---|---|---|
| Revalidate | Does existing work remain valid under the new production reality? | Does not itself change production intent |
| Reconcile | Can existing work adapt to current production reality without changing the authorized production objective? | Preserves authorized objective |
| Replan | Is the current production path no longer suitable for achieving the approved objective? | Changes the path, not silently the authorized destination |

**Replanning may change the path, but must not silently change the authorized destination.** Changes to authority-owned intent, scope, constraints, or risk decisions require the appropriate Human / Decision Authority.

### Plan Revision Carry-forward

A new Production Plan Revision does not discard all prior work. Prior PWUs and artifacts may be carried forward, revalidated, reconciled, or superseded. Material historical semantics and lineage must not be overwritten.

### Cancelled and Superseded

- **Cancelled:** the production activity is no longer required.
- **Superseded:** the underlying objective remains relevant, but a newer production path or Work Unit replaces the particular one.

Superseded work is not failed merely because production reality changed. Cancellation does not erase already committed Trusted Production Reality. The subsequent [D closure](spg-side-effect-governance.md) confirms Compensation as a new governed production action that appends history.

### Baseline Candidate Staleness

Baseline Candidates also require validity checks. If a Candidate expects source Baseline **B37** while the Current Trusted Baseline is **B38**, it may not commit directly.

It must undergo revalidation, reconciliation, supersession, or replanning. This guard does not imply global invalidation of all work associated with B37.

A reconciled Candidate must be represented by a **new exact Candidate revision** rather than mutating the previously accepted snapshot. Prior acceptance of revision N does not authorize revision N+1. The already-closed A Commit Eligibility / Authorization / Execution distinction remains authoritative; no new C Completion model is defined here.

## 4. B4 — Runtime Crash Recovery Closure: PASSED

### Recover Knowledge Before Execution

**Recover knowledge before recovering execution.** Runtime restart first reconstructs trustworthy understanding of current production reality; it must not immediately restart unfinished Executors.

### Recovery Barrier

A **Recovery Barrier** is a logical governance rule during unresolved recovery reconciliation:

- Do not blindly start new authoritative execution.
- Do not Commit under unresolved authority ambiguity.
- Inspect persisted governance state and external execution reality as needed.

The barrier does not require a particular infrastructure primitive or imply that safe observation must stop.

### Recovery Anchor

**Current Trusted Baseline Authority is the primary recovery anchor.** Recovery reconstructs understanding from:

- Current Trusted Baseline.
- Working Production States.
- Plan Revisions.
- PWUs.
- Execution Attempts.
- State Transition Journal.
- Baseline Candidates.
- Known artifact reality.

Derived projections, dashboards, and caches are not recovery authority. The A closure's before/after authoritative Baseline switch failure boundaries remain in force.

### Unreconciled Production Reality

> Unreconciled Production Reality represents observed engineering reality that cannot yet be safely associated with authoritative production state.

Examples include:

- An artifact exists but its completion record is missing.
- An Attempt reports success but an expected artifact is missing.
- Git changes exist without provable PWU / Attempt lineage.
- A fenced Executor produces late output.

**Existing does not imply admitted.** Unknown or orphan reality must be represented explicitly and must not silently become Trusted Production Reality.

### Recovery Idempotence

**Recovery Reconciliation must be idempotent.** Repeated recovery over the same known production facts should converge toward the same governance state, not repeatedly create retries, generations, duplicate Production Issues, or duplicate Plan Revisions.

### Recovery Responsibility Boundary

**Recovery restores governance control; governed production activity restores the product.** Recovery Runtime may observe, classify, reconcile governance state, fence invalid execution, and select an allowed recovery path.

It must not silently finish incomplete product work outside a PWU / Attempt / Replan process. Authority may change governance decisions but cannot rewrite observed production facts.

### Recovery Completion

Recovery completes when:

- The authoritative Trusted Baseline is known.
- Working State is classified.
- Active / unknown Attempts have known governance status or are safely blocked/fenced.
- Baseline Candidates are classified.
- Unreconciled reality is explicitly represented.
- Production State Projection is coherent.
- No unresolved authority ambiguity prevents safe continuation.

Recovery completion does **not** require all production work to be complete. It means: **the system reliably knows where production currently stands**. The subsequent [C closure](spg-completion-trust.md) separately defines Production Completion and Trusted Completion; this B-layer meaning remains unchanged.

## 5. Reconciliation & Recovery Principles — CLOSED

The following 20 principles are preserved as the B-level closure set. Future verification references may identify them by this section's stable list number.

1. Classify before recover.
2. Failure and Divergence are distinct.
3. Execution success does not imply current production validity.
4. Recover at the lowest sufficient level.
5. Preserve maximum valid work.
6. Escalate recovery scope only when required to restore consistency.
7. Observation loss does not imply execution failure.
8. Resume preserves Attempt identity; Retry creates new history.
9. Never retry into unresolved uncertainty without safe fencing/isolation.
10. Late or zombie execution cannot regain authoritative production rights.
11. Baseline advancement triggers impact evaluation, not global invalidation.
12. Revalidate, Reconcile and Replan are distinct.
13. Replanning may change the path but not silently change the authorized destination.
14. Cancelled and Superseded have different semantics.
15. Recover knowledge before recovering execution.
16. Recovery restores governance control rather than product correctness.
17. Recovery must be idempotent.
18. Unreconciled production reality must not be silently admitted.
19. Recovery completes when production authority/state becomes coherent again, not when all production work is complete.
20. Authority may change governance decisions but cannot rewrite observed production facts.

## 6. Distributed Governance and Capability Boundaries

The [architecture principles](architecture-principles.md) record **No Actor Owns Production Truth Alone**, **Distributed Responsibility, Governed Adjudication**, **Provider Consolidation Does Not Collapse Authority Boundaries**, and **Replaceable Intelligence, Durable Governance**.

Runtime is logical transition authority, not the creator or sole owner of all truth. It adjudicates authoritative state changes using domain-owned facts, artifacts, evidence, contracts, policy, authority decisions, and transition rules. This is not majority voting. Human intent, strategic judgment, risk ownership, and applicable final acceptance remain meaningful and cannot bypass production consistency or rewrite observed facts.

Ownership remains unchanged: Decision Intelligence owns decision semantics; YiJue remains an independent Product / possible Provider; SPG owns production governance; producers own artifact content; Git owns code history; Guardian owns Assurance Truth; ECF owns governed Context; Human Governance owns authority decisions. Provider consolidation does not consolidate these logical authority domains.

## 7. Verification and Implementation Boundary

The [Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md) records future executable verification requirements, benchmark candidates, and the reported real incident-derived regression candidate. None is implemented or executed by this documentation task.

This closure does not implement production/runtime code, tests, benchmarks, schemas, APIs, Event Sourcing, distributed locks, Guardian, ECF, Semantic Conflict Engine, model routing, or model-specific autonomy levels. It does not change physical service topology or expand SPG Lite MVP. Execution Lease, fencing, isolation, validity, and Recovery Barrier are confirmed semantics; their concrete technical realization remains unselected.

## 8. Current Architecture Workflow

| Item | Status |
|---|---|
| Runtime Architecture Refinement | CLOSED |
| A. State Foundation | CLOSED |
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

The subsequently admitted [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) is CLOSED with Coding Readiness PASS. The [FVS-1 Contract](spg-fvs-1-implementation-contract.md) records F3-D CLOSED, but S1-A implements no recovery or Repository Integration behavior. The 12-area discovery scope remains FROZEN and reopens only on new material evidence.
