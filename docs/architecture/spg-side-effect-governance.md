# SPG Side-effect Governance Closure

- **Record date:** 2026-08-27
- **Status:** D. Side-effect Governance — CLOSED
- **Sub-review status:** D1 / D2 / D3 — CLOSED; D4 Closure Review — PASSED
- **Governing architecture:** [Architecture Baseline v0.1](system-architecture-baseline-v0.1.md)
- **Prior layers:** [A. State Foundation](spg-state-foundation.md), [B. Reconciliation & Recovery](spg-reconciliation-recovery.md), and [C. Completion & Trust](spg-completion-trust.md)
- **Scope:** Confirmed logical Runtime semantics and governance boundaries; not implementation design

This document records the supplied D1 Side-effect Semantics & Boundary, D2 Side-effect Authority & Execution Safety, D3 Compensation & External Reality reviews, and D4 PASSED closure result. It does not claim implementation or newly executed verification. Architecture Baseline remains **v0.1**.

A/B/C/D are reviewed and documented. The [Final Runtime Architecture Closure and Readiness Review](spg-runtime-architecture-readiness.md) is PASSED; Runtime Architecture Readiness is PASS. This does not claim implemented Runtime behavior or begin coding.

## 1. D1 — External Side-effect Semantics

### External Side Effect — Confirmed Runtime Semantic

> An External Side Effect is a production action that changes state beyond the disposable local execution boundary and whose effects may persist independently of the originating Execution Attempt.

Examples include Git merge or protected-branch mutation, deployment, database migration, production configuration mutation, package publication, cloud-resource mutation, marketplace submission, external notification, external API mutation, and destructive or durable data operations.

An isolated Attempt-workspace mutation is not automatically a material External Side Effect. Side-effect semantics depend on the reality changed, not merely Artifact type or subsystem.

### Distinct realities

```text
Physical Change
!= Authoritative Production Change
!= Observed External Reality
```

An Attempt-local file may physically exist without entering Trusted Production Reality. Infrastructure may change before SPG commits that reality. The Trusted Baseline may advance while an external environment has not converged. These distinctions remain explicit.

### Classification principle

Side-effect governance is driven primarily by repeatability, compensability / reversibility, external durability, and blast radius, not subsystem name alone.

| Logical classification | Meaning |
|---|---|
| Disposable Internal Mutation | Effect remains inside an isolated / disposable working boundary |
| Idempotent / Safely Repeatable Effect | Repeated delivery may safely converge to the same intended external state |
| Reversible / Compensatable Effect | Effect persists, but a governed recovery path exists |
| Irreversible / Externally Durable Effect | Effect cannot be meaningfully erased from history |

This is a logical classification idea, not a frozen taxonomy enum.

## 2. Rollback and Compensation

**Rollback ≠ Compensation.**

Rollback may restore a controlled state to a prior state. Compensation is a **new governed production action** intended to move current external reality from an undesired or divergent state toward an acceptable governed state after an earlier effect occurred.

```text
wrong email sent → send correction
deployment caused severe problem → deploy governed recovery revision
```

Compensation does not erase history.

```text
EO-41 deploy B41
        ↓
EO-42 compensate toward B40-compatible state
```

Both remain immutable historical production facts. Compensation appends history and must not rewrite or delete the original effect record.

## 3. Side-effect Intent, Permit, and Operation Identity

Three logical semantics remain distinct:

| Semantic | Governing question |
|---|---|
| Side-effect Intent | What external reality is intended to change? |
| Side-effect Permit / Authorization | What exact effect is allowed, under what scope and Authority? |
| Effect Operation Identity | What logical external operation is executing, observed, retried, or reconciled? |

SPG Lite may represent them in one physical record. Three persistence entities are not required.

### Declared before effect; observed after effect

```text
Effect Intent
        ↓
Authorization
        ↓
Execution
        ↓
Observation
        ↓
Reconciliation
```

