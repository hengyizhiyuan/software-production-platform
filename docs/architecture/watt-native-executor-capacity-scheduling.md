# Watt-native Executor Capacity Scheduling & Execution Queue

Date: 2026-09-11. Final technical closure status updated 2026-09-13. Status:
**ARCHITECTURE AMENDMENT COMPLETE; IMPLEMENTED; TECHNICALLY QUALIFIED**.

This document amends the [Watt-native Executor Blueprint](watt-native-executor-blueprint.md)
by defining how finite execution capacity is assigned when multiple users and
Production Work Units (PWUs) compete for Executor resources. The current
PostgreSQL-backed implementation supplies fair round-robin, FIFO, aging,
eligibility, fenced allocation leases, resource waits that release workers,
and Human-visible queue projections. Concurrency, crash, starvation and
performance qualification passed under the final Q-case and continuity
evidence. Human Product Acceptance is deferred by Human governance. This does
not change the PWU lifecycle or introduce a new source of product or production
truth. See the [final technical closure](../evidence/watt-native-executor-technical-closure.md).

The following invariants remain normative:

- Steering owns **WHAT NEXT**.
- The Executor owns **HOW** within an admitted execution envelope.
- A PWU is a governed Production Unit, not an Execution Slice.
- Execution continuity does not require continuous execution.
- Capacity scheduling never redefines Product Intent, Work, Plan, PWU scope,
  production authority, Completion, or Verification truth.

## 1. Capacity Scheduling Plane boundary

The Capacity Scheduling Plane sits between an admitted, runnable PWU execution
and the Executor Runtime. Its narrow responsibility is:

> Decide when and on which eligible execution capacity an already-authorized,
> runnable execution may proceed.

It may maintain runnable queue entries, evaluate resource eligibility, apply an
admitted fairness policy, issue and release Execution Allocations, and expose
queue Reality for Human observation.

It must not:

- interpret or redefine Motive, Work, or Product Intent;
- decide what production step should happen next;
- create, split, merge, or rewrite a PWU;
- grant authority or expand an execution envelope;
- select implementation strategy inside the PWU;
- declare Completion, Verification, Runtime Commit, or Trusted Baseline truth;
- infer priority from model output or Executor preference.

Capacity availability is execution Reality. It may constrain when an admitted
step runs, but it does not change why the Work exists or what the Plan means.

## 2. Ownership model

| Concern | Owner | Scheduling relationship |
| --- | --- | --- |
| Product Intent, major priority, risk acceptance, authority | Human Governor | Scheduler consumes explicit governed policy and cannot replace Human authority. |
| WHAT NEXT, Plan direction, PWU formation | Steering | Supplies the admitted next production unit; scheduler cannot revise it. |
| Production contract, authority envelope, runnable eligibility | SPG / governed production control | Only an authorized, runnable execution request may enter the eligible queue. |
| Queue order, capacity eligibility, fairness, allocation lease | Capacity Scheduling Plane | Owns when eligible execution receives finite capacity. |
| HOW within the execution envelope | Executor | Consumes an allocation without gaining broader authority. |
| Completion, Verification, Runtime, Trusted Baseline facts | Existing production, assurance, and Runtime owners | Scheduler observes these facts and releases capacity; it does not manufacture them. |
| Human-visible queue state | Control Room or another projection surface | Projects scheduling Reality without becoming a lifecycle owner. |

An Execution Allocation is capacity permission, not production authorization.
Both must be valid:

~~~text
Production Authority
+
Runnable Eligibility
+
Execution Allocation
--------------------
Executor may run
~~~

## 3. Architecture relationship

~~~text
Work
  ↓
Steering
  ↓
PWU
  ↓
Capacity Scheduler
  ↓
Execution Allocation
  ↓
Executor Runtime
~~~

- Work supplies the governed objective and Reality relationship.
- Steering determines the appropriate next production step.
- PWU carries the bounded production contract and authority envelope.
- Capacity Scheduler orders runnable execution and assigns finite capacity.
- Execution Allocation is a fenced, time-bounded right to consume specified
  resources.
