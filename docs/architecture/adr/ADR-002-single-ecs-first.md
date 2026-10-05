# ADR-002: Single ECS First

- **Status:** Accepted for Stage 0; placement is revisited by measured need
- **Decision:** Start the Cloud Worker runtime on one Alibaba Cloud Linux 3
  ECS with Docker Compose and a dedicated `/data` disk. Keep services logically
  separated and their persistent paths explicit.
- **Context:** The qualified node has 4 vCPU, a 16 GiB instance specification
  and a 100 GB data disk. The current stack runs and survives a Compose
  `down`/`up` with local database and application data intact.
- **Reason:** One host limits early cost and operational complexity while Watt
  validates real workload and recovery behavior. It provides a concrete
  baseline for deciding when to split services.
- **Consequence:** The ECS/data disk remains a single failure domain; local
  persistence is not machine-loss recovery. Off-host backup and a tested
  restore are required before a production durability claim. Split placement
  only when measured contention, reliability or governance needs justify it.

See [scaling strategy](../scaling-strategy.md) and
[operations](../operations.md).
