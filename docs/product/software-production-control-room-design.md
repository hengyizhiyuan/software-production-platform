# Watt Software Production Control Room Design

## 1. Status, authority, and scope

```text
Document type
    AUTHORITATIVE PRODUCT ARCHITECTURE

Software Production Control Room
    FUTURE PRODUCT DIRECTION / NOT IMPLEMENTED

WIC Core
    CLOSED / PASS
```

This document defines the product concept and information architecture of the
Watt Software Production Control Room. It evolves the
[Workspace-first Product Experience Principles](workspace-first-experience-principles.md)
and remains governed by the
[Watt Product North Star](../architecture/watt-product-north-star.md) and the
closed
[Work Interaction & Closed-loop Refinement Core](../architecture/work-interaction-closed-loop-refinement.md).

It does not define an implementation, frontend components, API behavior,
persistence, database entities, or an implementation roadmap. The existing MVP
Goal / Work Control Room does not by itself satisfy the complete future concept
defined here.

## 2. Product positioning

Watt is not creating:

- a traditional project dashboard;
- a Jira replacement;
- a chat workspace;
- a task-management system;
- a generic AI assistant page.

Watt Control Room is:

> A Human-facing operational view of AI-native software production.

Its purpose is to help the Human understand:

- what software production objective is active;
- what Reality currently exists;
- what production state is occurring;
- what requires attention;
- why decisions are made;
- why results can be trusted.

The Control Room helps the Human govern and collaborate with Watt without
turning the Human into a continuous monitor of internal execution mechanics.

## 3. Industrial inspiration and Watt adaptation

Watt borrows durable ideas from mature production systems:

- visual management;
- production transparency;
- plan-versus-reality management;
- work-in-progress visibility;
- exception-based management;
- quality assurance;
- traceability.

These ideas are principles, not a mechanical manufacturing metaphor. Software
production differs because requirements evolve, interpretation is necessary,
creation is knowledge-intensive, and production paths are less repetitive.
Watt must therefore combine:

```text
Industrial production control
    +
Knowledge-work understanding management
```

The result must preserve governed Reality and operational clarity while
supporting refinement, creativity, adaptation, and Human judgment.

## 4. Core Control Room questions

The Control Room should answer:

1. What are we producing?
2. What is the current production Reality?
3. Are we aligned with Human intent?
4. Is production healthy?
5. What requires Human attention?
6. Why can we trust the result?

These questions define an information architecture, not a screen layout.

## 5. Control Room information architecture

### 5.1 Production Objective

Industrial analogy: production order or manufacturing objective.

Watt equivalent: Motive plus Work.

Answers:

> What value are we trying to produce?

Conceptually contains:

- Human Motive;
- Current Work;
- Desired Outcome;
- current satisfaction state.

Source: WIC and governed Work Reality.

### 5.2 Understanding Alignment

Industrial production commonly assumes that an order is already clear.
Software production cannot make that assumption. Watt needs an explicit layer
that answers:

> Do Human and AI understand the same thing?

```text
Human said
    ↓
Watt interpreted
    ↓
Governed Reality
```

Conversation is provenance. Governed Reality is truth.

Source: WIC.

### 5.3 Production Status

Industrial analogy: shop-floor production status.

Watt equivalent: current software-production state.

Answers:

> What is happening now?

Conceptually contains:

- current lifecycle phase;
- current production stage;
- meaningful progress signal;
- execution health;
- waiting or blocking reason.

Examples may include `DESIGN`, `PRODUCE`, `VERIFY`, `INTEGRATION`, and
`COMPLETE` where those states are supported by existing authoritative
Reality. The Control Room should not elevate token counts, raw Agent logs, or
meaningless technical events into Human-facing production status.

### 5.4 Plan versus Reality

Industrial analogy: production plan compared with actual output.

Watt equivalent: Plan Steering compared with current governed Reality.

Answers:

> Why are we doing this next?

Conceptually contains:

- current direction;
- expected next step;
- Reality basis;
- meaningful deviations;
- reassessment reasons.

Plan Steering owns planning and WHAT NEXT. The Control Room only projects and
explains that Reality.

### 5.5 Attention / Exception Center

Industrial analogy: Andon and exception management.

Its purpose is to prevent important issues from remaining hidden.

Current Attention may include:

- Human decision required;
- Verification failure;
- blocked dependency;
- scope expansion.

Emerging Directions may include an idea such as:

> Future failure recovery would also be useful.

The Control Room should preserve it as:

```text
Emerging Direction
    Failure recovery capability

Status
    Recorded

Impact
    Does not affect current production
```

The principle is to preserve ideas without causing uncontrolled scope drift.
Recording an Emerging Direction does not admit it into Current Work, Plan, or
production Authority.

### 5.6 Quality and Trust

Industrial analogy: quality inspection and traceability.

Watt equivalent: evidence-based trust.

Answers:

> Why should we believe this result?

This layer projects relationships to:

- Completion;
- Verification;
- Evidence;
- Runtime Reality;
- Trusted Baseline.

It does not create or reinterpret those facts.

### 5.7 Production Timeline

Industrial analogy: manufacturing history and traceability.

Watt equivalent: Reality evolution history.

Conceptually contains:

- Work revisions;
- decisions;
- production cycles;
- Verification events;
- Baseline changes.

History is preserved. Reality evolves through traceable transitions rather than
being overwritten by the newest conversation or status.

### 5.8 Interaction

Interaction remains available, but it is not the center of the Control Room. It
is one communication channel and one source of provenance.

The Control Room should remain meaningful without raw chat because it also
projects Understanding, Plan, Production, Attention, and Evidence.

## 6. Human and engineering views

### 6.1 Human Operational View

The default view conceptually emphasizes:

- objective;
- status;
- attention;
- understanding;
- next direction;
- trust.

### 6.2 Engineering Governance View

The advanced view conceptually exposes:

- revisions;
- contracts;
- Evidence lineage;
- relevant technical detail.

The governing principle is progressive disclosure: preserve complete
governance and traceability without requiring every Human to process every
technical fact by default.

## 7. Exception-based management

Watt should not require the Human to continuously monitor every detail. The
system should surface:

- deviations;
- risks;
- decisions;
- required intervention.

The Control Room should not optimize for displaying maximum information. It
should optimize for correct Human attention allocation.

## 8. What Watt must not copy from manufacturing

Watt explicitly rejects using the manufacturing analogy to justify:

- production-quantity KPIs;
- code-volume metrics;
- token consumption as productivity;
- rigid fixed workflows;
- factory-style deterministic sequencing.

Software production requires interpretation, refinement, creativity, and
adaptation. Industrial inspiration must improve governance and visibility
without suppressing those properties.

## 9. Relationship with existing architecture

Truth and responsibility ownership remains:

| Capability | Ownership |
|---|---|
| WIC | Human Interaction and Work evolution |
| Plan Steering | WHAT NEXT |
| SPG | Governed production execution |
| Executor | HOW inside the approved execution envelope |
| Verification / Runtime | Evidence Truth |
| Control Room | Human-facing operational projection |

The Control Room owns no new truth. It does not replace, merge, or weaken any
of these boundaries.

## 10. MVP boundary

This document defines:

- product philosophy;
- information hierarchy;
- Human mental model.

It does not introduce:

- a Control Room entity;
- a database model;
- a Workspace entity;
- Workspace hierarchy;
- Sub-workspace;
- Work graph;
- a project-management model.

No code, API, UI, schema, migration, WIC behavior, Plan behavior, SPG behavior,
or Runtime behavior is authorized by this document.

## 11. Future evolution directions

Possible future areas include:

- role-based projections for developer, technical lead, manager, and enterprise
  owner;
- production-economics views covering capacity, cost, and throughput;
- advanced planning intelligence.

These are future directions only. They are not current capabilities, MVP
requirements, implementation commitments, or new truth owners.
