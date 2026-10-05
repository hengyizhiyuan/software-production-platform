# ADR-007: Worker Lease Recovery

- **Status:** Accepted; existing Native recovery reused and exposed.
- **Decision:** Allocation uses a durable lease, unique active ownership and
  monotonically advancing Worker epoch. On expiry, reconcile effects before
  requeue. Fence unresolved effects and reject late Worker results.
- **Context:** A Worker can disappear after model submission or a Tool effect.
  Those states cannot be treated as equivalent to a task that never started.
- **Reason:** Blind retries can duplicate external effects or falsely mark a
  task complete. The Native journal distinguishes settled and unknown fronts.
- **Consequence:** Recovery may pause for evidence; a safe settled frontier
  requeues the same Attempt with a new epoch. A timeout is not a success claim.
