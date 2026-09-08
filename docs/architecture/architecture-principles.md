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

## The System Consumes Capabilities, Not Intelligence Prestige

**Confirmed Architecture Principle:** The software production system evaluates and consumes models according to their ability to provide a required Production Capability under governed production conditions, rather than generic model prestige, provider brand, or overall intelligence ranking.

The relevant question is how effectively a provider performs the specific production responsibility assigned to it. Examples include Production Planning, Architecture Analysis, Implementation, Documentation, Verification, Context Preparation, Reconciliation, Migration Planning, and Test Generation. These examples do not add capabilities to the MVP or transfer governance authority to a model.

A model is not a Capability. One model/provider may supply multiple Capabilities, with different performance in each. Future evaluation should use capability-relative profiles and Capability × Task / PWU characteristics, not a single global intelligence score. The [Runtime Benchmark Strategy](spg-runtime-verification-benchmarks.md) records the future evidence framework; no scoring scale or model ranking is selected.

### Non-normative Senior / Junior Engineer Analogy

Two providers may eventually achieve the same production objective, just as a senior and a junior engineer may complete the same task with different production characteristics:

| Weaker demonstrated production capability | Stronger demonstrated production capability |
|---|---|
| Smaller safe PWUs; more detailed decomposition | Larger safe PWUs; coarser decomposition |
| More trial-and-error, retries, and rework | Better up-front reasoning and higher first-pass success |
| More verification burden and human intervention | Less rework and supervision |
| Longer time to trusted completion | Faster trusted completion |

This is an explanatory analogy about production behavior, not human worth, model identity, or a universal ranking. The same provider may exhibit either pattern depending on Capability, Context, and task. All comparisons retain the required trust and authority boundaries.

## Task Decomposition Is Also Resource Allocation

**Confirmed Architecture Principle; future adaptive behavior:** Production planning should adapt the shape and granularity of work to the capability and observed reliability of the assigned provider, within the Production Goal, Engineering Context, Risk / Authority Boundary, and Autonomy Policy.

