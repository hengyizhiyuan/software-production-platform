# Work-centric Production and Responsibility Principles

Status: **ARCHITECTURAL PRINCIPLE / FUTURE IMPLEMENTATION GUIDANCE**

Implementation impact: **DOCUMENTATION ONLY — NO NEW ENTITY, SCHEMA, API,
RUNTIME BEHAVIOR, ROLE MODEL, OR ACCESS SYSTEM**

## 1. Purpose and authority

This document connects existing Watt architecture across Work, Work Assets,
Work Reality, Plan Steering, PWU, Executor autonomy, context, capability
access, assurance, and Human-facing projections. It records the principles
that future implementation must preserve; it does not replace the detailed
contracts that own those domains.

The principles arise from Watt dogfooding:

1. fragmented Human–Architecture Lead–Executor loops imposed high information
   transfer, attention, and token cost;
2. large but bounded Codex missions performed better when the Executor received
   a clear objective, boundary, acceptance contract, and sufficient autonomy;
3. PWU therefore needs to preserve autonomous execution continuity while
   remaining governable, resumable, and independently verifiable;
4. the industrial-production analogy showed that each responsibility needs the
   information and capabilities relevant to its operation, rather than one
   undifferentiated project workspace.

These observations are design rationale. They do not prove that software
development should copy a manufacturing process literally.

## 2. Work is the production center

Watt is **Work-centric, not Project-centric**. Work is the first-class
production concept:

```text
Work
├── Motive / Intent
├── Governed Design Reality
├── Assets
│   ├── Repository Asset
│   ├── Issue / Planning Asset
│   ├── Design Artifact Asset
│   ├── Document Asset
│   ├── Runtime Asset
│   └── External System Asset
├── Work Reality
├── Steering Plan
├── PWUs
├── Execution History
└── Evidence
```

This is a conceptual responsibility model, not authorization for a new
database aggregate. Watt must not introduce a parallel first-class Project,
Project lifecycle, New Project workflow, or Import Project workflow.

Repositories, Jira boards, Figma files, PRDs, architecture documents, Runtime
environments, and external systems are **Assets associated with Work**. They
provide attributable inputs or execution surfaces. They do not automatically
become governed Truth:

```text
Repository Asset
    -> Repository Reality extraction
    -> attributable candidate context
    -> governed admission where required
    -> relevant Work Reality
```

PRD, Figma, Jira, Git, and Runtime sources retain their own attributable
Reality. They must not each acquire a competing Watt production lifecycle.
The detailed ownership remains in the
[Work-centric Production Model](work-centric-production-model.md) and
[Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md).

## 3. Human experience hides project plumbing

The Human primarily expresses **what they want to make happen**. Watt should
handle repository onboarding, asset association, context plumbing, and similar
operational detail unless a distinction becomes material to Human judgment.

```text
"Build an operations-management platform"
    -> Work with no Repository Asset initially

"Continue design and development from this Git repository"
    -> Work with an existing Repository Asset relationship
```

Both are Work-centered flows. The Human should not have to choose between a
New Project and Import Project mode, understand an asset-attachment workflow,
or manually assemble engineering context merely to express the Motive.

This principle does not authorize Work Asset Intake or Repository Intake
implementation. It defines the product experience those future capabilities
must support.

## 4. Industrial analogy: responsibility, not rigidity

A production-line worker normally needs the current operation, required
materials, process parameters, quality requirements, permitted actions, and
abnormal conditions. They do not continuously need every upstream origin,
author, commercial reason, or other station's activity.

Watt uses this analogy only to organize:

- responsibility;
- information supply;
- production boundaries;
- quality and exception handling.

Software production remains uncertain, knowledge-intensive, iterative, and
design-sensitive. Watt must not turn the analogy into rigid sequencing,
mechanical role separation, or an assumption that software work is repetitive
factory labor.

## 5. Work Reality, Steering, PWU, and Executor

The responsibility chain is:

```text
Work Reality
    -> Plan Steering determines WHAT NEXT at a meaningful outcome level
    -> PWU defines the autonomous governed production envelope
    -> Executor decides HOW inside that envelope
    -> independent Verification evaluates observed results
    -> New Reality feeds Steering and Work evolution
```

### 5.1 Steering owns meaningful direction

Plan Steering owns `WHAT NEXT`: the next meaningful outcome, capability,
decision, design result, production result, or acceptance boundary justified
by governed Reality. It must not become a generator of line-by-line coding
instructions, tool commands, or debugging moves.

