# Reality-driven Plan Steering — MVP Behavioral Contract

## Status and Authority

```text
Reality-driven Plan Steering
    MVP BEHAVIORAL CONTRACT = DEFINED / ADMITTED
    MVP CLOSED / PASS
    REAL LONG-LIVED DOGFOOD / HUMAN ACCEPTANCE PASS
    MATERIAL MVP CORE PRODUCT CAPABILITY
```

This contract remains the behavioral Source of Truth. MVP-PLAN-STEER-1C
through 1L implement its bounded MVP behavior without defining a final general
planning schema or reopening PLAN-1B and SPG authority semantics.

It specializes the admitted
[Reality-driven Plan Steering — Foundational Principles](reality-driven-plan-steering-principles.md)
and uses the product semantics established by the
[Motive / Work / Plan Concept Calibration](motive-work-plan-concept-calibration.md).
The foundational principles remain authoritative where this bounded MVP
behavioral contract does not add operational precision.

## MVP Product Objective

Reality-driven Plan Steering allows Watt to guide a potentially long-lived
Motive / Work from Current Reality toward its intended outcome without making
the Human a manual Continue button.

The current Human Governor and Architecture Lead AI collaboration is the
accepted behavioral baseline:

- **Human** owns the goal, direction, major product decisions, major
  architecture trade-offs, and scope/risk Authority.
- **AI** evaluates Current Reality, determines what should happen next,
  controls progression rhythm, decides whether more refinement or design is
  needed, determines when work is mature enough for implementation, reviews
  execution Reality, inserts necessary Findings, and proposes or continues the
  next step within its Authority.
- **SPG** truthfully executes admitted engineering-production steps.

The MVP should preserve the useful behavior of that collaboration while
improving continuity, reconstructability, automatic progression,
observability, reduced Human attention, model/session/environment decoupling,
and resistance to Plan drift. The reference behavior is the minimum accepted
baseline, not the design ceiling.

## Core Steering Loop

```text
Motive / Work
    ↓
Current Plan
    ↓
Assemble Plan Frame from governed Reality
    ↓
Evaluate Current Reality
    ↓
Determine Next Step
    ↓
Human-owned decision required?
    ├─ YES → HUMAN_ATTENTION
    └─ NO  → AUTO_CONTINUE
    ↓
Execute / Refine / Design / Produce / Verify / Accept as appropriate
    ↓
Observe New Reality
    ↓
Preserve / Elaborate / Revise Plan as justified
    ↓
Work outcome achieved?
    ├─ NO  → continue loop
    └─ YES → COMPLETE
```

The default product behavior is `AUTO_CONTINUE`. Human must not become a
manual Enter, Continue, Next, or Proceed button.

## Plan-Step Granularity

Autonomous progression must remain stepwise, observable, and reconstructable.
It must not collapse into one giant opaque task followed by long silent
execution and unexplained failure or completion.

A Plan Step should exist when completing it produces a recognizable Reality
change that can materially affect subsequent progression, Verification,
recovery, Human judgment, or Plan reconstruction.

Appropriate Plan-Step examples include:

- confirm an MVP product boundary;
- complete architecture design;
- establish an engineering baseline;
- implement a bounded capability;
- complete Verification;
- perform Product Acceptance.

Reading one file, searching one symbol, invoking one tool, running one command,
or inspecting one log are normally SPG or Executor activities, not Plan Steps.

Split a Plan Step only when the split provides meaningful value in stability,
failure isolation, Verification quality, Human-decision timing,
recoverability, or Plan reconstructability. Maximum fragmentation is not a
goal.

## Minimum MVP Plan Frame

The conceptual minimum Plan Frame contains:

1. Motive / Work Objective.
2. Current Plan: current phase, completed Steps, current Step, and known future
   Steps.
3. Governed Decisions.
4. Constraints and boundaries.
5. Current governed Reality.
6. Open Findings and blockers.
7. Verification and Acceptance evidence.
8. Latest material Reality change.
9. Relevant Human priority and direction decisions.

This is not a final persistence schema. Complete ECF is not required for MVP.

## Truth Ownership

> **Plan owns progression state and rationale. Plan references governed
> Reality. Plan does not become another Source of Truth for that Reality.**

Plan may own:

- Plan identity and revision;
- Step structure and progression state;
- current and Next Step;
- progression rationale;
- Plan-revision rationale;
- Reality references supporting Steering decisions.

