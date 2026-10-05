# ADR-008: Resource Governance

- **Status:** Accepted with an explicit v1 bound and remaining disk-quota gap.
- **Decision:** Persist per-Execution active-time, model/tool, log-payload and
  direct-write artifact bounds. Enforce Worker concurrency from its registry;
  preserve Docker log rotation and disk inspection on the single ECS.
- **Context:** A 100 GB data disk can be exhausted by long execution, logs,
  artifacts or temporary builds. Native ResourceEnvelope already bounded model
  submissions, tool effects and active time semantically.
- **Reason:** Resource use must be governable and visible before adding a
  Worker pool. A limit breach must produce evidence and safe recovery.
- **Consequence:** Runtime timeout stops heartbeat and triggers lease/effect
  reconciliation. Direct writes and returned Tool output have byte limits.
  Arbitrary process-generated workspace files are not under a hard quota yet;
  that remains a separate storage qualification requirement.
