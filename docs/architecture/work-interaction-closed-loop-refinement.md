# Work Interaction & Closed-loop Refinement — Architecture Contract

## 1. Status and scope

```text
WIC-1 Architecture Contract
    DEFINED / ADMITTED

Work Interaction & Closed-loop Refinement Core
    IN PROGRESS

WIC Slice 1 — Interaction Truth Spine & Pre-Work Understanding
    IMPLEMENTED / PASS
```

This contract specializes the approved
[工律 / Watt Product North Star](watt-product-north-star.md). It defines one
cohesive capability pillar spanning pre-Work formation and interaction during a
long-lived Work. The architecture checkpoint itself created no Runtime behavior;
the admitted Slice 1 now implements the additive pre-Work truth spine,
interpretation/readiness capability, API, and minimum UI without Work admission.

The closed Governed Production and Reality-driven Plan Steering Core remains
authoritative. WIC does not reopen or weaken Work/Production admission
separation, PWU boundaries, Executor autonomy, independent Verification,
Candidate Authorization, Runtime Commit, or Trusted Baseline semantics.

## 2. Objective and non-objective

WIC owns this semantic chain:

```text
Human Input
    -> Interpretation
    -> Impact Assessment
    -> governed admission where appropriate
    -> versioned Work Reality
    -> Plan reassessment
    -> production / feedback
    -> continuing Interaction
```

It must support both:

- interaction before a Work exists; and
- continuing interaction around an admitted active or currently satisfied Work.

WIC is not a general chat platform, second planning engine, execution
orchestrator, Evidence store, ECF replacement, or model-owned memory. It does
not require a Project/Initiative hierarchy, Multi-PWU/DAG, full Guardian/ECF,
multimodal externalization, YiJue, or advanced branching.

## 3. Product mental model

### Interaction

An **Interaction** is one continuing Human–Watt communication relationship. It
has identity independent of Work, so it may begin with no `work_id`. It owns
ordered Interaction provenance and an explicit current focus, not engineering
or production truth.

An Interaction may produce no Work, one Work, or sequentially related Works.
Every Work association is explicit and historical; selecting or proposing a
new Work must not silently rebind earlier messages. The MVP may keep one current
Work focus per Interaction while preserving prior associations.

### Motive

Motive is the Human's evolving desired change in the world. Interaction helps
Watt reconstruct it; governed Work Reality records what has actually been
admitted.

### Work and Work Reality

Work is the governed realization relationship around a Motive. **Work Reality**
is the current versioned authoritative representation of its admitted outcome,
context, constraints, significant requests, scope, decisions, and provenance.
It references facts owned by other domains rather than copying them.

### Plan, production cycle, and feedback

Plan Steering owns progression and answers `WHAT NEXT` from governed Reality.
SPG owns truthful execution of an exact admitted production step. A production
cycle is bounded by its exact contract and cannot be rewritten by later input.
Feedback is input from Human, user testing, Verification, Runtime, engineering
findings, or production outcomes whose relevance to Work must be interpreted.

## 4. Semantic layers and minimum contracts

These are semantic contracts, not final database tables or aggregate roots.

### 4.1 Interaction Record

An append-only record of what was communicated, minimally attributable to an
Interaction, actor/source, order/time, content identity, optional current Work
focus, and applicable retention classification.

It may be raw provenance. It is not a fact, decision, Work revision, Plan input,
Production Contract, or execution Authority merely because it exists.

### 4.2 Interpretation Candidate

A provider-neutral, advisory interpretation of one or more new inputs against
an exact basis. The bounded MVP meaning kinds are:

```text
CONTEXT
FACT
CORRECTION
CONSTRAINT
REQUEST
PREFERENCE
QUESTION
DECISION_INPUT
FEEDBACK
OBJECTIVE_OR_SCOPE_CHANGE
NEW_WORK_CANDIDATE
```

One candidate may contain multiple meaning items. Each item preserves source
Interaction Record references, confidence/uncertainty where useful, rationale,
and whether Human clarification is required. The kinds are an extensible
minimum vocabulary, not a universal ontology.

### 4.3 Work Admission Readiness Assessment

Readiness answers whether the current shared understanding contains enough
governed clarity to create a legitimate Work relationship. It is evaluated
against a versioned **Work Admission Profile** selected for the relevant Work
shape, not one global schema.

Every profile can require or conditionally require:

- sufficiently clear Motive and desired outcome;
- relevant context and material constraints;
- Engineering Resource and bounded scope when required;
- applicable Human Authority;
- resolution of questions that prevent lawful admission.

The result identifies profile/version, satisfied requirements, unresolved
blocking and non-blocking questions, basis references/fingerprint, rationale,
and `READY` or `NOT_READY`. Readiness means enough clarity to govern the Work,
not every future production detail. It cannot require an exact Production
Contract before a long-lived Work is admitted.

### 4.4 Shared Understanding Projection

A rebuildable Human-facing projection over Interaction candidates and governed
Reality. It preserves three visibly distinct layers:

```text
WHAT THE HUMAN SAID
WHAT WATT INTERPRETED
WHAT WAS GOVERNED / ADMITTED
```

At minimum it shows:

- interpreted Motive and desired outcome;
- admitted key context/facts, constraints, and requests;
- unresolved material questions;
- latest candidate change and expected impact;
- candidate/admitted/rejected/superseded distinction;
- Work Admission Readiness or current Work/Plan impact.

The projection does not own truth and must be reconstructable. Compactness is a
product requirement; an ever-growing requirements document is not.

### 4.5 Impact Assessment

Impact Assessment answers: **What does this input mean for the current governed
Work and any active production cycle?** It binds the exact Interpretation
Candidate and basis, including applicable Motive, current Work Reality revision,
constraints, Plan revision/Step, production cycle/contract, decisions,
Verification/Runtime facts, and Authority envelope.

The bounded MVP must represent these dispositions, alone or in a validated
combination:

```text
NO_GOVERNED_CHANGE
UPDATE_CANDIDATE_UNDERSTANDING
WORK_REVISION_PROPOSED
PLAN_REASSESSMENT_REQUIRED
CURRENT_CYCLE_REMAINS_VALID
DEFER_TO_PRODUCTION_BOUNDARY
CURRENT_RESULT_MAY_BE_INSUFFICIENT
HUMAN_GOVERNANCE_REQUIRED
NEW_WORK_RECOMMENDED
```

The assessment states rationale, affected governed subjects, current-cycle
effect, proposed next governance action, and required Authority. It is advisory
until Watt admission validates freshness, scope, authority, and consistency.
The interpreter cannot mutate Work truth or Plan state.

### 4.6 Governed Work Reality Revision

An admitted Work change creates an immutable, reconstructable **Work Reality
Revision**. It minimally identifies:

- Work and revision identity/order;
- previous revision and exact basis fingerprint;
- admitted semantic change set;
- supporting Interaction/candidate/feedback references;
- retained and changed objective, context, constraints, requests, and scope;
- rationale and applicable Human/policy Authority;
- supersession/current-revision relationship;
- creation/admission time.

The current Work view is a projection of the admitted revision chain. Existing
facts and revisions remain historical. `overwrite Work JSON from latest chat`
is prohibited. Facts, Verification, Runtime evidence, and Baselines remain
owned by their source domains and are referenced by identity.

### 4.7 Work Transition Proposal

When input should not mutate the focused Work, WIC may propose continuation of
the current Work, governed reopening/refinement, or transition to a new Work.
The proposal records rationale and source/current Work relationships. It is not
Work admission or production Authority.

## 5. Admission and Authority

Before Work admission, Watt Native Interpretation may accumulate candidate
understanding and ask focused clarification questions. No first utterance or
Interaction Record automatically creates a governed Work. Once the applicable
admission profile is `READY`, the Shared Understanding exposes the proposed
Motive, outcome, important context, constraints, scope, and open non-blockers.
The existing applicable Human admission boundary remains mandatory.

For an admitted Work, low-risk contextual changes may be admitted only under an
explicit bounded policy that does not change Motive, outcome, scope,
constraints, risk, or Authority. Material correction, constraint, goal/scope,
risk, or acceptance changes require the applicable Human governance record.
WIC cannot infer expanded Authority from the Work relationship.

New Work creation after a notice/default transition is permitted only when its
admission readiness is satisfied. It creates no Production Contract, Candidate
Authorization, or inherited Authority. Exact countdown timing and UI are
Product Experience choices.

## 6. Core journeys

### A. Pre-Work interaction

```text
Interaction created without Work
    -> multiple Interaction Records
    -> candidate interpretation evolves
    -> clarification as needed
    -> Shared Understanding distinguishes candidate/admitted
    -> profile-specific readiness reaches READY
    -> Human admits Work
    -> first Work Reality Revision + explicit Interaction association
    -> existing long-lived Steering bootstrap
```