The [Production Planner direction](production-intelligence-architecture.md#task-decomposition-is-also-resource-allocation) records the implications. This principle does not implement adaptive decomposition or change SPG Lite scope.

## Price Should Correspond to Observable Production Value

**Confirmed Product / Architecture Principle for future pricing:** If models, strategies, or autonomy configurations have different user-facing prices, those differences should be explainable through benchmark- and production-backed outcomes: trusted completion, speed, safe autonomy, and total production cost, including Human Attention Cost.

Higher model execution cost may be justified by lower observed rework, intervention, or trusted change lead time; price alone establishes none of those benefits. The [future transparent strategy selection direction](future-capabilities.md#benchmark-backed-model--production-strategy-selection) records how evidence may support a user's choice. No commercial prices, billing plans, or subscription tiers are defined.

## No Model Prestige Pricing

**Confirmed Product / Architecture Principle:** Model price or user-facing production price must not be justified solely by model prestige, opaque branding, or generic benchmark rankings unrelated to the assigned Production Capability.

The platform purchases a Production Capability contribution, not the model's full abstract intelligence identity. As a non-normative role analogy, a person may have many talents, while the contribution relevant to a particular engagement is performance in that role. This does not define human worth or a compensation policy.

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

## Reality-driven Plan Steering Foundational Principles

Reality-driven Plan Steering is intended as a primary Watt product
differentiator, not merely a task-list generator. Its normative foundations
are:

- **Facts constrain the Plan.** Governed Reality, not transient model memory,
  constrains material planning direction.
- **Models reason over the Plan; models do not own the Plan.** Model, provider,
  session, host, or environment replacement does not by itself authorize a
  material Plan change.
- **Plan must be reconstructable from governed Reality.** Direction, current
  step, rationale, decisions, Findings, and revision causes must survive loss of
  the originating conversation.
- **Roadmap guides production; Reality governs roadmap.** Preserve the admitted
  Plan by default and revise it only when traceable governed Reality justifies
  change.

Materially equivalent governed facts, objectives, constraints, and decisions
should yield materially equivalent Plans without requiring deterministic LLM
wording or micro-ordering. Material divergence must be detectable and
explainable. New model output alone is not New Reality.

The complete product thesis, anti-drift requirements, Plan Revision provenance,
fresh-session reconstruction requirement, Human/SPG boundaries, and reserved
design questions are authoritative in
[Reality-driven Plan Steering — Foundational Principles](reality-driven-plan-steering-principles.md).
The capability remains a material MVP core gap and is not yet implemented.

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

## Runtime Parent Governance Principles

**Confirmed Architecture Constitution**, consolidated by the [Runtime Architecture Final Closure and Readiness](spg-runtime-architecture-readiness.md).

The detailed A/B/C/D invariants are interpreted under eight parent principles:

| Parent principle | Governing meaning |
|---|---|
| Facts Before Claims | Participant claims do not substitute for observable, traceable production facts. |
| Observed Does Not Mean Admitted | Existing, generated, retrieved, or observed reality does not automatically become admitted Trusted Production Reality. |
| Validity Is Relational | Validity is governed relative to specific reality, revisions, dependencies, Context, policy, and Authority conditions. |
| History Is Appended, Not Rewritten | New reality creates governed history rather than rewriting prior material facts. |
| Authority Changes Permission, Not Facts | Authority may change what is permitted but cannot fabricate or erase observed facts, Findings, or Evidence. |
| No Actor Owns Production Truth Alone | Production truth is composed from domain-owned inputs and governed transitions; this is not majority voting. |
| Recover Coherence, Not Appearance | Recovery restores truthful, consistent, governable state rather than cosmetic success. |
| Replaceable Intelligence, Durable Governance | Provider evolution does not redefine fundamental Contract, Responsibility, Authority, and trust semantics. |

Together they govern State Authority, execution and observation, recovery and reconciliation, Completion and Trust, Commit, governed External Effects, and observed convergence as one Runtime loop.

## Preserve Semantic Separability Before Physical Separability

**Implementation Guidance**, not a physical architecture commitment:

> Distinct architecture semantics must remain distinguishable even when the first implementation represents them using shared physical structures.

Production Validity Basis, Verification Basis, Authority Requirement, and Side-effect Permit may share a physical representation without becoming the same semantic. Likewise, Side-effect Intent, Permit, and Effect Operation may coexist inside a thin External Effect Record while retaining distinct meanings.

Do not create one service, class, database, or table per architecture noun by default. This protects SPG Lite feasibility while preserving later evolution.


## Human Authority Does Not Imply Runtime Bypass

**Current Architecture Principle**, confirmed by [State Foundation closure](spg-state-foundation.md).


Human participants may possess higher-level authority over intent, direction, constraints, risk acceptance, and final production acceptance. That authority does not grant unrestricted privilege to bypass production consistency, lineage, state-transition, or Commit rules.

Authority is expressed through governed goal / direction decisions, constraint decisions, exception decisions, risk acceptance, and acceptance of an exact Baseline Candidate. Production Governance Runtime determines how those authorized decisions may consistently change production reality. It is the sole logical transition authority, not the owner of Human Authority or Assurance Truth.

## Governed Participant Principle

**Current Architecture Principle:** Human, AI, Executor, Guardian, and other production actors are governed participants, each with Responsibility, Authority, Capability, Context, and Policy Boundary.

> Equal submission to production governance does not imply equal responsibility or equal authority.

Human and Machine do not have identical authority. Humans retain strategic judgment, risk ownership, and applicable final acceptance; machines receive operational autonomy within policy. Neither may silently bypass authoritative state-transition rules.

## No Actor Owns Production Truth Alone

**Confirmed Architecture Principle:** No individual Human, AI model, Executor, Planner, Guardian, Context Provider, plugin, or other production participant may unilaterally define authoritative production truth.

Each contributes according to its Responsibility and Authority:

| Participant | Domain-owned contribution |
|---|---|
| Human | Intent, constraints, risk decisions, applicable acceptance |
| Production Planner | Plan and replanning proposals |
| Executor | Execution facts and Work Product Artifacts |
| Guardian / Verification | Evidence, findings, assurance conclusions |
| Context Capability | Governed Context |
| Production Governance Runtime | Governed adjudication and authoritative state transitions |

Production truth emerges through governed composition of facts, artifacts, evidence, contracts, policy, authority decisions, and state-transition rules. This is **not majority voting** and does not make all actors equally authoritative. Human strategic judgment, intent, risk ownership, and applicable final acceptance remain meaningful.

## Distributed Responsibility, Governed Adjudication

**Confirmed Architecture Principle:** Responsibility and intelligence are distributed across production participants, while authoritative production-state admission is governed through explicit contracts and transition rules.

Production Governance Runtime remains logical transition authority. It does **not** itself invent all truth or own every input domain; it adjudicates authoritative state changes using inputs owned by other domains. A sole logical transition boundary is not a sole creator/owner of production truth and does not require one physical service.

This complements Human Authority Does Not Imply Runtime Bypass and Human Agency First. Authority may change governance decisions but cannot rewrite observed production facts.

## Validity Is Relational

**Confirmed Architecture Principle:**

> Validity is not a permanent intrinsic property carried by an object. It is a governed conclusion relative to specific production reality, versions, Context, dependencies, policies, and constraints.

PWU Validity is relative to Production Validity Basis; Evidence Freshness to Verification Basis; Authority Decision validity to exact Candidate / Policy; Commit Eligibility to current Baseline and required obligations. This connects A's exact-revision state semantics, B's validity and reconciliation semantics, and the [C Completion & Trust closure](spg-completion-trust.md).

The principle rejects `verified = true forever`, `approved = true forever`, `accepted = true forever`, and `valid = true forever`. It does not define a Materiality engine, Evidence dependency graph, policy implementation, or database representation.

## Trust Is Obligation Satisfaction Before It Is a Score

**Confirmed Architecture Principle:** Trusted Completion primarily means required Completion, Verification, Evidence freshness, Hard Gate, Authority, and blocking-condition obligations are satisfied for an exact Baseline Candidate.

A future confidence or Trust Score may support prioritization, decision support, additional Verification, or Autonomy Policy. It cannot replace hard governance Contracts or become the authoritative Commit gate. Hard Gates block eligibility unless governed Exception is permitted; Soft Signals inform risk, confidence, routing, or review intensity without automatically blocking Commit.

## Execution Capability Does Not Imply Side-effect Authority

**Confirmed Architecture Principle:** Technical ability to deploy, migrate, publish, delete, provision, or mutate external systems does not grant authority to perform that effect. Material effects require explicit governed Intent, scoped Authorization, least Authority / blast radius, freshness, and provenance.

Human Authority may authorize a governed effect but cannot bypass Runtime consistency or fabricate external facts. Attempt fencing must deny stale execution at the external-effect boundary.

## External Reality Is Observed, Not Assumed

**Confirmed Architecture Principle:** Command or API acknowledgement does not establish external convergence. Physical Change, Authoritative Production Change, and Observed External Reality remain distinct. Partial, Unknown, and Divergent external reality must be represented rather than guessed.

Observed reality does not automatically become Trusted Production Reality. It must be compensated or enter the normal governed Plan / Verification / Authority / Commit path.

## Compensation Appends History

**Confirmed Architecture Principle:** Rollback and Compensation differ. Compensation is a new governed production action based on current observed reality; it preserves the original effect and may itself fail. Hidden cleanup and blind inverse operations are not governance.

## Governed Integration Atomicity

**Confirmed Architecture Principle:** Across independent systems without universal physical atomicity, coherent production governance is preserved by making intended external transitions identifiable, authorized, observable, reconcilable, and recoverable.

This provides no invisible transition, unexplained partial state, silent Authority bypass, guessed external truth, or overwritten effect history. It does not promise simultaneous Git / Database / Cloud / external API changes, universal CAS, exactly-once delivery, 2PC, or one Commit / Effect ordering.

### FVS-1 Repository Integration specialization

The [FVS-1 Contract](spg-fvs-1-implementation-contract.md) specializes this principle for one narrow REPOSITORY_REF_ADVANCE effect:

    Git Commit Object
    !=
    Repository Integration
    !=
    SPG Runtime Commit

FVS-1 uses stable operation identity, expected-source Git ref CAS, observed convergence, eligibility re-check, then a local PostgreSQL Runtime Commit. **Repository Reality First, Trusted Baseline Commit Second** is frozen only for this FVS effect and must not be generalized to every future External Effect. Git and PostgreSQL do not form one global transaction.

## Provider Consolidation Does Not Collapse Authority Boundaries

**Confirmed Architecture Principle for future provider evolution:** A single powerful model or provider may implement planning, implementation, analysis, review, or several other capabilities. Physical provider consolidation must not collapse logical Responsibility, Contract, or Authority boundaries.

The same provider must not gain permission to propose → execute → self-verify → self-accept → Commit production reality merely because it is highly capable. Every output remains subject to the relevant capability contract and governed transition/authority rules.

This does not prohibit reuse of the same model or require a different provider for every role. It preserves independent governance semantics rather than mandating physical-service separation.

## Replaceable Intelligence, Durable Governance

**Strategic Architecture Principle / Design Consequence:** Intelligence providers may be replaced, upgraded, specialized, or consolidated without redefining the fundamental governance and trust semantics of software production.

Model capability can evolve quickly; Contract and Authority boundaries should remain comparatively stable. Stronger models may receive wider autonomy through policy, but they do not automatically inherit unrestricted production authority. This does not claim all models are equally capable.

True model decoupling goes beyond API-level switching. The [future Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md) evaluates whether governance remains consistent across provider behavior, without statically assigning autonomy by model brand or price.

Capability differences should manifest through performance, safe autonomy, PWU granularity, production cost, verification burden, and Human attention requirements. They must not require redefining Production Contracts, State semantics, the Authority model, Guardian's trust model, or governance invariants. Stronger models improve production performance without absorbing platform ownership or bypassing assurance and acceptance gates.

These principles accompany the [B Reconciliation & Recovery Closure](spg-reconciliation-recovery.md); they introduce no implementation module or new MVP capability.

## One Product Architecture, Multiple Runtime Profiles

**Current Architecture Principle:** SPG maintains one product architecture, one domain model, one Runtime governance model, and one primary codebase while deployment environments bind capabilities through Runtime Profiles.

Global, Mainland, enterprise-private, and future custom profiles may differ in provider/model configuration, adapters, placement, and future residency policy. They must not redefine Production Run, PWU, Attempt, Completion, Governance, Commit, or Trusted Baseline semantics. Separate regional products are not the intended architecture. See [Runtime Profile, Provider Placement, and Containerized Deployment](runtime-profile-provider-deployment.md).

## Provider and Model Selection Is Configuration

Provider identity, model identity, and model version are capability-binding/configuration concerns, not SPG domain logic. SPG Core consumes stable Capability Contracts. Regional or vendor differences belong behind Runtime Profile bindings and compatibility adapters.

Model Provider and Executor Provider remain distinct abstractions. An Executor may internally bind a model/provider, but model identity does not replace the governed Execution Capability Contract.

## Containerization Does Not Redefine Domain Architecture

Containerization is an infrastructure and packaging concern. Docker and Docker Compose are the preferred FVS/local deployment direction, but containers must not redefine capability ownership, Authority, state semantics, or trusted-transition rules. Local-first validation and container-ready packaging do not select a production region, production database topology, distributed worker design, or Kubernetes.

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

## Conversation-to-Contract Principle

**Confirmed Architecture Principle:**

> Raw conversation content is source material for extracting candidate engineering information, but it is never an authoritative execution basis.

Execution authority requires governed transformation:

```text
Conversation
→ extraction / refinement
→ governed admission
→ Artifact / Contract
→ Context Package
→ execution
```

`Raw Conversation → Executor` is prohibited as an authoritative execution dependency. Conversation may remain provenance for an admitted Artifact, audit evidence, Human review, interaction history, or later extraction. A PWU may depend on an admitted Decision derived from conversation; it must not depend directly on a raw chat message.

Context Assembly / future ECF may include only admitted, versioned, traceable engineering inputs as task Authority. Conversation / Interaction Store records what was said; governed Engineering Artifacts record what was admitted; Production State records what is authoritative; Context Package records what execution may rely upon.

This principle is concretized by the [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md).

## Artifact-Agnostic Production and Horizon

**Confirmed Implementation Guardrail:** SPG Lite Runtime must not require Code Artifact as the universal terminal for PWU Satisfaction, Plan Completion, Production Run Completion, Candidate formation, or Trusted Baseline formation.

Production Horizon defines the authorized stopping boundary and Target Outcome of a Production Run. Production Planner may not extend work beyond that Horizon merely because downstream work is technically possible. Analysis, Design, Documentation, Implementation, and other admitted Artifact outcomes share the same governed Runtime semantics.

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

## System-Level Production Differentiation

**Architecture principle:** AI-native software-production differentiation is
created by the coherent organization of intelligence, Authority, context,
execution, evidence, Runtime Reality, and feedback—not by an isolated Agent,
model, prompt, workflow, or UI.

The qualitative model is:

```text
Production Capability
    = Planning
    x Context Fidelity
    x Execution Discipline
    x Assurance
    x Reality Feedback
```

This is an architecture reasoning model rather than a measured metric. It
expresses that severe weakness in one factor can dominate the complete system.
Current capability, future direction, practical evidence, and unproven
hypotheses are separated in
[Software Production System Differentiation and Architectural Barriers](software-production-system-differentiation-and-barriers.md).

## AI-native Development Execution

**Development principle:** substantial Watt capabilities should be delivered
through Product/Architecture alignment, a bounded Mission Contract, autonomous
Executor implementation, Evidence/Reality review, and Human Acceptance.

```text
Human Governor
    owns Intent, material Authority, risk, and acceptance

Architecture Lead AI
    preserves the capability boundary and reviews Reality

AI Executor
    owns HOW inside the admitted development envelope
```

The system rejects both unrestricted autonomy against a vague goal and Human
micro-management of every technical move. The Executor should have the largest
stable envelope that remains explicit and reviewable; it must stop when
objective, Authority, risk, scope, acceptance conditions, or relevant Reality
materially changes.

The complete responsibility model, Mission Contract semantics, PWU continuity
rationale, lessons learned, and current/future boundary are recorded in
[AI-native Development Execution Principles](ai-native-development-execution-principles.md).
