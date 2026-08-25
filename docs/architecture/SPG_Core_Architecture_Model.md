# SPG Core Architecture Model

This document records the current SPG architecture model and its future architecture directions. It is an Architecture Decision record, not an implementation specification. Future Capability and Architecture Hypothesis statements are not current capabilities.

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

Production State Manager is responsible for **Reality Tracking + State Transition Governance**.

### State Projection

Derives current state from production events.

### State Transition Governance

Governs whether a state transition is valid.

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
| Business Decision | YiJue / Human |
| Production Planning | Production Planner |
| Quality Assurance | Guardian |
| Engineering Context | ECF |

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

Determines the next permitted action from current state and applicable boundaries.

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

SPG uses Capability-oriented Architecture, not AI Employee Architecture. This snapshot is a capability model and does not require each capability to be a separate runtime module.

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

## Production Completion Intelligence

> SPG must understand when software production has reached an acceptable completion state.

Completion is not equivalent to `Task Completed`. It is:

> Production Reality Meets Completion Contract.

### Completion Layers

SPG Completion Judgment may distinguish:

- **Intent Completion:** whether the goal remains valid
- **Plan Completion:** whether the production plan is complete
- **Artifact Completion:** whether required production artifacts are complete
- **Engineering Completion:** whether engineering quality and verification requirements are met
- **Outcome Completion:** whether the intended real-world value is achieved

Responsibility is separated across systems:

```text
Decision Validity       → Decision Intelligence Capability
Production Completion   → SPG
Engineering Trust       → Guardian
Business Outcome        → Reality / External System
```

Production Completion Intelligence is a Future Capability / Architecture Direction, not a current implementation capability.

## Completion State Model

A future completion model should not be a simple Boolean:

```text
PLANNING
    ↓
IMPLEMENTING
    ↓
VERIFYING
    ↓
PRODUCTION_COMPLETE
    ↓
OUTCOME_PENDING
    ↓
OUTCOME_CONFIRMED
```

## Completion Contract

A future Completion Contract defines before production what conditions constitute completion. It may include:

- Expected Artifact
- Verification Requirement
- Quality Gate
- Acceptance Condition

Completion Contract is a Future Capability / Architecture Direction and is not fully implemented in the MVP.

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

- **YiJue:** evaluates Decision Frame changes and helps answer “Should we change direction?”
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

## SPG and YiJue Authority Boundary

YiJue is responsible for **Should**, Decision Validity, and Business / Strategic Choice.

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

Future capability evaluation should be evidence-based rather than based only on subjective scores:

```text
Capability Execution
        ↓
Guardian Verification
        ↓
Outcome Evidence
        ↓
Capability Performance Model
```

This model may support future capability selection and optimization. It is not implemented in the MVP.

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

> Cost per Trusted Change is the comprehensive cost of moving one software change from Intent to a trusted Production State.

It may include:

- Planning Cost
- Execution Cost
- Verification Cost
- Governance Cost
- Rework Cost

The strategic competition is not simply about the lowest code-generation cost. It is about the lowest cost of trusted software production.

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
        ↓
SPG
Production Governance
        ↓
Guardian
Assurance
        ↓
ECF
Engineering Context
        ↓
Production State
Software Evolution Management
```

Each system retains separate responsibility, ownership, Source of Truth, authority, and lifecycle boundaries.

## MVP Guidance

The current objective is not to build a complete AI Software Factory. The guiding principle is:

> Current Product First, Architecture Future Ready.

The current SPG design should:

- Support rapid YiJue development
- Validate the AI-native engineering loop
- Preserve future extension boundaries

Future directions may include Capability Management, Production State Platform, Semantic Merge, and Enterprise Governance. These are not current MVP implementations.


