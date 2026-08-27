# SPG Core Architecture Model

This document records the current SPG architecture model and its future architecture directions. It is an Architecture Decision record, not an implementation specification. Future Capability and Architecture Hypothesis statements are not current capabilities.

The minimum current domain-object and contract view is consolidated in [SPG Lite Domain Model and Contract Boundary Baseline](spg-lite-domain-contract-baseline.md). That document refines SPG Lite semantics without narrowing or expanding the full SPG architecture described here.

## Runtime Review Status and Refinement Boundary

The [Runtime Findings Review](spg-runtime-findings-review.md) records the closed tabletop exercise and frozen failure-mode discovery. The [Runtime Architecture Final Closure and Readiness](spg-runtime-architecture-readiness.md) records Runtime Architecture Refinement CLOSED and Runtime Architecture Readiness PASS.

[State Foundation](spg-state-foundation.md), [Reconciliation & Recovery](spg-reconciliation-recovery.md), [Completion & Trust](spg-completion-trust.md), and [Side-effect Governance](spg-side-effect-governance.md) preserve the closed A/B/C/D semantics. The [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) records I1/I2/I3 CLOSED, I4 PASSED, Coding Readiness PASS, and **AUTHORIZED FOR CONTROLLED IMPLEMENTATION**. No specific implementation slice is authorized here.

Architecture Baseline remains **v0.1**. A confirms State / Commit foundations; B confirms Reconciliation / Recovery; C confirms Completion / Trust; D confirms External Side Effect, Intent / Permit / Operation Identity, external fencing, Observed External Reality, Compensation, and Governed Integration Atomicity. The cross-layer semantic, ownership, failure-containment, provider-decoupling, and SPG Lite feasibility reviews passed. Physical mechanisms, Design Artifact taxonomy, Production Issue representation, and deferred capabilities remain unselected.

Event-driven / Event-sourced Production State remains a Future Direction. Confirmed durable history and projection requirements do not commit MVP to Event Sourcing, a new runtime module, API, schema, feature, or physical service.

## SPG Core Logical Responsibility Model — Confirmed

```text
Production Planner
        ↓
Production Governance Runtime
        ↓
Production State Projection
```

| Logical responsibility | Responsibility boundary |
|---|---|
| Production Planner | Owns production planning and adaptive plan evolution; proposes plans / production changes |
| Production Governance Runtime | Sole logical authority validating, admitting, and performing authoritative SPG production-state transitions |
| Production State Projection | Produces current understandable views from persisted production facts; not the final production authority |

Executor reports execution facts / artifacts; Verification / Guardian reports verification / assurance facts; Human Governor issues authority decisions. None directly mutate authoritative production reality. Runtime owns transition semantics, not Human Authority, business decisions, artifact content, or Assurance Truth.

**No Actor Owns Production Truth Alone; Distributed Responsibility, Governed Adjudication.** Runtime adjudicates domain-owned inputs through explicit contracts and transition rules; it does not invent or solely own all truth. This is not majority voting. Provider consolidation must not collapse logical Authority / Contract boundaries. **Replaceable Intelligence, Durable Governance** allows stronger providers wider policy-bounded autonomy, not unrestricted authority or an assumption of equal model capability. See [architecture principles](architecture-principles.md).

The model is frozen **only as logical responsibility decomposition**, not deployable services or microservices. The capability descriptions below are read under this authority boundary.

## State Foundation and Human–Machine Governance

Trusted Production Baseline → Working Production State → exact sealed Baseline Candidate → Eligibility → Authorization → Commit → New Trusted Production Baseline.

Trusted Baselines are immutable reference sets. Working State has stable identity and evolving projections with preserved history. Executable PWUs bind to explicit source Baseline / Plan Revision; material plan changes create new revisions, and executable PWU meaning cannot be silently rewritten after an attempt starts. Execution Attempts preserve concrete execution facts; State Transition Journal durably preserves material governance transitions.

Only successful Commit changes Current Trusted Baseline authority, after validating the expected source Baseline. Failure before the authoritative switch leaves the previous Baseline authoritative; failure of derived views or follow-up synchronization after the switch does not undo it. Git remains authoritative for code history, not the entire governed production reality.

**Human Authority Does Not Imply Runtime Bypass.** Human Agency First preserves intent, direction, constraints, risk, exceptions, and applicable final acceptance; it does not make the human an unrestricted production superuser. Human, AI, Executor, Guardian, and other actors are governed participants with different Responsibility / Authority. Equal submission to governance does not mean identical authority.

PWU obligations use the working semantic term **Satisfied**; Human / Policy Final Acceptance primarily targets an exact Baseline Candidate, not every PWU by default. Integrated is derived lineage/integration state, not a mandatory primary PWU terminal state. Detailed completion semantics remain for C.

See the [closed State Foundation record](spg-state-foundation.md) for definitions, failure boundaries, all 20 invariants, and the explicit MVP complexity guard.

