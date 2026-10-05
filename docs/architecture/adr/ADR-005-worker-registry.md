# ADR-005: Worker Registry

- **Status:** Accepted and implemented in Cloud Worker Runtime v1.0.
- **Decision:** A Worker has a stable persisted identity, runtime metadata,
  precise capability/capacity declaration, heartbeat, operational status and
  attributable liveness evidence. An expired heartbeat projects `OFFLINE`;
  `DRAINING` blocks new allocations.
- **Context:** Native execution already stored expiring Worker offers but did
  not preserve full identity metadata or heartbeat while idle.
- **Reason:** API and scheduler must reason about actual execution capacity
  without depending on one process or assuming that a silent Worker is ready.
- **Consequence:** Worker IDs must be unique across future nodes. Heartbeat
  writes and events require retention policy; registration alone is not proof
  that a Worker completed an Execution.