The Interaction continues; admission is a governed phase change, not the end of
conversation or an awkward handoff to a disconnected ticket.

### B. Active Work interaction

New input is interpreted against reconstructed Work/Plan/production Reality.
A question may receive an answer with `NO_GOVERNED_CHANGE`. Context or feedback
may propose a revision. Material changes require governance. Once admitted, a
new Work Reality Revision makes Plan reassessment eligible.

### C. Input while production is active

An admitted PWU/Attempt remains bound to its exact objective, Source Baseline,
scope, constraints, and Completion Contract. WIC never injects incremental chat
into the Executor or mutates that contract.

- If the new input has no material effect, the cycle continues unchanged.
- If it affects only future progression, admit the Work revision and reassess
  at the production boundary.
- If it may make the current result insufficient, preserve the cycle's exact
  historical truth and require fresh satisfaction/Steering assessment before
  Candidate integration or Work completion.
- If safety, Authority, or material direction is affected, request Human
  governance and stop at the nearest lawful existing boundary; WIC does not
  fabricate cancellation/recovery authority.

Ordinary Executor technical self-refine remains internal to the stable Attempt
envelope and does not become a Human interaction event.

### D. Feedback after production

```text
authoritative Human/user/Verification/Runtime/engineering feedback reference
    -> WIC interpretation and impact assessment
    -> governed Work Reality Revision where appropriate
    -> Plan Frame observes changed Reality
    -> Plan Steering preserves/elaborates/revises Plan
    -> another exact production cycle only when PRODUCE is lawfully admitted
```

WIC references source evidence; it does not copy and claim ownership of it.

### E. Completed Work followed by new demand

Work outcome and relationship openness are separate product dimensions:

```text
Outcome:       IN_PROGRESS | CURRENTLY_SATISFIED
Relationship:  OPEN | ARCHIVED
```

These are Product semantics, not required database enums. Existing Steering
`COMPLETE` and Work `COMPLETED` remain truthful evidence that the admitted
outcome was satisfied. In the WIC product model, completion normally yields
`CURRENTLY_SATISFIED + OPEN`, so interaction remains possible.

Input may continue the same Work when it materially serves the same Motive,
preserves historical truth, and passes Work-revision Authority. A materially
new primary outcome, independent resource/scope, or demand whose admission
would obscure the completed boundary produces `NEW_WORK_RECOMMENDED`. The MVP
may offer a notice and default transition; no production or Authority is
inherited silently. Explicit archival closes the relationship without deleting
its reconstructable history.

## 7. Plan Steering and SPG integration

WIC owns interpretation, impact assessment, Work-change admission, and the
resulting Work Reality revision. It does not choose or execute the next Plan
Step.

```text
admitted Work Reality Revision
    -> existing Plan Frame references changed Work Reality
    -> existing Plan Steering evaluates Current Reality
    -> preserve / elaborate / revise / HUMAN_DECISION / PRODUCE / COMPLETE
```

Plan Steering remains owner of `WHAT NEXT`. SPG remains owner of exact
production admission and truthful execution. WIC cannot create a Run/PWU,
authorize a Candidate, commit a Baseline, or close a Steering Step.

An implementation must make Work-revision identity/fingerprint part of the
relevant Plan Frame basis so stale interpretations or decisions fail closed.
It must preserve existing production-cycle lineage and decide the effect of a
new revision before trusting a result against the latest Work Reality.

## 8. Responsibility boundaries

| Capability | Owns | Must not own |
| --- | --- | --- |
| WIC | Interaction provenance, candidate interpretation, impact assessment, Work-change admission coordination, Work Reality revision semantics, Shared Understanding projection | Plan progression, production execution, source-domain evidence truth |
| Work Truth | Current admitted Motive/outcome/context/constraints/requests/scope and revision lineage | Raw conversation as truth, production facts |
| Plan Steering | Plan/Revision/Step progression, rationale, next action from governed Reality | Work-input interpretation, SPG execution |
| SPG | Exact production admission, PWU/Attempt lifecycle, observation/Verification coordination, Candidate/Integration/Commit transitions | Conversation or Work interpretation |
| Executor | Work inside one admitted Attempt envelope and provider evidence | Work/Plan truth, Verification or Authority |
| Verification / Runtime | Their own evidence, findings, observed and operational Reality | Work-change admission |
| Future interpretation/deliberation provider | Advisory candidate interpretation/reasoning through a typed capability | Work mutation, Authority, Plan or production truth |

