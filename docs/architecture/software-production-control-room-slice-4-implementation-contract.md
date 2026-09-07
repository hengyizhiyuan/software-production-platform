# Watt Control Room Slice 4 - Human Product Acceptance Contract

## 1. Status and authority

~~~text
Contract
    DEFINED

Control Room Slice 1 - Production Control Foundation
    CLOSED / PASS

Control Room Slice 2 - WIC Integration
    CLOSED / PASS

Control Room Slice 3 - Production Intelligence
    CLOSED / PASS

Control Room Slice 4 - Human Product Acceptance
    NOT STARTED
~~~

This contract defines the bounded Human Product Acceptance activity for the
Watt Software Production Control Room. It is governed by:

- [Control Room Design](../product/software-production-control-room-design.md);
- [Control Room MVP Scope](../product/software-production-control-room-mvp-scope.md);
- [Control Room MVP Information Architecture](../product/software-production-control-room-mvp-information-architecture.md);
- [Control Room MVP Implementation Planning](../product/software-production-control-room-mvp-implementation-planning.md);
- [Control Room Slice 1 Contract](software-production-control-room-slice-1-implementation-contract.md);
- [Control Room Slice 2 Contract](software-production-control-room-slice-2-implementation-contract.md);
- [Control Room Slice 3 Contract](software-production-control-room-slice-3-implementation-contract.md).

This document records acceptance obligations only. It does not execute Human
acceptance, claim an acceptance result, authorize Provider or Dogfood
activity, or authorize implementation of a future module.

## 2. Slice identity and purpose

**Name:** Control Room Slice 4 - Human Product Acceptance.

**Purpose:** Validate whether the completed Slice 1-3 projections form a
coherent Human-facing operational experience for AI-native software
production.

Slice 4 validates product usability and truthful interpretation of existing
Reality. It does not add a major capability, create a new source of truth, or
change WIC, Plan Steering, SPG, Verification, or Runtime behavior.

## 3. Acceptance objective

The representative acceptance activity must determine whether a Human can use
the Control Room to answer five questions.

### 3.1 Objective

> What are we producing?

Expected existing sources:

- Motive;
- governed Work Reality.

### 3.2 Understanding

> Does Watt understand what I mean?

Expected existing sources:

- Human expression;
- Watt interpretation;
- governed Reality.

The experience must preserve the distinction among what the Human said, what
Watt interpreted, and what became governed truth.

### 3.3 Status

> What is happening now?

Expected existing sources:

- Production Status;
- current production activity;
- existing Attention and blocker Reality.

### 3.4 Direction

> Why is the next step this?

Expected source:

- existing Plan Steering projection, including its admitted rationale and
  Reality basis when available.

The Control Room must not infer or manufacture a direction that Plan Steering
has not established.

### 3.5 Trust

> Why should I trust this result?

Expected existing sources:

- Completion;
- Verification;
- Runtime Commit;
- Trusted Baseline;
- Active Runtime distinction when relevant.

Absence or incompleteness of a trust fact must remain visible rather than being
presented as trust.

## 4. Scope

This contract covers:

- one Human-operated Control Room acceptance journey;
- review of information coherence across the Slice 1-3 projections;
- identification of missing or misleading Reality;
- validation of the Human mental model formed by the product surface;
- preservation of truthful failure or uncertainty as Product Reality.

The acceptance activity evaluates the current product surface. It does not
create a second acceptance-specific lifecycle or truth model.

## 5. Representative acceptance journey

Validate one representative end-to-end production story:

~~~text
Motive formation
    |
    v
Governed Work
    |
    v
Production activity
    |
    v
Attention / Human decision
    |
    v
Direction understanding
    |
    v
Trusted result
~~~

The Human should be able to follow this story through the Control Room without
requiring internal implementation knowledge or treating conversational claims
as governed Reality.

The journey may use existing governed transitions and existing product
capabilities. This contract does not authorize creation of production facts,
a Provider call, or an unrelated Dogfood scenario.

## 6. Product review criteria

### A. Cognitive clarity

Determine whether the Human can understand:

- what is happening;
- why it is happening;
- what requires Human attention.

### B. Information consistency

Confirm:

- no contradictory Reality is presented;
- no duplicated truth appears to have independent authority;
- no critical explanation needed for a governed action or trust judgment is
  missing.

### C. Progressive disclosure

Confirm:

- the default view is understandable and not overloaded;
- relevant detail is available when the Human needs to investigate the
  projected Reality.

This criterion does not authorize a new detail explorer or new UI
architecture.

### D. Industrial control room principles

Validate:

- state transparency;
- exception and Attention visibility;
- traceability from the presented condition to existing Reality.

## 7. Architecture and product boundaries

Control Room remains a Human-facing projection layer.

Truth and capability ownership remain:

- WIC: Interaction, Interpretation, and Work evolution;
- Plan Steering: WHAT NEXT and direction rationale;
- SPG: governed production execution;
- Verification: verification result and evidence truth;
- Runtime: Runtime Commit, Trusted Baseline, and Active Runtime Reality;
- Human Governance: admitted Human decisions and final product acceptance.

Slice 4 does not transfer, duplicate, or redefine any of these
responsibilities.

## 8. Explicit non-scope

Slice 4 must not introduce:

- new Control Room features;
- a new UI architecture;
- a Workspace entity;
- a Control Room entity;
- a role or permissions system;
- a dashboard framework;
- Production Execution Package or Production Passport;
- Context Assembly or ECF implementation;
- Stop, Pause, Resume, or Reality Reconciliation;
- new database tables, migrations, lifecycle states, or state ownership;
- changes to WIC, Work Authority, Plan Steering, SPG, Verification, or Runtime.

## 9. Evidence requirements

The acceptance activity must preserve:

- Human acceptance observations;
- the representative journey and the Reality viewed at each relevant stage;
- identified gaps;
- product improvement findings;
- the final acceptance and closure recommendation.

Evidence must distinguish observed product behavior from interpretation. A
failed expectation must remain recorded as historical evidence and must not be
rewritten as success after a later improvement.

### 9.1 Product Experience Gap

Use this classification for observations such as:

- confusing or ambiguous information;
- a missing explanation in the Human-facing projection;
- poor visibility or ineffective information hierarchy.

These findings should remain product-experience findings unless evidence shows
a missing authoritative Reality or capability boundary.

### 9.2 Architecture Gap

Use this classification when evidence shows:

- missing Reality ownership;
- a missing or violated capability boundary.

Do not promote every usability observation into architecture work.

## 10. Closure criteria

Control Room Slice 4 closes only when:

- a Human completes the representative Control Room journey;
- the Human can answer the five acceptance questions from the projected
  Reality;
- no critical Reality misunderstanding remains;
- findings are recorded and classified as Product Experience Gap or
  Architecture Gap;
- next product priorities are identified without silently authorizing them;
- Human Product Acceptance and Architecture Lead Reality Review support
  closure.

Creation of this contract does not satisfy these criteria.

## 11. Validation and execution boundary

The later separately authorized acceptance activity may perform:

- focused UI and product validation;
- Human acceptance observation;
- documentation and evidence recording.

It must not perform broad implementation, introduce new architecture or
capabilities, invoke a Provider, or run unrelated Dogfood.

Any missing capability discovered during acceptance must be reported and
classified. It must not be implemented under this contract.