- Executor Runtime determines HOW and produces checkpoints, artifacts, reports,
  and evidence under the existing lifecycle.

Executor results return through existing observation, Completion, Verification,
and Reality-update paths. Scheduling does not create a parallel production
lifecycle.

## 4. Production Unit and Execution Slice

A **Production Unit (PWU)** is a governed unit of production. It carries
meaningful scope, contracts, authority, context requirements, and Verification
obligations. Its identity persists across waits, checkpoints, restarts,
Executor replacement, and multiple allocations.

An **Execution Slice** is a finite interval during which an Executor consumes an
Execution Allocation. It is a scheduling and resource-consumption concept, not
a production object.

| Dimension | PWU / Production Unit | Execution Slice |
| --- | --- | --- |
| Purpose | Define bounded production | Consume finite execution capacity |
| Owner | Steering/SPG production semantics | Scheduler and Executor Runtime |
| Lifetime | May span waits, attempts, and checkpoints | Ends on release, expiry, checkpoint, failure, or bounded yield |
| Authority | Carries admitted production scope | Carries no new production authority |
| Completion | Existing Completion and Verification semantics | Slice end does not imply PWU completion or failure |
| Continuity | Durable production identity and Reality | Replaceable interval of runtime occupancy |

~~~text
One PWU
  → zero or more waiting periods
  → one or more Execution Slices
  → durable checkpoints between slices
~~~

Returning checkpointed execution to the queue is not automatic PWU
decomposition and is not preemption. It continues the same governed Production
Unit under a later allocation.

## 5. Queue and allocation contracts

This amendment defines semantic contracts, not a database schema.

### Execution Queue Entry

One queue entry represents one currently runnable capacity request. A future
durable representation should identify:

- queue-entry identity;
- PWU and authorized Attempt/grant revision;
- accountable user fairness group;
- enqueue sequence and time;
- required capability, provider, runtime profile, and resource envelope;
- eligibility fingerprint needed to reject stale authority;
- queue condition, wait reason, and aging information;
- scheduling policy version and allocation history reference.

There must not be multiple active entries for the same runnable grant revision.
A queue entry cannot rewrite the PWU, its contracts, or its authority.

### Execution Allocation

An Execution Allocation is a fenced, time-bounded capacity grant. Its future
contract should identify:

- allocation identity and source queue entry;
- PWU and authorized Attempt/grant revision;
- selected Executor Runtime or worker profile;
- reserved provider, capability, and resource constraints;
- lease epoch, issue time, start deadline, expiry, and release condition;
- scheduling decision reason and policy version;
- fencing information preventing stale or duplicate writers.

Allocation validity is checked together with existing authority, lease, and
write-fencing rules. An expired or released allocation cannot be reused.

## 6. MVP scheduling policy

The initial policy is intentionally simple and explainable:

1. **Fair round-robin between users.** Each user with at least one eligible
   runnable entry receives turns as capacity becomes available.
2. **FIFO within each fairness group.** Within a user's eligible queue, the
   earliest admitted runnable entry is considered first.
3. **Aging prevents starvation.** An entry waiting beyond an admitted threshold
   gains temporary precedence over ordinary rotation. Aging changes service
   order only; it never bypasses eligibility, authority, resource constraints,
   or concurrency fences.
4. **No commercial weighting yet.** Pricing, subscription tier, customer value,
   and model preference do not affect MVP ordering.

Resource-incompatible entries may be skipped without losing their original FIFO
age. The wait reason remains visible; when compatibility returns, the entry
resumes consideration with preserved age.

## 7. Human-visible Execution Queue semantics

~~~text
Entered queue
  ↓
Waiting for resource
  ↓
Allocated
  ↓
Executing
  ↓
Checkpoint completed
  ↓
Returned to queue (when more execution is required)
  ↓
Resumed
  ↓
Completed
~~~

These are projections over queue, allocation, Executor, and production Reality.
They are not new PWU lifecycle states.