The [closed Reconciliation & Recovery record](spg-reconciliation-recovery.md) distinguishes execution success from production validity and restores coherent governance before execution resumes. The [closed Completion & Trust record](spg-completion-trust.md) distinguishes Produced, Satisfied, Trusted Completion, and Commit. The [Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md) remains future verification work only; it implements no tests or trust mechanisms.

## Software Production Governor (SPG)

SPG is the Software Production Governor: a capability-oriented software production governance layer.

SPG manages software production state and drives the governed production loop. It is not a Project Manager, Super AI Brain, or Decision Engine.

## Production State Management Principle

> SPG manages software production state, not merely project status.

Traditional project status focuses on Task, Owner, Status, and Progress. SPG Production State represents the current reality of software production:

- Intent
- Design
- Production Progress
- Change
- Artifact
- Verification
- Trust Level

Production State answers:

- What is the current goal?
- What is the currently accepted design?
- How far has production progressed?
- What changed recently?
- How trustworthy is the current artifact?
- What action is allowed next?

## Production State Manager

Production State Manager remains a capability grouping for **Reality Tracking + State Transition Governance**, not an additional authority. Under the confirmed logical decomposition, authoritative transitions belong exclusively to Production Governance Runtime; consumable state views belong to Production State Projection.

### State Projection

Derives current views from persisted production facts. The view may be rebuilt and is not the final authority; this does not require Event Sourcing.

### State Transition Governance

Uses Production Governance Runtime to validate, admit, and perform governed state transitions. This capability grouping does not directly mutate authoritative state.

### Reality Synchronization

Synchronizes:

- Executor results
- Guardian results
- ECF Context
- Human Approval

### State Query

Provides queries over current production reality.

### Responsibility Boundary

| Responsibility | Owner |
|---|---|
| Business / Strategic Decision | Human Authority, supported by Decision Intelligence Capability |
| Production Planning | Production Planner |
| Quality Assurance | Guardian |
| Engineering Context | ECF |

YiJue may support Business / Strategic Decision as a Decision Intelligence Provider; the responsibility is not assigned to the YiJue product itself.

## Event-driven Production State Model

This is a **Future Architecture Direction**, not an MVP requirement.

The long-term model is:

```text
Production Events
        ↓
State Projection
        ↓
Current Production State
```

Example events include:

- IntentCreated
- BlueprintGenerated
- PlanCreated
- WorkItemStarted
- ArtifactGenerated
- VerificationCompleted
- BaselineCommitted

An Event records **what happened**. State represents **what is currently true**.

## Engineering Consistency Principle

> Software production conflicts should not be limited to code conflicts. The system must consider engineering intent, design constraints, and behavioral consistency.

Future conflict categories may include:

- Code Conflict
- Design Conflict
- Behavior Conflict
- Intent Conflict
- Context Conflict

## Engineering Conflict Detection

This is a **Future Capability / Architecture Hypothesis**.

Its purpose is to detect situations where:

> Code can merge, but engineering meaning cannot safely merge.

It is concerned with semantic engineering consistency beyond code-level merge conflicts. It is not implemented in the MVP.

## Runtime Orchestrator

Runtime Orchestrator is the capability that:

> Drives the software production loop according to Production State.

It is responsible for:

### State Observation

Observes current Production State.

### Transition Decision

Coordinates the next permitted action from current state and applicable boundaries. Authoritative production-state changes must pass through Production Governance Runtime; Runtime Orchestrator is not a parallel transition authority.

### Capability Routing

May coordinate:

- Production Planner
- Executor Capability
- Guardian
- ECF
- Decision Intelligence Capability, when necessary

### Workflow Execution

Executes the software production workflow.

Runtime Orchestrator is not a Project Manager, Super AI Brain, or Decision Engine.

## Governed Adaptation Principle

AI-native production is neither a completely fixed process nor a freely generated process. The long-term model is:

```text
Production Pattern + Policy Constraint + AI Adaptation
        ↓
Governed Adaptation
```

Pattern provides experience boundaries. Policy provides safety constraints. AI adapts the process according to context.

This is an Architecture Direction; complete adaptive workflow capability is not implemented in the MVP.

## SPG Core Architecture Snapshot

```text
Software Production Governor (SPG)
├── Production Planner
│   ├── Generate Blueprint
│   ├── Generate Plan
│   └── Adapt Plan
├── Runtime Orchestrator
│   └── Execute Production Loop
├── Production State Manager
│   └── Maintain Production Reality
├── Artifact Steward
│   └── Manage Engineering Facts
├── Impact Analyzer
│   └── Analyze Change Impact
└── Progress Intelligence
```

SPG uses Capability-oriented Architecture, not AI Employee Architecture. This snapshot remains a capability inventory, read under the confirmed Planner → Governance Runtime → State Projection logical responsibility model above. It does not establish competing state authorities or require each capability to be a separate runtime module.

## SPG Production Loop

