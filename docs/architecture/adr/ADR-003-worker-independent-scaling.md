# ADR-003: Worker Independent Scaling

- **Status:** Accepted as a scaling constraint; worker pool not yet qualified
- **Decision:** Worker lifecycle and capacity must be independently scalable
  from the API. Keep durable queue/lease ownership, attempt fencing and
  checkpoint/effect reconciliation at the execution boundary.
- **Context:** Today one `native-worker` container and a separate Coordinator
  use PostgreSQL-backed execution state. Worker readiness/heartbeat and
  Compose restart were checked; a multi-worker or host-loss exercise has not
  been performed for this deployment.
- **Reason:** Model/tool work varies independently from Human request volume.
  More API replicas cannot solve a saturated execution queue.
- **Consequence:** Stage 1 can move execution to a Worker ECS without adding a
  broker. Stage 2 may add Workers after proving concurrent claim, lease,
  idempotent side effects and shared checkpoint/artifact access. Choose a new
  queue technology only if measured contention and a safe migration justify it.

See [target architecture](../production-target.md) and
[scaling strategy](../scaling-strategy.md).
