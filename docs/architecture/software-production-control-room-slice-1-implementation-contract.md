# Watt Control Room Slice 1 — Production Control Foundation Implementation Contract

## 1. Status and authority

```text
Contract
    DEFINED

Control Room Slice 1 — Production Control Foundation
    CLOSED / PASS

Architecture Lead Reality Review
    PASS

Closure
    ADMITTED 2026-09-07
```

This contract defines the bounded implementation slice and records its final
Reality closure for the Watt Software Production Control Room. It is governed
by:

- [Control Room Design](../product/software-production-control-room-design.md);
- [Control Room MVP Scope](../product/software-production-control-room-mvp-scope.md);
- [Control Room MVP Information Architecture](../product/software-production-control-room-mvp-information-architecture.md);
- [Control Room MVP Implementation Planning](../product/software-production-control-room-mvp-implementation-planning.md);
- [Work Interaction & Closed-loop Refinement Contract](work-interaction-closed-loop-refinement.md).

This document defines engineering obligations only. Implementation authority
was supplied separately by the bounded Control Room Slice 1 implementation
task; this contract does not authorize Slice 2, Provider, or Dogfood work.

## 2. Slice identity and purpose

**Name:** Control Room Slice 1 — Production Control Foundation.

**Purpose:** Introduce the minimum Human-facing Control Room projection over
existing Watt Reality.

The purpose is not to create a new management system. It is to let the Human
answer:

1. What are we producing?
2. What is happening now?
3. What requires my attention?

```text
Existing governed Reality
    ↓
bounded Control Room projection
    ↓
Human operational understanding
```

The projection owns no truth, Authority, lifecycle, or production transition.

## 3. Included capability

### 3.1 Production Objective Projection

Project:

- Motive;
- Current Work;
- Desired Outcome;
- satisfaction state.

Source: existing WIC and Work Reality.

Requirements:

- preserve exact source meaning and absence;
- introduce no new Source of Truth;
- introduce no duplicate Work model;
- do not infer an objective or satisfaction state when existing Reality does
  not establish it;
- keep any source identity needed for truthful navigation or refresh without
  copying ownership into the Control Room.

### 3.2 Production Status Projection

Project:

- current Work state;
- current production phase;
- current execution status;
- current blocking or waiting condition.

Source: existing Work, SPG, and Runtime Reality.

Requirements:

- introduce no lifecycle state;
- do not modify Runtime;
- distinguish absent, pending, active, blocked, and completed Reality only
  through meanings already supported by source projections;
- translate technical state into Human-meaningful status without changing its
  authoritative meaning;
- avoid token metrics, raw Agent logs, and non-material implementation noise.

### 3.3 Attention Center Projection

Project:

- existing Human Attention requirements;
- blocked conditions;
- existing transition or review needs;
- an Emerging Direction only when it is already available from existing
  governed/advisory projections.

Source: existing WIC, Runtime, and Verification facts and projections.

Requirements:

- introduce no new Attention ownership model;
- retain source ownership and material reason;
- distinguish action-required Attention from an Emerging Direction;
- never promote an idea, warning, or advisory interpretation into Work,
  Authority, or production scope;
- expose only actions already supported by existing governance.

## 4. Explicit non-scope

### 4.1 WIC Deep Integration — deferred to Slice 2

Slice 1 does not implement:

- a complete Shared Understanding experience;
- Human-said versus Watt-interpreted comparison;
- Interpretation lifecycle presentation.

Slice 1 may consume the minimum existing WIC projection needed for Objective or
Attention. It must not claim this satisfies the future Understanding Alignment
surface.

### 4.2 Plan Intelligence — deferred to Slice 3

Slice 1 does not implement:

- Plan-versus-Reality presentation;
- Plan rationale;
- next-step explanation.

Plan Steering remains the owner of WHAT NEXT.

### 4.3 Trust Explorer — deferred to Slice 3

Slice 1 does not implement:

- detailed Evidence presentation;
- a lineage explorer;
- Verification visualization.

Existing Verification and Runtime facts may contribute an Attention condition,
but Slice 1 must not create a new trust interpretation.

### 4.4 Control Actions — deferred

Slice 1 does not implement:

- Stop;
- Pause;
- Resume;
- Reality reconciliation.

It must not expose a destructive process action as a substitute for governed
production control.

### 4.5 Architecture changes — forbidden

Slice 1 must not introduce:

- a Workspace entity;
- a Control Room entity;
- new database tables;
- new lifecycle states;
- new state ownership.

## 5. Implementation boundary