Material effects are governed before execution through explicit Intent and after execution through observed external reality. Runtime cannot depend only on after-the-fact Executor reporting.

## 4. D2 — Side-effect Authority and Execution Safety

### Capability does not imply Authority

> Execution capability does not imply authority to perform a specific External Side Effect.

Technical ability to deploy, migrate, publish, delete, provision, or mutate production infrastructure does not grant production authority.

### Scoped authorization

Every material effect requires scoped authorization against explicit governed Intent. Scope may include action, target, environment, desired state / Artifact revision, originating PWU / Attempt, Candidate revision, production Context, execution generation, validity period, constraints, and blast-radius limit.

This is confirmed semantics, not a generalized authorization engine.

### Least Authority and least blast radius

Permissions constrain action, environment, resource scope, target, quantity / blast radius, Candidate / Artifact revision, and validity.

```text
allowed:
deploy artifact A81 to staging/service-a

not implied:
deploy any artifact to production
```

### Human Authority does not imply Side-effect Runtime bypass

Human Authority may authorize a governed effect but does not bypass Runtime state consistency, provenance, identity, or observation requirements. Authority changes permitted governance conditions; it does not fabricate external facts.

## 5. Side-effect Permit and Fencing

> Side-effect Permit is a scoped, governed grant of authority to perform one specific class of external effect under explicit production conditions.

Conceptual scope may include operation, target, environment, desired Artifact / state, origin PWU / Attempt, Candidate revision, execution generation, Authority source, validity, and constraints.

A permanent first-class Permit entity is not required if SPG Lite preserves equivalent semantics through an External Effect Record.

### Fencing reaches the external-effect boundary

> Fencing is incomplete unless stale execution authority is also denied at the external-effect boundary.

If EA-17 generation 3 is fenced and EA-18 generation 4 becomes current, effect authorization tied to generation 3 loses current Authority. A Zombie Executor cannot retain effect Authority merely because it remains physically active.

### No broad permanent Executor privilege

Governed effects do not assume broad, durable, unrevocable production credentials held directly by Executors. Short-lived credentials, scoped tokens, role assumption, CI/CD credentials, an effect broker, or provider-specific authorization are future implementation options; none is selected here.

## 6. Preconditions and Authorization Freshness

Relevant external preconditions should be validated before execution whenever supported.

```text
Expected external state: B40
Desired external state:  B41
Observed external state: B42
```

Runtime must reconcile rather than blindly execute stale B40 → B41 Intent.

External systems may expose revisions, resource versions, ETags, expected HEAD, schema versions, or conditional APIs. SPG does **not** require universal atomic compare-and-set. Where unavailable, governance relies more on observation, scoped authorization, fencing, reconciliation, stricter Policy, and compensation.

Side-effect Authorization is scoped to the exact governed production reality that justified it. A Permit for BC-41/R2 and Artifact A81 does not authorize BC-41/R3 or A82 after material change.

Side-effect Authorization participates in **Validity Is Relational**.

## 7. Retry and Operation Identity

SPG does not depend on universal exactly-once external execution.

```text
request sent
        ↓
external system executes
        ↓
response lost
```

Safety relies on stable Operation Identity, idempotency where supported, observation, reconciliation, and compensation where necessary.

### Execution Retry versus Effect Delivery / Observation Retry

- **Execution Retry:** creates a new Execution Attempt, such as EA-17 → EA-18.
- **Effect Delivery / Observation Retry:** retries delivery, query, or observation of the same logical Effect Operation, such as retry/query EO-41.

They are distinct. Where provider semantics allow, the same logical Effect Operation preserves stable identity across delivery retries.

Retry eligibility includes unresolved external reality. If an earlier Attempt may have produced a durable effect and that reality cannot be safely observed, fenced, or deduplicated, Runtime must not blindly create an equivalent new external action. It may query, reconcile, block, escalate, or compensate.

## 8. External Effect Lifecycle

