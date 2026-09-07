# Watt Control Room Slice 3 - Production Intelligence Implementation Contract

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
- [Control Room Slice 2 Contract](software-production-control-room-slice-2-implementation-contract.md);
- [Reality-driven Plan Steering Principles](reality-driven-plan-steering-principles.md).

This document records engineering obligations and the resulting bounded
implementation Reality. Implementation authority was supplied separately by
the Slice 3 implementation task; this contract does not authorize Slice 4,
Production Execution Package, Context Assembly, Provider, or Dogfood work.

## 2. Slice identity and purpose

**Name:** Control Room Slice 3 - Production Intelligence.

**Purpose:** Extend the existing Control Room so the Human can answer:

> Why is this the next direction?

> Why can we trust the result?

~~~text
Existing Plan Steering Reality
    +
Existing Completion / Verification / Runtime Reality
    |
    v
bounded Human-facing projection
    |
    v
direction and trust are understandable without transferring ownership
~~~

"Production Intelligence" in this slice means a coherent Human-facing
projection of existing facts. It is not a new Planner, trust engine, evidence
model, or lifecycle owner.

## 3. Included capability A - Current Direction / Plan Projection

### 3.1 Current direction

Display the current admitted production direction using existing Plan
Steering Reality, including when available:

- Work objective;
- active Plan revision identity and revision number;
- current Plan step type, objective, completion condition, and state;
- known next step or steps;
- current automatic progression condition;
- current Human-attention or stop condition.

The projection must not describe a merely possible step as the current
admitted direction.

### 3.2 Why this step is next

Display existing rationale and Reality basis, including when available:

- Plan Steering selection rationale;
- latest Steering Decision reason and outcome;
- Reality references already attached to that decision;
- relevant blocker or Human-attention reason;
- the active Plan revision on which the direction depends.

The projection may organize these facts for Human comprehension. It must not
invent a rationale, infer Authority, or perform a new Plan decision.

### 3.3 Deviation and reassessment information

Display relevant deviation or reassessment information only when it already
exists in Plan Steering or Attention Reality, such as:

- a changed active Plan revision;
- an existing Steering outcome;
- an existing stop reason;
- an existing Human decision requirement;
- an existing blocker supported by Reality references.

Absence of an existing deviation or reassessment fact must be shown as absent.
Slice 3 does not introduce a new deviation detector, reassessment engine, Plan
revision, or planning state.

### 3.4 Plan ownership boundary

Plan Steering remains the owner of WHAT NEXT. The Control Room may read and
render its current projection, but may not:

- create or edit a Plan;
- select or advance a step;
- create a Steering Decision;
- trigger automatic replanning;
- admit a Plan revision;
- resolve a blocker or Human decision.

## 4. Included capability B - Trust Summary Projection

### 4.1 Trust relationship

Display a concise relationship among existing trust facts:

~~~text
Completion Reality
    |
    v
Verification Reality
    |
    v
Runtime Commit Reality
    |
    v
Current Trusted Baseline
~~~

The presentation must preserve that these are distinct facts and transitions.
It must not collapse them into a synthetic score or a generic success badge.

### 4.2 Completion

Display whether the existing production result has reached the Completion
condition represented by current Work/production Reality. Relevant existing
facts may include produced artifacts, current production step, completion
outcome where projected, and a remaining blocker or risk.

Completion must not be inferred from Provider completion, artifact existence,
or a completed UI request alone.

### 4.3 Verification

Display the existing Verification summary and whether required obligations
pass, fail, remain missing, or are not yet available.

Verification remains the evidence authority. The Control Room must not run a
verifier, reinterpret a failed obligation as passing, or create a replacement
trust judgment.

### 4.4 Runtime Commit and Trusted Baseline

Display whether an existing trusted Runtime Commit is present and whether the
result is represented by the Current Trusted Baseline. Relevant existing facts
include:

- latest trusted Runtime Commit identity already projected for the Work;
- Work Result `trusted_result`;
- repository state already projected by Work Result;
- Current Trusted Baseline revision and tree identity already projected by
  Runtime Activation Reality.

No Runtime Commit or Trusted Baseline advancement may be inferred or created
by rendering this summary.

### 4.5 Trusted Baseline and Active Runtime distinction

The summary must preserve the established Runtime semantic:

~~~text
Trusted Baseline
    !=