```text
Observe
   ↓
Understand
   ↓
Plan
   ↓
Execute
   ↓
Verify
   ↓
Update State
   ↓
Replan
```

This is the SPG continuous production loop.

## MVP Boundary

### MVP Include

- Production Intent
- Production Plan
- Iteration
- Work Item
- Artifact Tracking
- Progress View
- Basic Production State
- Human Intervention

### Future Capability

The following are explicitly not MVP capabilities:

- Semantic Conflict Detection
- Production State Merge
- Multi-user Production Branch
- Autonomous Process Optimization
- Self-learning Production Pattern Evolution
- Event-driven Production State implementation
- Complete Governed Adaptation automation

## Architecture Relationship Summary

```text
Decision Intelligence Capability
        ↓
Approved Decision Artifact
        ↓
SPG
Production Governance
        ↓
Software Production
        ↓
Guardian
Assurance Intelligence

ECF
Context Intelligence
```

YiJue, SPG, Guardian, and ECF retain separate responsibilities, ownership, Source of Truth, and lifecycle boundaries. This document does not modify their internal designs.

## Validation Boundary

- No Design Lead AI architecture name is introduced; the current name is Production Planner.
- Future capabilities are explicitly marked as Future Capability, Architecture Direction, or Architecture Hypothesis.
- YiJue, Guardian, and ECF responsibilities are not expanded or reassigned.
- No MVP feature, API, database model, or code implementation is added by this document.

## Production Autonomy Governance

> SPG should maximize AI production autonomy within explicit organizational risk boundaries.

SPG should pursue **Governed Autonomy**:

- Not Human approval of every AI action
- Not AI deciding everything

The degree of autonomy should be determined by impact scope, risk, and reversibility rather than by operation type alone.

Relevant factors include:

- Intent Impact
- Authority Impact
- Constraint Impact
- Architecture Impact
- Risk Level
- Reversibility

## SPG Autonomy Level Model

This is an Architecture Direction:

```text
Level 0 — Manual Production
Level 1 — AI Assisted Execution
Level 2 — Workflow Automation
Level 3 — Bounded Autonomous Production
Level 4 — Adaptive Production System
Level 5 — Autonomous Software Organization
```

The MVP target is Level 2–3. Level 4 is a long-term direction. Level 5 is a Research Direction.

## Production Autonomy Policy

A future Production Autonomy Policy should configure autonomy boundaries rather than hard-code them. It may define:

- Allowed Autonomous Actions
- Required Approval
- Escalation Rules
- Risk Constraints

For example, a low-risk change may be executed automatically, an architecture change may require approval, and a security-boundary change may require immediate escalation.

This policy capability is a Future Capability / Architecture Direction and is not fully implemented in the MVP.

## Autonomy Boundary Principle

The Human Governor does not approve every individual step. Human responsibility is to define:

- Intent
- Risk Tolerance
- Authority Boundary
- Policy

Within the authorized boundary, AI may perform Planning, Execution, and Adaptation.

## Production Completion Intelligence — Confirmed C Semantics

> SPG must understand when software production has reached an acceptable and trustworthy completion state.

Completion is layered:

```text
Execution Attempt Finished
!= Work Product Produced
!= PWU Satisfied
!= Production Plan Complete
!= Trusted Completion
!= Committed Trusted Production Change
```

The [C closure](spg-completion-trust.md) confirms Output Obligation Manifest, versioned PWU / Plan Completion Contracts, Verification Basis, Evidence Freshness, policy-driven Authority, and Trusted Completion. Completion criteria precede claims; Executor self-report cannot establish Satisfaction. Production Completion remains distinct from Business Outcome Achievement.

Trusted Completion means an exact Baseline Candidate satisfies required Completion, Verification, Policy, and Authority obligations. It is not itself Trusted Production Reality; only successful Commit changes the Trusted Production Baseline.

Guardian / Verification retains assurance truth and Evidence qualification. SPG owns Completion Contracts, required Verification obligations, state-transition eligibility, Candidate admissibility use, and Commit governance. These are confirmed architecture semantics, not an implemented Completion engine, Guardian, Trust Score, schema, or workflow.

### MVP boundary

SPG Lite may use simple explicit Completion, Verification, and Authorization records. Trust Graphs, Evidence ontologies, Policy DSL, multi-authority engines, Trust scoring, full Verification orchestration, and other deferred mechanisms are not MVP requirements.

## Side-effect Governance — Confirmed D Semantics

The [D closure](spg-side-effect-governance.md) confirms that External Side Effects cross the disposable execution boundary. Physical Change, Authoritative Production Change, and Observed External Reality remain distinct.

Side-effect Intent, scoped Permit / Authorization, and stable Effect Operation Identity are separate logical semantics. Execution capability does not imply Side-effect Authority; Permit freshness and Attempt fencing extend to the external boundary. Runtime does not assume universal CAS, exactly-once execution, or broad permanent Executor credentials.

