# ADR-004: Data Lifecycle Governance

- **Status:** Accepted policy direction; automatic cross-provider cleanup not implemented
- **Decision:** Every temporary artifact needs an owner, reference check,
  retention rule and bounded cleanup path. Authoritative transaction and
  evidence history must not be deleted through generic disk pruning.
- **Context:** The single ECS has a 100 GB data disk. Docker images, test
  containers, build cache, workspaces and logs can grow independently. A
  bounded Docker cleanup command exists; native workspace and Preview
  retention have their own reference-aware policies.
- **Reason:** Age-only or blanket cleanup may erase active Work/evidence;
  leaving all temporary data forever can exhaust `/data` and stop the runtime.
- **Consequence:** Operators inspect candidates and disk usage, prune only
  eligible Docker objects, and retain Work/evidence dependencies. Monitoring,
  automated scheduling and future object-storage migration require explicit
  ownership and qualification before they are claimed operational.

See [data lifecycle](../data-lifecycle.md) and
[operations](../operations.md).
