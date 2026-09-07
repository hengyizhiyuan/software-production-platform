# Watt Software Production Control Room State Experience Design

## 1. Status, authority, and scope

```text
Document type
    PRODUCT DESIGN / STATE-AWARE EXPERIENCE SEMANTICS

Control Room state experience
    DESIGNED / NOT IMPLEMENTED

WIC Core
    CLOSED / PASS
```

This document defines how the Watt Control Room experience should change as
software-production Reality changes. It specializes:

- [Workspace-first Experience Principles](workspace-first-experience-principles.md);
- [Software Production Control Room Design](software-production-control-room-design.md);
- [Software Production Control Room MVP Surface Design](software-production-control-room-mvp-surface-design.md).

The named states below are **experience contexts projected from existing Watt
Reality concepts**. They are not new domain lifecycle states, a UI state
machine, persistence records, or implementation requirements.

## 2. Core principle

```text
Control Room is state-aware.
```

It must not present the same information in every production state with only a
different label or color. Different Reality requires different Human
attention.

The goal is:

> Provide the right Reality view at the right moment.

The underlying truth and ownership remain unchanged. Only information emphasis,
explanation, and attention priority adapt to the current governed Reality.

## 3. State experience model

### State A — Motive Formation

**Context:** Before governed Work exists.

**Source:** WIC Interaction.

**Human question:**

> Does Watt understand what I want?

**Control Room emphasis:** Understanding Alignment.

Show:

- Human intent;
- Watt interpretation;
- unresolved questions;
- readiness.

Do not emphasize production, execution, or technical implementation detail.

Expected Human feeling:

> We are thinking this through together.

### State B — Work Formation / Admission

**Context:** Interaction is ready to become governed Work.

**Human question:**

> Are we ready to start working?

**Control Room emphasis:** Shared Understanding and Admission Decision.

Show:

- current understanding;
- proposed scope;
- constraints;
- what will become governed Reality.

```text
READY != Authority
```

Human Work admission remains explicit. A readiness projection must not imply
that Work already exists or that production is authorized.

### State C — Active Planning

**Context:** Work exists, while production has not started or the next
direction is being determined.

**Source:** Plan Steering.

**Human question:**

> Why is this the next thing?

**Control Room emphasis:** Plan versus Reality.

Show:

- current objective;
- next direction;
- rationale;
- assumptions;
- unresolved decisions.

The Control Room explains the current Plan direction. It does not own or
perform planning.

### State D — Active Production

**Context:** SPG execution is active.

**Industrial analogy:** Normal production operation.

**Human question:**

> What is happening now?

**Control Room emphasis:** Production Status and Current Activity.

Show:

- current phase;
- execution health;
- meaningful progress signal;
- waiting or blocking reason;
- required Human attention.

Avoid raw model logs, token data, and internal implementation noise that does
not improve Human understanding or governance.

### State E — Exception / Human Attention

**Context:** Current Reality requires Human involvement.

Examples include:

- scope expansion;
- Authority decision;
- Verification failure;
- blocked dependency;
- ambiguous direction.

**Industrial analogy:** Andon or exception handling.

**Control Room emphasis:** Attention Center.

Show:

- what happened;
- why attention is needed;
- possible options;
- likely impact.

The Control Room should not merely display an alert. It should provide enough
governed context to help the Human make the required decision without
manufacturing Authority or selecting on the Human's behalf.

### State F — Verification / Trust Establishment

**Context:** A production result exists and trust is being established.

**Human question:**

> Can I trust this?

**Control Room emphasis:** Quality and Trust.

Show:

- Completion status;
- Verification Evidence;
- Runtime Reality;
- Trusted Baseline relationship;
- Evidence lineage.

```text
Generated != Trusted
```

The Control Room projects trust evidence. It does not create Verification or
Runtime truth.

### State G — Currently Satisfied / Continue

**Context:** The current Work outcome has been achieved.

```text
Work currently satisfied
    !=
Interaction terminated
```

**Control Room emphasis:** Satisfaction State.

Show:

- achieved outcome;
- historical Evidence;
- remaining Interaction openness;
- possible Emerging Directions.

Expected Human feeling:

> The work is complete, but collaboration continues.

### State H — Evolution / New Direction

**Context:** New Human input appears after completion or during Work.

**Control Room emphasis:** Attention and Evolution.

Distinguish:

- continuation of Current Work;
- Work refinement;
- Emerging Direction;
- new Work recommendation.

The governing principle is to preserve ideas without losing focus. New input
does not silently redefine Current Work, admitted intent, or production
Authority.

## 4. State transition experience

The Control Room should make meaningful transitions understandable. A
transition explanation should identify the Reality change and its consequence,
not merely announce a new status.

### Formation → Admission

Explain:

> We now have enough shared understanding to begin governed Work.

This explanation does not replace explicit Human admission.

### Production → Attention

Explain:

> The current path requires Human decision.

The Control Room should also expose the relevant reason, options, and impact.

### Completion → Evolution

Explain:

> The previous objective is satisfied; a new direction may begin.

The completed result remains historical truth. A continuation, refinement, or
new Work still follows its existing governance boundary.

## 5. Industrial concepts adapted

| Industrial concept | Watt experience meaning |
|---|---|
| Normal Production | Active software production |
| Andon Exception | Human Attention |
| Quality Gate | Verification and trust establishment |
| Production History | Reality lineage |
| Plan Deviation | Plan-versus-Reality reassessment |

These mappings improve Human understanding and operational governance. They do
not redefine existing Watt domain objects or lifecycle semantics.

## 6. Software-specific differences

Software production differs from manufacturing. The Control Room must preserve:

- evolving intent;
- interpretation;
- uncertainty;
- refinement;
- creative exploration.

It must not optimize for:

- throughput alone;
- task-completion speed;
- AI utilization.

It should optimize for:

> Trusted software outcomes.

Operational visibility must coexist with adaptation and knowledge work rather
than forcing every Work through a rigid deterministic sequence.

## 7. Ownership and truth boundary

The state-aware experience remains a Human-facing projection:

| Reality area | Existing owner |
|---|---|
| Interaction, interpretation, Work evolution | WIC |
| Next direction and reassessment | Plan Steering |
| Governed production execution | SPG |
| Execution inside an admitted envelope | Executor |
| Verification and Runtime Evidence Truth | Verification / Runtime |
| State-aware Human emphasis | Control Room projection |

Changing the projected experience does not change the underlying truth,
Authority, or lifecycle.

## 8. Explicit non-goals

This design does not introduce:

- new lifecycle states;
- a UI state machine;
- dashboard implementation;
- a database model;
- a KPI system;
- user roles or permissions.

It does not authorize changes to UI, API, schema, migrations, WIC, SPG, Plan
Steering, Executor, Verification, Runtime, or tests.
