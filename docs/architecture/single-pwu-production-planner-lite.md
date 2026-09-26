# Single-PWU Production Planner Intelligence Lite

> Historical PLAN-1B slice contract. Its single-PWU admission and deferred
> multi-PWU statements describe that slice at closure, not the current runtime.
> Current versioned multi-PWU lineage is described in
> [Watt AI-Native Software Production Architecture](watt-ai-native-software-production-architecture.md#versioned-multi-pwu-production).

## Status

**MVP-PLAN-1B: CLOSED / PASS**

**MVP-PLAN-1A: NOT IMPLEMENTED — PLAN_AUTHORITY_BOUNDARY_FINDING CONFIRMED**

This slice adds planning intelligence to the existing one Work → one Plan
Revision → one governed PWU model. It does not authorize multi-PWU production,
change Candidate authority, or introduce another execution state machine.

## Concept Calibration

PLAN-1B is the narrow current implementation of planning for one admitted
production step. It does not define Plan as permanently equivalent to a short
execution checklist, nor Work as an atomic task. A Work may be broad and
long-lived; PWU is the bounded production-unit concept. The conceptual Plan may
guide a Motive/Work through current Reality, next-step selection, refinement,
design, Human decisions, governed production, and reassessment over time.

That broader **Reality-driven Plan Steering** capability is now implemented for
the closed MVP behavior. PLAN-1B remains CLOSED / PASS and is not reopened. See
[Motive / Work / Plan Concept Calibration](motive-work-plan-concept-calibration.md)
and the [Reality-driven Plan Steering MVP Behavioral
Contract](reality-driven-plan-steering-mvp-contract.md).

## Production Plan Proposal

Production Planner Lite transforms governed Work facts into a durable,
provider-neutral Production Plan Proposal containing:

- the exact desired outcome and production objective;
- one or more ordered logical steps inside one PWU;
- exact artifact/change targets;
- inherited constraints;
- the verification approach;
- assumptions and unresolved questions;
- one-PWU fit classification;
- exact Engineering Resource and Source Baseline identity.

The steps are production strategy, not independently executable PWUs. The
proposal is stored with the Work and, after `ADMIT_WORK_DRAFT`, is carried by
the sole PWU's Completion Contract. Materialized Execution Input renders the
approved desired outcome, target operation, constraints, ordered steps,
verification approach, and authorized paths.

## Fit and Authority

The fit classification is one of:

- `ONE_PWU_FIT`: the Work may enter the current one-PWU Runtime;
- `NEEDS_REFINEMENT`: ambiguity or an authority mismatch blocks admission;
- `MULTI_PWU_REQUIRED`: independently governed sequencing exceeds the MVP.

For legacy `IMMEDIATE_PRODUCTION` Work, only `ONE_PWU_FIT` may reach Human Work
Draft Approval and Runtime admission. For `LONG_LIVED_STEERING` Work, Human
admission governs the Work envelope without creating Run/PWU Reality; PLAN-1B
and `ONE_PWU_FIT` remain mandatory when a later exact `PRODUCE` Step seeks
production admission. The other classifications create no production Run,
Plan Revision, PWU, Attempt, or Provider authority.

Future duration-aware sizing may advise this boundary, but does not change its
Authority. See [Duration & Capacity Semantic
Foundation](duration-capacity-semantic-foundation.md).

Planner intelligence is not Production Authority. A proposal must exactly
preserve the admitted desired outcome, objective, Engineering Resource,
Artifact Target, constraints, verification expectation, and Source Baseline.
A provider proposal that changes any of these facts is replaced by a truthful
`NEEDS_REFINEMENT` proposal containing the authority violation; expanded paths
never enter the executable contract.

The Human sees the Plan Summary before the existing `ADMIT_WORK_DRAFT`
decision. No separate mandatory Plan approval exists. The Work Draft approval
binds the exact proposal as part of the governed Production Contract.

## Provider-Neutral Boundary

`ProductionPlanner` accepts only governed Work, Engineering Scope, exact
Artifact Target, exact Baseline, constraints, verification expectation, and
admitted repository context references. Conversation history is not an
authority input. The current deterministic/rule-assisted provider may later be
replaced without changing the Production Plan contract or Runtime authority
model. No real Provider Turn is part of PLAN-1B.

## PLAN-1A Authority Finding

MVP-PLAN-1A remains not implemented. Current Candidate Authorization is exact
per PWU, and Runtime Commit advances the Trusted Baseline. A pending successor
PWU bound to baseline B0 cannot silently acquire authority against B1. Correct
successor activation would require additional planning, authorization,
baseline-rebinding, and recovery semantics beyond the current MVP need.

Therefore multi-PWU sequential production, successor baseline activation,
intermediate Candidate auto-authorization, Plan-derived repository integration
authority, parallel/DAG execution, and autonomous replanning remain
`DEFERRED_BY_MVP`. This finding does not invalidate the current one-PWU model.

## Evidence Mapping

| Evidence | Focused proof |
|---|---|
| PLANB-01–04 | Explicit durable proposal, ordered logical steps, no PWU identity in steps, and unchanged one-PWU Runtime flow |
| PLANB-05–07 | Provider-neutral Planner protocol and governed request facts without conversation-history authority |
| PLANB-08–10 | Exact target, inherited constraints, and explicit verification approach |
| PLANB-11–13 | One fit proposal creates exactly one PWU after approval; both non-fit states create none |
| PLANB-14–15 | Authority validation prevents Engineering Scope or artifact-path expansion |
| PLANB-16–17 | HTTP/UI Plan Summary precedes the unchanged `ADMIT_WORK_DRAFT` gate |
| PLANB-18–19 | MEI contains the approved ordered steps while authorized paths and Completion Contract remain controlling |
| PLANB-20–21 | Existing ORCH focused flow and trusted-completion semantics remain compatible |
| PLANB-22–24 | Multi-PWU and adjacent Phase-2 capabilities remain absent; Planner implementation stays replaceable |

## MVP Boundary

PLAN-1B adds no ECF, Guardian, Provider routing, Worker Fleet, Recovery,
multi-PWU orchestration, successor baseline logic, or automatic authorization.
The small Composer collapse control is a development usability patch only and
does not alter backend production semantics.
