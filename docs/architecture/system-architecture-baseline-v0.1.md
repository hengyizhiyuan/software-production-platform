# AI Native Software Production System Architecture Baseline v0.1

- **Status:** Program-level Architecture Source of Truth
- **Version:** 0.1
- **Baseline date:** 2026-08-25
- **Clarification:** Production Work Unit / Production Artifact terminology and State Foundation logical semantics refined without changing the architecture version

## 1. Purpose and Interpretation

This baseline records the current program-level agreement for the AI Native Software Production System. It exists to:

1. Preserve system-level architecture consensus.
2. Make capability ownership and dependency direction explicit.
3. Guide subsequent MVP alignment.
4. Prevent responsibility drift across products, platforms, and providers.

This document does not add a Feature, create an implementation commitment, expand a future commercial model, or replace detailed subsystem and project design documents.

The status labels used here have precise meanings:

- **Current Baseline:** an accepted architecture boundary, ownership rule, or contract. It does not imply that every related implementation exists today.
- **Future Direction:** an allowed evolution path, not a committed roadmap deliverable.
- **Open Question:** an unresolved design topic that does not block the v0.1 baseline.

Where a detailed document conflicts with this baseline at the system-boundary level, the conflict must be resolved explicitly rather than silently changing capability ownership.

## 2. System Mission — Current Baseline

> Establish a software production system centered on Human Governance and amplified by AI Capability.

The system is not primarily intended to increase code generation speed. Its system-level objective is to reduce the production cost of **Trusted Software Change**.

```text
Human Intent and Authority
        ↓
Governed AI Capability
        ↓
Software Production and Verification
        ↓
Trusted Software Change
```

Human Authority retains Intent, Value Judgment, Risk Acceptance, approval where required, and final accountability. AI capabilities amplify understanding, decision support, planning, execution, verification, and adaptation within explicit boundaries.

## 3. Five Capability Plane Model — Current Baseline

The system-level model contains five capability planes:

| Plane | Primary responsibility | Principal boundary |
|---|---|---|
| Human Governance Plane | Intent, authority, value judgment, risk acceptance, accountability | Human Governor |
| Decision Intelligence Plane | Intent understanding, decision reasoning, Decision Artifact formation | Decision Intelligence Capability |
| Production / Control Plane | Decision-to-production governance, planning, work coordination, execution coordination, Production State | Software Production Platform / SPG |
| Assurance Plane | Independent evidence, findings, gates, and qualification | Guardian |
| Context Plane | Authoritative engineering context, projection, and lineage | ECF |

Execution participates through a capability contract within the production flow. The Execution System owns execution behavior and generated Work Product Artifacts within the Production Artifact Domain; SPG coordinates execution but does not absorb executor or artifact ownership.

The primary flow is:

```text
Human Governor
        │ Intent / Authority
        v
Decision Intelligence Capability
        │ Decision Artifact Candidate
        v
Human Governance Gate
        │ Accepted Decision Artifact
        v
Design Governance / Engineering Baseline
        │
        v
Software Production Platform
        │ Production Governance (SPG)
        v
Production Work Unit
        │ Capability Assignment
        v
Execution Capability
        │ Work Product Artifact
        v
Engineering Assurance (Guardian)
        │ Verification Evidence / Qualification
        v
Trusted Production State

ECF Engineering Context Capability
        └── provides governed Context Projection to every plane
```

This diagram represents artifact and responsibility flow, not system containment. Guardian and ECF remain independently owned capabilities. Decision Intelligence Provider and Execution Provider implementations remain replaceable behind contracts.

## 4. Capability Ownership Model — Current Baseline

### 4.1 Decision Intelligence Capability

Decision Intelligence Capability is responsible for:

- Understanding Human Intent.
- Forming Decision Artifact Candidates.
- Supporting complex decision reasoning.

It is not responsible for:

- Software production workflow.
- Code execution.
- Engineering verification or Assurance Truth.

A candidate becomes an accepted Decision Artifact only through the applicable Human Authority and governance process.

### 4.2 YiJue Product Boundary