Plan must not independently own duplicate authoritative copies of Trusted
Baseline, Repository Reality, Runtime Reality, Findings, Verification evidence,
Human decisions, or Acceptance evidence. Those facts remain owned by their
authoritative systems or records.

```text
Plan Revision R7
    based on:
        Work W1
        Decision D4
        Finding F9
        Trusted Baseline B12
        Acceptance A3
```

The Plan references those facts instead of copying them into Plan-owned truth.

## Facts-Constrain-Plan Continuity

The admitted principles remain normative:

```text
Facts constrain the Plan.

Models reason over the Plan;
models do not own the Plan.

Plan must be reconstructable from governed Reality.

Roadmap guides production;
Reality governs roadmap.
```

The MVP operational default is:

> **Preserve the admitted Plan unless governed Reality justifies change.**

New model output alone is not New Reality. Changing model, provider, AI
session, machine, or execution environment must not by itself materially alter
the Plan.

## MVP Next-Step Types

The admitted type set is:

| Type | Meaning |
| --- | --- |
| `REFINE` | Current understanding, scope, or solution is insufficiently mature. |
| `HUMAN_DECISION` | A material decision cannot safely be derived from governed Reality and belongs to Human Authority. |
| `DESIGN` | The next meaningful result is product, architecture, or solution design. |
| `PRODUCE` | The step is sufficiently mature for governed engineering production through SPG. |
| `VERIFY_ACCEPT` | Produced Reality requires engineering Verification and/or Product Acceptance. |
| `COMPLETE` | The long-lived Work outcome has been satisfied. |

`FIX_FINDING` is not a separate Next-Step type. A Finding is Reality and
rationale that may make `REFINE`, `DESIGN`, `PRODUCE`, `VERIFY_ACCEPT`, or
`HUMAN_DECISION` the appropriate Next Step.

## Minimum Next-Step Contract

```yaml
type: REFINE | HUMAN_DECISION | DESIGN | PRODUCE | VERIFY_ACCEPT | COMPLETE
objective: meaningful result sought by this step
reason: why this is the appropriate next move
reality_refs: governed facts supporting the judgment
human_required: true | false
completion_condition: recognizable Reality that closes the step
```

Example:

```yaml
type: PRODUCE
objective: Implement Runtime Activation Lite
reason: >
  Human Product Acceptance failed because Active Runtime did not match the
  Trusted Baseline.
reality_refs:
  - Finding F42
  - Trusted Baseline B17
  - Acceptance A8
human_required: false
completion_condition: >
  Active Runtime equals Trusted Baseline with consistent application and
  static evidence.
```

> **No Next Step without Reality-grounded rationale.**

A materially significant Next Step must be explainable as: because these
governed facts are true, this is the appropriate next move.

## Steering Outcomes

Next-Step Type and Steering Outcome are distinct dimensions.

The MVP Steering Outcomes are:

```text
AUTO_CONTINUE
HUMAN_ATTENTION
COMPLETE
```

For example, a `DESIGN` Next Step may produce either `AUTO_CONTINUE` or
`HUMAN_ATTENTION`, depending on Authority. Design, production, and Verification
categories do not themselves determine Authority semantics.

## Auto-Continue Default

Use `AUTO_CONTINUE` when:

- the current Step is closed;
- the next appropriate Step is supported by governed Reality;
- prerequisites are satisfied;
- no new Human-owned decision exists;
- admitted scope and constraints remain preserved;
- material risk/cost Authority has not changed.

The Human does not need to press Continue, Next, or Proceed merely to keep the
Plan moving. This is a core product requirement.

## MVP Human Attention Boundary

Human Attention is required when at least one condition holds:

### Motive or Desired Outcome Ambiguity

The system can no longer safely determine the outcome the Human intends.

### Major Product or Architecture Decision

Multiple materially valid paths exist and governed Reality plus accepted
principles cannot safely resolve the choice for the Human.

### Scope or Authority Expansion

Continuation requires expanding admitted scope, Authority, or production
boundary. AI may recommend the expansion but may not silently grant it.

### Risk or Cost Tolerance Boundary

Continuation would cross an already governed material risk/cost tolerance and
requires Human trade-off judgment.

### Human Product Acceptance or Subjective Completion Judgment

The result requires Human experiential or subjective acceptance that
engineering evidence alone cannot establish.

> **No Human Attention without a decision that matters.**

Do not create Human Attention merely because a Step completed, another Step is
available, Verification failed with an obvious bounded fix, or the system wants
permission to continue normally.

## Human Attention Quality

When Human Attention is necessary, Watt should provide:

- the decision required;
- Watt's recommendation;
- Reality-grounded reason;
- alternatives;
- material trade-offs;
- expected impact.

The Human can accept the recommendation, choose an alternative, or refine and
discuss. Watt should form a reasonable judgment first rather than returning
the thinking work to the Human unnecessarily.

## Authority-Uncertainty Safety Rule

```text
Uncertain about solution?
    AI may continue reasoning or refinement.

Uncertain about Authority?
    STOP → HUMAN_ATTENTION.
```

AI uncertainty about permission to make a material decision must never be
resolved by silently assuming Authority.

## Step Progression and Plan Revision

```text
Step progression
    = movement within the admitted Plan trajectory.

Plan revision
    = governed Reality materially changes the Plan's previous judgment.
```

Normal Step completion does not automatically create a Plan Revision. Moving
from `Step 2 CLOSED` to `Step 3 CURRENT` without material change remains within
the same Plan Revision.

## Material Plan Revision Triggers

A material Plan Revision is justified when governed Reality causes at least
one of:

1. a new blocker or Finding changes the viable path;
2. Human changes a material objective, scope, constraint, or priority;
3. Reality disproves a key Plan assumption;
4. a material dependency changes;
5. Completion, Verification, or Acceptance evidence shows the planned path is
   insufficient to achieve the Work outcome.

A Plan Revision must reference the governed Reality or Human decision that
justifies it.

> **Plan Revision requires a factual reason, not merely a model preference.**

## Non-Revision Events

The following do not normally justify material Plan Revision:

- normal Step completion;
- Verification `PASS`;
- progression to an already planned Step;
- model, session, or provider change;
- wording changes;
- local implementation preference;
- Executor-internal technique changes;
- a model preferring another materially equivalent ordering.

## Progressive Step Elaboration

`STEP_ELABORATION` allows distant work to remain coarse and become more
detailed as execution approaches.

```text
Step 4: Implement Inventory Management MVP

becomes:

4.1 Inventory entry
4.2 Stock adjustment
4.3 Low-stock detection
```

If elaboration does not materially change objective, admitted scope, major
dependency, direction, or a Human-owned decision, it is not a material Plan
Revision.

> **Far work may remain coarse. Near work becomes detailed.**

Large Motives must not be forced into an exhaustive upfront task list.

## Plan History Events

MVP conceptual semantics distinguish at least:

- `STEP_TRANSITION`: normal progression;
- `STEP_ELABORATION`: refinement of a coarse current or future Step without a
  material direction change;
- `PLAN_REVISION`: a material Plan change justified by governed Reality.

This supports reconstruction and anti-drift. It does not prescribe an event
store or persistence schema.

## Plan-Level Observability

Automatic progression must remain observable. A user should eventually be able
to understand:

- Motive / Work objective;
- current Plan phase;
- completed Steps;
- current Step;
- known Next Steps;
- current activity category;
- why the current Step is active;
- where progression stopped;
- whether Human Attention is required;
- what Reality each material Step produced.

Plan-level observability and production activity detail remain distinct:

```text
Plan level:
    Where is the Motive going and where are we now?

SPG level:
    What is happening inside the current production Step?
```

This contract does not redesign UX or UI.

## Plan Reconstructability Acceptance Target

A new AI instance with no prior conversational continuity, potentially a
different model or provider, and access only to the persisted Plan plus
referenced governed Reality must be able to reconstruct materially:

- what the Human wants;
- where the Work stands;
- what has already been established;
- the current Step and why it is current;
- relevant decisions, constraints, and Findings;
- the next appropriate move.

It should reach a materially equivalent development direction unless governed
Reality has changed. This is a product requirement, not merely disaster
recovery.

## SPG Invocation Boundary

```text
Plan Steering
    determines what should happen next.

SPG
    truthfully executes an admitted engineering-production Step.
```

For `Next Step Type = PRODUCE`, Plan Steering may form or initiate appropriate
governed production input, but it must not bypass Work or production Authority,
the Production Contract, PWU boundary, Observation, Verification, Candidate and
Human Authority where required, or Runtime Commit and Trusted Baseline
semantics.

SPG results return as New Reality. Plan Steering then reassesses. Plan Steering
must not duplicate SPG.

## Future Human Attention Extension: Milestone / Alignment Acceptance

**FUTURE ITERATION — NOT AN MVP BLOCKER**

Future Plan Steering may support deliberate Human checkpoints at meaningful
stage milestones before final Work completion, such as a large functional
module, major product phase, major architecture milestone, or an Alignment
Artifact ready for experiential calibration.

