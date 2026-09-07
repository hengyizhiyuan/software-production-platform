# Watt Software Production Control Room MVP Information Architecture

## 1. Status, authority, and scope

```text
Document type
    PRODUCT DESIGN / MVP INFORMATION ARCHITECTURE

Control Room MVP information architecture
    DESIGNED / NOT IMPLEMENTED

WIC Core
    CLOSED / PASS
```

This document defines the default information hierarchy, conceptual primary
screen structure, progressive disclosure, and interaction flow for the Watt
Software Production Control Room MVP. It specializes:

- [Software Production Control Room Design](software-production-control-room-design.md);
- [Control Room MVP Surface Design](software-production-control-room-mvp-surface-design.md);
- [Control Room State Experience Design](software-production-control-room-state-experience.md);
- [Control Room MVP Scope](software-production-control-room-mvp-scope.md).

It defines product information architecture only. It does not define frontend
components, visual styling, responsive behavior, API contracts, persistence,
database entities, or implementation work.

## 2. Core principle

The Control Room is a decision-support surface. It should optimize:

> Correct Human attention allocation.

It should not optimize for maximum information density.

The first screen should answer:

1. What are we producing?
2. What is happening now?
3. Is Reality aligned?
4. What requires attention?
5. What happens next?

The answers must be projected from existing governed Reality. Information
placement does not create new truth or Authority.

## 3. Default landing experience

### 3.1 Production Objective — Highest priority

Purpose:

> What are we trying to achieve?

Contains:

- Motive;
- Current Work;
- Desired Outcome;
- satisfaction state.

### 3.2 Production Status — Highest priority

Purpose:

> Where are we now?

Contains:

- lifecycle phase;
- current meaningful activity;
- execution health;
- blocking or waiting reason.

### 3.3 Attention Center — High priority

Purpose:

> What needs me?

Current Attention contains:

- Human decisions;
- blockers;
- exceptions.

Emerging Attention contains:

- possible future directions;
- new ideas;
- unresolved opportunities.

The two categories must remain distinguishable. An Emerging Direction is
preserved without being admitted into Current Work or production scope.

### 3.4 Understanding Alignment — High during formation and refinement

Purpose:

> Do Watt and I understand the same thing?

```text
Human said
    ↓
Watt interpreted
    ↓
Governed Reality
```

This area may become less prominent or collapse during stable production, but
its semantic distinction remains available.

### 3.5 Current Direction — Medium priority

Purpose:

> Why is this next?

Contains:

- current Plan direction;
- rationale;
- relevant Reality basis.

Plan Steering owns WHAT NEXT. This area only projects the admitted direction.

### 3.6 Trust Summary — Medium priority

Purpose:

> Why should we trust this?

Contains summary relationships to:

- Verification;
- Completion;
- Runtime Reality;
- Trusted Baseline.

The summary must preserve uncertainty and distinct evidence meanings. Detailed
Evidence remains available through progressive disclosure.

## 4. Information layout model

The following zones are conceptual priority groups, not UI containers or
frontend components.

### 4.1 Primary Zone

Always visible:

- Production Objective;
- Production Status;
- Attention Center.

These answer:

> What matters now?

### 4.2 Secondary Zone

Visible with lower default priority:

- Understanding Alignment;
- Current Direction;
- Trust Summary.

These answer:

> Why is this happening?

### 4.3 Deep Detail Zone

Available through progressive disclosure:

- Evidence details;
- lineage;
- contracts;
- technical information;
- historical timeline.

This preserves governance depth without overloading default Human attention.

## 5. Lifecycle-aware information priority

These are experience priorities derived from existing Reality, not new domain
lifecycle states.

### 5.1 Formation

Priority:

1. Understanding Alignment;
2. open questions;
3. readiness.

Production detail should not dominate before governed Work and production
exist.

### 5.2 Planning

Priority:

1. Production Objective;
2. Plan Direction;
3. Reality Basis.

### 5.3 Production

Priority:

1. Production Status;
2. Attention;
3. Current Activity.

### 5.4 Exception

Priority:

1. Attention;
2. impact;
3. decision options.

The information should help the Human decide rather than merely announce a
problem.

### 5.5 Completion

Priority:

1. Trust Summary;
2. achieved outcome;
3. evolution opportunities.

Completion should preserve Interaction openness and distinguish continuation
from an Emerging Direction or new Work recommendation.

## 6. Interaction placement

Interaction is always available, but it is not the primary Control Room screen.

```text
Control Room
    What is true and important now?

Interaction
    How the Human communicates with Watt.
```

Chat history must not become the main product surface or substitute for
governed Reality. Interaction contributes expression and provenance while the
Control Room projects Current Reality and attention.

## 7. Progressive disclosure

### 7.1 Human Operational View

Default view:

- objective;
- status;
- attention;
- understanding;
- direction.

Language should be Human meaningful.

### 7.2 Engineering View

Optional deeper view:

- technical detail;
- Evidence;
- lineage;
- contracts;
- Runtime detail.

Language should remain engineering precise.

```text
Human understanding first.
Engineering depth second.
```

Progressive disclosure changes visibility and explanation, not truth,
Authority, or evidence ownership.

## 8. Control action placement

Control actions should appear close to the Reality that makes them relevant.

Examples:

- Attention requiring a Human decision should present the governed decision
  action near its reason and impact;
- production control should appear only when supported by an admitted
  governance capability.

The Control Room must not expose ungoverned destructive controls. In
particular, a simple “Kill process” action is not a truthful production-control
semantic and must not substitute for future Governed Stop and reconciliation.

## 9. Industrial design principles adapted

Watt borrows:

- visual management;
- exception visibility;
- state transparency;
- traceability.

Watt does not copy:

- manufacturing KPI dashboards;
- throughput obsession;
- deterministic workflow assumptions.

The information architecture should make adaptive knowledge work governable,
not force software production into a factory-output model.

## 10. Explicit non-goals

This design does not define:

- frontend components;
- visual styling;
- responsive layout;
- database entities;
- a Workspace entity;
- a Control Room entity;
- a dashboard builder;
- customizable widgets;
- user roles or permissions.

It does not authorize changes to UI, API, schema, migrations, WIC, SPG, Plan
Steering, Executor, Verification, Runtime, or tests.