YiJue is:

- A Consumer Product / Application.
- A possible Decision Intelligence Provider.
- The intended first Reference Implementation / Reference Provider for mature Decision Intelligence integration.

YiJue is not:

- The Software Production Platform.
- An SPG component.
- An ECF module.
- A Guardian dependency.
- A hard dependency required to bootstrap SPG.

YiJue retains independent product ownership, product experience, runtime, policy, business logic, and lifecycle. This baseline does not modify YiJue internal architecture or reduce its strategic value.

### 4.3 SPG Boundary

SPG governs the transition from an accepted Decision to a controlled Production Process.

SPG is responsible for:

- Production Planning.
- Production Work Unit management.
- Execution coordination.
- Production Governance.
- Change coordination.
- Production State maintenance at the current platform boundary.

SPG is not responsible for:

- Business or strategic Decision authority.
- General-purpose Decision Intelligence.
- Assurance Truth.
- Provider-specific intelligence internals.

### 4.4 Guardian Boundary

Guardian transforms a Production Change and its supporting facts into independent Assurance Evidence.

Guardian owns:

- Evidence qualification.
- Findings.
- Assurance Gates.
- Qualification decisions within its authority boundary.

Guardian does not:

- Decide what the business should do.
- Plan the production process.
- Modify business goals.
- Own SPG Production State.

The MVP may retain only an Assurance Extension Point and basic verification. This ownership model does not assert that complete Guardian integration currently exists.

### 4.5 ECF Boundary

ECF is responsible for Engineering Context Delivery, including:

- Context Authority.
- Context Projection.
- Context Lineage.

ECF is not:

- A generic conversational Memory system.
- A YiJue Context module.
- A downstream system after Guardian.
- The owner of SPG Production State.

ECF provides governed Context Projections across planes. It does not absorb the responsibility or lifecycle of the consuming capability.

## 5. Dependency Direction — Current Baseline

### Dependency Direction Follows Capability Ownership

System dependencies follow capability contracts and ownership boundaries, not product delivery order or the maturity of one implementation.

Incorrect:

```text
SPG → YiJue Product
```

Correct:

```text
SPG
  ↓
Decision Intelligence Interface
  ↓
Decision Intelligence Provider
  ├── Lightweight Provider
  ├── YiJue Decision Engine
  ├── Enterprise Provider
  └── Third-party Provider
```

SPG consumes the Decision Intelligence Interface and Decision Artifact Contract. It must not depend on a provider-specific model, prompt, Agent topology, internal reasoning representation, product API, or deployment lifecycle.

The same rule applies across the system:

- Production capability depends on an Execution Contract, not a specific executor runtime.
- Assurance consumers depend on the Assurance Contract, not Guardian internals.
- Context consumers depend on Context Projection contracts, not a concrete ECF data source.
- Roles depend on Role Contracts, not a single Agent instance or model.

## 6. Decision Intelligence Bootstrapping — Current Baseline Decision

### Decision Intelligence Contract First

The Software Production Platform does not wait for a complete Decision Intelligence Product before validating the production loop.

```text
Decision Intelligence Contract
        ↓
Lightweight Provider
        ↓
SPG Production Loop Validation
        ↓
Replace / Upgrade Provider
        ↓
Mature Provider Integration
```

A Lightweight Provider may use an LLM, Governed Prompt, and Limited Context Assembly. Its limited purpose is to:

- Validate the production loop.
- Validate the Decision Artifact Contract.
- Reveal capability gaps using real production evidence.

It is not a replacement for YiJue, a second Consumer Product, a complete Decision Room, or a complete Decision Intelligence Engine.

This section fixes the architecture dependency and evolution order. It permits bootstrapping but does not commit the MVP to a concrete provider, API, adapter, or YiJue integration.

## 7. Production Work and Artifact Model — Current Baseline

### 7.1 Production Work Unit Generalization Principle

> Production Work Unit represents a governed production activity that transforms intent into a validated production outcome. It is not limited to coding activities.

