# SPG Lite Domain Model and Contract Boundary Baseline

- **Status:** Current program-level domain and contract baseline
- **Parent baseline:** AI Native Software Production System Architecture Baseline v0.1
- **Baseline date:** 2026-08-26
- **State Foundation clarification:** A CLOSED; logical state / Commit and PWU Acceptance semantics aligned without changing Architecture Baseline v0.1

## 1. Purpose and Scope

This document consolidates the accepted SPG Lite domain model, responsibility boundary, autonomy boundary, Human Governor interaction model, and capability-contract boundary.

**SPG Lite** means the minimum governed domain and contract view needed to align the current production-loop MVP. It is not a separate product, deployment, runtime, or implementation module.

This baseline:

- Clarifies existing domain concepts and ownership.
- Defines logical contracts without defining API endpoints or transport.
- Guides MVP alignment without expanding MVP scope.
- Preserves the YiJue, Guardian, ECF, Execution, and Human Governance boundaries.

It does not define a database schema, class model, service decomposition, endpoint, event protocol, or implementation commitment.

The [State Foundation Closure](spg-state-foundation.md) records confirmed runtime state / Commit semantics and 20 invariants under this baseline. The [Reconciliation & Recovery Closure](spg-reconciliation-recovery.md) now records B CLOSED, B1/B2/B3 CLOSED, B4 PASSED and 20 Recovery principles. Execution Lease, fencing, validity, and Recovery Barrier are logical semantics, not selected infrastructure. C. Completion & Trust is NEXT, NOT STARTED; D remains NOT STARTED. Architecture Baseline remains v0.1.

## 2. Governing Principles

### Contract First

Capabilities communicate through owned contracts rather than implementation dependencies.

### Ownership Before Integration

System integration must follow capability ownership. Ownership must not be assigned according to implementation order, existing product boundaries, or current technical convenience.

### Generated Does Not Equal Trusted

AI-generated or tool-generated output does not automatically become trusted production truth. Trust requires applicable verification, admission into governed state, and authority.

### Contract Before Implementation

Stable responsibility, authority, and artifact contracts should be defined before implementations are replaced, integrated, or scaled.

These principles define architecture boundaries. They do not claim that every contract has a current API or dedicated runtime.

## 3. SPG Lite Domain Model

The logical domain flow is:

```text
Approved Intent / Decision Artifact
        ↓
Production Plan
        ↓
Production Work Unit (PWU)
        ↓
Execution Capability
        ↓
Work Product Artifact
        ↓
Verification Capability / Guardian Evaluation
        ↓
Verification Evidence / PWU obligations satisfied
        ↓
Exact Baseline Candidate / Commit Eligibility
        ↓
Human / Policy Final Acceptance (Commit Authorization)
        ↓
Governed Commit
        ↓
Trusted Production Baseline

Context Package supplies bounded context to planning,
execution, and verification.

Human Decision Record preserves authority decisions,
risk acceptance, acceptance, and governed exceptions.
```

The diagram represents domain-object and authority flow, not a full PWU state machine. Final Acceptance targets the exact Baseline Candidate, not every PWU by default. It does not imply that every object is stored separately or that every capability is currently integrated.

## 4. Core Domain Objects

### 4.1 Production Plan

> Production Plan is a governed execution strategy that transforms approved intent into coordinated production activities.

**Owner:** SPG

Responsibilities:

- Transform approved intent into production strategy.
- Organize Production Work Units.
- Maintain execution coordination state.

It is not responsible for:

- Business decision making.
- Strategic intent definition.
- Replacing the approved Decision Artifact.

Material changes to executable scope, dependencies, execution path, required capability, expected output, completion conditions, verification obligations, or authority / risk boundary create a new Production Plan Revision. Presentation-only or non-semantic annotations do not necessarily require a new revision.

### 4.2 Production Work Unit (PWU)

> Production Work Unit is the smallest governed production activity that can be planned, assigned, executed, verified, and evaluated for satisfaction of its production obligations.

PWU is not equivalent to Coding Task. It represents governed production activity and may be categorized as:

- Implementation.
- Documentation.
- Context Preparation.
- Analysis.
- Verification.
- Planning.

Its logical attributes are:

- Intent.
- Scope.
- Required Capability.
- Input Context.
- Expected Output.
- Verification Requirement.
- Acceptance Criteria.
- Lifecycle State.
- Dependencies.
- Evidence.

These are domain semantics, not a database or API schema.

