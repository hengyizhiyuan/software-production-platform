# Guided Design Core

Status: **IMPLEMENTED / FOCUSED VALIDATION PASS**
Human Product Acceptance: **PENDING**

## Purpose

Guided Design Core gives a long-lived Work a reconstructable product/system
design process between governed Work formation and production admission. It
solves the gap where Watt could interpret a Motive and steer typed Steps, but
could not explain which design questions normally matter, what had been
resolved, what remained open, or why one design issue was current.

The intended journey is:

```text
Motive and continuing Human Interaction
  -> governed Work Reality
  -> Guided Design process and agenda
  -> Plan Steering selects one current design issue
  -> DESIGN / REFINE produces an advisory candidate
  -> application validation admits a governed SemanticStepResult
  -> agenda and PlanFrame are reconstructed from current Reality
  -> design readiness and a reviewable production proposal
  -> Human proposal review
  -> PLAN-1B / SPG production admission
```

A vague Motive does not directly create a Production Contract, PWU, Executor
Attempt, or repository mutation.

## Ownership boundaries

| Capability | Ownership |
| --- | --- |
| WIC | Human Interaction, interpretation, Shared Understanding, focus and Work evolution |
| Guided Design Core | Design-process schema, agenda issue semantics, issue status, agenda rationale and design readiness |
| Plan Steering | `WHAT NEXT`, the active Plan revision and the one current focus |
| DESIGN / REFINE | Semantic work for the current admitted issue |
| Work Reality | The current Human-governed Motive, outcome, context, constraints and scope envelope |
| Human Authority | Material product direction, scope/risk trade-offs, Authority expansion and production-proposal review |
| SPG | Exact production admission and the bounded PWU/Attempt envelope |
| Executor | `HOW` inside the admitted production envelope |
| Completion / Verification | Independent production and obligation Evidence |
| Runtime | Repository integration, Runtime Commit and Trusted Baseline truth |

Guided Design is not a second Planner, Work lifecycle, production system, or
conversation store. A design agenda is process structure, not Authority.

## Semantic model

The persisted `GuidedDesignProcessRecord` selects a provider-neutral schema by
identity and version, records its Work and Work Reality basis, objective and
condition. `DesignAgendaRevisionRecord` is append-only process history: one
active revision per process, an exact predecessor, rationale, Reality
references and an ordered issue set.

Each `DesignIssue` records:

- stable key, title, objective and why it matters;
- applicability and dependency hints;
- completion condition and criticality;
- Human-Authority relevance and required output class;
- `OPEN`, `SATISFIED`, `SKIPPED`, or `REOPENED` state;
- mandatory skip/reopen rationale;
- the exact Steering Step and admitted semantic result when applicable;
- provenance references.

The MVP ships a versioned seed registry containing General Product/System
Design v0.1, Technical System Design v0.1, and Existing Product Evolution v0.1.
The selected schema identity, version, and rationale are persisted. These are
extensible methodology assets, not a fixed questionnaire, schema marketplace,
or workflow editor. Active stage/focus guidance and facilitation semantics are
defined in the [Guided Design Facilitation Layer](guided-design-facilitation-layer.md).

## Current focus and progression

The agenda provides candidate issue structure. Plan Steering creates the typed
`DESIGN` Steps and owns which one is `CURRENT`; `design_issue_key` is the exact
bridge. The product projection derives current focus by joining the active
agenda revision to the current Steering Step. Guided Design never advances its
own parallel state machine.

The semantic input includes the admitted Work outcome, constraints, Work
Reality context facts and requests, exact Baseline/Resource/Scope, governed
Reality references, bounded repository context, the current design issue, and
summaries of earlier admitted design results. Each Provider Turn is ephemeral:
later issues depend on persisted Reality rather than thread memory.

An intermediate design issue cannot form a production proposal. Only the final
implementation-readiness issue may do so, and it cannot claim completion
without a typed reviewable proposal. Provider output remains advisory until
strict domain and application admission succeeds.

## Governed design results

`SemanticStepResultCandidate` is Provider advice. Existing strict validation
checks exact Work/Plan/Step/basis, Baseline tree, evidence references,
constraints, scope and Authority. Only an admitted `SemanticStepResultRecord`
may satisfy an agenda issue. Its identity, summary, decisions, constraints,
evidence and provider metadata remain reconstructable and become input to later
issues and PlanFrame.

Agenda revision N+1 marks the exact issue satisfied and cites that result. Old
revisions remain `SUPERSEDED`; they are not rewritten. A result may be reused
after the agenda revision it caused, but changes in non-agenda governed Reality
invalidate that reuse and require a fresh semantic result.

## Agenda reassessment and feedback

