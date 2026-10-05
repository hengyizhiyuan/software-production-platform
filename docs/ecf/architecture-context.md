# ECF Architecture Context Source v1.0

Status: **canonical repository source definition**, not an implemented ECF
endpoint or an active ECF registration. This document tells a future ECF
consumer how to assemble decision-scoped architecture context from the
Production Infrastructure Baseline. ECF still owns context selection,
freshness, provenance and projection; Watt retains decision and action
authority. See [the current ECF integration boundary](../context/ecf-integration.md).

## Source manifest

| Context category | Canonical source | Meaning |
| --- | --- | --- |
| Architecture decisions | [`ADR-001`](../architecture/adr/ADR-001-runtime-separation.md), [`ADR-002`](../architecture/adr/ADR-002-single-ecs-first.md), [`ADR-003`](../architecture/adr/ADR-003-worker-independent-scaling.md), [`ADR-004`](../architecture/adr/ADR-004-data-lifecycle-governance.md) | Accepted constraints and their consequences |
| Runtime facts | [runtime baseline](../architecture/runtime-baseline.md), [Compose source](../../deploy/cloud-worker/docker-compose.yml) | Observed single-ECS topology and versioned deployment configuration |
| Deployment constraints | [target architecture](../architecture/production-target.md), [operations](../architecture/operations.md) | Boundary, isolation, persistence, recovery and upgrade conditions |
| Scaling assumptions | [scaling strategy](../architecture/scaling-strategy.md) | Conditional stages and measurements, not a user-count entitlement |
| Operational constraints | [data lifecycle](../architecture/data-lifecycle.md), [operations](../architecture/operations.md) | Retention, cleanup, backup/restore and unresolved decisions |
| Cloud Worker Runtime Context source | [Cloud Worker Runtime](../architecture/cloud-worker-runtime.md), [ADR-005](../architecture/adr/ADR-005-worker-registry.md), [ADR-006](../architecture/adr/ADR-006-execution-lifecycle.md), [ADR-007](../architecture/adr/ADR-007-worker-lease-recovery.md), [ADR-008](../architecture/adr/ADR-008-resource-governance.md) | Worker identity/capacity, Execution lifecycle, lease/recovery and resource limits |

The Git revision/tree of these files is the **document provenance**. A live
runtime fact also needs an observation timestamp, exact Cloud Connection and
InstanceId, method/evidence, and freshness check. The current target is
`cn-wulanchabu / i-0jl386xnbauudq5j9jk0`; replacing it does not rewrite the
historical baseline. ECF must return current observed reality for a new target
or mark the old fact stale/unknown. A design statement cannot override newer
measured runtime evidence, and a live observation cannot silently change an
accepted ADR.

## Proposed context record shape

```text
architecture_context_version: watt-production-infrastructure-v1
decision_scope: exact Work/Task and the architecture question being answered
source_revision: repository commit + tree + file paths
decisions: ADR id, status, exact revision, required constraints
runtime_facts: target identity, observation time, evidence reference, freshness
deployment_constraints: required placement/isolation/data conditions
scaling_assumptions: stage, trigger evidence, unverified assumptions
operational_constraints: backup/restore/retention/upgrade requirements
runtime_context_entry: exact Worker and Execution IDs, observed status, lease epoch,
  heartbeat/evidence references and freshness, only when decision scope needs them
unresolved: explicit unknowns and decisions requiring an owner
```

This is a **future consumption structure**, not an API schema, generated
payload, ECF policy or registration implemented by this task. A consumer must
request only the sources relevant to its decision, preserve their exact
revision and distinguish `observed`, `accepted decision`, `proposed policy`
and `unverified`. If a required source is missing, conflicting or stale, the
consumer reports that state rather than guessing from an old session summary.

Cloud Worker Runtime v1 supplies persisted source facts through Watt's
authenticated `/api/cloud-worker/*` projection and database records. A future
ECF Runtime Context consumer must bind exact Work/Task/Attempt, Worker ID,
timestamp and evidence digest, and must treat expired heartbeat or unresolved
lease as stale/uncertain. This entry is a source definition, not a new ECF
service or a transfer of Worker scheduling authority to ECF.

Do not include `.env` values, credentials, raw secrets or account-wide cloud
authority in the context package. ECF provides need-to-know engineering
context; it does not grant need-to-act authority. Human authorization,
Guardian assurance and runtime verification keep their existing owners.
