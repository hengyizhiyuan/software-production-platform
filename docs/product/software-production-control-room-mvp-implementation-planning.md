# Watt Software Production Control Room MVP Implementation Planning

## 1. Status, authority, and scope

```text
Document type
    PRODUCT IMPLEMENTATION PLANNING BRIDGE

Control Room MVP implementation
    PLANNED / CODING NOT AUTHORIZED

WIC Core
    CLOSED / PASS
```

This document defines how a first Control Room MVP may be built by projecting
existing Watt capabilities. It is governed by:

- [Software Production Control Room Design](software-production-control-room-design.md);
- [Control Room MVP Surface Design](software-production-control-room-mvp-surface-design.md);
- [Control Room State Experience Design](software-production-control-room-state-experience.md);
- [Control Room MVP Scope](software-production-control-room-mvp-scope.md);
- [Control Room MVP Information Architecture](software-production-control-room-mvp-information-architecture.md).

It is an implementation-planning bridge only. It does not authorize coding,
UI/API modification, schema changes, migrations, Provider activity, or
Dogfood.

## 2. Implementation principle

The Control Room is a projection layer over existing Reality. It must not
become:

- a new Source of Truth;
- a new lifecycle owner;
- a duplicate Work model;
- a duplicate Runtime model.

```text
Existing governed Reality
    ↓
existing application projections and APIs
    ↓
Control Room information hierarchy
    ↓
Human understanding and governed action
```

Projection logic may organize, prioritize, and explain existing facts. It must
not manufacture state, infer Authority, or silently reconcile contradictory
Reality.

## 3. Capability mapping

| Control Room area | Existing source capability | Projection responsibility |
|---|---|---|
| Production Objective | WIC Shared Understanding, Work, and Work Reality | Present Motive, Current Work, Desired Outcome, and satisfaction without creating another Work representation |
| Understanding Alignment | WIC Interaction, Interpretation, and Shared Understanding | Distinguish Human expression, Watt interpretation, unresolved questions, and governed Reality |
| Production Status | Existing Work projection, SPG production state, and Runtime facts | Translate current phase, meaningful activity, health, and blocking/waiting reason into Human-facing status |
| Attention Center | Existing WIC, Work, Plan Steering, Runtime, and Verification attention/exception projections | Prioritize facts requiring Human attention and distinguish them from Emerging Directions |
| Current Direction | Existing Plan Steering Plan/decision projection and Reality basis | Explain WHAT NEXT and why without selecting or changing the Plan |
| Trust Summary | Existing Completion, Verification, Runtime Commit, Trusted Baseline, and Work Result projections | Summarize why a result is or is not trusted while preserving evidence ownership |
| Interaction Entry | Existing WIC Interaction flow | Let the Human continue collaborating without treating conversation as Truth or production Authority |

The Control Room may compose these existing projections for presentation. Their
source capabilities retain ownership and lifecycle semantics.

## 4. MVP implementation strategy

Prefer incremental projection over redesign.

A bounded first approach is:

```text
Existing Watt UI
    +
Control Room projection capability
    +
information hierarchy refinement
```

The plan must not assume a full UI replacement. Existing same-origin APIs,
existing Human decision paths, existing polling, and existing projections
should be reused wherever they truthfully satisfy the product information
requirements.

Implementation should add the smallest presentation/projection seams needed to
make existing Reality understandable. A missing projection is not automatic
authority to redesign its source domain.

## 5. Bounded implementation slices

### Slice 1 — Control Room Foundation

**Purpose**

Establish the Control Room's default Human attention hierarchy over the
existing Watt product surface.

**Reused capabilities**

- existing Watt UI and same-origin application delivery;
- existing Work and Runtime read projections;
- existing polling mechanism;
- existing Product Objective, status, and Attention data.

**Expected outcome**

The opening experience makes Production Objective, Production Status, and
Attention the primary operational context, with lower-priority information
available progressively. No new truth store or lifecycle is introduced.

### Slice 2 — WIC Integration

**Purpose**

Connect continuing Human–Watt interaction and Understanding Alignment to the
Control Room without making chat the primary product surface.

**Reused capabilities**

- Interaction records;
- advisory Interpretation;
- Shared Understanding;
- Work Admission readiness and Human Authority;
- Work Reality revisions;
- satisfaction and Work-transition projections.