The former simplified lifecycle ending in Accept is clarified at two levels:

```text
PWU: Plan → Assign → Execute → Produced → Verified / Qualified → Satisfied
Production: exact Baseline Candidate → Authority Acceptance → Commit
            → Trusted Production Baseline
```

**Satisfied** is a working semantic term for meeting PWU obligations, not a frozen state enum. Human Final Acceptance is not required by default for every PWU; Human / Policy Final Acceptance primarily targets an exact sealed Baseline Candidate. **Integrated** is derived lineage/integration state for artifacts/PWUs included in a committed Baseline, not a mandatory primary PWU terminal state.

Every executable PWU binds to an explicit source Baseline and Plan Revision, not “the current plan”. After a PWU creates an Execution Attempt, its executable semantics cannot be silently rewritten. Material changes require explicit revision, replacement, or supersession; the final revision implementation mechanism is not frozen.

Detailed completion remains for C. Completion & Trust, NEXT but NOT STARTED. The [closed B semantics](spg-reconciliation-recovery.md) govern failure/divergence, Resume/Retry, validity, supersession, and recovery: Resume preserves Attempt identity, Retry creates new history, and technically successful work can be STALE. Concrete lifecycle representation remains unselected; this does not fully redesign the PWU state machine.

### 4.3 Context Package

> Context Package is a bounded collection of relevant engineering context prepared for a specific production activity.

Principles:

- Minimum Sufficient Context.
- Purpose-specific.
- Not a full repository dump.
- Not the canonical context source.

A Context Package is an activity-scoped projection or preparation artifact. It does not replace source repositories, governed facts, or an ECF Context Projection.

**Future Direction:** a Context Package may be supplied through an ECF Projection. This is an integration direction, not a current ECF implementation commitment.

### 4.4 Work Product Artifact

> Work Product Artifact is the concrete output generated by a Production Work Unit.

Work Product Artifact is the actual output instance. Production Artifact is the domain classification.

Examples include:

- Code Artifact.
- Documentation Artifact.
- Context Artifact.
- Analysis Artifact.
- Verification Artifact.

The producing Execution Capability Provider owns the generated artifact. SPG owns its relationship to the Work Unit and maintains lineage and lifecycle coordination; SPG does not own the generated content.

### 4.5 Verification Evidence

Verification Artifact is not equivalent to Verification Evidence.

```text
Verification Artifact
        ↓
Verification Capability / Guardian Evaluation
        ↓
Verification Evidence
```

A Verification Artifact is a raw Work Product such as a test result, scan result, or benchmark result. Verification Evidence is trusted assurance information admitted through the applicable Verification / Guardian authority boundary.

Verification Evidence does not by itself equal final Acceptance. Acceptance remains subject to the applicable policy and Human Authority.

### 4.6 Human Decision Record

> Human Decision Record is the record of a human authority decision affecting production-state transitions.

Examples include:

- Plan approval.
- Risk acceptance.
- Final acceptance.
- Approval of a governed exception.

Its purpose is to preserve accountability, explain authority decisions, and prevent an override from being hidden in Conversation History.

Any exception from the normal governance flow must produce a Human Decision Record. This is a record and authority requirement, not a storage-schema commitment. A Human Decision Record expresses authority; it does not bypass runtime consistency, lineage, transition, or Commit rules.

### 4.7 Confirmed State Foundation Semantics

The [closed State Foundation](spg-state-foundation.md) refines this minimum domain view:

| Concept / responsibility | Confirmed logical meaning |
|---|---|
| Trusted Production Baseline | Immutable references to accepted production reality; artifact content remains with its authoritative owner |
| Working Production State | Stable identity, evolving projection, preserved history; not Trusted State |
| Execution Attempt | Immutable concrete execution fact bound to PWU, Plan Revision, source Baseline, relevant Context, Provider, and result; attempts never overwrite one another |
| State Transition Journal | Durable record of material governance transitions; not a requirement for Event Sourcing |
| Baseline Candidate | Exact sealed snapshot proposed as next Trusted Baseline; material changes create a new revision |
| Current Trusted Baseline Pointer | Unique logical authority for the current trusted reality; not a mandated database field |
| Production Governance Runtime | Sole logical authority validating, admitting, and performing authoritative SPG state transitions |
| Production State Projection | Rebuildable current view from persisted facts, not final authority |