```text
Milestone Reality
    ↓
Human Alignment / Acceptance Checkpoint
    ↓
PASS       → continue
correction → Refinement / Plan reassessment
```

This may later integrate with
[Interpretation Externalization and Multimodal Alignment](interpretation-externalization-and-multimodal-alignment.md).
It is not added to the current MVP mandatory Attention set beyond already
required Product Acceptance.

## Future Human Attention Extension: Resource / Capability Boundary Crossing

**FUTURE ITERATION — NOT AN MVP BLOCKER**

Future Plan Steering may require Human awareness or approval when progression
activates a materially new class of resource or capability, for example:

- moving from design into Executor-backed code production;
- provisioning or activating database resources;
- activating paid model or API usage;
- activating cloud or GPU resources;
- enabling external services;
- entering a capability that materially changes cost or resource footprint.

This is related to, but distinct from, a generic risk/cost threshold. The
question is not only whether an action is expensive, but whether Watt is about
to activate a new resource or capability class that changes the user's
resource/cost footprint. No policy, threshold, UX, or final Authority semantics
are designed here.

## Future Human Attention Extension Registry

Current MVP Attention remains intentionally narrow. Future candidate
extensions currently include:

1. Milestone / Alignment Acceptance.
2. Resource / Capability Boundary Crossing.

Additional categories may be admitted from real Dogfood evidence. This list is
not frozen.

## Explicit MVP Non-goals

This contract does not require current MVP implementation of:

- multi-model voting or consensus;
- advanced autonomous replanning;
- DAG or parallel Plan execution;
- multi-Motive resource scheduling;
- cross-project optimization;
- complex risk scoring;
- Plan optimality scoring;
- Monte Carlo roadmap simulation;
- complete ECF;
- Guardian Plan assurance;
- unattended long-horizon production;
- automatic major product decisions;
- Interpretation Externalization;
- a milestone-acceptance framework;
- a resource-activation policy framework;
- browser E2E;
- Linux deployment.

These may evolve later based on Reality.

## MVP Design Philosophy

The current Human Governor and Architecture Lead AI collaboration is a proven
reference behavior. MVP should productize that useful behavior instead of
inventing an unnecessarily elaborate theoretical planning framework.

The reference is the minimum acceptable baseline, not the design ceiling.
Improvements are appropriate when they materially improve continuity, quality,
stability, observability, reconstructability, reduced Human burden, or
anti-drift behavior without adding layers that merely relay information.

> **If a new layer adds no new Truth, Authority, Evidence, Decision semantics,
> or material user value, it should not exist.**

## Current Capability Status

MVP-PLAN-STEER-1C persists a provider-neutral Steering Plan, immutable admitted
revisions, stable ordered Steps, admitted Steering Decisions, typed external
Reality references, and append-only transition/elaboration/revision history.
The single authoritative current-Step representation is Step state, protected
by a database invariant allowing at most one `CURRENT` Step per revision.

For 1C, the decision basis fingerprint is canonical SHA-256 over the persisted
Work identity, admission mode, and update time, requirement/outcome/objective/constraints, the
active Steering revision identity and number, the exact current Step identity
and governed fields, and sorted typed Reality references. Decision prose and
reasoning-provider identity are deliberately excluded: they are decision output
and diagnostic metadata, not the governed basis.

MVP-PLAN-STEER-1D assembles an ephemeral Plan Frame from persisted Work,
Engineering Scope, active Steering truth, governance decisions, current Trusted
Baseline, and relevant Runtime/Completion/Verification Reality. A replaceable
provider-neutral capability returns an advisory `NextStepCandidate`; the
application recomputes the current basis and admits it only when lineage,
Reality references, authority, scope, and completion evidence remain valid.
The existing Steering Decision remains the persisted decision Source of Truth.
Five typed MVP Steering Attention reasons and their bounded decision context are
projected without overloading Candidate Authorization. No decision is executed
automatically in this Slice.

MVP-PLAN-STEER-1E connects an admitted current `PRODUCE` Step to one existing
governed SPG production cycle. A long-lived Work may own multiple cycle
bindings, but each binding remains an independent Run with one runtime Plan
Revision and one PWU. Each later cycle binds the Current Trusted Baseline at
its own admission; this is not successor-PWU rebasing. The bridge validates the
materialized request against the persisted Work objective, exact Engineering
Scope and Resource, constraints, target/change boundary, forbidden areas, and
Verification boundary before creating a Run. A mismatch records typed
`SCOPE_OR_AUTHORITY_EXPANSION` Human Attention and creates no Runtime lineage.