Steering may influence PWU size so that the next production mission is coherent
and governable. It does not micromanage the Executor's implementation strategy.
The authoritative semantics remain in the
[Reality-driven Plan Steering MVP Contract](reality-driven-plan-steering-mvp-contract.md).

### 5.2 PWU is an autonomous production station

A PWU is not merely a tiny task. It is a bounded autonomous production
operation that should eventually provide or derive:

- Objective and Expected Outcome;
- Relevant Constraints;
- Acceptance Criteria and Required Evidence;
- Allowed Action Boundary;
- Required Context;
- Required Asset and Capability Access.

The design goal is:

> **Execution continuity without execution monolithicity.**

> **生产连续，但执行不必连续。**

PWU granularity must be large enough for engineering continuity and autonomy,
yet bounded enough for pause, reconstruction, recovery, Verification, and
replanning. Watt should avoid tiny task fragmentation, SPG-issued coding
instructions, and repeated SPG–Executor debugging ping-pong.

### 5.3 Executor owns HOW within the envelope

Inside an admitted PWU/Attempt envelope, the Executor should be highly
autonomous. It may normally decide implementation details, code organization
inside allowed scope, local refactoring, tests and debugging, ordinary
environment repairs, and bounded self-refinement.

The Executor must return control before changing:

- Product Intent;
- Work Scope materially;
- architecture or Truth ownership;
- Human Authority;
- admitted resource, repository, risk, or production boundaries.

The target is **high autonomy within governed boundaries**—neither uncontrolled
AI nor micro-managed AI. The precise Attempt, continuation, and STOP semantics
remain in the
[Executor Autonomy Envelope](executor-autonomy-envelope-attempt-granularity-mvp-contract.md).

## 6. Minimum-sufficient production environment

Higher quality does not mean supplying every participant with all available
information and access. Each current responsibility should receive the
minimum sufficient environment needed to make the correct decision and perform
the admitted operation:

- Context;
- Assets;
- Tools;
- Capabilities;
- Authority;
- Evidence requirements.

This reduces attention dilution, context drift, stale-information misuse,
token cost, cognitive burden, and avoidable blast radius.

```text
Steering / PWU
    -> determine the production need

ECF
    -> Need-to-know / Least Context

Asset Routing
    -> required materials and attributable sources

Capability / Asset Access Provisioning
    -> Need-to-act / Least Privilege

Executor
    -> autonomous execution inside the prepared environment

Verification / Guardian
    -> independent quality assurance

Reality
    -> feedback, Work evolution, and replanning
```

This combined production environment is broader than ECF alone.

### 6.1 ECF: need-to-know / least context

ECF is responsible for discovering, assembling, checking freshness, preserving
provenance for, and projecting the context relevant to the current decision or
operation. Examples include applicable Product Intent, admitted decisions,
current Work Reality, Repository Reality, constraints, prior evidence, and open
Findings.

ECF is not IAM and does not grant action authority. Context selection and
action authorization may share a minimum-sufficient principle, but they remain
separate ownership domains. See [ECF Integration](../context/ecf-integration.md).

### 6.2 Capability access: need-to-act / least privilege

A Human or AI Executor should receive only the Assets and capabilities needed
for the current Work/PWU. For example:

```text
repository A       read / write
test database      scoped read / write
Jira issue         read
production DB      no access
deployment         no access
```

Where possible, Watt should prepare this environment automatically instead of
making a worker manually request Git, issue-system, database, or infrastructure
permissions as routine production plumbing. Permissions still exist and must
remain enforced; the product integrates them into the production system.

Future architecture should preserve a distinct capability/access provisioning
seam:

```text
PWU / Production Contract
    -> required production capabilities
Capability / Asset Access Provisioning
    -> minimum sufficient action authority
Executor
    -> bounded use
```

This document neither designs nor authorizes a full IAM subsystem.

### 6.3 Identity-centric and Work-centric authorization

Traditional authorization commonly accumulates broad, long-lived permissions
on a user identity. Watt's desired direction is:

```text
Work / PWU responsibility
    -> derive temporary and scoped capability needs
    -> provision capability
    -> expire or revoke it when no longer required
```

This resembles task-scoped capability, just-in-time access, and least
privilege, but Watt is not bound here to any specific IAM, RBAC, ABAC, token,
credential, or infrastructure implementation.

## 7. Responsibility-aware Reality projection

The governing principle is:

> **One Reality. Different responsibility projections.**

Views may change information priority, aggregation, detail, and default
attention. They must not create separate Truth, lifecycle ownership, or
conflicting state for different roles.