Commit Eligibility, Commit Authorization, and Commit Execution are distinct. Only successful Commit changes Current Trusted Baseline authority, after checking the expected source Baseline. Failure before the authoritative switch preserves the previous authority; derived-view or follow-up synchronization failure after the switch does not undo Commit.

The confirmed core decomposition is Production Planner → Production Governance Runtime → Production State Projection, **logical responsibilities only**, not deployable services. These semantics do not finalize Production Issue representation, artifact taxonomy, Completion Contract placement, detailed lifecycle, schema, or API.

## 5. Autonomy and Authority Boundary

Within approved Intent, Scope, Constraints, and policy, SPG may coordinate planning, assignment, execution, verification, and state progression.

SPG must not:

- Create or modify the Business Decision.
- Silently expand approved Scope.
- Treat generated output as trusted without verification and admission.
- Convert Verification into Acceptance without the required authority.
- Hide an exception or authority override in runtime memory or Conversation History.

An Executor may execute the PWU Contract, report issues, and return Work Product Artifacts. It cannot silently modify PWU Scope, Expected Output, Verification Requirement, or Acceptance Criteria.

Human Governor retains Goal Authority, Strategic Direction, Risk Acceptance, approval where required, Final Acceptance, and accountability. **Human Authority Does Not Imply Runtime Bypass:** Human Agency First is not unrestricted runtime privilege. Human, AI, Executor, Guardian, and other actors are governed participants with different Responsibility / Authority.

Planner proposes plans / changes; Executor and Verification / Guardian report facts / artifacts; Human Governor issues authority decisions. Production Governance Runtime alone validates, admits, and performs authoritative SPG state transitions, without taking ownership of those decisions, artifact content, or Assurance Truth.

## 6. SPG Lite Contract Boundary Model

### 6.1 Decision Artifact Contract

| Field | Definition |
|---|---|
| Owner | Decision Intelligence Domain |
| Consumer | SPG |
| SPG-facing semantics | Goal, Constraint, Scope, Acceptance Criteria |

SPG consumes an approved Decision Artifact projection. It may interpret it for production planning but cannot modify the Business Decision or strategic authority encoded by the owning domain.

### 6.2 Production Plan Contract

| Field | Definition |
|---|---|
| Owner | SPG |
| Consumers | Human Governor, Execution Coordination |
| Defines | Production strategy, Work Unit structure, dependencies, coordination status |

The contract expresses governed production strategy with explicit Plan Revision bindings for executable work. Planner proposes revisions; authoritative state transitions pass through Production Governance Runtime. This does not define a database model or require a dedicated planning service.

### 6.3 PWU Contract

| Field | Definition |
|---|---|
| Owner | SPG |
| Consumer | Executor Capability |
| Defines | Intent, Required Capability, Context, Expected Output, Verification Requirement |

Scope, Constraints, Acceptance Criteria, and dependencies remain governed inputs. The Executor cannot silently modify them; it must report a conflict or request a governed change.

### 6.4 Context Contract

| Field | Definition |
|---|---|
| Owner | Context Capability; future ECF for ECF-owned projections |
| Consumers | Planner, Executor, Verification Capability |
| Defines | Bounded, purpose-specific Context Package / Projection semantics |

Context consumption uses bounded projection rather than unrestricted raw-information access. A Context Package is not the canonical source and does not transfer ECF ownership to SPG.

### 6.5 Execution Contract

| Field | Definition |
|---|---|
| Owner | Execution Capability Interface |
| Consumer | SPG Execution Coordination |
| Input | Production Work Unit, Context Package, Constraints |
| Output | Execution Result, Work Product Artifact, Issues |

SPG depends on the Execution Contract, not on a specific Executor, model, Agent, tool, or runtime implementation.

### 6.6 Artifact Contract

The Artifact Contract follows the principle:

> Producer owns artifact content; SPG maintains lineage, relationship, and lifecycle coordination.

SPG may reference an artifact, relate it to a PWU, record its lifecycle status, and consume its declared metadata. It does not directly own generated artifact content or become the canonical store for all artifact domains.

### 6.7 Verification Contract

| Field | Definition |
|---|---|
| Owner | Verification Capability; Guardian for Guardian-owned Assurance Evidence |
| Consumers | SPG, Human Governor / Acceptance Authority |
| Input | Work Product Artifact, Acceptance Criteria |
| Output | Verification Result, Verification Evidence |

Verification evaluates an artifact against criteria and returns result and evidence. Verification does not equal Acceptance.