For Steering-enabled Work, a Runtime Commit proves only that the associated
production cycle is trusted. Closing a `PRODUCE` Step additionally requires
referenced Completion `PRODUCED`, Verification `PASS`, exact Candidate and
Authorization, converged Integration, Runtime Commit, and the advanced Trusted
Baseline. Work-level `COMPLETED` is projected only from an admitted `COMPLETE`
Steering Decision with matching trusted evidence. Legacy Works without a
Steering Plan retain Runtime Commit → Work `COMPLETED` compatibility.

MVP-PLAN-STEER-1F adds a bounded process-local driver over those persisted
facts. Each iteration reloads Work, active Plan revision, current Step,
decisions, Runtime evidence, and Trusted Baseline; it performs no more than one
semantic Steering action and then compares authoritative fingerprints. PRODUCE
delegates to ORCH and stops while a production cycle is active. ORCH terminal
outcomes re-enable Steering assessment. Typed Human, completion, production,
blocked, no-progress, transition-bound, and shutdown stops prevent hidden
spinning. Startup eligibility is reconstructed from persistence, and a
read-only Plan projection exposes current/next Steps, rationale, automatic
state, associated production cycle, Attention, and last stop without copying
SPG Attempt/Dispatch detail into Plan truth.

MVP-PLAN-STEER-1G separates long-lived Work admission from exact production
admission. The explicit Work mode preserves legacy immediate-production Works
while allowing a Human to admit a long-lived objective, constraints, exact
Engineering Resource, and bounded Scope without an Artifact/Change Contract or
Runtime lineage. That admission creates an initial provider-neutral Steering
Plan whose first Step may be `REFINE`, `DESIGN`, `HUMAN_DECISION`, or—when an
exact production boundary is already admitted—`PRODUCE`. PLAN-1B and Run/PWU
creation remain mandatory at the exact `PRODUCE` boundary. Authority expansion
still records `SCOPE_OR_AUTHORITY_EXPANSION` and stops before Runtime creation.

MVP-PLAN-STEER-1H converges the dedicated Work approval endpoint and Work Draft
Attention resolution on one post-admission application service. The service
reads the admitted Work mode from persisted Reality, sends immediate-production
Work to the existing Production Orchestrator, and idempotently bootstraps then
schedules the Plan Steering Driver for long-lived Work. Startup repairs only
the truthful incomplete state `READY + LONG_LIVED_STEERING + no SteeringPlan`
before applying the existing driver restart-eligibility rules. Bootstrap or
driver-scheduling failure never falls through to production, and UI reads do
not drive progression. MVP-PLAN-STEER-1H is **CLOSED / PASS** after focused
validation and Architecture Lead Reality Review; real long-lived Dogfood
continues.

MVP-PLAN-STEER-1I makes `DESIGN` and `REFINE` executable governed semantic
Steps rather than control-flow labels. A provider-neutral capability receives
a reconstructable input bound to the active Plan revision, exact current Step,
Plan Frame basis, admitted Work/Scope/Resource, Trusted Baseline, governance
references, and bounded repository context. Its typed output remains advisory
until application validation admits an immutable Semantic Step Result. A
semantic Step cannot close without a completion-satisfied result referenced by
the exact Steering Decision. `DESIGN` may produce a bounded Production Plan
proposal, but it does not mutate the repository, authorize production, or
create Run/PWU; actual production still crosses the existing authority,
PLAN-1B `ONE_PWU_FIT`, and SPG admission boundary. Authority uncertainty or
expansion stops at governed Human Attention. 1I is **CLOSED / PASS** after
focused validation and Architecture Lead Reality Review; real Provider
Dogfood continues.

MVP-PLAN-STEER-1J constrains real semantic Provider generation with the JSON
schema derived from the same typed payload model used by strict application
parsing. The schema exposes only current Watt target vocabulary and typed
artifact shapes, while bounded allowed areas retain repository-relative `/**`
syntax. JSON/Pydantic parsing, fresh-basis reconstruction, evidence, scope,
authority, completion, and result-admission checks remain fail closed. A
Provider schema match remains advisory rather than Authority. When the bounded
Driver stops on a governed invariant, the Work API now reuses its existing
`STOPPED / BLOCKED` projection instead of implying semantic execution is still
active. The structured-output gap is resolved in implementation and focused
validation; the broader execution-observability gap is only partially mitigated
and remains open. 1J is **CLOSED / PASS** after Architecture Lead Reality
Review; real Provider Dogfood continues.

