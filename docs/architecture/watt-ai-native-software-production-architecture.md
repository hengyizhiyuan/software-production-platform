# Watt AI-Native Software Production Architecture

Date: 2026-09-21

Status: **ARCHITECTURE BASELINE / FOUNDATIONS IMPLEMENTED**. This document
consolidates the intended capability relationships for the next generation of
Watt. It distinguishes current Repository Reality from designed but
unimplemented directions. The bounded foundations described in the
implementation-status section are now Repository Reality; broader runtime,
management, and lifecycle capabilities remain future work.

## Vision

Watt is not a coding agent. Watt is an AI-native software production system.

Its goal is to enable Human collaboration, AI intelligence, Engineering
Reality, Production Governance, execution, and Assurance to form a closed loop:

```text
Human Collaboration
        ↓
Context Intelligence
        ↓
Engineering Knowledge
        ↓
Production Governance
        ↓
Execution
        ↓
Assurance
        ↓
Evolution
```

The loop is evidence-driven rather than chat-driven. Intelligence proposes and
adapts; governed Reality, explicit authority, and lifecycle contracts determine
what is current and what may progress.

## Capability layers

The layers below describe logical responsibility. They are not requirements for
separate services, databases, agents, or user-interface surfaces.

| Layer | Conceptual owner | Primary question | Current status |
|---|---|---|---|
| Interaction Intelligence | Response Contract | How should Watt collaborate with the Human now? | v3 implemented; refining |
| Context Intelligence | Context Orchestrator | What governed information is needed now? | Bounded selection foundation implemented |
| Engineering Reality | ECF | What context exists, with what source and freshness? | Foundation/seams established; full capability pending |
| Domain Intelligence | Software Domain Grounding | What should an engineer consider? | Pattern representation and structured activation foundation implemented |
| Production Intelligence | Software Production SOP | How should this engineering activity progress? | Activity/checkpoint/evidence foundation implemented |
| Governance | Steering and existing authority boundaries | What governed action is allowed and next? | Steering implemented within current scope |
| Execution | Task Contract, PWU, Executor | What bounded work is executed, and how? | Task Contract foundation integrated into PWU/Executor |
| Assurance | Guardian | Is the result sufficiently supported and trustworthy? | Foundation/integration boundary established; full capability pending |

### Cross-cutting evaluation capability

The **AI Software Production Evaluation Framework** evaluates the balanced
system capability to understand Human intent, produce software well, and assure
the result. It is cross-cutting rather than a new production stage or authority
owner. Evaluation consumes governed, versioned evidence from the layers above;
it cannot change Semantic Truth, admit Work, authorize execution, waive
Assurance, or declare Human Acceptance.

See [Watt AI Software Production Evaluation
Framework](watt-ai-software-production-evaluation-framework.md).

## Interaction Intelligence Layer

**Owner:** Response Contract.

This layer determines how Watt collaborates with the Human for the current turn.
It includes:

- Interaction Mode;
- EXPLORE Interaction Strategy, including Intent Refinement;
- Reasoning Sequence;
- Information Budget;
- Question Budget;
- Judgment Consistency; and
- Advancement Obligation.

Its contract is turn-scoped and advisory. It does not own Engineering Truth,
Production Authority, or execution. An `EXECUTE` posture may request governed
progression, but cannot admit Work, choose a Steering transition, authorize a
side effect, or claim that execution occurred.

Intent Refinement is the EXPLORE strategy used when one unresolved decision has
high impact on the next product or engineering choice. It asks the minimum
high-value question and contributes the result to the existing governed intent
understanding. It is not a separate module, Agent, Skill, or source of Semantic
Truth, and it does not reopen a settled execution instruction.

See [WIC Response Contract](wic-response-contract.md).

## Context Intelligence Layer

**Conceptual owner:** Context Orchestrator.

This layer selects, prioritizes, trims, and assembles the context required for
the current reasoning or engineering obligation.

```text
ECF:                  What exists?
Context Orchestrator: What is needed now?
```

Candidate sources include:

- Response Contract;
- System Capability Reality;
- Engineering Semantic Truth;
- ECF Reality;
- Repository and Runtime Reality;
- Decision Memory;
- Software Domain Grounding;
- Software Production SOP; and
- Guardian Evidence.

More context does not equal better reasoning. Assembly should optimize
relevance, sufficiency, latency, and cognitive clarity. Every selected item
retains the authority, provenance, and freshness semantics of its owning source.
The Context Orchestrator does not absorb ECF.

System Capability Reality is the repository-versioned, evidence-bounded source
for Watt's identity and current capabilities. It identifies Watt as an
AI-native software production system across intent understanding, engineering
reasoning, production, bounded execution, verification/assurance, and Reality
management. It is not marketing or execution authority and cannot support
claims of external effects without an integration, authority, and evidence.
Response Contract consumes that Reality through a turn-scoped capability
alignment: ordinary knowledge remains an ordinary answer, software-production
how-to receives a bounded production-path connection, and an explicit build or
change request enters the existing governed production preparation path.

See [WIC Context Orchestration](wic-context-orchestration.md).

## Engineering Reality Layer

**Owner:** ECF for Context Projection semantics.

The Engineering Reality view keeps distinct projected domains:

- **Reality Fabric** — attributable Work, Repository, Runtime, and production
  observations;
- **Semantic Reality** — governed meaning, authority, epistemic state,
  provenance, and supersession;
- **Decision Reality** — current and historical decisions, rationale, authority,
  and lifecycle status; and
- **Evidence Reality** — attributable Human, Engineering, and Assurance evidence
  references.

These domains are separated so that facts, decisions, and evidence do not
collapse into one undifferentiated memory. ECF may project or preserve
references to source-owned Reality; it does not take ownership of Work Reality,
Engineering Semantic Truth, Human authority, SPG Production State, Git history,
or Guardian Assurance Evidence.

ECF is not a generic knowledge database. General Engineering Patterns remain in
Domain Intelligence rather than contaminating project-specific Reality.

See [ECF Integration](../context/ecf-integration.md).

## Domain Intelligence Layer

**Conceptual owner:** Software Domain Grounding.

An **Engineering Pattern** is:

> A reusable engineering cognitive framework organized around a software
> engineering decision space.

A Pattern is not a document, RAG result, fixed rule, workflow, or implementation
recipe. It may provide:

- a mental model;
- decision dimensions;
- credible options;
- trade-offs;
- failure awareness; and
- attributable evidence and applicability conditions.

The governing principle is:

> Pattern constrains reasoning space, not Human expression space.

Patterns support attention and judgment. They do not override explicit Human
intent, Semantic Truth, Work Reality, Production Policy, or execution authority.

See [WIC Software Domain Grounding](wic-software-domain-grounding.md).

## Production Intelligence Layer

**Conceptual owner:** Software Production SOP.

Software Production SOP is **Engineering Activity guidance**. It explains how a
kind of software work should progress; it does not specify which button to click
and is not a workflow engine.

Candidate Engineering Activities include:

- Discovery;
- Feature Delivery;
- Bug Resolution;
- Incident Response;
- Architecture Decision;
- Refactoring;
- Investigation;
- Migration;
- Optimization; and
- Release.

The activity catalog is evolutionary. It must be shaped by implementation and
Dogfood Reality rather than frozen as a complete taxonomy before use.

### SOP runtime principles

SOP is guidance, not control flow. It supplies activity-aware considerations,
expected evidence, and possible checkpoints while preserving adaptive planning,
Steering, and authority boundaries.

A **Checkpoint** represents an evidence expectation. It is not automatically a
mandatory approval, UI gate, fixed stage, or Human interruption. Whether a
checkpoint requires action depends on risk, authority, evidence sufficiency,
and current Reality.

Depth is risk-driven:

- low-risk, reversible work may use lightweight checkpoints and bounded
  evidence;
- higher-risk, irreversible, security-sensitive, or broadly impactful work may
  require additional evidence, independent verification, and Guardian
  involvement.

SOP and Guardian must not combine into a heavyweight workflow that creates
ceremonial approvals or blocks safe progress without an executable Human action.

### Enterprise extension direction