### 6.8 Human Decision Contract

| Field | Definition |
|---|---|
| Owner | Human Governance Domain |
| Consumer | SPG Governance Flow |
| Output | Human Decision Record |

Human Decision Record is the governed exception / authority-decision and accountability mechanism. Any exception must be explicit, attributable, and recorded. It does not grant unrestricted runtime bypass: Runtime applies authorized decisions consistently with production-state and Commit rules. Final production acceptance binds to an exact Baseline Candidate revision.

## 7. Domain Object Ownership Matrix

| Domain object | Owner | SPG relationship |
|---|---|---|
| Production Plan | SPG | Owns strategy and coordination state |
| Production Work Unit | SPG | Owns governed activity definition and lifecycle coordination |
| Context Package | Producing Context Capability / Provider | Consumes and relates it to a PWU; does not treat it as canonical context |
| Work Product Artifact | Producing Execution Capability Provider | Maintains lineage, relationship, and lifecycle coordination |
| Verification Evidence | Guardian / Assurance Domain | Consumes trusted evidence; does not redefine Assurance Truth |
| Human Decision Record | Human Governance Domain | Records and applies the authorized transition; cannot rewrite the decision |

## 8. Contract Ownership Matrix

| Contract | Owner | Primary consumer |
|---|---|---|
| Decision Artifact Contract | Decision Intelligence Domain | SPG |
| Production Plan Contract | SPG | Human Governor / Execution Coordination |
| PWU Contract | SPG | Executor Capability |
| Context Contract | Context Capability / Future ECF | Planner / Executor / Verification Capability |
| Execution Contract | Execution Capability Interface | SPG Execution Coordination |
| Artifact Contract | Producing Capability / Artifact Provider | SPG and downstream governed consumers |
| Verification Contract | Verification Capability / Guardian Assurance boundary | SPG / Acceptance Authority |
| Human Decision Contract | Human Governance Domain | SPG Governance Flow |

## 9. Boundary Consistency

### SPG

SPG owns:

- Production Plan.
- Production Work Unit.
- Production coordination and related governance state.
- Artifact lineage and relationship tracking.

SPG does not own:

- Decision Intelligence or Business Decision.
- Generated artifact content.
- Assurance Truth.
- Canonical Context.

### YiJue

YiJue remains a Consumer Product and possible Decision Intelligence Provider. It is not an SPG component and is not required by the SPG Lite domain model.

### Guardian

Guardian owns its Assurance Evidence and qualification authority. It does not own Production Planning, PWU definition, or SPG Production State.

### ECF

ECF owns Context Projection Capability and its authoritative semantics. It does not own SPG State. Context Package support through ECF remains Future Direction.

### Execution Capability

The producing Execution Capability Provider owns generated Work Product Artifacts. It executes within the PWU Contract and cannot silently redefine governed Scope.

### Human Governor

Human Governor retains strategic authority, risk acceptance, governed exceptions, and applicable Final Acceptance of exact Baseline Candidates. Human Decision Records preserve those decisions as explicit artifacts; they do not permit direct mutation of authoritative production reality.

## 10. MVP Implementation Boundary

This domain and contract baseline does not add an implementation module or expand the MVP. In particular, it does not require:

- A new service for each domain object or contract.
- New database tables or schemas.
- New API endpoints or transport protocols.
- Complete Guardian or ECF integration.
- A new artifact repository.
- A new workflow engine.
- Autonomous acceptance or authority transfer.

Existing MVP mechanisms may represent these semantics minimally while preserving the ownership and contract boundaries. The State Foundation does not require Event Sourcing, distributed transactions, a distributed state store, a complex workflow engine, a graph database, distributed locking, Production State Branching, or microservices. Ordinary persistence, explicit records / revisions, transition history, Git references, and simple controlled commit logic are permitted directions, not a selected implementation.

Architecture reserves future; product does not consume future.

## 11. Future Design Questions

The consolidation exposes the following non-blocking Future Design questions:

1. What contract versioning and compatibility policy is needed when Executor, Context, and Verification providers evolve independently?
2. What admission protocol turns a Verification Result into Guardian-qualified Verification Evidence and then into an accepted production-state transition?
3. How should Context Package provenance and freshness be preserved when Future ECF Projection becomes a provider?
4. What minimum transition-authority matrix is needed for PWU lifecycle exceptions without encoding a database or workflow implementation prematurely?

These questions do not change the current baseline or create implementation commitments.