After each admitted semantic result, the driver reloads Work, Plan, Baseline,
governance, semantic results and the active design agenda. The application seam
supports explainable issue skip and reopen, plus complete agenda revision. A
revision may reorder, omit satisfied issues from future Steps, add a compatible
issue, or reopen an earlier issue, but it must preserve rationale and valid
Reality references.

WIC remains the route for Human input and Human-governed Work evolution.
Verification, Completion, Runtime, engineering or Human governance evidence can
be supplied as the basis for `reopen_issue`; Steering validates that every
referenced fact exists before accepting the revised Plan. This supports the
feedback loop without changing historical production facts or mutating an
active Production Contract. Advanced autonomous replanning or retry remains out
of scope.

## Readiness

`DesignReadiness` is explicitly `READY` or `NOT_READY`. `NOT_READY` lists each
unresolved critical issue and its completion condition. `READY` means all
currently applicable critical questions have governed satisfaction evidence or
an explicit governed skip rationale. It does not mean that production is
authorized, that every possible topic has been discussed, or that the Work is
complete.

Readiness is recomputed from the active agenda and provenance on every
projection. A reopened critical issue makes it `NOT_READY` again.

## Review before production Authority

When the final design issue produces a valid exact proposal, Guided Design is
`READY` but the driver records
`PRODUCTION_PROPOSAL_REVIEW_REQUIRED` and stops before Run/PWU creation. The
existing Attention surface presents `APPROVE` and `REQUEST_REFINEMENT`.

The Human can inspect the current Work outcome/scope/constraints and the
existing Production Plan proposal fields before deciding. Approval records an
exact governance decision bound to Work Reality, Steering revision/Step,
semantic result and proposal. Refinement records governance and reopens the
readiness issue. Only approval permits Plan Steering to transition to
`PRODUCE`, where existing Authority validation, PLAN-1B and SPG remain
mandatory.

This implements the Guided Design portion of
`PRE_AUTHORIZATION_WORK_PREVIEW_REQUIRED`. Broader product presentation and
Human Product Acceptance remain separately governed; this checkpoint does not
claim the overall finding is universally closed.

## Persistence and restart

Migration `20260908_27` adds the original Guided Design persistence. Migration
`20260908_28` adds persisted schema-selection rationale together with the
Human–Watt conversation/Turn foundation described in the
[Human–Watt Collaboration Layer](human-watt-collaboration-layer.md).

The original Guided Design migration adds:

- `guided_design_processes`;
- append-only `guided_design_agenda_revisions`, with one active revision;
- `steering_steps.design_issue_key`;
- the typed production-proposal review Attention reason.

Process selection, agenda history, issue state/rationale, current Step links,
semantic result links and Work Reality basis live in PostgreSQL. Bootstrap is
idempotent. Reconstruction does not need Provider thread continuity, chat
memory, or a production cycle. A missing or stale governed reference fails
closed.

## Product projection

`WorkResponse.guided_design` and
`GET /api/works/{work_id}/guided-design` expose the process objective/schema,
agenda revision, current focus and rationale, progress, issue state, readiness
blockers and next known governed transition. The existing Control Room adds one
progressively disclosed Guided Design panel; it does not redesign the product
surface or expose raw Provider transcripts.

## Provider neutrality

The design contracts contain no external coding-agent semantics. The current
API-key semantic provider uses the strict typed wire schema enforced by
application parsing. Provider and model identity are provenance metadata,
never Work Truth, Design Truth, Plan Truth or Authority. Another API-key
provider can implement the same `SemanticStepCapability` contract.

## Invariants

- Conversation is not Work or design truth.
- Interpretation is not Authority.
- Vague Motive does not directly trigger production.
- Design Schema is not Plan Steering; Plan Steering owns `WHAT NEXT`.
- A design issue closes only with admitted governed evidence.
- Earlier governed results, not hidden Provider memory, inform later issues.
- Provider output alone cannot change governed Reality.
- Readiness is not production Authority.
- Guided Design never owns production.
- Human proposal review creates no production facts by itself.
- PLAN-1B/SPG remain the production admission boundary.
- Active production contracts and historical design revisions are immutable.

## Non-goals

This capability does not implement ECF, a generic BPM/workflow engine,
user-authored workflow DSL, Multi-PWU/DAG planning, advanced autonomous
branching/replanning, enterprise multi-user governance, portfolio/project
management, a second Work hierarchy, production retry redesign, or broad UI
redesign.

## Validation and status

Focused evidence is recorded in
[Guided Design Core Focused Validation](../evidence/guided-design-core-focused-validation.md).
Deterministic, PostgreSQL, restart, API/UI, affected production trust-boundary
regressions and an isolated real Codex Provider proof pass. Human Product
Acceptance of the experience is still pending.