Future effective guidance may be composed as:

```text
Effective SOP
    = Global SOP
    + Organization SOP Extension
    + Project Constraints
```

The principle is **extension, not replacement**. Organization guidance may
specialize global guidance, and project constraints may narrow applicability,
but neither silently deletes global invariants or higher-authority Reality.
Conflict and precedence semantics remain a future design concern.

## Pattern and SOP relationship

Pattern answers: **What should engineers consider?**

SOP answers: **How should engineering work progress?**

Their relationship is many-to-many, not an inheritance tree:

- an Authentication Pattern may support Feature Delivery, Architecture
  Decision, and Security Review activities;
- a Feature Delivery SOP may consume Authentication, Data Modeling, and API
  Design Patterns.

Pattern activation does not select an SOP, and an SOP does not own Pattern
content. Context Orchestration selects the relevant combination for the current
Work, risk, and Response Contract.

## Governance Layer

**Owner:** Steering within existing Work Admission, Human Authority, and policy
boundaries.

Governance determines:

- whether the proposed progression is allowed under current authority;
- the next governed action; and
- which authority boundary applies.

Steering owns formal `WHAT NEXT` for the Work. It does not manufacture Human
approval, rewrite Work Reality, or take ownership of execution. Existing
admission and authority mechanisms remain decisive.

### Production visibility / Steering projection

Work Plan Projection is the Human visibility layer over the current Steering
Plan and Work Reality. It shows the admitted Work goal, completed stage, current
stage, and known remaining path. It is not a workflow engine or a rigid task
sequence: Steering continues to own `WHAT NEXT`, while Executor owns `HOW`.

When Reality requires a different path, Steering creates a new Plan revision.
The projection changes to that active revision and exposes the recorded change
reason and affected Reality references. Superseded revisions and plan-change
history remain persisted; the UI does not silently rewrite the old path.

The principle is:

> AI Intelligence != Production Authority.

Domain Intelligence and SOP may advise. Steering and the applicable authority
boundaries govern progression.

## Execution Layer

**Owners:** Task Contract, PWU, and Executor according to their distinct
responsibilities.

The intended relationship is:

```text
Software Production SOP
        ↓ guidance
Steering
        ↓ governed next action
Task Contract
        ↓ bounded execution obligation
Production Work Unit
        ↓ lifecycle
Executor
```

The implemented Task Contract foundation makes the execution obligation explicit:

- Objective;
- Scope;
- Constraints;
- Acceptance;
- Evidence;
- Out of Scope; and
- Authority.

PWU owns the governed execution lifecycle. Executor owns how admitted work is
performed inside its envelope. Neither SOP nor Task Contract grants authority
beyond admitted Work and current governance.

### Task Contract lifecycle direction

The candidate lifecycle is:

```text
Draft
  → Approved
  → Active
  → Suspended
  → Superseded
  → Completed
```

This is a future architecture direction, not a frozen state machine or current
schema. Valid transitions, owners, recovery, amendment, and terminal semantics
require separate design and implementation authorization.

PWU lineage should preserve references to:

- SOP lineage;
- Task Contract lineage;
- Decision lineage; and
- Evidence lineage.

Lineage makes later verification and correction traceable; it does not make a
historical input current or trusted by association.

## Assurance Layer

**Owner:** Guardian.

Guardian validates:

- evidence sufficiency and integrity;
- correctness claims;
- governance and boundary compliance; and
- confidence appropriate to the decision and risk.

Guardian is not only a test runner. Tests are one source of Engineering
Evidence; Assurance also considers subject identity, revision, scope,
provenance, findings, unresolved risk, and applicable gates. Guardian does not
own Work, Planning, execution, or Human Acceptance.

See [Guardian Integration](../assurance/guardian-integration.md).

## Decision and evidence foundation

Reasoning Summary, Decision Trace, and Evidence remain separate:

- Reasoning Summary preserves useful rationale, considered factors, and
  assumptions without raw chain-of-thought;
- Decision Trace records options, selected decision, rationale, authority,
  evidence, and lifecycle status;
- Evidence records attributable Human, Engineering, or Assurance observations.