Observed External Reality may diverge from Trusted Reality and reuses B-level reconciliation. Compensation is new governed production based on current observed reality and appends history. **Governed Integration Atomicity** makes transitions identifiable, authorized, observable, reconcilable, and recoverable without claiming universal physical atomicity.

These are architecture semantics, not Side-effect Gateway, deployment automation, Saga, 2PC, compensation engine, schema, API, or implementation readiness.

## Planning Continuity Principle

> AI-native production systems must maintain project intent, discussion context, and planned reasoning continuity despite local interaction interruptions.

The system should not lose the overall production objective, planned path, or reasoning continuity because of a local interaction interruption.

The production system should distinguish:

- Main Production Objective
- Current Planned Agenda
- Temporary User Inquiry
- New Decision Requirement

SPG should not simply follow the latest input without considering the main production line.

## Intent Classification Before Response

This is a Future Capability / Architecture Direction. SPG may classify an input as:

1. Main Task Progression
2. Temporary Question
3. New Requirement
4. Architecture Change Request
5. Exploration Discussion

According to the classification, the system may directly process it, record a follow-up, create a new Decision, update the Plan, or return to the main line.

## MVP Boundary for Autonomy, Completion, and Continuity

The MVP includes:

- Basic autonomy policy
- Human approval points
- Basic completion conditions
- Progress tracking

The MVP does not include:

- Fully adaptive autonomy
- Dynamic policy learning
- Outcome-based automatic completion
- Advanced interruption management

The autonomy, completion intelligence, and continuity capabilities described above remain explicitly separated into Current Architecture Principles and Future Capability directions.

## Production Intent Governance

> SPG maintains continuous awareness of software production intent, active goals, planned agenda, and change impact, ensuring that temporary interactions do not unintentionally disrupt the production process.

Production Intent Governance maintains production coherence across time and interaction. It is a Future Capability / Architecture Direction and is not a complete MVP implementation.

## Goal-oriented Interaction Principle

AI-native production is not:

```text
Input → Response
```

It is:

```text
Production Goal
        ↓
Current Agenda
        ↓
User Input
        ↓
Impact Assessment
        ↓
Appropriate Action
```

User input does not automatically become the highest-priority event. The system first assesses how the input affects the current production goal.

## Production Intent Hierarchy

```text
Production Intent
        ↓
Active Production Agenda
        ↓
Current Work Item
        ↓
User Interaction
        ↓
Temporary Exploration
```

Content closer to Production Intent has higher production priority.

## Intent Classification Before Response

A future SPG capability should classify user input as:

### Type 1: Main Production Progression

Directly enters the current production flow.

### Type 2: Temporary Question

Receives an answer and then returns to the main production line.

### Type 3: Exploration Discussion

Records insight without automatically changing Production State.

### Type 4: Requirement Change

Enters Impact Analysis.

### Type 5: Architecture Change Request

Pauses the relevant flow and enters Architecture Review.

This is a Future Capability / Architecture Direction, not a current complete implementation.

## Production Agenda

Production Agenda is a persistent representation of current production objectives, active topics, planned discussions, and next actions.

```text
Program Goal
        ↓
Current Production Objective
        ↓
Current Phase
        ↓
Active Topic
        ↓
Pending Topics
        ↓
Next Planned Actions
```

Example:

```text
Goal: Build AI Native Software Platform
Current Topic: Autonomy Boundary Design
Next Topics: Completion Intelligence; Authority Model; Multi-user Coordination
```

## Controlled Interruption Principle

Users may raise new questions at any time. SPG should classify the input, assess its impact, and decide whether the interaction should:

- Continue
- Pause
- Branch
- Replace

```text
User Input
        ↓
Intent Classification
        ↓
Impact Assessment
        ↓
Action Decision
```

### Continue

The input does not affect the current production path.

### Pause

The current task is temporarily suspended.

### Branch

A separate exploration path is created. This is a Future Capability and is not implemented in the MVP.

### Replace

The current Production Intent is changed through the applicable governance process.

## Component Boundary

Production Intent Governance does not replace:

- **Production Planner:** Production Planning
- **Runtime Orchestrator:** Workflow Execution
- **Production State Manager:** Production State

It maintains production coherence across time and interaction.

## Relationship with Other Systems

- **Decision Intelligence Capability:** evaluates Decision Frame changes and helps answer “Should we change direction?” YiJue may provide this capability through the provider-independent contract.
- **SPG:** governs Production Frame changes and answers “How should production continue?”
- **ECF:** provides Context and historical facts.
- **Guardian:** verifies whether a change is trustworthy.

## AI Native Production Continuity Principle

> AI-native software production systems must preserve long-running production intent and reasoning continuity instead of behaving as stateless conversational assistants.

## MVP Boundary for Production Intent Governance

The MVP only needs to:

- Preserve the current Production Goal
- Preserve the Active Agenda
- Support human confirmation of major direction changes

The MVP does not implement:

- Complete autonomous intent management
- Automatic branch governance
- Automatic long-term planning optimization


## SPG Authority Model

