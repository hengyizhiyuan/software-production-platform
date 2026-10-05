# ADR-006: Execution Lifecycle

- **Status:** Accepted and implemented as a read model over Native Executor.
- **Decision:** Execution Request identity is the existing Attempt ID. Work,
  Task Contract, priority, queue state, allocation, outcome and evidence are
  persisted in the canonical Native Executor tables; the Cloud Worker API
  projects their lifecycle rather than maintaining a competing state machine.
- **Context:** Native Executor already owns durable admissions, queue entries,
  Attempt state, events and result-ready claims.
- **Reason:** A second mutable execution table could disagree with Product/Work
  and erase recovery truth. A typed projection makes the current state usable
  without duplicating authority.
- **Consequence:** `RESULT_READY` maps to `VERIFYING`, not Product completion.
  `CREATED` and `QUEUED` events are atomic; the first observable current state
  is `QUEUED`. Future lifecycle changes must update the projection and tests.