See [Watt Decision and Evidence Architecture](watt-decision-evidence-architecture.md).

## Reality-driven implementation strategy

> Architecture hypotheses must be validated by implementation Reality.

The intended development sequence is:

### Phase 0 — Architecture Freeze

Record capability responsibilities, authority boundaries, hypotheses, and
explicit non-goals before implementation.

### Phase 1 — Capability Implementation

Implement the smallest coherent capability slice without silently expanding
adjacent ownership or future scope.

### Phase 2 — Focused Verification

Verify the new invariant at the cheapest sufficient layers, including bounded
integration where cross-layer behavior matters.

### Phase 3 — Dogfood Reality Check

Exercise the capability through real Human journeys. Treat contradictions,
friction, and failure evidence as architecture input rather than explaining them
away.

### Phase 4 — Integration into production flow

Integrate the qualified capability through owned contracts and existing
governance, preserving lineage and rollback boundaries.

Milestone Closure requires Full Regression plus Human E2E acceptance under the
applicable closure policy. This is a development environment; the strategy does
not impose production-style shadow rollout requirements.

## Roadmap placement

```text
Core Architecture
  Response Contract
  Semantic Truth
  ECF
  Domain Grounding
  Software Production SOP
  Task Contract
  Guardian

Cross-cutting Capability
  AI Software Production Evaluation Framework

Future
  Pattern Evolution
  Pattern Studio
  Evaluation Platform
```

The Evaluation Framework is a current architecture baseline. The Evaluation
Platform remains future work.

## Implementation status

```text
RESPONSE_CONTRACT = V4 IMPLEMENTED / REFINING
INTENT_REFINEMENT_STRATEGY = IMPLEMENTED
SYSTEM_CAPABILITY_REALITY = FOUNDATION_IMPLEMENTED
GOVERNED_RESPONSE_RECOVERY = FOUNDATION_IMPLEMENTED
ENGINEERING_SEMANTIC_TRUTH = IMPLEMENTED
WORK_REALITY = IMPLEMENTED
ECF = FOUNDATION_ESTABLISHED / FULL_CAPABILITY_PENDING
STEERING = IMPLEMENTED_WITHIN_CURRENT_SCOPE
WORK_PLAN_PROJECTION = IMPLEMENTED_WITHIN_CURRENT_SCOPE
PWU = IMPLEMENTED_WITHIN_CURRENT_SCOPE
EXECUTOR = IMPLEMENTED_WITHIN_CURRENT_SCOPE
GUARDIAN = FOUNDATION_ESTABLISHED / FULL_CAPABILITY_PENDING

CONTEXT_ORCHESTRATOR = FOUNDATION_IMPLEMENTED / GENERAL_PLATFORM_PENDING
SOFTWARE_DOMAIN_GROUNDING = FOUNDATION_IMPLEMENTED
SOFTWARE_PRODUCTION_SOP = FOUNDATION_IMPLEMENTED
TASK_CONTRACT = FOUNDATION_IMPLEMENTED / PWU_INTEGRATED
DECISION_EVIDENCE = FOUNDATION_IMPLEMENTED / EMBEDDED_LINEAGE
TASK_CONTRACT_LIFECYCLE = ARCHITECTURE_DIRECTION / IMPLEMENTATION_PENDING
AI_SOFTWARE_PRODUCTION_EVALUATION_FRAMEWORK = ARCHITECTURE_BASELINE / PLATFORM_PENDING
```

## Explicit non-goals

```text
NOT_IMPLEMENTED:
- Pattern Studio
- Pattern management UI
- Pattern Evolution engine
- WIC Evaluation Corpus
- Benchmark infrastructure
- Evaluation Platform
- Leaderboard or public ranking
- Automated evaluation infrastructure
- Full adaptive Software Production SOP runtime and administration
- Automated knowledge mining
- General retrieval/index/caching Context Orchestrator platform
```

The foundation uses provider-neutral immutable contracts and existing WIC/PWU
boundaries. It adds no schema, separate service, workflow engine, UI, Pattern
management product, enterprise SOP administration, or rollout mechanism.
