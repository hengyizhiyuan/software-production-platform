# ADR-009: Execution Context Binding

- **Status:** Accepted.
- **Decision:** Product Execution requires an exact Work revision, Task Contract,
  IRK identity, fresh ECF fingerprint, source revision, Workspace ID and
  verification obligations before queue admission. Missing context returns
  `EXECUTION_CONTEXT_NOT_READY`.
- **Context:** A durable queue can otherwise run stale or ungoverned work after
  the Human conversation and Work have changed.
- **Reason:** Execution authority must derive from persisted, current Work
  Reality rather than raw Human prose or a Worker inference.
- **Consequence:** Incomplete or stale Product work blocks explicitly. Existing
  owner services retain their decision and verification authority.