**Expected outcome**

The Human can see what was said, what Watt interpreted, what is governed, what
remains unresolved, and whether new input continues Current Work, refines it,
or remains an Emerging Direction. Existing admission and transition governance
remains unchanged.

### Slice 3 — Production Intelligence

**Purpose**

Project the current production path, direction, exception state, and trust
evidence into one coherent Human operational view.

**Reused capabilities**

- Plan Steering direction and Reality basis;
- SPG production lifecycle and orchestration projections;
- Work status and Current Activity;
- existing Attention;
- Completion and Verification;
- Runtime Commit and Trusted Baseline;
- existing Work Result projection.

**Expected outcome**

The Human can understand what is happening, why the current step is next, what
is blocked, and why a result is or is not trusted. The projection does not
perform planning, execution, Verification, Runtime commitment, or baseline
advancement.

### Slice 4 — Human Product Acceptance

**Purpose**

Validate that the integrated Control Room helps a Human understand and govern a
real Watt lifecycle without relying on internal implementation knowledge.

**Reused capabilities**

- the completed Slice 1–3 projections;
- existing governed Human decisions and transitions;
- existing WIC, Plan Steering, SPG, Verification, and Runtime Reality.

**Expected outcome**

Human acceptance evidence demonstrates that the Human can answer the five
Control Room success questions, recognize required attention, continue
Interaction, and use only admitted governed actions. Any failure remains
truthful Product Reality and is not repaired by manufacturing state.

Slice 4 is a future acceptance activity. This planning document does not
authorize Dogfood or Provider execution.

## 6. Technical boundary

The MVP should avoid premature infrastructure.

Do not introduce:

- WebSocket;
- Event Bus;
- a new state store;
- a Workspace entity;
- a Control Room entity.

Reuse:

- existing APIs;
- existing projections;
- existing polling.

Freshness must be communicated truthfully within those mechanisms. A perceived
need for real-time behavior does not automatically justify a new transport or
event architecture.

## 7. Control action boundary

The MVP supports only actions already admitted by existing governance:

- observation;
- Human decisions;
- existing governed transitions.

Deferred:

- Governed Stop;
- Pause;
- Resume;
- Reality reconciliation.

```text
Control Room action capability
    <=
existing governance capability
```

No control may bypass Human Authority, WIC admission, Plan Steering, SPG,
Verification, Runtime, or recovery semantics. A destructive process control is
not a substitute for a truthful governed transition.

## 8. Risks and containment

### 8.1 Projection complexity

**Risk:** Combining multiple source projections may create duplicated or
contradictory meanings.

**Containment:** Preserve source ownership, identify the Reality basis, and
avoid introducing a second derived truth model.

### 8.2 Stale-information perception

**Risk:** Polling and multi-stage Reality may make the Human believe a view is
current when it is not.

**Containment:** Present meaningful freshness/waiting semantics from available
Reality and never imply stronger synchronization than the existing system
provides.

### 8.3 Human and Engineering view mixing

**Risk:** Technical precision may overwhelm the default Human view, while
oversimplification may hide material governance facts.

**Containment:** Use progressive disclosure: Human-meaningful operational
language first and engineering-precise Evidence detail when requested.

### 8.4 Dashboard-platform expansion

**Risk:** The Control Room may expand into custom widgets, generic analytics,
project management, or KPI infrastructure.

**Containment:** Keep implementation tied to the admitted MVP questions and
scope. Defer customization, organization views, economics, and unrelated
dashboard capabilities.

## 9. Success criteria

The Control Room MVP succeeds when a Human can answer, from one coherent
operational context:

1. What are we producing?
2. What is happening now?
3. What needs my attention?
4. Why is this direction correct?
5. Why can I trust the result?

Success additionally requires that:

- all answers remain traceable to existing governed Reality;
- Interaction remains available without becoming the Truth surface;
- Human decisions use existing Authority boundaries;
- no duplicate Work, Runtime, planning, or Evidence model is introduced.

## 10. Explicit non-goals

This plan does not define:

- UI implementation details;
- frontend components;
- database schema;
- a Control Room entity;
- a Workspace entity;
- KPI or productivity scoring;
- user roles or permissions.

It does not authorize WebSocket, Event Bus, new persistence, API changes, UI
changes, code changes, migrations, tests, Provider execution, or Dogfood.