Active Runtime
~~~

When existing Runtime Activation Reality shows that the active application is
not yet at the Current Trusted Baseline, the Control Room must present that
condition truthfully. A trusted repository result must not be presented as
active product behavior until existing Runtime Reality supports that claim.

### 4.6 Trust ownership boundary

The Trust Summary may explain why existing facts support or do not yet support
trust. It must not introduce:

- a trust score;
- a new Evidence record;
- a new Verification authority;
- a new Completion condition;
- a new Runtime Commit path;
- a new Trusted Baseline pointer;
- a claim stronger than the source Reality.

## 5. Existing source mapping

Slice 3 should reuse the current read projections and frontend patterns.

| Control Room information | Existing source Reality |
|---|---|
| Current direction and current/next steps | `GET /api/works/{work_id}/steering` current and known-next step projections |
| Rationale and Reality basis | Steering selection rationale, latest decision reason/outcome, and existing Reality references |
| Reassessment or stop condition | Active Plan revision, Steering outcome, automatic progression state, stop reason, and existing Attention |
| Completion and Verification summary | Existing Work projection and `GET /api/works/{work_id}/result` |
| Runtime Commit / trusted result | Existing Work and Work Result projections |
| Current Trusted Baseline / active application | Existing Runtime Activation projection returned with Work Result |

If a required source fact is not exposed by an existing read projection, the
implementation must show it as unavailable or seek separate bounded authority
for the smallest projection-only exposure. A missing display field is not
authority to create a new source model or lifecycle.

## 6. Architecture and authority boundary

Ownership remains:

| Capability | Owner |
|---|---|
| Interaction, Interpretation, and Work evolution | WIC |
| Plan direction, reassessment, and WHAT NEXT | Plan Steering |
| Governed production execution | SPG |
| Execution mechanics | Executor |
| Completion and Verification evidence truth | Completion / Verification |
| Runtime Commit, Trusted Baseline, and active Runtime Reality | Runtime |
| Human-facing direction and trust display | Control Room projection |

The Control Room may compose these read projections for presentation. It may
not redefine their meaning, transition their lifecycle, or acquire their
Authority.

## 7. Explicit non-scope

Slice 3 must not implement:

- Plan editing or Plan admission;
- automatic replanning or a new Planner;
- step selection, progression, or execution;
- new Plan Steering behavior;
- trust scoring;
- an Evidence explorer or new Evidence model;
- Guardian or Production Passport;
- new Completion or Verification behavior;
- Runtime Commit, baseline advancement, or Runtime activation behavior;
- Stop, Pause, Resume, or Reality Reconciliation;
- a Workspace or Control Room domain entity;
- new database tables, migrations, lifecycle states, WebSocket, Event Bus, or
  another state store;
- a dashboard framework or generic KPI system.

Slice 3 does not authorize WIC, Plan Steering, SPG, Executor, Verification, or
Runtime semantic changes.

## 8. Implementation strategy boundary

Prefer:

- the existing Steering and Work Result APIs;
- existing Work and Attention projections;
- existing Runtime Activation projection;
- existing frontend patterns established by Slices 1 and 2;
- existing polling and safe DOM rendering.

Avoid:

- backend ownership changes;
- duplicated Plan or trust Reality;
- hidden inference that fills missing evidence;
- a frontend rewrite;
- new infrastructure for freshness or visualization.

The implementation should add only the minimum presentation/projection glue
required to make existing direction and trust facts understandable.

## 9. Validation contract

The Slice 3 implementation must prove:

1. the Human can identify the current admitted direction;
2. the Human can understand why the current or next step exists from existing
   rationale and Reality references;
3. missing rationale or reassessment information remains explicit;
4. the Human can distinguish Completion, Verification, Runtime Commit, Current
   Trusted Baseline, and Active Runtime conditions;
5. trusted and not-yet-trusted results are presented truthfully;
6. a Trusted Baseline / Active Runtime divergence is not hidden;
7. existing Plan Steering behavior and Authority remain unchanged;
8. existing Completion, Verification, and Runtime ownership remain unchanged;
9. Slice 1 Objective/Status/Attention and Slice 2 Understanding Alignment
   behavior remain valid;
10. reading or refreshing the Control Room creates no Interaction, Work, Work
    Reality revision, Plan revision, Steering Decision, Run, PWU, Attempt,
    Provider activity, Completion, Verification, Runtime Commit, Trusted
    Baseline change, or Runtime activation.