## 9. Provider neutrality and privacy

MVP uses **Watt Native Interaction / Interpretation Capability only**. The
capability contract consumes selected Interaction Records plus exact governed
basis and returns a typed candidate. Provider/model identity is metadata. Watt
validates and admits every result; session memory and hidden reasoning are not
truth.

Future optional deliberation, including an independently admitted 易决
capability, may implement the same advisory seam. WIC, Work, and Plan data must
not depend on YiJue, a provider protocol, or one model session. No YiJue MVP
dependency or detailed integration is defined here.

Raw Interaction Records and governed truth have distinct retention and
Authority semantics. The architecture must permit future retention, redaction,
sensitive-material, and context-assembly policies. Raw chat need not be
permanent and must not enter an Executor Context Package merely because it was
retained.

## 10. Restart and reconstruction

After process, provider, or session restart Watt must reconstruct from persisted
governed records:

- current Work Reality revision and revision history;
- current Plan and admitted decisions;
- Interaction ordering/associations and required provenance;
- unresolved candidates/questions and admission/impact outcomes;
- Shared Understanding or sufficient inputs to rebuild it;
- active production binding and any deferred reassessment.

A transcript alone is insufficient. Equivalent governed Reality must produce a
materially equivalent Shared Understanding and impact boundary across model or
provider changes.

## 11. Bounded WIC MVP implementation envelope

The bounded MVP remains one cohesive Watt module and may be delivered in four
implementation slices without creating separate first-order subsystems:

1. **Truth spine:** provider-neutral contracts and persistence for Interaction
   provenance, candidates/assessments, immutable Work Reality revisions, and
   restart reconstruction.
2. **Pre-Work formation:** multi-turn text interaction, native interpretation,
   profile-specific readiness, compact Shared Understanding, Human Work
   admission, and existing Steering bootstrap.
3. **Active Work evolution:** new input, bounded impact assessment, candidate
   change review/admission, Work revision, Plan Frame basis integration, and
   active-production guards.
4. **Feedback and completion transition:** source-fact references through the
   same path, another cycle through existing Steering/SPG, and lightweight
   completed-Work/new-Work transition.

MVP assumptions may include one local Human identity, text interaction, one
current Work focus per Interaction, Watt Native interpretation, simple
profile-specific readiness rules, compact projections, and existing serial
Steering/SPG execution.

Explicit non-goals are YiJue integration, full ECF/Guardian, multimodal
externalization, Multi-PWU/DAG, general conversation search, multi-user
collaboration, advanced branching/merge, autonomous semantic branching,
complex user-behavior management, and UI redesign beyond the minimum later
admitted interaction surface.

## 12. Required MVP evidence

A future implementation plan must map focused evidence at least to:

1. first utterance creates Interaction truth but no Work;
2. multi-turn clarification reconstructs after restart;
3. candidate and admitted understanding are visibly distinguishable;
4. readiness is profile-specific and blocks on material ambiguity only;
5. Human admission creates the initial Work revision and existing Steering;
6. a question against an active Work creates no governed change;
7. a constraint/correction cannot change Work without valid admission;
8. an admitted Work revision changes the Plan Frame basis and triggers
   reassessment, not a second planner;
9. input during an Attempt cannot mutate or incrementally prompt its contract;
10. a materially stale/insufficient result cannot close the latest Work Reality;
11. feedback references source evidence and may produce another lawful cycle;
12. Steering `COMPLETE` preserves an open Human relationship;
13. materially new demand recommends a new Work without inheriting Authority;
14. raw conversation never enters production Authority or Executor input;
15. provider output remains advisory and stale-basis admission fails closed;
16. legacy immediate-production and existing long-lived production paths remain
    compatible.

Real Provider/Dogfood proof is required only when separately admitted by the
future implementation plan.

## 13. Architecture closure

No Architecture STOP condition was found:

- existing Work identity can gain versioned governed Reality without redefining
  Work or adding Project/Initiative;
- existing Plan Steering already consumes reconstructable Work/Reality basis;
- exact production contracts and Attempt lineage can remain immutable;
- completion can preserve historical satisfaction while relationship openness
  remains a separate Product semantic;
- provider-neutral candidates fit existing advisory/admission patterns.

```text
WIC MVP ARCHITECTURE
    READY FOR IMPLEMENTATION PLANNING
```

This status authorizes planning only. It does not authorize implementation.