> SPG authority is not traditional permission management. It governs who has authority to approve, define, and execute engineering state transitions.

Traditional systems commonly model:

```text
User → Role → Permission → Action
```

AI-native production systems should model:

```text
Authority → Change Impact → Allowed Transition
```

The authorization object is not merely an Action. It is **Engineering Change Authority**: authority over changes to engineering facts and production state.

## Change Authority Principle

> In AI-native software production systems, authorization should be based on the impact of changes rather than the type of actions.

Relevant factors include:

- Intent Impact
- Authority Impact
- Constraint Impact
- Architecture Impact
- Risk Level
- Reversibility

## Human Governance Role Model

Human Governor is a governance responsibility, not a specific job title and not an equivalent of Administrator.

```text
Human Governance
├── Human Governor
├── Organization Administrator
├── Product Authority
├── Architecture Authority
├── Security Authority
└── Developer / Engineer
```

Different people may hold the same governance responsibility in different organizations.

## Authority Layer Model

### Layer 1: Governance Authority

Responsible for Intent, Risk Boundary, and Autonomy Policy.

### Layer 2: Domain Authority

Responsible for Product Decision, Architecture Decision, and Security Decision.

### Layer 3: Execution Role

Responsible for Implement, Execute, and Validate.

## Authority Chain

```text
Human Governance Authority
        ↓
Domain Authority
        ↓
SPG Runtime
        ↓
Executor
```

This is not a traditional organizational hierarchy. It represents different types of responsibility and authority.

## SPG and Decision Intelligence Authority Boundary

Decision Intelligence Capability structures and evaluates **Should**, Decision Validity, and Business / Strategic Choice. Human Authority retains applicable approval and accountability. YiJue may provide the capability as an independently evolving Consumer Product / provider implementation.

SPG is responsible for **How**, Production Planning, and Production Execution.

When SPG discovers that production requires a change to the goal, direction, or value trade-off, it must not decide autonomously:

```text
Production Issue
        ↓
Decision Required
        ↓
Decision Intelligence Engine / Provider
        ↓
Decision Artifact
        ↓
SPG Updates Production Plan
```

## Multi-Actor Production Coordination

AI-native software production includes multiple actors:

- Human
- AI Planner
- AI Executor
- AI Reviewer
- External System

The collaboration model evolves from Code Collaboration to **Production Collaboration**.

## Semantic Production Conflict

Traditional collaboration focuses on Text Conflict and Code Conflict. AI-native production must also consider Semantic Production Conflict.

> Two changes may have no textual conflict but may conflict in production intent, architecture, context, or system behavior.

Future conflict categories may include:

- Intent Conflict
- Design Conflict
- Context Conflict
- Artifact Conflict
- Verification Conflict

Semantic conflict detection is a Future Capability / Architecture Direction, not an MVP implementation.

## Production Change Proposal

A production change should not directly modify Production State in the long-term model. It should first form a **Production Change Proposal**.

```text
Production Change Proposal
├── Intent
├── Affected Area
├── Expected Impact
├── Artifacts
├── Risk
├── Verification Plan
└── Authority Requirement
```

Production Change Proposal is a Future Capability / Architecture Direction and is not implemented in the MVP.

## Production State Integration Direction

The future model evolves from:

```text
Git Branch → Code Merge
```

To:

```text
Production State Branch → Production State Integration
```

A Production State Branch may contain:

- Intent
- Context Snapshot
- Plan
- Change Set
- Artifact
- Evidence

## Future Production Merge Principle

Future integration is not merely code-difference merging. It is production-state integration that considers:

- Intent Compatibility
- Design Compatibility
- Context Compatibility
- Artifact Compatibility
- Verification Compatibility

Production Branch, Semantic Conflict Detection, Production State Merge, and Multi-Agent Coordination are Future Capabilities / Architecture Directions, not MVP implementations.

## MVP Boundary for Authority and Coordination

The MVP retains only:

- Basic Authority Role
- Basic Approval Boundary
- Basic Change Ownership

The MVP does not implement Production Branch, Semantic Conflict Detection, Production State Merge, or Multi-Agent Coordination.

## From Code Collaboration to Production Collaboration

Traditional software collaboration centers on:

```text
Code Change → Code Merge
```

AI-native software production evolves toward:

```text
Production Change → Production State Integration
```

Multiple intelligent production actors may change a system concurrently. Even when code has no textual conflict, system-level conflict may still exist.

This is a Current Architecture Principle. It does not imply that the integration mechanisms are implemented in the MVP.

## Production State Branch

> A Production State Branch represents an alternative software evolution path based on a specific production intent, context, and change hypothesis.

A Production State Branch is a software future-state evolution space organized around a particular intent and change hypothesis.

It is not a Git Branch:

- Git Branch manages code evolution.
- Production State Branch manages production-state evolution.

### Production State Branch Structure

This is a Future Capability / Architecture Direction:

```text
Production State Branch
├── Intent Layer
├── Context Snapshot
├── Baseline Layer
├── Production Plan
├── Change Proposal Set
├── Verification Evidence
└── Production State
```

### Relationship with Git

Production State Branch does not replace Git. It is a higher-level production-semantic container that may contain a Git Branch or Implementation Branch.

```text
Production State Branch
        contains
Git Branch / Implementation Branch
```

### Branch Creation Principle

Not every change should create a Branch. Production Planner may consider:

- Change Scope
- Risk
- Reversibility
- Dependency
- Impact

The outcome may be direct modification or creation of a Production State Branch. This decision model is not implemented in the MVP.

## Production State Version

> Production State Version is a version of trusted production reality, not merely a code snapshot.

A future Production State Version may contain:

- Code Version
- Architecture Baseline
- Decision Baseline
- Context Snapshot
- Verification Evidence

Production State Version is a Future Capability / Architecture Direction.

## Production State Integration

Future integration is not merely Code Merge. It is **Production State Integration**.

Before integration, the system should assess:

- Intent Compatibility
- Architecture Compatibility
- Context Compatibility
- Artifact Compatibility
- Verification Compatibility

This is a Future Capability / Architecture Direction, not an MVP implementation.

## Production State Merge Intelligence

Production State Merge Intelligence is a future capability responsible for judging whether multiple production-state changes can jointly form a new trusted production state.

Potential outcomes include:

- Compatible
- Merge With Conditions
- Conflict Detected
- Decision Required

It is not implemented in the MVP.

## Semantic Conflict Engine

> Detect conflicts in production meaning rather than only textual differences.

Semantic Conflict Engine is a Future Capability / Architecture Direction for detecting semantic production conflicts beyond code text.

### Semantic Conflict Taxonomy

Future conflict categories may include:

- Intent Conflict
- Assumption Conflict
- Constraint Conflict
- Architecture Conflict
- Domain Conflict
- Context Conflict
- Verification Conflict

### Conflict Detection Pipeline

A future model may use:

```text
Semantic Extraction
        ↓
Semantic Alignment
        ↓
Dependency Impact Analysis
        ↓
Invariant Checking
        ↓
Verification
        ↓
Conflict Resolution
```

### Conflict Resolution Boundary

Semantic Conflict Engine does not replace the decision system:

```text
Conflict Detection
        ↓
Decision Required?
        ↓
Decision Intelligence Engine / Provider
        ↓
Decision Artifact
        ↓
Continue Production
```

## Relationship with Guardian

The capabilities are complementary:

- **Guardian:** Is this change trustworthy?
- **Semantic Conflict Engine:** Can multiple trustworthy changes coexist?

Semantic Conflict Engine does not replace Guardian, and Guardian does not own semantic production integration.

## MVP Boundary for Production State Integration

The MVP does not implement:

- Production State Branch
- Semantic Conflict Engine
- Production Merge Pipeline
- Automated Semantic Merge

The MVP retains:

- Production State Snapshot
- Change Proposal
- Artifact Lineage
- Verification Evidence

These retained capabilities do not imply that branch creation or semantic merging is implemented.

## Production Work Unit Generalization Principle

> Production Work Unit represents a governed production activity that transforms intent into a validated production outcome. It is not limited to coding activities.

Production Work Unit is a production-governance abstraction rather than a synonym for Coding Task. Categories may include:

- **Implementation Work Unit:** code implementation, API development, configuration changes.
- **Documentation Work Unit:** architecture document update, API specification, Decision Record.
- **Context Preparation Work Unit:** repository analysis, context package generation, knowledge extraction.
- **Analysis Work Unit:** root cause analysis, impact analysis, architecture analysis.
- **Verification Work Unit:** test execution, security verification, benchmark evaluation.
- **Planning Work Unit:** production planning, migration planning, refactoring planning.

The categories define production responsibility only. They do not require dedicated runtimes, workflows, or MVP features.

## Production Artifact Domain

> Production Artifact represents all governed outputs generated during software production.

```text
Production Artifact Domain
   ├── Code Artifact
   ├── Documentation Artifact
   ├── Context Artifact
   ├── Analysis Artifact
   └── Verification Artifact
```

Production Artifact is the domain category. **Work Product Artifact** is a concrete output of a Production Work Unit.

A Verification Artifact is a raw Work Product from verification activity; Verification Evidence is qualified within the Guardian / Assurance authority boundary. A Context Artifact is a generated Work Product; an authoritative Context Projection remains governed by ECF. The taxonomy does not transfer Guardian or ECF ownership to SPG.

```text
Production Intent
        ↓
Production Work Unit
        ↓
Work Product Artifact
        ↓
Verification Evidence
        ↓
Trusted Production State
```

The producing Execution System or Capability Provider retains ownership of the generated artifact. SPG governs the Work Unit and coordinates artifact lifecycle, lineage, and production-state transitions; it does not become a Coding Platform, Documentation System, Knowledge Management System, or universal artifact repository.

## From Resource Management to Capability Management

