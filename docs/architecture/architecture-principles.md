# Long-term Architecture Principles

This is a living architecture document. It records long-term directions and explicitly labeled Current Architecture Principles. The [closed State Foundation](spg-state-foundation.md) confirms logical governance semantics under Architecture Baseline v0.1, not implementation or physical-service design. No section expands the current MVP.
## AI-Native Software Production System

The platform is not an AI coding tool. It solves how humans and AI can continuously produce trustworthy software through a governed production loop.

```text
Intent → Design → Planning → Execution → Verification → Feedback → Refinement
```

The platform enables continuous software production rather than isolated development stages.

## Engineering Capability over Model Capability

The platform should not be designed as a wrapper around a specific frontier model.

Its fundamental value comes from providing:

- Engineering context
- Governance
- Workflow
- Role abstraction
- Authority boundaries
- Artifact management
- Verification
- Assurance

Models provide intelligence capability. The platform provides a production system in which that intelligence can reliably participate in software production.

> Model capability determines execution capability.
>
> Platform capability determines production reliability, scalability, and sustainability.

## Model Independence

The platform should preserve engineering understanding independently of model versions. It should not rely on a model to permanently store:

- Project intent
- Design rationale
- Historical decisions
- Current baseline
- Task status
- Governance rules

These must exist as explicit, platform-managed artifacts.

The platform should enable model replacement, executor replacement, model capability upgrades, and cost/performance trade-offs without losing:

- Project understanding
- Engineering continuity
- Decision history
- Production governance

## Target Architecture and Current MVP

Target Architecture describes long-term direction. Current MVP Implementation describes the smallest scope currently being built. They must remain distinct.

These long-term principles are not MVP requirements. The current MVP remains focused on:

- Project Workspace
- Context Management
- Role-based AI collaboration
- Task lifecycle
- Executor integration
- Artifact management

Future capabilities should be activated only after sufficient real-world production experience has been accumulated.

## Strategic Value

The platform does not compete with AI model providers. It enables organizations to continuously absorb advances in AI models while maintaining a stable software production system.

Future users may choose different executors according to cost, speed, capability requirements, and risk profile. The platform remains valuable regardless of which model generation dominates.



## AI Execution Speed ≠ Software Evolution Correctness

AI Executors can increase software production speed, but they do not inherently guarantee long-term architectural consistency, Feature completeness, or preservation of design intent.

The platform therefore relies on Context, Design Authority, Verification, and Assurance to maintain system stability during rapid evolution.

## Controlled Autonomy

The platform should be neither a system in which humans manually control every AI action nor a completely autonomous software factory.

AI is responsible for:

- Understanding goals
- Planning paths
- Decomposing tasks
- Coordinating execution
- Analyzing feedback
- Adjusting plans

Human authority remains responsible for:

- Goal Authority
- Strategic Direction
- Major Trade-off
- Risk Acceptance
- Final Governance

## AI Capability Evolution Independence

The platform's value must not depend on any single generation of model capability. Model changes primarily affect execution speed, cost, efficiency, and single-task quality.

The platform's independent value comes from:

- Context
- Workflow
- Governance
- Verification
- Baseline
- Production Loop

The platform should remain useful as model capability evolves rather than lose its value with each model generation.

## AI-native Software Production Requires Dynamic Engineering Management

Traditional software management often assumes that planning and execution are separated, design, development, and testing have clear phase boundaries, change is costly, and plans are stabilized to reduce coordination cost. This favors:

```text
Static Planning → Execution → Change Control
```

AI-native software production changes these conditions. Lower design, implementation, verification, and modification costs enable a faster:

```text
Design → Implementation → Verification → Adjustment
```

The production model should therefore evolve from static plan-driven management to dynamic state-driven management.

## Governed Adaptive Planning

AI-native development does not remove planning. It changes planning from a one-time frozen commitment into a governed object that evolves with reality feedback.

```text
Intent → Planning → Execution → Verification → Reality Feedback
    → Plan Adjustment → Continue Execution
```

Plans may change, but changes must be evidence-based, traceable, explainable, and governed. Dynamic adjustment is not arbitrary adjustment. The production record must preserve Decision Record, Change Reason, Impact Context, and New Baseline.

## Progress Reflects Reality, Not Commitment

Progress primarily supports state understanding, risk identification, decision support, and production governance. It is not required to increase linearly. Feature adjustment, design refactoring, task decomposition changes, or a decrease in completion may represent a return from an incorrect path toward a more correct target state.

## Organizing Intelligence Is the Core Challenge

The platform's central challenge is not simply making AI smarter. It is organizing intelligence so that it can participate productively in complex software production.

This requires attention to:

- Coordination among AI roles
- Organizational goals
- Long-term project state
- Explicit authority boundaries
- Trustworthy production outcomes
- Continuous feedback and evolution

The principle is:

> Make AI productive in a governed software production system.

## Platform Positioning Principle

The platform is not an AI tool with software production added around it. It is an AI-native Software Production System in which AI is a core production capability and first-class production factor, organized, governed, verified, and continuously evolved without displacing human agency.

Its value is based on long-term software-production invariants rather than on the shortcomings of any model generation.

## Human-governed AI Software Production

AI-native software production preserves validated software engineering principles, including Architecture Boundary, Incremental Delivery, Verification, Version Control, Change Management, and Quality Assurance.

The evolution is in the execution subject and production organization:

```text
Human-driven Software Development
                ↓
Human-governed AI Software Production
```

## Organizing Intelligence

The central problem is not how to call a stronger model, write a better prompt, or add more Agents. It is:

> How can intelligence be organized so that it can collaborate reliably and produce trustworthy results in complex software production?

AI-native software production capability emerges from the combination of:

- Intelligence Capability
- Role Organization
- Responsibility Boundary
- Authority Model
- Context Infrastructure
- Artifact Management
- Verification
- Governance
- Continuous Feedback

Together these form a scalable software production system.

## Core Platform Abstraction

The first-class abstraction is not Agent. Agent is one implementation of Role capability.

```text
Role
Responsibility
Authority
Context
Artifact
Gate
```

The platform manages how intelligence is organized to participate in production, not how many bots are created.

## Human Agency First

Human defines Intent, Goal, Value Judgment, Risk Tolerance, Governance Authority, and Final Accountability.

AI amplifies Analysis, Design, Execution, Verification, and Optimization.

The system provides Context, Coordination, Evidence, and Trust.

**Current Architecture Principle — State Foundation clarification:** Human Agency First does not mean an unrestricted production superuser. Humans retain meaningful authority over intent, direction, organizational constraints, risk ownership, high-impact exceptions, and final acceptance where policy requires it. They do not directly mutate authoritative production state outside governance rules.

## Human Authority Does Not Imply Runtime Bypass

**Current Architecture Principle**, confirmed by [State Foundation closure](spg-state-foundation.md).

Human participants may possess higher-level authority over intent, direction, constraints, risk acceptance, and final production acceptance. That authority does not grant unrestricted privilege to bypass production consistency, lineage, state-transition, or Commit rules.

Authority is expressed through governed goal / direction decisions, constraint decisions, exception decisions, risk acceptance, and acceptance of an exact Baseline Candidate. Production Governance Runtime determines how those authorized decisions may consistently change production reality. It is the sole logical transition authority, not the owner of Human Authority or Assurance Truth.

## Governed Participant Principle

**Current Architecture Principle:** Human, AI, Executor, Guardian, and other production actors are governed participants, each with Responsibility, Authority, Capability, Context, and Policy Boundary.

> Equal submission to production governance does not imply equal responsibility or equal authority.

Human and Machine do not have identical authority. Humans retain strategic judgment, risk ownership, and applicable final acceptance; machines receive operational autonomy within policy. Neither may silently bypass authoritative state-transition rules.

## Authority Before Convenience

**Current Architecture Principle:** Authoritative production reality is determined by governance authority state, not UI, cache, progress display, or successful completion of all derived projections.

Only successful Commit of an exact sealed Baseline Candidate changes Current Trusted Baseline authority, after expected source-Baseline validation. Failure before the authoritative switch leaves the previous Baseline authoritative; failure of derived views or follow-up synchronization after the switch does not undo it.

Trusted Baselines are immutable. Working State is distinct from Trusted State. Recorded historical production facts are preserved even when current views change. These are logical constraints, not Event Sourcing, distributed transaction, schema, or service requirements.

## Architecture Reserves Future; Product Does Not Consume Future

State Foundation semantics may be expressed through ordinary persistent storage, explicit records / revisions, transition history, Git references, and simple controlled commit logic. No particular implementation is selected here.

They do not require SPG Lite to implement Event Sourcing, distributed transactions, a distributed state store, a complex workflow engine, a graph database, distributed locking, Production State Branching, or microservices.

## Intelligence Organization over Agent Accumulation

The platform should not optimize for the number of Agents, models, or prompts. It should organize intelligence into:

- Explicit roles
- Explicit responsibilities
- Explicit authority
- Explicit context
- Explicit artifacts
- Explicit verification mechanisms

The future platform's first-class concern is how intelligence is organized to participate in production.

## Intelligence Capability Separation Principle

The AI-native software production system should not be built as one general-purpose intelligence. It should combine clearly bounded, governable, verifiable, and evolvable intelligence capabilities.

Each capability should have:

- Independent responsibility
- Independent Source of Truth
- Independent Authority Boundary
- Explicit input and output contract

## Capability Contract Layer

Production Planner should not implement every intelligence capability directly. It may invoke domain capabilities through a Capability Contract Layer.

```text
Production Planner
        ↓
Capability Contract Layer
   ┌───────────┬────────────┬───────────┐
   │ Decision  │ Production │ Assurance │
   │ Decision  │ Executor   │ Guardian  │
   └───────────┴────────────┴───────────┘
        ↓
ECF Context Layer
```

Production Planner understands the production goal, advances the engineering process, and coordinates capabilities. It does not absorb every domain intelligence responsibility.

## Capability Contract Before Capability Implementation

The platform should define a capability's responsibility boundary, input/output semantics, authority, and artifact contract before selecting or requiring a concrete provider implementation.

```text
Capability Boundary
        ↓
Capability Contract
        ↓
Bootstrap Provider
        ↓
Production-loop Validation
        ↓
Replaceable Mature Provider
```

Consumers depend on the Contract, not on a product, model, Agent, prompt, data source, or runtime. This allows capability implementations to evolve without reversing ownership or dependency direction.

For Decision Intelligence, SPG depends on the Decision Intelligence Interface and consumes the Decision Artifact Contract. A lightweight provider may validate that boundary before a mature YiJue or enterprise provider is integrated. This is an architecture principle, not a current implementation commitment.

## Ownership Before Integration

System integration must follow capability ownership. Ownership must not be assigned according to implementation order, existing product boundaries, or current technical convenience.

Consumers depend on contracts owned by the responsible capability. Integration does not transfer responsibility, Source of Truth, authority, or artifact ownership to the orchestrating system.

## Generated Does Not Equal Trusted

AI-generated or tool-generated output must not automatically become trusted production truth.

```text
Generated Output
        ↓
Verification
        ↓
Admission
        ↓
Applicable Authority
        ↓
Trusted Production State
```

Verification does not equal Acceptance. Trust requires evidence, governed admission, and the applicable authority decision.

## Contract Before Implementation

Stable responsibility, authority, and artifact contracts should be defined before implementations are replaced, integrated, or scaled. A Contract is an architecture boundary; it does not imply a current API, service, provider integration, or MVP commitment.

## Production Work Unit Generalization Principle

> Production Work Unit represents a governed production activity that transforms intent into a validated production outcome. It is not limited to coding activities.

A Production Work Unit may represent implementation, documentation, context preparation, analysis, verification, or planning. SPG governs and coordinates the production activity; it does not become the domain system that performs or owns every type of work.

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

## Production Artifact Domain

Production Artifact is the domain category for all governed outputs generated during software production, including Code, Documentation, Context, Analysis, and Verification Artifacts. **Work Product Artifact** is the concrete output of a Production Work Unit.

The producing Execution System or Capability Provider retains artifact ownership. Verification Artifact does not replace Guardian-qualified Verification Evidence, and Context Artifact does not replace an ECF-governed Context Projection. SPG coordinates lifecycle and governance without becoming a Coding Platform, Documentation System, Knowledge Management System, or universal artifact repository. This terminology clarification does not expand MVP scope.

## Production Planner as a Role

Production Planner is an **AI Native Software Production Governor**: an AI Role responsible for keeping the software production process continuously convergent.

It is not a Coding Agent, Project Management Tool, Super Agent, or Chatbot. Its core responsibilities are:

- Maintain Production Intent
- Maintain Project Intelligence
- Drive the Production Iteration Loop
- Maintain Engineering Coherence
- Coordinate Capability Execution

## AI Role vs Agent Instance Separation

Production Planner is a system Role, not a single Agent instance. A runtime may use one instance, multiple instances, or different capability configurations. The Role must not be frozen as one model plus one prompt.

## Production Intelligence over Single Intelligence

The AI-native production system should combine bounded intelligence capabilities rather than construct one all-purpose AI. Each capability has independent responsibility, Source of Truth, Authority Boundary, and explicit input/output Contract.


## Capability-oriented Naming Principle

AI-native systems should define core components by responsibility and capability, not by implementation technology or anthropomorphic role.

AI is an implementation approach, not the capability definition. Production Planner may be implemented through AI Reasoning, Rule Engine, Pattern Library, Optimization Logic, Human Input, or a combination of these.

## Production Planner

Production Planner is the capability responsible for transforming approved production intent into adaptive software production blueprints and production plans.

It is responsible for:

- Blueprint Generation
- Production Plan Generation
- Plan Adaptation

It is not responsible for Business Decision, Product Strategy, Value Judgment, deciding whether a product should exist, or general-purpose Decision Intelligence. Those belong to Human Governor, Decision Intelligence Capability, or Architecture / Product Authority.
