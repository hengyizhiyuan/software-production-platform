# Watt Workspace-first Product Experience Principles

## 1. Status, authority, and scope

```text
Document type
    AUTHORITATIVE PRODUCT PRINCIPLE

Workspace-first product direction
    FUTURE DIRECTION / NOT IMPLEMENTED

WIC Core
    CLOSED / PASS
```

This document records why Watt needs a Workspace-first product experience and
defines its product philosophy, Human mental model, information hierarchy,
relationship to existing capabilities, and current boundary. It specializes
the [Watt Product North Star](../architecture/watt-product-north-star.md) and
projects the closed
[Work Interaction & Closed-loop Refinement Core](../architecture/work-interaction-closed-loop-refinement.md).

It does not define UI components, API behavior, persistence, database entities,
or an implementation roadmap.

## 2. Core product thesis

Workspace is not:

- a chat container;
- a Jira replacement;
- a project dashboard;
- a task list;
- a document folder;
- a Notion clone.

Workspace is:

> A Human–Watt shared attention surface centered around a Motive.

Its purpose is to help Human and Watt continuously maintain:

- what they are trying to achieve;
- what is understood;
- what has been decided;
- what is happening now;
- what evidence supports current Reality;
- what deserves attention next.

The primary product value is continuity of shared attention, not accumulation
of information or exposure of internal machinery.

## 3. Human mental model

The Human should not feel:

> I am creating tasks for an AI.

The Human should feel:

> I am working with Watt on something important.

Workspace therefore supports continuing collaboration around a Motive rather
than a sequence of isolated requests. This relationship may continue before
Work admission, during governed Work evolution, through production and
feedback, and after a Work becomes currently satisfied.

## 4. Workspace is a product projection

Workspace is a **product projection**, not a new Source of Truth. It presents
existing governed realities for Human understanding without replacing their
ownership:

| Capability | Existing truth ownership |
|---|---|
| WIC | Human Interaction, Interpretation, Shared Understanding projection, and Work evolution |
| Plan Steering | WHAT NEXT |
| SPG | Governed production execution |
| Executor | HOW inside the admitted execution envelope |
| Verification / Runtime | Evidence Truth |

Workspace composes views over these realities. It does not acquire their
Authority, duplicate their state, or silently reconcile disagreement between
them.

## 5. Information hierarchy

The following layers describe Human questions and conceptual information. They
do not prescribe screen layout or frontend components.

### 5.1 Current Focus

Answers:

> What are we working on?

Conceptually includes:

- Motive;
- Current Work;
- Desired Outcome;
- current satisfaction state;
- current attention focus.

### 5.2 Shared Understanding

Answers:

> Do Watt and I understand this the same way?

```text
Human said
    ↓
Watt interpreted
    ↓
Governed Reality
```

Raw conversation is not truth. Workspace must preserve the distinction between
Human expression, advisory interpretation, and admitted Reality.

### 5.3 Plan / Direction

Answers:

> Why is the next action this?

This is a projection of Plan Steering, admitted decisions, and relevant Reality
changes. Workspace explains direction; it does not replace Planning or decide
WHAT NEXT.

### 5.4 Activity

Answers:

> What is happening now?

Activity should communicate:

- the current stage;
- meaningful progress;
- blockers;
- whether Watt is still working.

It should avoid exposing internal Agent mechanics that do not help the Human
understand or govern the work.

### 5.5 Evidence / Trust

Answers:

> Why should I believe this result?

This layer projects Verification, Completion, Runtime Reality, Baseline, and
Evidence lineage while preserving their existing truth ownership.

### 5.6 Interaction

Answers:

> How did we get here?

Conversation is collaboration history, provenance, and a record of Human
expression. It is not execution Authority or a Source of Truth.

## 6. Attention management

Workspace should help manage Human attention. Real work contains a current
focus as well as emerging ideas and possible future directions. The experience
must distinguish:

```text
Current Work
    !=
Emerging Directions
```

For example, when the Human says:

> Future failure recovery would also be useful.

the idea should be preserved and remain visible, while Current Work stays
protected from uncontrolled scope drift. Preserving an idea does not admit it
into current Work, Plan, or production Authority.

## 7. Workspace and conversation

```text
Workspace != Chat
```

Workspace contains projections of:

- Interaction;
- Understanding;
- Plan;
- Production;
- Evidence.

Conversation is one interaction channel. Future channels may include review,
structured decision, visualization, and other modalities. No particular
channel owns Workspace or governed Reality.

## 8. Product experience principles

### Principle 1 — Shared attention before information density

The goal is not to show everything. The goal is to show what matters now.

### Principle 2 — Human understanding before system state

Technical state should be translated into concepts that are meaningful to the
Human without weakening the underlying governance semantics.

### Principle 3 — Reality before conversation

Workspace reflects governed Reality, not merely chat history.

### Principle 4 — Progressive disclosure

The default experience should be simple for the Human, with deeper governance
and Evidence views available when needed.

### Principle 5 — Preserve continuity

The Human should feel:

> The same Watt relationship continues.

not:

> I opened another task.

## 9. Relationship with WIC Dogfood observations

Human WIC Dogfood validated the product relevance of:

- Interaction before Work;
- Shared Understanding;
- focus preservation;
- Work evolution;
- `CURRENTLY_SATISFIED` with an `OPEN` Interaction.

Observed future experience improvements include:

- Motive boundary calibration;
- better representation of emerging directions;
- Human-facing processing state;
- Workspace attention presentation.

These are Product Experience improvements, not WIC Core failures. WIC remains
`CLOSED / PASS`.

## 10. Current boundary

This document defines principles only. A future implementation should begin
with minimal projections over existing Reality.

It does not introduce:

- a Workspace entity;
- Workspace hierarchy;
- Sub-workspace;
- Work tree;
- Work graph;
- a project-management model.

Those remain future product and architecture decisions. This document creates
no implementation commitment and does not change WIC, Plan Steering, SPG,
Executor, Verification, Runtime, API, UI, schema, or migration behavior.