Traditional software organization often follows:

```text
Project
   ↓
Assign People
```

AI-native software production evolves toward:

```text
Production Need
   ↓
Production Work Unit
   ↓
Capability Allocation
   ↓
Human / AI Provider
```

The long-term scheduling object is production capability, not simply a person or Agent.

## Capability Unit

> A Capability Unit represents a reusable production capability that can be assigned to Production Work Units.

A Capability Unit may contain:

- Capability Identity
- Purpose
- Input Requirement
- Output Contract
- Required Context
- Authority Requirement
- Verification Requirement
- Performance History

Capability Unit is a stable capability abstraction. It is not equivalent to an Agent.

## Capability and Provider Separation

A Capability may be provided by different provider types:

```text
Capability
   ├── AI Provider
   ├── Human Provider
   └── Tool Provider
```

For example, Architecture Analysis Capability v1 may be provided by different AI models or a human architect. The Capability Contract remains independent of the provider implementation.

## Capability Provider

Capability Provider is the concrete actor that provides a production capability. It may be:

- Human Expert
- AI Executor
- External Service
- Tooling System

A Provider does not own the final capability definition. The Capability Contract exists independently.

## Capability Registry

Capability Registry is a future enterprise production capability directory. It may record:

- Capability ID
- Capability Contract
- Provider
- Required Context
- Authority Requirement
- Historical Performance
- Evidence History
- Cost
- Availability

It may support Production Planner in capability matching and scheduling. Dynamic registry intelligence is a Future Capability / Architecture Direction.

## Capability Matching

The future matching flow is:

```text
Production Work Unit
        ↓
Capability Requirement
        ↓
Capability Matching
        ↓
Provider Selection
        ↓
Execution
```

Matching may consider:

- Capability Fit
- Domain Experience
- Historical Performance
- Cost
- Availability
- Authority Compatibility

Dynamic Capability Matching is not implemented in the MVP.

## Capability Identity Principle

Production capabilities should not be bound to a specific model or executor. A capability should be named by responsibility and contract, such as **Architecture Analysis Capability v1**, rather than a provider-specific name such as a model-based Architecture Agent.

This preserves executor replacement, model evolution, and independent capability lifecycle.

## Capability Evolution

A capability may evolve through versions:

```text
Capability v1 → Capability v2 → Capability v3
```

Future evolution may use:

- Benchmark
- Guardian Evidence
- Outcome Feedback
- Historical Performance

Capability evolution is a Future Capability / Architecture Direction.

## Capability Performance Feedback

**The System Consumes Capabilities, Not Intelligence Prestige.** Future evaluation should describe performance for a specific Provider × Capability under governed Task / PWU conditions, not reduce a model to one global intelligence score. One provider may have different performance profiles in Planning, Implementation, Documentation, Architecture Analysis, and Verification.

```text
Controlled benchmarks + Governed Capability Execution history
        ↓
Verification / Guardian Evidence + Production telemetry
        ↓
Governed outcome evidence
        ↓
Capability Performance Profile (Provider × Capability)
```