External effects do not collapse into a generic SUCCESS / FAILED Boolean.

```text
DECLARED
    ↓
AUTHORIZED
    ↓
DISPATCHED
    ↓
ACKNOWLEDGED
    ↓
OBSERVED
    ↓
CONVERGED
```

Exceptional semantics may include UNKNOWN, PARTIALLY_CONVERGED, DIVERGED, FENCED, and BLOCKED. These are logical states, not frozen database enums.

> External-effect success is established by sufficient observed convergence to governed desired reality, not command or API acknowledgement alone.

A deployment API returning 200 does not prove the desired Artifact is running, health requirements are satisfied, or traffic converged. Observation scope remains explicit and compatible with C-level Evidence Scope.

## 9. D3 — Observed External Reality and Divergence

Runtime may observe deployed version, cloud-resource state, production configuration, database schema version, package state, or provider acceptance independently from its Trusted Production Baseline.

Observed External Reality is a production fact. It is not automatically Trusted Production Reality.

Trusted and Observed External Reality may temporarily diverge, but divergence remains explicit and governed:

```text
Trusted Baseline = B40
Observed Production = B41
```

or:

```text
Trusted Baseline = B41
Observed Production = B40
```

External Reality Divergence is Production Divergence and reuses B-level recovery / reconciliation rather than creating another recovery framework.

An observed effect remains fact even when unauthorized, stale, Zombie-originated, or invalid. Authority may decide whether to keep, compensate, governably adopt, or escalate. It cannot declare that an observed event did not happen.

## 10. External Reality Reconciliation

> External Reality Reconciliation is a governed process comparing desired / trusted production reality with observed external reality and determining the appropriate recovery path.

Logical inputs include desired and observed external state, Trusted Baseline, Effect Operation history, Candidate / Artifact revision, Authority / Policy, Verification / Assurance Evidence, and compensation options.

Possible semantic outcomes include CONVERGED, retry same Operation, observe again, compensate, governably adopt observed reality, replan, block, or Authority escalation. Outcome enums are not frozen.

## 11. Compensation Is Governed Production

A compensation action participates in Intent, identity, provenance, Authority, side-effect Policy, observation, reconciliation, and history. Hidden cleanup outside governance is not allowed.

Compensation may fail. Runtime must preserve accurate divergent reality and choose Block, Replan, Authority escalation, or further governed recovery rather than enter an uncontrolled loop.

Compensation is planned against **current observed external reality**, not a blind inverse of an old operation. If the original transition was B40 → B41 and current observed reality is B42, Runtime cannot blindly perform B41 → B40.

### Compensate versus governably adopt

External Reality Reconciliation may:

- **Compensate:** move external reality toward current governed trusted Intent.
- **Governably Adopt:** treat observed reality as input to a new governed Plan / Candidate / Verification / Authority / Commit path.

```text
Observed Reality
        ↓
Reconciliation
        ↓
Candidate / Plan
        ↓
Verification
        ↓
Authority
        ↓
Commit
        ↓
New Trusted Production Reality
```

Observed reality does not become Source of Truth merely because it happened. Fait-accompli admission is prohibited.

## 12. Governed Integration Atomicity

> Across independent systems where physical atomicity cannot be guaranteed, SPG preserves coherent production governance by making each intended external transition identifiable, authorized, observable, reconcilable, and recoverable.

Cross-system production atomicity is primarily a governance problem, not a universal database transaction problem. SPG does not claim Git, Database, Cloud, App Store, external APIs, and SPG Baseline all change at the same instant.

Intermediate and divergent states remain visible, attributable, governed, and recoverable.

Governance guarantees:

- No invisible external transition.
- No unexplained partial state.
- No silent Authority bypass.
- No guessed external truth.
- No overwritten effect history.

No universal physical atomicity is claimed.

## 13. Commit / Effect Ordering

