# Watt Production Infrastructure Scaling Strategy v1.0

Status: **conditional migration plan**. User counts are planning bands, not
capacity guarantees. Advancement requires observed load, recovery behavior
and service-level objectives. The current [single-ECS baseline](runtime-baseline.md)
is Stage 0.

| Stage | Planning band | Placement | Why and measurable trigger | Migration path |
| --- | --- | --- | --- | --- |
| 0 | 0–20 users | Optional frontend, API, Worker/Coordinator/Tool Host, PostgreSQL on one ECS | Minimize cost and operational steps while the queue, CPU, memory and disk have headroom. Review when sustained API latency, queue wait, worker saturation or data-disk growth harms actual use. | Keep independent Compose services and persistent paths; measure API latency, queue age, active workers, database and disk before changing topology. |
| 1 | 20–100 users | Application ECS, Worker ECS, dedicated database host/service | Separate request latency from model/tool CPU and isolate database I/O when contention is measured; count alone does not trigger this. | Restore PostgreSQL into dedicated data runtime; give API and Worker the same durable DB endpoint; move Tool Host/sandbox with Worker; replace host-local workspace/socket assumptions; verify queue recovery and end-to-end execution before cutting over. |
| 2 | 100–1000 users | Application replicas, Worker pool, persistent queue, independent database | Add execution capacity when queue age, lease contention or per-worker saturation persists despite Stage 1 sizing. | Scale current DB-backed worker claims first; verify leases, fencing, idempotent effects and checkpoint access with two or more Workers. Consider a dedicated broker only if measured DB queue contention justifies migration and continuity semantics can be preserved. |
| 3 | 1000+ users | Multiple nodes; consider region placement and resource scheduling | Address distinct workload classes, failure domains or geographic/compliance needs that one region/pool cannot meet. | Partition worker resource profiles and placement; define artifact/queue/data locality and cross-region recovery contracts; qualify failover and governance lineage before any multi-region production claim. |

At every stage record baseline and post-migration p95 API latency, oldest
eligible queue item age, completion/failure rate, worker lease recovery time,
database CPU/connections/storage, `/data` free space and restore results.
Choose thresholds from actual product objectives and measurements; this
document does not invent an SLA or prescribe user-count-only scaling.

Current single-ECS failure domain persists through Stage 0. Stage 1 is not
complete when containers merely run on different machines: shared runtime
state, credentials, database durability, queue recovery and sandbox placement
must all be verified. Stage 2 must preserve Work/Task/Attempt identities and
authority across the pool. Stage 3 is a consideration, not an approved
multi-region deployment.
