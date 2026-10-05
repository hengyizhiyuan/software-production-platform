# ADR-001: Runtime Separation

- **Status:** Accepted for Production Infrastructure Baseline v1.0
- **Decision:** API/Application, Worker/Execution and Data remain logically
  separate. API persists governed work; an independent Worker claims and
  executes it; PostgreSQL and referenced files hold durable state. Co-location
  on one ECS must not collapse these responsibilities.
- **Context:** The current Compose stack runs API, Worker, Coordinator, Tool
  Host and PostgreSQL as distinct services on one ECS. The queue and leases are
  PostgreSQL-backed; API health and Worker heartbeat are independently checked.
- **Reason:** The Product request path must remain responsive, attempts must
  survive process restart, and future node separation must preserve authority,
  queue, checkpoint and evidence lineage.
- **Consequence:** Changes may share physical infrastructure but must preserve
  service contracts and persisted identities. Cross-node deployment later
  requires explicit addressing, workspace/receipt durability and Tool Host
  isolation; it cannot rely on API memory or local socket semantics.

See [runtime baseline](../runtime-baseline.md) and
[target architecture](../production-target.md).