A **Capability Performance Profile** is a future benchmark- and production-history-backed description, not provider marketing or a frozen scoring schema. See the [Runtime Benchmark Strategy](spg-runtime-verification-benchmarks.md#51-capability-performance-profile) for candidate dimensions, equivalent-outcome comparison, and the feedback relationship to Planner decomposition, routing, autonomy, verification, and user strategy selection.

**Task Decomposition Is Also Resource Allocation:** capability and reliability may influence safe PWU granularity. Wider autonomy requires capability-specific evidence and policy permission, not a model's brand or price. These are design principles; profiles, adaptive allocation, and routing remain future capabilities, not MVP implementations.

This feedback preserves **Replaceable Intelligence, Durable Governance**. Provider performance cannot redefine Production Contracts, State semantics, Authority, Guardian's trust model, or governance invariants. Evidence informs choices without transferring authoritative state-transition responsibility to the provider.

## Production Capability Graph

> Production Capability Graph is an enterprise software production capability relationship map.

Future nodes may include:

- Capability
- Provider
- Artifact
- Evidence
- Project
- Domain

Future relationships may include:

- Capability used for
- Capability depends on
- Capability verified by
- Capability improved by

Capability Graph Intelligence is a Future Capability / Architecture Direction.

## M×N AI-native Organization Model

Traditional organization often maps:

```text
Person → Project
```

AI-native production may map:

```text
Production Need
        ↓
Production Work Unit
        ↓
Capability Allocation
        ↓
Human / AI Provider
```

This creates an M×N model:

- One capability can serve multiple projects.
- One project can dynamically compose multiple capabilities.

Automatic organization formation is not implemented in the MVP.

## Relationship with SPG Production Concepts

```text
Production Goal
        ↓
Production Planner
        ↓
Production Work Unit
        ↓
Capability Allocation
        ↓
Execution
        ↓
Work Product Artifact
        ↓
Guardian Verification
        ↓
Production State Update
```

Production Planner plans and allocates capability requirements. It does not redefine the ownership of Decision Intelligence Capability, Guardian Assurance Intelligence, or ECF Context Intelligence.

## MVP Boundary for Capability Management

The MVP supports only:

- Capability Interface
- Basic Capability Registry
- Manual Capability Assignment

The MVP does not implement:

- Dynamic Capability Matching
- Capability Marketplace
- Capability Graph Intelligence
- Automatic Organization Formation

These remain Future Capabilities / Architecture Directions.

## Software Production Efficiency Evolution

Traditional software production can be represented as:

```text
Output = Human Capability × Time
```

AI-native software production extends this model:

```text
Output = Human Judgment × AI Execution Capacity × Production System Efficiency
```

AI value is not limited to replacing execution. It also improves the efficiency of the overall production system.

## Cost per Trusted Change

> Trusted Production Cost, expressed as Cost per Trusted Change, is the total cost required to produce an accepted Trusted Production Change, not the model API cost of one request.

The conceptual cost decomposition includes Model / Executor Cost, Planning / Decomposition Cost, Verification / Assurance Cost, Retry Cost, Rework Cost, Human Attention Cost, Recovery Cost, Delay Cost, and Failure Propagation Cost. Governance coordination remains part of the relevant production effort; future accounting must avoid counting overlapping effort twice. This is not a frozen accounting formula or a new production-state object.

A higher-cost provider may reduce retries, rework, verification rounds, and Human attention or support larger safe PWUs and longer autonomous runs. Safe autonomy is therefore a potential economic output. **The cheapest model call is not necessarily the cheapest production capability**; higher price alone does not establish lower total cost.

The [Runtime Benchmark Strategy](spg-runtime-verification-benchmarks.md#6-future-production-economics-measurement) is the detailed reference for this cost decomposition and the **Trusted Change Efficiency** candidate metric family, measured against equivalent governed production objectives. Metric definitions, weights, and thresholds remain future work.

**Price Should Correspond to Observable Production Value** and **No Model Prestige Pricing** guide [future strategy selection](future-capabilities.md#benchmark-backed-model--production-strategy-selection). Users may eventually choose production-economic configurations backed by evidence, not opaque model labels. No prices, billing plans, tiers, or MVP capabilities are introduced.

## AI-native Production Bottleneck Shift

Traditional software bottlenecks include coding speed, human scale, and communication cost.

As AI increases execution capacity, bottlenecks shift toward:

- Context Management
- Decision Quality
- Verification Cost
- Production Coordination

This is why Decision Intelligence, Production Governance, Assurance Intelligence, and Context Intelligence must work together while retaining separate boundaries.

## Human Leverage Model

AI-native organization is not defined simply by reducing the number of people. It increases the **Human Leverage Ratio**: how much production capability one person can govern and drive.

The long-term model is:

```text
Human Governance
        ↓
Multiple AI Production Capabilities
```

Human judgment and accountability remain central while AI expands the governed production capacity.

## Software Factory Direction

Traditional software services primarily sell Human Time. A future AI Software Factory may provide Trusted Software Production Capability.

Customers would obtain outcomes and production capability rather than simply purchasing human effort. This is a Future Business Direction, not a current SPG capability or MVP scope.

The Software Production System is the underlying capability system; a Software Factory is one possible future commercial form built on it.

## Production Recipe / Software Production Process Asset

Scaling software production may require reusable Production Recipes: software production process assets composed of:

```text
Standard Process + Context Adaptation + AI Optimization
```

A Recipe is neither a completely fixed process nor a randomly generated AI workflow. It preserves a standard route while allowing contextual adaptation and AI improvement.

Production Recipe is a Future Capability / Business Direction and is not implemented in the MVP.

## AI Software Factory Flywheel

A future value flywheel may be:

```text
More Projects
        ↓
More Production Data
        ↓
Better Capability
        ↓
Better Recipe
        ↓
Lower Trusted Production Cost
        ↓
More Competitive Delivery
        ↓
More Projects
```

This is a Future Business Direction, not a statement of current capability.

## System Value Boundary

The long-term capability relationship is:

```text
Decision Intelligence Capability
        │ Decision Artifact Contract
        v
SPG Production Governance ───────→ Execution
        ^                              │
        │                              v
ECF Engineering Context          Guardian Assurance
                                       │ Evidence
                                       v
                              SPG Production State
```

Each system retains separate responsibility, ownership, Source of Truth, authority, and lifecycle boundaries.

## MVP Guidance

The current objective is not to build a complete AI Software Factory. The guiding principle is:

> Current Product First, Architecture Future Ready.

The current SPG design should:

- Support rapid YiJue development
- Remain operable without waiting for YiJue Decision Engine completion
- Validate the AI-native engineering loop
- Preserve future extension boundaries

Future directions may include Capability Management, Production State Platform, Semantic Merge, and Enterprise Governance. These are not current MVP implementations.
