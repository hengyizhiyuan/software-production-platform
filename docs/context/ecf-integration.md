# Engineering Context Fabric Integration

This document records Watt's consumption boundary for canonical ECF v0.1.
ECF owns the Decision Context contract, source selection, status, provenance,
and fingerprint. Watt owns policy selection, source adaptation, Task admission,
execution freshness, Verification lineage, and Human-facing blockers.

ECF owns **Need-to-know / Least Context**. It does not own IAM, credentials,
asset permissions, or action authorization. Future capability/access
provisioning owns **Need-to-act / Least Privilege** as a distinct seam, even
when both responsibilities follow the same minimum-sufficient principle. See
the [Work-centric Production and Responsibility Principles](../architecture/work-centric-production-and-responsibility-principles.md).

Under the [Work-centric Production Model](../architecture/work-centric-production-model.md),
ECF assembles context from attributable Work Assets. It does not create a
Project container or turn an Asset into Work Truth:

```text
Work + admitted Asset relationships
    -> ECF discovery / freshness / provenance / projection
    -> decision-scoped Engineering Context
```

## Decision Context v0.1 consumption

The versioned `watt-ecf-decision-context-v1` registry activates only for exact
Workspace Product UI and Alibaba ECS Delivery source boundaries. Documentation,
unrelated repository changes, and legacy tasks keep their existing admission
path. Product ownership is resolved from the Work and the Product's accepted
Managed Source before projecting any source. The current Git revision supplies
document and repository provenance; Work Reality comes from persisted Work.

The gated path is Work/Steering Reality → canonical `ecf.assemble_context` →
`READY` → Task Contract → Production. Missing, conflicting, or stale context
stops formation. Protected Intent, Invariant, Constraint, and Decision sources
enter typed Task obligations with exact source revision and ECF fingerprint.
The Context Orchestrator remains Watt-owned and cannot trim required protected
content to meet its budget.

The same package is recalculated before execution preparation and again before
dispatch. A changed fingerprint stops the old task with
`DECISION_CONTEXT_CHANGED`; a material Steering replan forms a fresh Task
Contract. An unchanged Executor retry retains its Task identity.

Verification evidence carries the package fingerprint and every obligation.
Only a passing exact Node test target is marked as mechanically covered;
other obligations remain `UNVERIFIED`. Guardian receives the typed lineage and
blocks a readiness claim that lacks Verification or an exact Guardian effect.
Guardian does not decide ECF completeness, and ECF does not decide assurance.

Milestone closure context readiness uses the ECF closure contract and only
persisted PASS Verification records from the same Product. `READY` means only
that Governance may evaluate closure; it never declares the Product closed.
Session Bootstrap has a registered ECF contract but no Watt runtime handoff
consumer yet, so session summaries do not become governed decision sources.

The independent runtime mounts ECF and Guardian checkouts. In `REQUIRED` mode,
Watt startup validates canonical ECF v0.1 and the owner Reality runtime.

## Governed Execution Context Boundary

The [SPG Lite Runtime Implementation Contract](../architecture/spg-lite-runtime-implementation-contract.md)
continues to govern execution context. ECF v0.1 adds a prior Decision Context
gate for registered decisions; it does not replace Watt's Context Orchestrator.

Context Packages may rely on admitted, versioned, traceable Engineering
Artifacts, Work Asset references, Contracts, facts, constraints, and Baseline
references as execution Authority. Raw conversation may be preserved as
provenance, audit evidence, or interaction history, but it must not be inserted
as task Authority or become a direct execution dependency.

Every Execution Attempt must remain traceable to the exact governed Context Package used.