A Production Work Unit may be assigned to a Human, AI, Tool, or other Capability Provider. Its category describes the production responsibility, not the implementation technology or actor type.

Production Work Unit categories may include:

#### Implementation Work Unit

- Code implementation.
- API development.
- Configuration changes.

#### Documentation Work Unit

- Architecture document update.
- API specification.
- Decision record.

#### Context Preparation Work Unit

- Repository analysis.
- Context package generation.
- Knowledge extraction.

#### Analysis Work Unit

- Root cause analysis.
- Impact analysis.
- Architecture analysis.

#### Verification Work Unit

- Test execution.
- Security verification.
- Benchmark evaluation.

#### Planning Work Unit

- Production planning.
- Migration planning.
- Refactoring planning.

These categories clarify semantics only. They do not add an MVP workflow, subsystem, provider, or implementation commitment.

### 7.2 Production Artifact Domain

> Production Artifact represents all governed outputs generated during software production.

Production Artifact is a domain category, not a synonym for deployment artifact or code output:

```text
Production Artifact Domain
   ├── Code Artifact
   ├── Documentation Artifact
   ├── Context Artifact
   ├── Analysis Artifact
   └── Verification Artifact
```

**Work Product Artifact** is the concrete output of a Production Work Unit. One Work Unit may produce one or more Work Product Artifacts classified within the Production Artifact Domain.

The producing Execution System or Capability Provider retains ownership of generated Work Product Artifacts. SPG coordinates their lifecycle, lineage, governance state, and relationship to Production Work Units; it does not become the content owner or system of record for every artifact domain. Guardian retains ownership of Assurance Evidence, and ECF retains ownership of Context Projection semantics.

Category membership does not transfer authority:

- A **Verification Artifact** is a Work Product such as a raw test, scan, or benchmark result. **Verification Evidence** is evidence qualified within the Guardian / Assurance authority boundary. Not every Verification Artifact is accepted Verification Evidence.
- A **Context Artifact** is a generated Work Product such as a context package. An authoritative **Context Projection** remains governed by ECF. Not every Context Artifact is an ECF Context Projection.

### 7.3 Artifact Flow Model

Artifacts are the cross-system collaboration language. Conversation History is not the Source of Truth.

The normalized flow is:

```text
Human Intent
        ↓
Decision Intelligence Capability
        ↓
Decision Artifact Candidate
        ↓ Human Authority / Governance, where applicable
Decision Artifact
        ↓
Engineering Baseline
        ↓
Production Work Unit
        ↓
Work Product Artifact
        ↓
Verification Evidence
        ↓
Trusted Production State
        ↓
Engineering Context Update / Projection
```

The Context update closes the information loop; it does not make ECF the downstream owner of Production State. ECF projects relevant engineering facts while SPG and the logical Production State Domain retain production-governance state responsibility.

## 8. Core Artifact Ownership — Current Baseline

| Artifact | Logical owner | Boundary note |
|---|---|---|
| Decision Artifact | Decision Intelligence Domain | Provider creates instances; Human Authority governs acceptance where required |
| Engineering Baseline | Design Governance Domain | Logical design-governance boundary; not a new implementation commitment |
| Production Work Unit | SPG | Governed unit of production coordination |
| Work Product Artifact | Execution System / producing Capability Provider | Concrete output produced by a Production Work Unit |
| Verification Evidence | Guardian / Assurance Domain | Complete Guardian runtime integration may remain future work |
| Context Projection | ECF | Projection does not transfer source ownership to the consumer |
| Trusted Production State | Production State Domain | Maintained within the current SPG boundary; future independent boundary remains open |

Logical ownership defines semantic authority and dependency direction. It does not require each domain to be deployed as a separate service, repository, database, or runtime in the MVP.

SPG owns Production Work Unit governance and coordination, not the generated artifact content. This generalization does not make SPG a Coding Platform, Documentation System, or Knowledge Management System.

## 9. Evolution Principles — Current Baseline

### Capability Contract Before Capability Implementation

Define, in order:

1. Capability Boundary.
2. Contract.
3. Ownership and authority.
4. Replaceable Provider / Implementation.

