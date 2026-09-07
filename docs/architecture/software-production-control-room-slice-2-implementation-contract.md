# Watt Control Room Slice 2 - WIC Integration Implementation Contract

## 1. Status and authority

~~~text
Contract
    DEFINED

Control Room Slice 1 - Production Control Foundation
    CLOSED / PASS

Control Room Slice 2 - WIC Integration
    CLOSED / PASS

Architecture Lead Reality Review
    PASS

Closure
    ADMITTED 2026-09-07
~~~

This contract defines the next bounded implementation slice for the Watt
Software Production Control Room. It is governed by:

- [Control Room Design](../product/software-production-control-room-design.md);
- [Control Room MVP Scope](../product/software-production-control-room-mvp-scope.md);
- [Control Room MVP Information Architecture](../product/software-production-control-room-mvp-information-architecture.md);
- [Control Room MVP Implementation Planning](../product/software-production-control-room-mvp-implementation-planning.md);
- [Control Room Slice 1 Contract](software-production-control-room-slice-1-implementation-contract.md);
- [Work Interaction & Closed-loop Refinement Contract](work-interaction-closed-loop-refinement.md).

This document records engineering obligations and the resulting bounded
implementation Reality. Implementation authority was supplied separately by
the Slice 2 implementation task; this contract does not authorize Slice 3,
Provider, or Dogfood work.

## 2. Slice identity and purpose

**Name:** Control Room Slice 2 - WIC Integration.

**Purpose:** Expose Human-Watt understanding alignment inside the existing
Control Room so the Human can answer:

> Does Watt understand what I mean?

~~~text
Existing WIC Reality
    |
    v
bounded Understanding Alignment projection
    |
    v
Human can compare expression, interpretation, and governed meaning
~~~

The Control Room remains a projection layer. It owns no Interaction,
Interpretation, Work Reality, Authority, lifecycle, or transition.

## 3. Truth separation requirement

The presentation must preserve three distinct layers:

~~~text
Human said
    |
    v
Watt interpreted
    |
    v
Governed Reality
~~~

These layers must not be flattened into one summary.

### 3.1 Human said

Source: existing WIC Interaction records and their existing source/sequence
identity.

The projection may summarize or select relevant Human expression for usability,
but must preserve that this is what the Human expressed. Human expression is
not automatically Interpretation, Work Truth, Work Authority, or production
scope.

### 3.2 Watt interpreted

Source: the existing current WIC assessment and Shared Understanding
projection.

The projection may show the interpreted Motive, Desired Outcome, candidate
context, candidate constraints, current requests, and unresolved material
questions already present in WIC Reality. It must expose when an assessment is
missing or no longer current. An advisory interpretation must not be presented
as admitted Work Reality.

### 3.3 Governed Reality

Source: the existing admitted Work Reality revision associated with the
Interaction and current Work.

The projection may show the governed Motive, Desired Outcome, constraints,
relevant context facts, and revision identity already present in WIC Reality.
Before admission, Governed Reality must be shown as absent rather than copied
from an advisory assessment.

## 4. Included capability

### 4.1 Understanding Alignment Projection

Display the relationship between:

- Human expression;
- Watt interpretation;
- governed Work Reality.

Requirements:

- use existing WIC facts and projections;
- preserve source identity and current/stale meaning where available;
- make advisory versus governed meaning visible;
- introduce no duplicate interpretation truth;
- introduce no lifecycle or transition;
- do not infer agreement merely because text is similar;
- do not turn a display comparison into Work admission or revision.

### 4.2 Shared Understanding Projection

Display, when present:

- current understood objective;
- confirmed constraints;
- relevant facts;
- unresolved questions.

Source rules:

- interpreted/candidate values come from the current existing WIC assessment
  and remain labeled as interpretation;
- confirmed values come from the admitted Work Reality revision and remain
  labeled as governed;
- unresolved questions come from the existing assessment/readiness projection;
- missing or stale values remain explicit.

The projection must not combine candidate and governed values into an
untraceable synthetic truth.

### 4.3 Interpretation Status

Display a Human-meaningful understanding condition using only existing WIC
Reality.

Examples of presentation language include:

- understood;
- needs clarification;
- waiting for Human decision.

These are presentation labels, not new WIC lifecycle states. Their basis must
remain existing facts such as assessment currency, readiness, unresolved
material questions, and an existing pending Human admission/decision
condition. The Control Room must not create or persist a parallel status.

## 5. Explicit non-scope

Slice 2 must not implement:

- a new Interaction model;
- a new Interpretation engine or Provider capability;
- new assessment storage;
- Work admission changes;
- automatic Work admission;
- automatic Work revision;
- automatic decision making;
- Plan creation, progression, reassessment, or revision;
- SPG planning, orchestration, execution, or completion changes;
- Runtime state or transition changes;
- Verification or Evidence ownership;
- a Workspace or Control Room domain entity.

Slice 2 does not authorize new backend domain models, persistence, database
tables, migrations, lifecycle states, WebSocket, Event Bus, or another state
store.

