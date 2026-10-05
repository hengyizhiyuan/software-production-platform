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

## Production Runtime Context source

The [Production Execution Runtime](../architecture/production-execution-runtime.md)
and [ADR-009](../architecture/adr/ADR-009-execution-context-binding.md),
[ADR-010](../architecture/adr/ADR-010-workspace-isolation.md),
[ADR-011](../architecture/adr/ADR-011-verification-before-completion.md)
are canonical design sources. For an exact Work/Task decision, a future ECF
Runtime Context may consume persisted IRK/Task/Execution linkage, queue and
lease state, Workspace source revision, verification records and immutable
result evidence with their timestamps and digests. It must distinguish a
Worker result claim from a verified Work outcome, and treat missing/stale
source, owner or verification evidence as unresolved. This adds no ECF endpoint
or new ECF decision authority.

The canonical [versioned Multi-PWU production source](../architecture/watt-ai-native-software-production-architecture.md#versioned-multi-pwu-production)
defines Production Plan/PWU context within that existing boundary. For a PWU,
preserve exact Work and Plan revision, scoped Task Contract, input source commit,
protected Product intent/invariants/decisions, qualified predecessor PWU and
Execution identities, output revisions, verification/artifact references, and
the ECF package fingerprint. Assemble context when that PWU's input is ready;
do not copy the entire Work context into every node or rewrite an executed
Task Contract. Queue capacity and Worker placement remain scheduling facts,
not ECF authority. Terminal Work Candidate lineage must cover the qualified
required graph before Human acceptance.
