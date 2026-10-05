# Watt Cloud Worker Runtime v1.0

Status: implemented on `codex/cloud-worker-runtime-v1` over the existing Watt
Native Executor. This capability extends the [Production Infrastructure
Baseline](runtime-baseline.md); it does not create a second queue, replace
Product/Work authority, or move ECF Decision Context responsibility.

## Ownership and model

| Resource | Canonical persistence | Meaning |
| --- | --- | --- |
| Worker identity and liveness | `executor_worker_registrations` | Stable configured `worker_id`, name, hostname, runtime version, precise tool/model capabilities, capacity, status, registration and heartbeat times |
| Worker evidence | `executor_worker_events` | Register, heartbeat, status change and offline observation with source, time and content digest reference |
| Execution Request | Existing `executor_queue` plus exact Attempt binding | `execution_id` is the Attempt ID; Work, Task Contract reference, priority and current queue state remain persisted in the Native Executor model |
| Assignment | `execution_allocations` and `executor_leases` | Exact Worker/Attempt/lease epoch; token digest is stored, not plaintext token |
| Execution evidence | Existing `execution_events`, steps, effects, receipts and checkpoints | Trace created, queued, assigned, started, worker result and recovery; Worker completion is not Product acceptance |

The API admits an exact `NativeExecutionAdmission` with an existing Work, PWU,
Attempt, Task Contract and authority basis. It never creates an ungoverned
standalone execution from free-form prose. `CREATED` and `QUEUED` evidence are
written in the same transaction; the first observable current status is
`QUEUED`. The read model maps canonical queue and Attempt state to `QUEUED`,
`ASSIGNED`, `RUNNING`, `RECOVERY_REQUIRED`, `VERIFYING`, `COMPLETED`, `FAILED`
or `CANCELLED`. `RESULT_READY` means verification is required; only a
satisfied Production Work Unit can project `COMPLETED`.

## Registry and heartbeat

The Worker registers before polling and receives its durable identity record.
It sends a configurable heartbeat while idle and renews its exact lease while
executing. `SPG_NATIVE_EXECUTOR_HEARTBEAT_SECONDS` defaults to 10 seconds;
`SPG_NATIVE_EXECUTOR_OFFLINE_SECONDS` defaults to 30 seconds and must be at
least twice the heartbeat interval. The Coordinator marks an expired Worker
`OFFLINE`. `DRAINING` prevents new assignments while existing work can finish;
the operator may change this state through the authenticated API. Capacity is
`max_concurrency` (default 1) and is enforced transactionally during claim.
The current ECS config advertises model, tool and build execution, not an
unimplemented generic deployment Worker capability.

## Queue, assignment and recovery

The API writes a persisted Execution Request into the existing Native queue.
The scheduler matches provider/resource profiles and exact capabilities,
respects Worker capacity, uses fairness groups and priority within a group,
and ages old work so priority cannot starve it indefinitely. PostgreSQL row
locking plus the existing unique active-allocation and live-lease constraints
prevent two Workers from owning the same Attempt simultaneously.

After a Worker crash, lease expiration is evidence, not permission to replay
effects. The Coordinator checks the effect journal. A settled frontier may be
requeued with a higher lease epoch; unresolved effects are fenced and remain
`RECOVERY_REQUIRED` for reconciliation. The old Worker cannot commit through
the new epoch. This is the existing Native Executor recovery contract, now
visible through the Cloud Worker projection.

## Resource bounds and interfaces

An admitted `ResourceEnvelope` persists maximum active seconds, model/tool
submission budgets, maximum log payload bytes and maximum direct `file.write`
artifact bytes. The Worker cancels work exceeding active time, stops lease
renewal and records the limit event; Coordinator recovery determines whether
requeue is safe. The Tool Host rejects oversized direct writes and returns a
failed bounded result when a tool output exceeds the log limit. Docker logs
retain their separate Compose size/rotation bound. Arbitrary process-generated
workspace growth is **not** yet a hard per-Execution disk quota; the current
node also uses bounded cleanup and disk inspection. A true filesystem quota
requires a qualified storage mechanism before it can be claimed.

Authenticated API surfaces:

- `GET /api/cloud-worker/workers` and
  `GET /api/cloud-worker/workers/{worker_id}/evidence`;
- `POST /api/cloud-worker/workers/{worker_id}/drain`;
- `POST /api/cloud-worker/executions` using the existing exact Native admission
  contract;
- `GET /api/cloud-worker/executions/{execution_id}` and its `/evidence` view.

The existing `/api/native-execution/*` routes remain available. ECF may later
consume a decision-scoped Runtime Context projection from these persisted
facts, but this branch does not add an ECF endpoint or change ECF authority.

## Scaling path

One Worker process on the current ECS is the first placement. Distinct Worker
IDs, shared PostgreSQL queue, lease epochs and configurable capacity form the
minimum pool boundary. Before moving Workers to another ECS, qualify remote
Tool Host/sandbox access, durable shared checkpoint/workspace data, secret
distribution, multi-Worker claim races and host-loss recovery. See
[scaling-strategy.md](scaling-strategy.md) and
[ADR-003](adr/ADR-003-worker-independent-scaling.md).