The preferred implementation is a projection over existing APIs and models.

Reuse:

- existing Work APIs and projections;
- existing Runtime projections;
- the minimum existing WIC data needed by this slice;
- existing polling.

Avoid:

- a frontend rewrite;
- a new event system;
- WebSocket;
- Event Bus.

The implementation may reorganize Human-facing information and add the minimum
bounded projection glue required by this contract. It may not fill missing
source Reality by creating a parallel model or silently deriving authoritative
state in the presentation layer.

## 6. Validation contract

The Slice 1 implementation must prove all of the following.

### 6.1 Objective

Given existing Work/WIC Reality, the Human can identify:

> What software production objective is active?

The projection shows Motive, Current Work, Desired Outcome, and satisfaction
when present, and remains truthful when any value is absent.

### 6.2 Status

Given existing Work/SPG/Runtime Reality, the Human can identify:

> What is happening now?

The projection communicates meaningful current state, phase/activity where
available, and any blocking or waiting reason without inventing a lifecycle
state.

### 6.3 Attention

Given existing WIC/Runtime/Verification Reality, the Human can identify:

> Does Watt need me?

Required Human Attention is visible with its reason. No-attention and
Emerging-Direction conditions remain distinguishable from action-required
Attention.

### 6.4 Non-interference

The implementation must prove that existing:

- WIC semantics;
- SPG semantics;
- Runtime truth and transitions;
- Work lifecycle;
- Plan Steering ownership;
- Verification ownership

remain unchanged.

It must also prove that reading or refreshing the Control Room creates no Work,
Run, PWU, Attempt, Provider activity, Verification, Runtime Commit, Baseline
change, or governance decision.

## 7. Testing expectations after implementation

The implementation must include:

- focused projection tests for Objective, Status, and Attention;
- absent/partial/blocked/completed Reality cases relevant to the three
  projections;
- read/refresh non-interference checks;
- affected existing regression tests for WIC, Work, SPG, and Runtime
  compatibility;
- bounded UI behavior validation showing the three Human questions are
  answerable.

Testing must remain proportionate to this slice. It must not become a full
product redesign or authorize a Provider/Dogfood run without separate
governance.

### 7.1 Focused validation evidence

The implemented presentation projection:

- composes existing Work, WIC Shared Understanding, Runtime execution-progress,
  and Attention API facts in the browser;
- matches WIC and Attention facts to the selected Work identity;
- preserves explicit absence instead of deriving Motive, satisfaction,
  activity, blockers, or direction from conversation;
- issues no API request and owns no mutation path;
- adds no backend model, API, schema, migration, lifecycle state, or truth
  owner.

Focused validation on 2026-09-07:

- Node web-state suite: 14 passed;
- UI and WIC contract suites: 9 passed;
- Work API and WIC PostgreSQL integration suites: 37 passed, 1 skipped because
  real Provider proof requires separate explicit authorization.

The PostgreSQL suites used the isolated spg_test database; the running Watt
application database remained spg_dev. No Provider was called.

## 8. Completion criteria

Control Room Slice 1 closes only when:

- implementation Reality matches this contract;
- the Human can answer the Objective, Status, and Attention questions;
- no new truth ownership, lifecycle, Work model, or Runtime model exists;
- source-domain boundaries and non-interference are proven;
- focused validation evidence exists;
- Architecture Lead Reality Review accepts the implementation and evidence.

Architecture Lead Reality Review confirmed:

- implementation Reality matches the three admitted projection capabilities;
- the Objective, Status, and Attention questions are answerable from existing
  source projections;
- the Control Room remains a presentation projection and owns no truth,
  lifecycle, Work model, Runtime model, or governance transition;
- no WIC Deep Integration, Plan Intelligence, Trust Explorer, or Control Action
  entered Slice 1;
- focused validation and non-interference evidence are preserved in Section
  7.1;
- no architecture boundary violation was found.

Final admitted Reality:

```text
Control Room Slice 1
    CLOSED / PASS

Architecture Lead Reality Review
    PASS
```

## 9. Future-slice compatibility

Slice 1 must leave bounded extension space for:

- **Slice 2 — WIC Understanding Alignment:** Shared Understanding and
  Human-expression versus interpretation versus governed-Reality experience;
- **Slice 3 — Production Intelligence:** Plan/Reality direction and trust
  projection;
- **Slice 4 — Human Product Acceptance:** real Human validation of the
  integrated Control Room experience.

Slice 1 must not pre-implement, duplicate, or constrain those capabilities
beyond preserving existing ownership and projection seams.
