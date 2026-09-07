# Watt Software Production Control Room MVP Scope

## 1. Status, authority, and scope

```text
Document type
    AUTHORITATIVE PRODUCT SCOPE

Control Room MVP capability boundary
    DEFINED / NOT IMPLEMENTED BY THIS DOCUMENT

WIC Core
    CLOSED / PASS
```

This document defines what the Watt Software Production Control Room must
provide for MVP, what may be deferred, and what is explicitly excluded. It is
governed by:

- [Software Production Control Room Design](software-production-control-room-design.md);
- [Control Room MVP Surface Design](software-production-control-room-mvp-surface-design.md);
- [Control Room State Experience Design](software-production-control-room-state-experience.md);
- [Workspace-first Experience Principles](workspace-first-experience-principles.md).

This is a product scope boundary. It does not define or authorize code, UI,
API, schema, migrations, new domain objects, or behavior changes.

## 2. Product objective

The MVP Control Room exists to help the Human understand and manage AI-native
software production.

Its goal is not maximum information visibility. Its goal is:

> Correct Human understanding and attention allocation.

The MVP should present enough governed Reality for the Human to understand the
objective, current state, required attention, direction, and trust without
requiring continuous inspection of internal system mechanics.

## 3. MVP core surfaces

### 3.1 Production Objective — MUST HAVE

Purpose:

> What are we producing?

Projection from:

- Motive;
- Work;
- Work Reality.

Show:

- current objective;
- Desired Outcome;
- current satisfaction.

### 3.2 Understanding Alignment — MUST HAVE

Purpose:

> Does Watt understand what the Human means?

Projection from WIC.

Show:

- Human intent;
- Watt interpretation;
- unresolved questions;
- governed understanding.

```text
Conversation is provenance.
Governed Reality is truth.
```

The surface must preserve this distinction rather than presenting the latest
conversation as admitted truth.

### 3.3 Production Status — MUST HAVE

Purpose:

> What is happening now?

Projection from Runtime and SPG.

Show:

- current phase;
- current meaningful activity;
- execution health;
- waiting or blocking reason.

Avoid token metrics, raw Agent logs, and implementation noise that does not
help Human understanding or governance.

### 3.4 Attention / Exception Center — MUST HAVE

Purpose:

> What requires Human attention?

Support Human understanding of:

- decisions requiring Human Authority;
- blocked conditions;
- scope expansion;
- Verification issues;
- Emerging Directions.

The governing principle is exception-based management. The Human should not
need to monitor every production detail to discover that intervention is
required.

### 3.5 Current Direction / Plan View — MUST HAVE

Purpose:

> Why is the next action this?

Projection from Plan Steering.

Show:

- current direction;
- rationale;
- relevant Reality basis.

The Control Room explains the Plan. It does not replace Plan Steering or own
WHAT NEXT.

### 3.6 Trust / Evidence Summary — SHOULD HAVE IN MVP

Purpose:

> Why should we trust the result?

Show the relationship to:

- Verification;
- Completion;
- Runtime Reality;
- Trusted Baseline.

A detailed Evidence explorer may be deferred. The summary must not manufacture
trust, collapse distinct evidence types, or reinterpret their existing truth
ownership.

### 3.7 Interaction Entry — MUST HAVE

Purpose:

> Continue working with Watt.

Interaction remains the Human communication channel. It is not the primary
truth source, the center of the Control Room, or automatic production
Authority.

## 4. Control action boundary

The Control Room is not limited forever to observation; it may support
controlled Human intervention. However:

```text
Action capability must never exceed governance capability.
```

### 4.1 MVP-supported actions

The MVP may support only actions already backed by admitted governance:

- view governed Reality;
- review Attention;
- provide Human decisions;
- approve governed transitions.

Presentation of an action must not create new Authority or bypass the
underlying WIC, Plan Steering, SPG, Verification, or Runtime contract.

### 4.2 Deferred actions

#### Governed Stop

Meaning: the Human requests stopping current production.

Required future semantic shape:

```text
Human Stop Request
    ↓
Reality Reconciliation
    ↓
Truthful stopped state
```

A simple “kill process” action is not an acceptable substitute. Process
termination alone does not establish truthful production, Attempt, workspace,
or recovery Reality.

#### Pause / Resume

Requires future semantics for:

- execution checkpoint;
- recovery;
- continuity guarantees.

#### Replan

Requires:

- governed Work Reality update;
- Plan reassessment.

These capabilities are deferred. This document does not admit their
implementation or imply that they already exist.

## 5. Required MVP state coverage

### Formation

Must provide Understanding Alignment.

### Production

Must provide Production Status.

### Attention

Must provide the Attention / Exception Center.

### Completion

Must provide a Trust / Evidence summary.

### Evolution

Must distinguish Current Work from an Emerging Direction.

These are experience coverage requirements projected from existing Reality,
not new domain lifecycle states.

## 6. Explicit MVP deferrals

The MVP does not include:

- a Workspace entity;
- a Control Room entity;
- a dashboard builder;
- custom widgets;
- a KPI system;
- productivity scoring;
- organization roles;
- permissions;
- multi-user collaboration;
- Sub-workspace;
- Work Graph;
- an advanced economics view;
- capacity-planning UI;
- fleet-operations UI.

These deferrals must not weaken the required MVP understanding, status,
attention, direction, or trust projections.

## 7. Industrial adaptation boundary

Watt borrows:

- transparency;
- exception management;
- traceability;
- quality thinking.

Watt does not borrow:

- factory-throughput metrics;
- worker-productivity metrics;
- deterministic workflows.

Software production remains knowledge work, interpretation-driven, and
adaptive. The Control Room should improve operational clarity without reducing
software work to quantity or utilization measures.

## 8. Future evolution directions

Possible future areas include:

- role-oriented views;
- production economics;
- capacity planning;
- advanced operational control;
- governed stop and recovery;
- advanced Evidence exploration.

These are future possibilities only. They are not MVP requirements, current
capabilities, or implementation commitments.

## 9. MVP scope summary

```text
MUST HAVE
    Production Objective
    Understanding Alignment
    Production Status
    Attention / Exception Center
    Current Direction / Plan View
    Interaction Entry

SHOULD HAVE IN MVP
    Trust / Evidence Summary

DEFERRED
    Governed Stop
    Pause / Resume
    Replan control
    Advanced Evidence exploration
    Role/economics/capacity/fleet views

EXCLUDED FROM MVP
    New Workspace or Control Room entities
    Hierarchy, Work Graph, KPI, scoring, permissions, and multi-user systems
```