Required focused evidence:

- Current Direction projection tests for current, known-next, blocked,
  Human-attention, missing, and revised-Plan conditions;
- Trust Summary projection tests for incomplete, Verification pass/fail,
  trusted, and Trusted-Baseline/Active-Runtime divergence conditions;
- bounded UI contract tests proving both Human questions are answerable;
- read/refresh non-interference checks;
- affected Plan Steering regression;
- affected Completion/Verification/Work Result regression;
- confirmation that Slice 1 and Slice 2 projections do not regress.

No Provider or Dogfood proof is authorized by this contract.

### 9.1 Focused validation evidence

The implemented presentation projection:

- reads the existing Work-specific Steering projection through the existing
  `GET /api/works/{work_id}/steering` boundary;
- treats an absent Steering Plan as unavailable instead of manufacturing a
  direction;
- renders the active Plan revision, current and known-next steps, selection
  rationale, exact existing Reality references, and existing stop/attention
  conditions;
- composes existing Work and Work Result facts into separate Completion,
  Verification, Runtime Commit, Current Trusted Baseline, and Active Runtime
  statements;
- preserves a trusted repository result and an active-at-baseline result as
  different conditions;
- uses text-only DOM rendering and the existing observational polling path;
- adds no backend model, API, persistence, schema, migration, lifecycle state,
  planning path, Verification authority, or Runtime transition;
- issues no mutation request from either Slice 3 render projection.

Focused validation on 2026-09-07:

- Node web-state suite: 23 passed;
- UI contract suite: 7 passed;
- Plan Steering, Runtime Activation, and Verification contract suites:
  35 passed;
- Plan Steering and Verification PostgreSQL integration suites: 51 passed;
- MVP application contract suite: 10 passed;
- MVP Work-flow PostgreSQL integration suite: 26 passed;
- JavaScript syntax checks: passed.

The PostgreSQL suites used only the isolated `spg_test` database. The product
database environment variable was removed from the test process. No Provider
or Dogfood activity occurred. The Work-flow suite reported four existing
Pydantic instance-level `model_fields` deprecation warnings; they did not
affect the result and are outside this Slice 3 projection scope.

## 10. Completion criteria

Control Room Slice 3 closes only when:

- the implementation projects existing Plan Steering and trust Reality;
- the Human can understand current direction, rationale, and trust basis;
- missing, blocked, failed, trusted, and not-active conditions remain truthful;
- no duplicated truth, lifecycle, state ownership, or Authority exists;
- existing WIC, Plan Steering, SPG, Completion, Verification, and Runtime
  behavior remains unchanged;
- focused validation and non-interference evidence exists;
- Architecture Lead Reality Review accepts the implementation and evidence.

Architecture Lead Reality Review confirmed:

- Current Direction projects only the existing active Plan revision, current
  and known-next steps, rationale, Reality references, and existing
  stop/attention conditions;
- the Control Room creates, edits, selects, admits, or replans no Plan or
  Steering direction;
- Trust Summary projects only existing Completion, Verification, Runtime
  Commit, Current Trusted Baseline, and Active Runtime facts;
- the Control Room calculates no trust score, replaces no Verification
  authority, owns no Evidence truth, and introduces no Guardian or Evidence
  Explorer capability;
- Plan Steering remains the owner of WHAT NEXT, Completion/Verification remain
  the owners of trust evidence, and Runtime remains the owner of Runtime
  Commit, Trusted Baseline, and Active Runtime Reality;
- no Control Room or Workspace entity, persistence, schema, migration,
  lifecycle state, or duplicated Reality ownership was introduced;
- the focused validation and non-interference evidence in Section 9.1 supports
  closure without an architecture boundary violation.

Final admitted Reality:

~~~text
Control Room Slice 3
    CLOSED / PASS

Architecture Lead Reality Review
    PASS
~~~

## 11. Future compatibility

Slice 3 must preserve future evolution space for:

- a detailed Evidence explorer;
- future Guardian and Production Passport capabilities;
- future governed process-control actions;
- future Workspace-first Control Room experience;
- Slice 4 Human Product Acceptance.

It must not pre-implement those capabilities or make a future Workspace,
Control Room entity, trust score, or dashboard platform mandatory.
