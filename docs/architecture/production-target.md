# Watt Production Infrastructure Target Architecture v1.0

Status: **target design**, derived from the [observed runtime baseline](runtime-baseline.md).
This is a migration direction, not a claim that the single-ECS dogfood node
already has independent nodes, durable remote storage or public ingress.
The infrastructure planes below describe deployable responsibility boundaries;
they do not redefine Watt's [governance capability planes](plane-model.md).

## Application plane

Owns Human interaction, Workspace/Product presentation, Work management and
HTTP APIs. It validates Human and Product authority, creates governed work,
records state transitions and reads persisted results. It may scale separately
from execution. It must not keep the only copy of a task in process memory or
perform a long model/tool run within an HTTP request. Optional frontend assets
can share the node initially, then be served independently without changing
Work identity or authorization.

## Execution plane

Owns Worker scheduling/claiming, Agent execution, external model invocation,
Tool Host operations and Production Environment sandbox execution. Workers
consume persisted queue/lease state and emit attributable execution records.
Tool operations remain bounded by Task authority and isolation requirements;
Workers do not decide Product acceptance or rewrite governance history. On the
current Alibaba Cloud Linux host, Tool Host requires the container-backed
Production Environment path because Landlock is unavailable there.

## Data plane

Owns PostgreSQL transaction data, queue/lease state, execution records and
metadata/references to artifacts and logs. Today this is one local PostgreSQL
container plus file-backed `/data/watt` and `/data/docker` content. Future
artifact/object storage and off-host backup require explicit provenance,
consistency and restore contracts; a copied image or log is not automatically
an authoritative Production Artifact or Evidence record.

## Placement path

| Capability | Current single ECS | First separation | Later scale |
| --- | --- | --- | --- |
| API and optional frontend | `api` on one host | Application ECS | Multiple application replicas behind governed ingress |
| Execution | Worker, Coordinator, Tool Host and local sandbox containers | Worker ECS with explicit tool/sandbox placement | Worker pool with leases, fencing and resource scheduling |
| Transactions and queue | PostgreSQL on `/data/postgres` | Dedicated database host or managed PostgreSQL after restore test | Independently sized database; queue technology reviewed from measured load |
| Workspace/artifacts | `/data/watt` on the host | Move only required shared/durable assets with identity and consistency rules | Object storage for immutable artifacts where justified |

Stage 1 must first replace host-local assumptions: API-to-Worker and
Worker-to-Tool-Host addresses, shared workspace access, Docker socket
placement, secret distribution, database reachability and migration ownership.
The existing PostgreSQL queue can remain during that step if lease and
throughput measurements permit. A new broker is not a prerequisite for node
separation. The exact sequence and triggers are in
[scaling-strategy.md](scaling-strategy.md).

### Non-negotiable migration checks

1. A Worker crash/restart must preserve accepted Work, attempt/lease lineage,
   checkpoint references and reconciliation behavior.
2. Application replicas must observe the same durable Product/Work/queue state
   and must not create duplicate side effects on retries.
3. Tool Host and sandbox execution must retain Task authority, isolation and
   evidence lineage after moving off the application host.
4. Artifacts, workspace files and database records must have a documented
   consistency and restore order before detaching the data disk.
5. New ingress or regions require explicit exposure, data residency and
   authority decisions; this baseline does not grant them.