| Responsibility level | Comparable industrial perspective | Minimum useful projection |
| --- | --- | --- |
| Execution / workstation | Operator / technician | Current PWU, required Assets, constraints, acceptance, quality state, immediate exceptions |
| Team / lead | Team leader / foreman | Active Work/PWU health, blockers, retry/rework, quality Findings, local resource pressure, Human Attention |
| Product / engineering management | Workshop manager | Multiple-Work progress, dependencies, delivery risks, major Findings, capability/milestone state |
| Program / organization | Plant manager / factory director | Strategic objectives, aggregate production health, meaningful throughput/cost/quality trends, major risks, authority decisions |

Higher responsibility does not mean more raw data:

```text
lower level  -> concrete / operational / immediate
higher level -> aggregated / exception-oriented / decision-oriented
```

A company governor should not need every Executor log. An Executor should not
receive unrelated program strategy. Every user should not receive an identical
dashboard.

### 7.1 Control Room reconciliation

The existing Control Room `Production Operator`, `Technical Lead`, and
`Product / Owner` surfaces are responsibility-centered projections over the
same underlying Reality. They are not new user-role records and do not become
owners of Work, Plan, Runtime, Evidence, or lifecycle transitions.

Future team and program/organizational projections may extend the attention
hierarchy while preserving the same rule. The current authoritative surface
boundary remains the
[Software Production Control Room MVP Surface Design](../product/software-production-control-room-mvp-surface-design.md).

### 7.2 Role management sequencing

Responsibility and role management is useful, but it is not the current
highest priority. Watt must first strengthen the
`Work -> Steering -> PWU -> Executor` production chain. When multiple Humans,
Works, and organizational production make it necessary, separately admitted
future work may introduce:

- a Responsibility Model;
- Attention Policy;
- View Projection;
- scoped Authority and capability mapping.

No user-role backend, team-management model, or organization hierarchy is
authorized here.

## 8. Guardian and Verification preserve autonomy

Guardian/Verification qualify observed results against the admitted contract.
They should validate:

- result and Evidence;
- contract satisfaction;
- important boundary violations;
- quality Findings.

They should not continuously micromanage every Executor action. A loop of tiny
Executor action, Guardian rejection, correction, and repeated rejection wastes
context and destroys useful autonomy. Assurance should create meaningful,
independent quality gates after bounded production activity. It must not absorb
Executor `HOW`, Steering `WHAT NEXT`, or Human Authority.

The detailed assurance boundary remains in
[Guardian Integration](../assurance/guardian-integration.md) and the existing
SPG Verification contracts.

## 9. Future implementation invariants

Future scoped implementation must preserve:

1. Work remains the production center; Asset kinds do not become parallel
   lifecycle owners.
2. Asset observations remain attributable and do not become Work Truth merely
   through attachment.
3. Steering selects meaningful next outcomes; PWU bounds autonomous
   production; Executor owns local technique.
4. Context assembly and action authorization remain distinct.
5. Capability is no broader or longer-lived than required by the admitted
   responsibility.
6. Responsibility views project one authoritative Reality.
7. Verification remains independent without turning into step-by-step control.
8. Human Authority remains required at material intent, scope, architecture,
   risk, acceptance, and production-boundary decisions.

## 10. Explicit non-goals

This principle does **not** authorize immediate implementation of:

- a Project entity or Project lifecycle;
- Work Asset Intake or Repository Intake;
- a generalized Work Asset schema;
- ECF;
- IAM/RBAC replacement;
- a role-management backend or organization hierarchy;
- a capability marketplace;
- a new Executor architecture;
- Guardian redesign;
- Multi-PWU/DAG orchestration or advanced Plan Steering.

Each requires a separate, bounded architecture and implementation decision.

## References

- [Watt Product North Star](watt-product-north-star.md)
- [Motive / Work / Plan Concept Calibration](motive-work-plan-concept-calibration.md)
- [Work-centric Production Model](work-centric-production-model.md)
- [Work Interaction & Closed-loop Refinement](work-interaction-closed-loop-refinement.md)
- [Reality-driven Plan Steering Principles](reality-driven-plan-steering-principles.md)
- [Reality-driven Plan Steering MVP Contract](reality-driven-plan-steering-mvp-contract.md)
- [Executor Autonomy Envelope](executor-autonomy-envelope-attempt-granularity-mvp-contract.md)
- [Software Production Control Room MVP Surface Design](../product/software-production-control-room-mvp-surface-design.md)
- [ECF Integration](../context/ecf-integration.md)
- [Guardian Integration](../assurance/guardian-integration.md)
- [Watt Development Roadmap](../roadmap/watt-development-roadmap-and-progress.md)