Provider replacement must not reverse capability ownership or require consumers to absorb provider internals.

### Architecture Reserves Future; Product Does Not Consume Future

Architecture may preserve extension points and compatible boundaries for Future Directions. Current products and MVPs must not pre-implement, depend on, or claim those future capabilities before they are validated and explicitly adopted.

An extension point is not an implementation. A future provider option is not a current dependency. A target architecture is not an MVP commitment.

## 10. MVP Boundary — Current Baseline

The current focus is the minimum governed production loop:

```text
Intent → Planning → Work Unit → Execution → Verification
    → Production State → Feedback / Next Iteration
```

The current baseline does not commit the MVP to build:

- A full Production State Platform.
- A Capability Marketplace.
- An Autonomous Organization.
- Full Enterprise Governance.
- Complete Guardian System Integration.
- Complete ECF Integration.
- Mature YiJue Decision Engine Integration.
- Multiple Enterprise Decision Providers.

## 11. Governance State Preservation

### Current Baseline Principle

Long-running production continuity must rely on Explicit Production State rather than Conversation History or a single Agent's memory. New input must not silently replace the active production objective or invalidate prior decisions.

### State Foundation Closure — Current Logical Semantics

The [State Foundation Closure](spg-state-foundation.md) records A CLOSED, A1 / A2 CLOSED, and A3 PASSED. It refines this v0.1 baseline without changing capability ownership, MVP scope, or the architecture version.

Trusted Production Baseline is an immutable reference set, distinct from evolving Working Production State. Execution Attempt and State Transition Journal preserve historical facts. Exact sealed Baseline Candidates pass through distinct Eligibility, Authorization, and Commit semantics. Only successful Commit, with expected source-Baseline validation, changes Current Trusted Baseline authority.

Production Planner → Production Governance Runtime → Production State Projection is confirmed **only as logical responsibility decomposition**. Runtime is the sole logical authority for authoritative SPG state transitions; projections are rebuildable views, not final authority. This does not define physical services.

**Human Authority Does Not Imply Runtime Bypass.** Human and Machine are governed participants with different responsibilities and authority. Human Agency First preserves strategic, risk, and applicable final-acceptance authority, not unrestricted runtime privilege. Final production acceptance primarily targets an exact Baseline Candidate, not every PWU by default.

Git retains code-history authority. Artifact producers, Decision Intelligence, Guardian, ECF, and Human Governance retain their domain ownership; SPG's governed composition does not absorb their truth. Detailed invariants and failure boundaries are in the linked closure record.

### Reconciliation & Recovery Closure — Current Logical Semantics

The [B closure](spg-reconciliation-recovery.md) records B CLOSED, B1/B2/B3 CLOSED, and B4 PASSED, with all 20 Recovery principles. Failure differs from Divergence; execution success does not prove current validity. Resume preserves Attempt identity; Retry creates new history. Execution Lease, fencing, isolation, validity evaluation, and Recovery Barrier are confirmed logical semantics, not chosen infrastructure.

Recovery preserves maximum still-valid work, expands scope only when necessary, and reconstructs governed knowledge before restarting execution. Runtime recovery restores governance control rather than silently finishing product work. Its completion means production authority/state is coherent, not that all production work is complete.

**No Actor Owns Production Truth Alone; Distributed Responsibility, Governed Adjudication.** Runtime adjudicates authoritative transitions from domain-owned inputs rather than inventing all truth. This is not majority voting and does not weaken Human Authority. Provider consolidation preserves logical Responsibility / Contract / Authority boundaries: **Replaceable Intelligence, Durable Governance** does not imply equal model capability or automatic unrestricted autonomy.

The [Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md) records future verification requirements and benchmark candidates only. No test, benchmark, model routing, or billing implementation is introduced.

### Future Direction

A more complete SPG Governance State Preservation capability may explicitly maintain:

- Current Objective.
- Current Stage.
- Completed Decisions.
- Pending Decisions.
- Next Valid Transition.

