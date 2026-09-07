# Watt Software Production Control Room MVP Surface Design

## 1. Status, authority, and scope

```text
Document type
    PRODUCT DESIGN / MVP EXPERIENCE BOUNDARY

Control Room MVP surfaces
    DESIGNED / NOT IMPLEMENTED

WIC Core
    CLOSED / PASS
```

This document defines MVP-level Human perspectives for the Software Production
Control Room. It specializes the
[Software Production Control Room Design](software-production-control-room-design.md)
and the
[Workspace-first Experience Principles](workspace-first-experience-principles.md).
It remains governed by the
[Watt Product North Star](../architecture/watt-product-north-star.md).

It defines product experience boundaries only. It does not define UI
components, routes, API behavior, persistence, database entities, user
accounts, permissions, or implementation work.

## 2. Purpose

Software Production Control Room is not a dashboard. It is:

> A Human-facing operational interface for AI-native software production.

Its purpose is to help Humans with different responsibilities answer:

- What are we producing?
- Where are we now?
- Is Reality aligned with intent?
- What requires attention?
- Why should we trust the result?

The Control Room should make production understandable and governable without
requiring the Human to inspect raw system mechanics.

## 3. Core principle

```text
One production Reality.
Multiple Human perspectives.
```

The system does not create different truths for different Humans. Each
perspective projects the same authoritative Reality while changing only:

- information priority;
- level of detail;
- default attention.

The Surface names below describe responsibility-centered perspectives. They do
not introduce persisted user roles, permissions, or organizational identities.

## 4. Surface A — Production Operator View

### Purpose

For a Human monitoring active production execution.

Industrial analogy: operator or line supervisor.

Primary Human question:

> What is Watt doing now?

### Production Status

Prioritizes:

- Current Work;
- current production phase;
- current execution state;
- production health;
- blockers.

### Current Activity

Prioritizes:

- current meaningful action;
- last meaningful update;
- waiting reason;
- Human attention requirement.

### Attention

Examples include:

- execution blocked;
- Human decision needed;
- Verification issue.

This perspective should avoid raw Agent logs, token information, and technical
events that do not materially affect Human understanding or intervention.

## 5. Surface B — Technical Lead View

### Purpose

For a Human accountable for architecture or engineering direction.

Industrial analogy: workshop manager.

Primary Human question:

> Why is production moving this way, and is it technically sound?

### Production Objective

Prioritizes:

- Motive;
- Work;
- Desired Outcome.

### Understanding Alignment

Prioritizes:

- Human intent;
- Watt interpretation;
- governed decisions.

It preserves the distinction between what was said, what was interpreted, and
what became governed Reality.

### Plan versus Reality

Prioritizes:

- current Plan;
- Reality changes;
- meaningful deviations;
- reassessment reasons.

Plan Steering remains the owner of WHAT NEXT. This view only projects and
explains the current direction.

### Quality and Trust

Prioritizes:

- Verification;
- Evidence;
- Trusted Baseline;
- lineage.

## 6. Surface C — Product / Owner View

### Purpose

For a Human accountable for outcome value.

Industrial analogy: factory manager or production owner.

Primary Human question:

> Will this achieve the intended outcome?

### Objective

Explains why the Work exists.

### Status

Summarizes the overall production state.

### Delivery Confidence

Projects:

- what is completed;
- known risks;
- unresolved attention.

It must not convert uncertainty into an unsupported score or promise.

### Outcome Evolution

Projects:

- current satisfaction;
- emerging future directions;
- admitted changes in objective.

This perspective should avoid unnecessary engineering detail by default while
keeping deeper Evidence available through progressive disclosure.

## 7. Shared core areas

The following conceptual areas are shared across all perspectives. Their source
ownership does not change between views.

### 7.1 Production Objective

Source: Motive and Work Reality.

Answers:

> What are we trying to produce?

### 7.2 Understanding Alignment

Source: WIC.

Answers:

> Do Human and Watt understand the same thing?

### 7.3 Production Status

Source: SPG and Runtime.

Answers:

> Where is production now?

### 7.4 Plan versus Reality

Source: Plan Steering.

Answers:

> Why is this next?

### 7.5 Attention / Exception

Source: WIC, Runtime, and Verification according to the underlying fact.

Answers:

> What needs Human attention?

### 7.6 Quality and Trust

Source: Verification, Evidence, and Runtime.

Answers:

> Why should we believe this?

The Control Room projects these areas. It owns no new production or Evidence
truth.

## 8. First-screen priority

The default Control Room opening experience should prioritize:

1. Current Production Objective;
2. Production Status;
3. Attention / Exceptions;
4. Understanding Alignment;
5. Current Direction;
6. Trust State.

It should not optimize for maximum information density. It should optimize for:

> Correct Human attention allocation.

This ordering is an experience priority, not a prescribed screen layout.

## 9. Progressive disclosure

### Default Human view

Shows:

- objective;
- status;
- attention;
- understanding;
- next direction.

### Expanded governance view

Shows:

- Evidence;
- lineage;
- contracts;
- technical details.

The governing principle is:

```text
Human understanding first.
Engineering depth second.
```

Progressive disclosure changes presentation depth, not the underlying Reality.

## 10. Relationship with Interaction

Interaction remains the communication channel. The Control Room is the
operational context.

```text
Interaction
    What was said

Control Room
    What is currently true and important
```

Conversation provenance remains available, but raw conversation does not own
production state, planning, Authority, or Evidence Truth.

## 11. Software-specific adaptation

Unlike manufacturing, software production cannot be managed only through
throughput. The Control Room must preserve:

- uncertainty;
- interpretation;
- refinement;
- evolving intent;
- knowledge-work characteristics.

The goal is not:

> Maximize AI output volume.

The goal is:

> Maximize trusted software production.

Industrial concepts are adapted to improve transparency, attention, quality,
and traceability without imposing rigid sequencing on creative and evolving
software work.

## 12. Explicit non-goals

This design does not introduce:

- a Workspace entity;
- a Control Room entity;
- a dashboard database;
- user roles;
- permissions;
- team management;
- project hierarchy;
- Sub-workspace;
- Work graph;
- a KPI system;
- productivity scoring.

It does not authorize changes to WIC, Plan Steering, SPG, Executor,
Verification, Runtime, API, UI, schema, migrations, or tests.