## 6. Architecture and authority boundary

Ownership remains:

| Capability | Owner |
|---|---|
| Interaction, Interpretation, Shared Understanding, and Work evolution | WIC |
| What should happen next | Plan Steering |
| Governed engineering production | SPG |
| Execution mechanics | Executor |
| Verification and Runtime evidence truth | Verification / Runtime |
| Human-facing alignment display | Control Room projection |

The Control Room may read and render these facts. It may not redefine their
meaning, resolve an ambiguity, admit a Work change, or advance production.

Human Authority remains required wherever the existing WIC/Work lifecycle
requires it. Visibility of a candidate interpretation is not Authority.

## 7. Implementation strategy boundary

Prefer:

- existing WIC APIs;
- existing Shared Understanding and Work Reality projections;
- existing frontend patterns established by Slice 1;
- existing safe DOM rendering and polling behavior.

Avoid:

- backend redesign;
- new domain or persistence models;
- duplicated WIC state;
- a frontend rewrite;
- an additional interaction lifecycle;
- hidden inference that fills gaps in existing WIC Reality.

The implementation may add only the minimum presentation projection glue
needed to keep the three truth layers distinguishable.

## 8. Validation contract

The Slice 2 implementation must prove:

1. the Human can see what Watt currently understood;
2. the Human can distinguish Human expression, AI interpretation, and governed
   Reality;
3. current, missing, stale, unresolved, and pending-Human conditions remain
   truthful to existing WIC facts;
4. candidate interpretation is never presented as governed Reality;
5. existing WIC behavior and lifecycle remain unchanged;
6. existing Work Authority and lifecycle remain unchanged;
7. reading or refreshing the Control Room creates no Interaction record,
   assessment, Work, Work Reality revision, Authority decision, Plan change,
   Run, PWU, Attempt, Provider activity, Verification, Runtime Commit, or
   Trusted Baseline change.

Required focused evidence:

- projection tests for the three truth layers;
- absent, stale, unresolved, governed, and pending-Human cases;
- bounded UI tests showing the Human question is answerable;
- read/refresh non-interference checks;
- affected WIC and Work regression;
- confirmation that Slice 1 Objective, Status, and Attention behavior remains
  unchanged.

No Provider or Dogfood proof is authorized by this contract.

### 8.1 Focused validation evidence

The implemented presentation projection:

- consumes the existing WIC Shared Understanding returned by the existing
  Interaction API;
- matches the selected Work to its existing current Interaction or governed
  Work Reality revision;
- renders Human expression, advisory Watt interpretation, and governed Work
  Reality as separate layers;
- exposes current, stale, unresolved, pending-Human, governed, and absent
  conditions without persisting a new WIC state;
- renders confirmed constraints and relevant facts only from governed Work
  Reality;
- issues no API request and owns no mutation path;
- adds no backend model, API, schema, migration, lifecycle state, admission
  path, or truth owner.

Focused validation on 2026-09-07:

- Node web-state suite: 18 passed;
- UI and WIC contract suites: 10 passed;
- Work API and WIC PostgreSQL integration suites: 37 passed, 1 skipped because
  real Provider proof requires separate explicit authorization;
- JavaScript syntax, Python compile/import, uv lock, and git diff checks:
  passed.

The PostgreSQL suites used the isolated spg_test database; the running Watt
application database remained spg_dev. No Provider was called.

## 9. Completion criteria

Control Room Slice 2 closes only when:

- the implementation correctly exposes existing WIC Reality;
- Human expression, Watt interpretation, and governed Reality remain visibly
  distinct;
- no duplicated truth, lifecycle, Work Authority, or state ownership exists;
- existing WIC and Work behavior remains unchanged;
- focused validation and non-interference evidence exists;
- Architecture Lead Reality Review accepts the implementation and evidence.

Architecture Lead Reality Review confirmed:

- the implementation matches the bounded Understanding Alignment, Shared
  Understanding, and Interpretation Status contract;
- Human expression, advisory Watt interpretation, and governed Work Reality
  remain visibly distinct;
- WIC remains the sole owner of Interaction, Interpretation, Shared
  Understanding, and Work evolution truth;
- the Control Room owns no interpretation lifecycle, admission, revision,
  Authority, Plan, SPG, Runtime, or Verification transition;
- no Workspace or Control Room entity, persistence, schema, migration, or new
  lifecycle state was introduced;
- the focused validation and non-interference evidence in Section 8.1 supports
  closure without an architecture boundary violation.

Final admitted Reality:

~~~text
Control Room Slice 2
    CLOSED / PASS

Architecture Lead Reality Review
    PASS
~~~

## 10. Future compatibility

Slice 2 must preserve future evolution space for:

- richer Motive refinement;
- future Workspace-first Control Room experience;
- advanced understanding-alignment capabilities;
- Slice 3 Production Intelligence;
- Slice 4 Human Product Acceptance.

It must not pre-implement those capabilities or make a future Workspace entity
mandatory.