The closed A/B records settle logical state / Commit and Reconciliation & Recovery semantics. Detailed completion, side-effect governance, persistence architecture, concrete recovery mechanisms, transition implementation, and autonomous behavior remain future design work. The exact next valid step is **Runtime Architecture Refinement → C. Completion & Trust**; C is NEXT, NOT STARTED, and D is NOT STARTED. This baseline does not introduce an implementation commitment or begin C.

## 12. Future Directions

The following directions are compatible with v0.1 but are not current capabilities or commitments:

- Mature YiJue Decision Engine integration through the Decision Intelligence Contract.
- Multiple Enterprise and Third-party Decision Providers.
- Complete Guardian and ECF integration.
- Independent Production State Platform evolution.
- Rich Governance State Preservation and transition control.
- Enterprise Provider Contract standardization.

Future work must preserve the ownership and dependency-direction rules in this baseline unless superseded by an explicit program-level architecture decision.

## 13. Open Questions

The following questions remain open and do not block v0.1:

1. Should the Production State Domain become an independently deployed long-term boundary, and at what maturity stage?
2. What is the detailed governed mapping from a Decision Artifact to an Engineering Baseline?
3. What minimum semantics, security controls, and portability requirements belong in an Enterprise Provider Contract?
4. How should a Production State Platform evolve from the current SPG-managed boundary without splitting Source of Truth?

## 14. Baseline Decision Summary

### Current Baseline

- Human Governance remains the authority and accountability boundary.
- The system uses the Five Capability Plane Model.
- Capability ownership determines dependency direction.
- SPG depends on Decision Intelligence Contract, not YiJue Product.
- Decision Intelligence Contract First is the bootstrapping strategy.
- Production Work Unit represents governed production activity, not only Coding Task.
- Production Artifact is a domain category; Work Product Artifact is a concrete Work Unit output.
- SPG Lite ownership and interactions are governed by the linked Domain Model and Contract Boundary Baseline.
- Generated output requires verification, admission, and applicable authority before becoming trusted production truth.
- Capability Contract precedes Provider implementation.
- Artifacts, evidence, and explicit state—not Conversation History—form the collaboration baseline.
- Architecture may reserve Future Directions, while products must not consume them early.

### Future Direction

- Mature and multiple Decision Intelligence Providers.
- Complete Guardian / ECF integration.
- Rich Governance State Preservation.
- Independent Production State Platform evolution.

### Open Question

- Production State independent boundary.
- Decision Artifact to Engineering Baseline mapping.
- Enterprise Provider Contract.
- Production State Platform evolution path.

## 15. Relationship to Detailed Documents

This baseline governs program-level system boundaries. Detailed documents remain responsible for their own scope:

- [Program-level Architecture Decisions](program-architecture-decisions.md) records individual program decisions and rationale.
- [SPG Lite Domain Model and Contract Boundary Baseline](spg-lite-domain-contract-baseline.md) records the current SPG Lite domain objects, autonomy boundary, Human Decision model, and capability-contract ownership.
- [SPG Core Architecture Model](SPG_Core_Architecture_Model.md) details SPG concepts and future directions.
- [SPG State Foundation Closure](spg-state-foundation.md) records confirmed state / Commit semantics, 20 invariants, and Human–Machine governance under v0.1; [Runtime Findings Review](spg-runtime-findings-review.md) preserves the discovery scope and current agenda.
- [SPG Reconciliation & Recovery Closure](spg-reconciliation-recovery.md) records B1/B2/B3 CLOSED, B4 PASSED, confirmed recovery semantics, and all 20 B-level principles under v0.1.
- [Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md) records future invariant verification, fault injection, provider-independent benchmarks, and the real incident-derived regression candidate, not current implementation scope.
- [MVP Architecture](mvp-architecture.md) defines the current MVP boundary.
- [Guardian Integration](../assurance/guardian-integration.md) and [ECF Integration](../context/ecf-integration.md) define integration boundaries without redesigning those systems.
- Product-specific documents retain product internals and implementation decisions.

Detailed documents may refine this baseline but must not silently redefine capability ownership, authority, artifact ownership, or dependency direction.