| Human-visible condition | Meaning |
| --- | --- |
| Entered queue | Authorized PWU execution is runnable and awaiting capacity. |
| Waiting for resource | Required worker, provider, capability, or resource capacity is unavailable; no worker is occupied. |
| Allocated | A fenced capacity grant exists, but active execution has not yet been observed. |
| Executing | Executor holds valid capacity and runs within its envelope. |
| Checkpoint completed | Durable progress/evidence was recorded through the existing lifecycle. |
| Returned to queue | The same PWU needs another slice and awaits allocation again. |
| Resumed | A later allocation continued from governed durable Reality. |
| Completed | Existing production semantics determined no further allocation is required; the scheduler did not declare completion. |

The projection should show the current wait reason and must not imply that queue
position promises an exact start time.

## 8. Runnable eligibility and worker occupancy

Only runnable execution consumes Executor worker capacity. Execution is runnable
only when existing authority, input/context, capability, resource, and
concurrency requirements permit it. Free capacity cannot make an incomplete or
unauthorized PWU runnable.

The following waits do not occupy a worker:

- **Provider capacity unavailable:** park until compatible provider capacity is
  observable; do not reserve an idle Executor worker.
- **Human input required:** exclude from runnable allocation until the existing
  governance owner records the Human decision.
- **Resource unavailable:** retain wait reason and eligibility age without
  holding a worker.
- **Capability unavailable:** park until an eligible provider/runtime exists;
  the scheduler cannot substitute an unauthorized capability.

Provider and resource reservation occurs at the latest safe point before
execution, consistently with the Blueprint's pre-call authority and reservation
rules. A reservation that cannot lead to runnable execution is released.

Checkpoint, allocation release, and return-to-queue behavior preserve existing
Attempt, lease, idempotency, and crash-recovery invariants. Scheduler wait
reasons do not replace lifecycle failure classifications.

## 9. Future extension seam

The contracts leave room for later governed policy without changing Work, PWU,
or Executor ownership:

- user weighting under explicit policy;
- enterprise priority classes;
- resource-aware scheduling;
- provider-aware routing;
- dynamic worker/capacity scaling;
- multi-host scheduling behind the same queue/allocation contract.

Future weighting must be explicit, versioned, explainable, and authorized. It
cannot be inferred from conversation, model preference, or unadmitted
commercial metadata. Provider-aware routing allocates eligible capacity; it
does not make a Provider the owner of a stable Capability Contract.

## 10. Explicit non-goals

This amendment does not define or authorize:

- a distributed scheduler;
- Kubernetes-like orchestration;
- forced or transparent preemption;
- an SLA or commercial entitlement system;
- predictive scheduling;
- automatic PWU decomposition;
- a new message broker, Event Bus, or queue product;
- a new PWU or Work lifecycle;
- automatic priority decisions by a model;
- implementation, schema, migration, API, or runtime changes.

The initial direction remains compatible with the Blueprint's single-host,
database-backed coordination model. Distributed scheduling is a future
extension, not an MVP dependency.

## 11. Consistency and qualification closure

This document refines the Blueprint's existing queue, lease, resource
reservation, and single-host coordination seams. It does not change the
approved lifecycle or qualification contracts.

The completed implementation and qualification evidence proves:

- no execution without both production authority and allocation;
- one active allocation/write owner for the applicable Attempt boundary;
- fair user rotation, FIFO ordering, and bounded anti-starvation aging;
- waiting entries consume no worker capacity;
- checkpoint/requeue/resume preserve PWU and Attempt Reality;
- Human-visible states are truthful projections;
- scheduler replacement cannot change Product Intent, Plan, or PWU scope.

These obligations are closed by the focused scheduling tests, the 100-round
allocation race, prescribed continuity injections and final Q-case ledger.
Future distributed/capacity evolution remains behind the same contracts and
does not reopen the qualified local scheduling plane.

## Final status

~~~text
CAPACITY_SCHEDULING_ARCHITECTURE_AMENDMENT_COMPLETE
CAPACITY_SCHEDULING_IMPLEMENTED
CAPACITY_SCHEDULING_TECHNICALLY_QUALIFIED
~~~
