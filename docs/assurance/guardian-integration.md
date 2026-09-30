# Guardian Integration

## Formal Positioning

**Guardian — Engineering Assurance System**

Guardian is platform-native, but platform-independent.

## Boundary

The platform is responsible for Orchestration. Guardian is responsible for Assurance.

Assurance validates observed results, Evidence, contract satisfaction,
important boundary violations, and quality Findings. It does not micromanage
each Executor move or replace the Executor's autonomy inside an admitted
production envelope. See the
[Work-centric Production and Responsibility Principles](../architecture/work-centric-production-and-responsibility-principles.md).

Model-mediated assurance judgments, where present, are candidates subject to
Guardian's own evidence and exact-subject validation. Watt's governed
Self-Refine semantics may support a bounded re-evaluation after contradiction;
they do not turn a wrong-revision PASS into truth, lower Guardian's evidence
bar, or transfer Assurance ownership to the Executor. Current exact-revision
Verification remains a deterministic rejection boundary; no new Guardian
reasoning runtime is claimed by this calibration.

Guardian is:

- Not an AI Code Reviewer
- Not an ordinary CI Gate
- Not an Agent inside a Consumer Application

## External Product and Work Relationship

For Work that produces or evolves an external product such as 易决, the current
direct integration is a **Reference / Transitional Integration**. The
long-term direction is **Platform-mediated Integration**. Guardian qualifies
Evidence for the governed Work/PWU; it does not own a Project lifecycle, Work,
Plan, or attached Assets.

This document does not design Guardian Core.

## Bounded software assurance station

The `REQUIRED` owner-runtime profile uses Guardian's canonical
`watt-guardian-software-assurance-v1` contract. Watt binds explicit business
effects to the current governed Work basis before Candidate sealing
through `POST /api/works/{work_id}/guardian-assurance/requirements`. The payload
contains `authority_identity` and `required_effects` using Guardian's
`EffectRequirement` contract. A long-lived Work uses its Work Reality revision;
a short Work uses its Human-approved Engineering Scope. The binding is immutable
for that admitted basis.
Watt sends the governed objective and constraints, exact Candidate commit/tree,
Preview identity, and Verification references. It does not send raw Human
conversation for Guardian interpretation.

After the exact Candidate Preview reaches READY, Watt calls the Guardian owner
runtime. `GET /api/works/{work_id}/guardian-assurance` exposes the current gate,
Finding count, summary, and result/evidence references. Watt stores only that
projection; Guardian owns the request, Findings, evidence, and result. The
Candidate authorization and Human Acceptance paths require Guardian PASS.
Neither PASS nor Human Acceptance creates Delivery Authorization.

For an admitted long-lived Work, `FAIL_REPAIRABLE` enters the existing Steering
production path under the same Work scope. The Steering revision names the
Guardian result and Finding evidence; Watt produces a successor Candidate and
submits it again. Work convergence history bounds repeated no-progress
outcomes. A short Work creates a successor Run/Plan/PWU under the same approved
scope and Completion Contract. `BLOCKED` never creates repair authority or a
PASS. A missing governed effect scope also blocks readiness.
