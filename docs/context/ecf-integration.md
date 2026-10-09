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
The initial policy applies to Watt's exact canonical source remote and an
exact Product owner of that managed source. It does not claim to protect
arbitrary customer repositories with similar file names.

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

### First Managed Greenfield production

The `MANAGED_PRODUCT_WEB_UI` consumer has a bounded first-production seam.
It is selected only for an exact Gitea Work source at Product source version 0,
without an imported origin, with an admitted greenfield IRK Production Intent
and an attributable immutable Work Reality / Governance revision. Existing
repository-owned Product UI context continues to use `PRODUCT_UI_CHANGE`.

The independent ECF v0.1 owner provides `MANAGED_GREENFIELD_PRODUCTION`:
Product Intent, Repository Reality and Work Reality remain mandatory.
Invariant, Approved Decision and approved Work restrictions are applicable
only where actual admitted owner facts establish them. The request may promote
registered optional classes to required; it cannot remove a base requirement.
ECF still owns completeness, source selection, conflicts and fingerprinting.

Product Intent is projected from the admitted IRK goal and Work Reality, with
exact Product/Work, semantic fingerprint, Work revision and Governance provenance.
There is no duplicate Product Intent table or README bootstrap. Ordinary Work
restrictions stay constraints. Only an explicitly Human-declared, IRK-typed
`CONSTRAINT` with subject `product_invariant`, present in admitted Work constraints,
enters Product Invariant. A real Human product choice is a `FACT` with subject
`approved_product_decision`; a production request is never a product approval.
Unresolved reserved decisions remain missing required context and fail closed.

Absence of a non-applicable invariant or decision is recorded as non-blocking,
not as a fabricated record. Available applicable records become protected Task
obligations. Every formation and pre-execution check rereads current owner facts;
changed source, intent, constraint or decision changes the package fingerprint
and fences the old Task. Previous incomplete packages and Quality Runs remain
historical evidence. Guardian, Verification and Human Acceptance are unchanged.

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

Owner dependency for this closure: ECF `codex/managed-greenfield-context-closure-v1`,
revision `5aa4f8833c359c15bd059eda5972aa3915bcc18c`
(tree `878d39d9c259272bb05f2e02bdf9d60c22fad460`). The ECS owner export must
match this committed revision; its previous export remains preserved.

### C1 managed API compatibility boundary

Nominal Decision Context `VERSION = "0.1"` is not sufficient for managed
production compatibility. The actual Watt gateway requires the managed
DecisionType, the typed `required_context_classes` Request argument, and the
registered contract's unchanged base requirements and explicit applicability.
It rejects a missing or incompatible capability with
`ECF_MANAGED_CONTRACT_INCOMPATIBLE` before source assembly; it never falls back
to `PRODUCT_UI_CHANGE` for a supplied managed context. Existing repository
context, completeness, authority and freshness checks remain in force.

The selected Owner combination for this C1 qualification uses ECF commit
`5aa4f8833c359c15bd059eda5972aa3915bcc18c`, tree
`878d39d9c259272bb05f2e02bdf9d60c22fad460`. ECF current main
`c6b568d006022e39b95daebedfecfb55e562ebe5` lacks that managed enum and Request
field despite the same nominal version; managed consumption is unsupported.
Its existing repository contracts remain separate valid interfaces. This
capability check does not fabricate an Owner revision, rewrite historical
Source Identity, or qualify a new application image or real production Work.
Exact application/test identities and results belong to the C1 qualification
receipt; no ECF source or context orchestrator is changed by this repair.