There is no universal Commit-before-Effect or Effect-before-Commit ordering rule. Ordering is effect-specific, protocol-specific, Policy-driven, and risk-aware.

Deployment, migration, package publication, release submission, and irreversible notification may use different patterns. Effect Protocol DSL and production-pattern engines remain deferred.

## 14. Related Effects, Partial Convergence, and Unknown Reality

Multiple effects may jointly represent one external production transition and preserve correlation for partial completion and recovery. Association semantics are confirmed; a first-class Effect Group entity is deferred. SPG Lite may use Candidate ID, transition / correlation ID, or shared production Intent.

Partial Convergence is a legitimate state:

```text
Desired: service-a=B41, service-b=B41, service-c=B41
Observed: service-a=B41, service-b=B40, service-c=B41
```

Runtime preserves what converged and what did not; it does not collapse the result into FAILED.

Unknown External Reality is a first-class recoverable governance state when observation is insufficient. Runtime must not guess success or failure. Risk, repeatability, and compensability govern re-query, retry of the same Operation Identity, blocking, or escalation.

## 15. Governed Temporary Divergence

External reality may remain temporarily divergent under explicit governance, with rationale, Authority, scope, validity / expiration where relevant, and follow-up obligation.

Temporary acceptance of divergence does not redefine the Trusted Production Baseline. Known divergence remains visible.

## 16. Reproducibility and Credential Boundary

External execution need not be physically reproducible, but its governed Intent and execution Context must be reproducibly inspectable: operation, target, parameters, Artifact revision, Candidate, production state, Authority, preconditions, Executor / provider, and Operation Identity.

Execution provenance may preserve credential reference, role, Authority scope, and issuer / source. It must not persist passwords, raw API secrets, private keys, or other raw secrets merely for reproducibility.

This is an architecture and security boundary, not secret-management implementation.

## 17. Ownership and Distributed Governance

### SPG owns / governs

- External desired state and Effect Intent.
- Effect identity and Side-effect Authority.
- Operation lineage and observed external state.
- Divergence representation and reconciliation.
- Compensation orchestration.
- Production-state transition governance.

### Guardian / Verification owns

- Evidence about observed external state.
- Health / correctness Verification.
- Deployment / migration assurance.
- Findings, Qualification, Gates, and assurance truth.

SPG cannot infer assurance truth merely because a target reached requested state. Guardian cannot mutate Trusted Production State.

### No Actor Owns Production Truth Alone

- Executor reports execution facts.
- External System / Observer reports observed external reality.
- Guardian contributes Evidence / Findings.
- Human / Authority contributes risk, Exception, and Acceptance decisions.
- Production Governance Runtime performs governed adjudication and allowed transitions.

Executor SUCCESS does not prove convergence. API 200 does not prove health. Human Acceptance cannot erase an external effect. Guardian PASS cannot directly Commit. Runtime cannot fabricate observations.

## 18. Strong Semantics, Thin First Implementation

SPG Lite may eventually preserve D semantics through a thin **External Effect Record** with fields equivalent to operation identity, origin PWU / Attempt, target, environment, desired state / action, logical classification, authorization scope, execution generation, Candidate / Artifact revision, current effect state, observed reality, compensation relation, and correlation identity.

Physical representation is implementation-specific. This closure creates no schema or code.

Minimum future behavior semantics are declare, authorize, dispatch, observe, and reconcile, with these rules:

- No blind retry under Unknown External Reality.
- Stale generation cannot retain effect Authority.
- Partial and Unknown reality remain explicit.
- Compensation is a new Operation.
- Observed reality is not silently admitted into Trusted Reality.

These are architecture semantics, not an implementation instruction.

## 19. Deferred Mechanisms

The following remain deferred and are not SPG Lite MVP commitments:

- Universal Side-effect Gateway.
- Full secret-management platform.
- Saga orchestration engine.
- Two-phase Commit.
- Distributed transaction coordinator.
- Universal exactly-once infrastructure.
- General-purpose compensation DSL.
- Automatic compensation planner.
- First-class full Effect Group engine.
- Cross-cloud desired-state controller.
- Universal external dependency graph.
- Universal idempotency layer.
- Automatic blast-radius scoring.
- Complete deployment / orchestration platform.
- Effect Protocol DSL.
- Generalized production-pattern engine.
- Generalized authorization engine.
- Physical External Effect schema or API.

## 20. D-Level Invariants — CLOSED

### Side-effect Semantics

1. External Side Effect is a mutation beyond the disposable execution boundary whose effect may persist independently of the originating Attempt.
2. Physical change, authoritative production change, and observed external reality are distinct.
3. Side-effect governance is driven by repeatability, compensability, durability, and blast radius rather than subsystem name alone.
4. Rollback and Compensation are distinct production semantics.
5. Material External Effects require explicit identity and provenance.

### Authority & Execution Safety

6. Execution capability does not imply Side-effect Authority.
7. Material External Effects require scoped authorization against an explicit governed Intent.
8. External-effect Authority must participate in Attempt fencing.
9. Stale Attempts must not retain current external-effect Authority.
10. Governed effects must not depend on broad permanent production privilege held by Executors.
11. Relevant external preconditions should be validated before execution when possible.
12. SPG does not depend on universal exactly-once execution.
13. Execution Retry and delivery retry of the same Effect Operation are distinct.
14. Command / API acknowledgement does not establish external reality convergence.

### External Reality & Recovery

15. Partial and Unknown external reality are legitimate governance states.
16. Trusted Production Reality and Observed External Reality may temporarily diverge, but divergence must remain explicit.
17. Compensation is a new governed production action and appends history rather than rewriting it.
18. Observed External Reality does not automatically become Trusted Production Reality.
19. Cross-system integration safety is achieved through identity, Authority, observation, reconciliation, and compensation rather than assumed physical atomicity.
20. Effect ordering is protocol-specific and Policy-driven; there is no universal Commit-before-Effect or Effect-before-Commit rule.

## 21. D4 Closure Review Result

The supplied D4 review result is **PASSED** across Side-effect boundary and classification, Intent / Permit / Operation Identity, least Authority and blast radius, Attempt fencing, Zombie containment, Retry and exactly-once assumptions, preconditions and Authorization freshness, lifecycle and observed convergence, Partial / Unknown reality, External Reality Divergence, Compensation and failure, compensate-vs-adopt, Governed Integration Atomicity, Commit / Effect ordering, ownership, Human Authority, provider independence, and MVP complexity control.

This is architecture closure, not implementation or verification completion.

## 22. Runtime Architecture State and Next Task

| Runtime Architecture Refinement item | Status |
|---|---|
| A. State Foundation | CLOSED |
| B. Reconciliation & Recovery | CLOSED |
| C. Completion & Trust | CLOSED |
| D. Side-effect Governance | CLOSED |
| D1. Side-effect Semantics & Boundary | CLOSED — reviewed |
| D2. Side-effect Authority & Execution Safety | CLOSED — reviewed |
| D3. Compensation & External Reality | CLOSED — reviewed |
| D4. Side-effect Governance Closure | PASSED |
| Final Closure / Architecture Readiness Review | PASSED |
| Runtime Architecture Readiness | PASS |

The A/B/C/D refinement body is reviewed and documented. Runtime Architecture Refinement is **CLOSED** and architecture readiness for the next governed design stage is **PASS**.

The subsequently admitted [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) is CLOSED with Coding Readiness PASS. The current next governed step is **Architecture Lead Reality Review → reconcile the existing Pre-Implementation Repository Reality Check against the newly admitted Source of Truth → authorize the first controlled vertical implementation slice if no blocker remains**.

This D-closure record did not perform that later Contract stage or start Coding, schemas, APIs, tests, Side-effect infrastructure, or implementation.