Long-lived Motive Dogfood #5 proved that Provider schema supply alone was
insufficient: strict response-format admission requires every property at every
object level to appear in `required`. The generated schema omitted default
collections and nullable fields, so the Provider rejected it before content
generation. MVP-PLAN-STEER-1K separates the strict typed Provider wire shape
from unchanged domain defaults. Wire collections are required and may be empty;
wire optional values are required keys and may be null. Conversion into the
existing domain proposal is deterministic and retains enum, typed-target,
repository-path, authority, completion, and production-admission validation.
1K is **CLOSED / PASS** after focused validation and Architecture Lead Reality
Review; real Provider Dogfood continues.

Long-lived Motive Dogfood #6 proved the recursive required-key correction with
the real Provider, then failed at the next strict response-format rule because
the generated `target_kind` schema combined `$ref` with a `description`
sibling. MVP-PLAN-STEER-1L keeps the typed Pydantic wire model authoritative and
applies one recursive structural adaptation to the schema supplied to the SDK:
every `$ref` node is emitted as pure `$ref`. Domain descriptions, enums, target
types, path constraints, null/empty semantics, wire-to-domain conversion, and
all application Authority checks remain unchanged. 1L is **IMPLEMENTED —
FOCUSED VALIDATION PASS — PENDING ARCHITECTURE LEAD REALITY REVIEW**; the parent
structured-output gap requires fresh real Provider evidence before closure.

The bounded integration closure supplied that evidence using two independent
disposable states and real Provider Turns. The Provider accepted the normalized
strict schema and returned valid structured DESIGN content; wire validation,
domain conversion, candidate creation, application admission, governed result
persistence, and reconstruction all passed. No Run, PWU, Runtime Commit, or
repository mutation existed before `PRODUCE`. This resolves
`SEMANTIC_PROVIDER_SCHEMA_REF_SIBLING_GAP` and the parent
`SEMANTIC_STRUCTURED_OUTPUT_GAP` by real Provider evidence. MVP-PLAN-STEER-1L is
**CLOSED / PASS** after Architecture Lead Reality Review. Human Dogfood is no
longer the iterative compatibility oracle:
fresh real Provider validation is part of bounded Executor self-refine for this
integration boundary.

The closure preserves `SPG_EXECUTION_GRANULARITY_CALIBRATION_REQUIRED` for
later architecture calibration, with the working hypothesis: govern the
execution envelope, not every Executor move. No SPG redesign or granularity
change is admitted by 1L. `SEMANTIC_EXECUTION_OBSERVABILITY_GAP` remains
**CONFIRMED / PARTIALLY MITIGATED / NON-BLOCKING**. Subsequent Dogfood #9 and
#10 evidence closes the MVP Core while preserving this post-Core Product
Experience deferral. See [Watt MVP Core Closure](../evidence/mvp-core-closure.md).

```text
Reality-driven Plan Steering
    MVP BEHAVIORAL CONTRACT = DEFINED / ADMITTED
    MVP CLOSED / PASS
    REAL LONG-LIVED DOGFOOD / HUMAN ACCEPTANCE PASS
    MATERIAL MVP CORE PRODUCT CAPABILITY

MVP-PLAN-STEER-1C
    STEERING TRUTH SPINE = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1D
    PLAN FRAME / STEERING DECISION / HUMAN ATTENTION LITE
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1E
    PRODUCE STEP → SPG BRIDGE / LONG-LIVED WORK COMPLETION SEPARATION
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1F
    BOUNDED AUTO-CONTINUE / RESTART / PLAN OBSERVABILITY
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1G
    LONG-LIVED WORK ADMISSION / STEERING BOOTSTRAP
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1H
    POST-ADMISSION STEERING ACTIVATION
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1I
    GOVERNED SEMANTIC DESIGN / REFINE EXECUTION LITE
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1J
    SCHEMA-CONSTRAINED SEMANTIC PROVIDER OUTPUT
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1K
    STRICT SEMANTIC PROVIDER WIRE SCHEMA COMPATIBILITY
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-STEER-1L
    STRICT PROVIDER PURE-$ref SCHEMA COMPATIBILITY
        = CLOSED / PASS
    ARCHITECTURE LEAD REALITY REVIEW = PASS

MVP-PLAN-1B
    CLOSED / PASS
    Single-PWU Production Planner Lite
```

PLAN-1B remains valid and closed. It does not satisfy long-lived Reality-driven
Plan Steering and is not reopened by this contract.
