# Watt Workspace-first Product Experience Principles

## 1. Status, authority, and scope

```text
Document type
    AUTHORITATIVE PRODUCT PRINCIPLE

Workspace-first product direction
    IMPLEMENTED IN PRODUCT EXPERIENCE / FURTHER EVOLUTION OPEN

Workspace four-quadrant structure
    HUMAN-APPROVED / IMMUTABLE WITHOUT EXPLICIT HUMAN GOVERNOR APPROVAL

WIC Core
    CLOSED / PASS
```

This document records why Watt needs a Workspace-first product experience and
defines its product philosophy, Human mental model, information hierarchy,
relationship to existing capabilities, and current boundary. It specializes
the [Watt Product North Star](../architecture/watt-product-north-star.md) and
projects the closed
[Work Interaction & Closed-loop Refinement Core](../architecture/work-interaction-closed-loop-refinement.md).

Apart from the approved Workspace structural invariant below, it does not
define UI components, API behavior, persistence, database entities, or an
implementation roadmap.

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

This document defines product principles and the approved Workspace structural
invariant below. Further implementation should use minimal projections over
existing Reality.

It does not introduce:

- a Workspace entity;
- Workspace hierarchy;
- Sub-workspace;
- Work tree;
- Work graph;
- a project-management model.

Those remain future product and architecture decisions. The invariant does not
change WIC, Plan Steering, SPG, Executor, Verification, Runtime, schema, or
migration ownership.

## 11. Workspace Four-Quadrant Invariant

> **Human Governor correction — 2026-10-15.** The semantics below were drifted:
> the 2026-10-01 text kept the 2×2 grid but redefined its surfaces (Reality as a
> status list, Code Assets moved out, Executor/Guardian activity reduced to one
> sentence). The Human Governor restates the authoritative four quadrants:
>
> | | Left | Right |
> |---|---|---|
> | Top | **设计文档 / 代码** — before production: the guided design framework (topics, status, current focus, Watt-decided items, "以当前方案进入生产"); during and after production: the resulting design document and code (tree, diff, preview entry) | **执行 Agenda** — Plan Steering's execution agenda: stages and steps, where Work is now, what comes next and why, including re-planning from problem routing |
> | Bottom | **生产状态** — live Executor activity (PWU, step, tool activity, progress, recovery) and Guardian activity (checking, gate, findings, repair progress) | **人工操作** — only items that genuinely need the Human, each with its prompt and action buttons (material questions, controlled-authorization revoke, credentials/permissions, acceptance) |
>
> **Human Governor structural approval — 2026-10-15 (later the same day).** The
> two bottom quadrants are swapped: 生产状态 bottom-left, 人工操作 bottom-right,
> because that reads more naturally in use. This is the explicit approval the
> immutability rule below requires; it changes position only, not semantics.
>
> Narrow screens stack 设计文档/代码 → 执行 Agenda → 生产状态 → 人工操作.
> Conversation stays a subordinate surface outside the grid. This correction
> supersedes the surface semantics of the table that follows; the immutability
> rule (explicit Human Governor approval for structural change) still applies.

`WORKSPACE_FOUR_QUADRANT_LAYOUT_IMMUTABLE = TRUE` is a permanent Human Governor
product decision. The primary desktop Workspace is one two-by-two structure in
this exact semantic and spatial order:

| | Human intention and control | System truth and execution |
|---|---|---|
| Top | **Agenda** — Human-visible governed direction | **Reality** — current canonical facts |
| Bottom | **Actions** — canonical Human Attention and review | **Production** — Human-readable Watt activity |

Agenda remains above Actions; Reality remains above Production. Guardian
assurance belongs in Reality, its repair progress in Production, and any real
Human decision in Actions. Candidate readiness belongs in Production; review,
Preview and Acceptance controls belong in Actions. Code Assets remains its
Product-scoped page, linked from Workspace. None becomes a fifth peer quadrant
or replaces one. Conversation is a subordinate interaction surface outside the
grid; advanced evidence stays behind progressive disclosure.

Internal content, typography, spacing, colors, responsive sizing and emphasis
may evolve. Only physically narrow screens may stack the four surfaces, in the
same Agenda → Reality → Actions → Production sequence. Removing, merging,
swapping, tabbing, demoting, or otherwise changing the existence, identity,
order, desktop placement, or primary status of any quadrant requires **explicit
Human Governor approval**. Silence or a feature integration request is not
approval. This constraint applies to future refactors, themes, integrations,
responsive work and framework migrations.

## 12. Conversation placement (restored — Human Governor, 2026-10-15)

The Composer and Current Interaction follow the approved
[Calibration Notes §18 and §21.2](watt-core-workspace-experience-calibration-notes.md#18-transient-current-interaction-layer):
the Composer is a one-line dock at the bottom of the central Workspace that
expands upward on focus and collapses after submission; the just-submitted
Human turn and Watt's streaming reply stay together in the central Current
Interaction; after a reading grace period (paused on hover, focus, selection or
expansion) the pair calmly fades out of the center and fades into the right
Conversation History, in order and exactly once. The right rail holds history
and provenance only — no primary Composer. Governed effects remain in the four
quadrants after the wording settles into history.
