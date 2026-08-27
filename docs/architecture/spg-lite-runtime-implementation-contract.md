# SPG Lite Runtime Implementation Contract

## 1. Purpose, authority, and interpretation

This document is the authoritative **SPG Lite Runtime — Implementation Contract / Runtime MVP Design** under Architecture Baseline **v0.1**. It admits the approved I1–I4 design conclusions into Repository Source of Truth.

It refines, without replacing:

- [System Architecture Baseline v0.1](system-architecture-baseline-v0.1.md);
- [SPG Lite Domain and Contract Baseline](spg-lite-domain-contract-baseline.md);
- [Runtime Architecture Final Closure and Readiness](spg-runtime-architecture-readiness.md);
- [A. State Foundation](spg-state-foundation.md);
- [B. Reconciliation & Recovery](spg-reconciliation-recovery.md);
- [C. Completion & Trust](spg-completion-trust.md);
- [D. Side-effect Governance](spg-side-effect-governance.md).
- [FVS-1 Governed Documentation Production Loop Contract](spg-fvs-1-implementation-contract.md) subsequently supplies the controlled slice-specific physical and executable contract without replacing this Runtime-level contract.

The statements in this document are classified as:

| Classification | Meaning |
| --- | --- |
| Confirmed Implementation Contract | A stable logical responsibility, input/output, identity, authority, or boundary that implementation must preserve |
| Confirmed MVP Runtime Semantic | An approved Runtime meaning or invariant; not necessarily a dedicated physical entity |
| Implementation Guidance | A permitted direction that keeps the first implementation small without selecting a final physical design |
| Deferred Capability | Explicitly outside the first controlled implementation unless separately approved |
| Physical Implementation Choice — scoped | Platform/general choices remain unfrozen; an admitted controlled slice may select bounded technology without creating a platform-wide mandate |

No production code, schema, API, test, CI, infrastructure, or specific implementation slice is created or authorized by this contract-admission task.

## 2. Design closure and implementation governance status

| Design item | Status |
| --- | --- |
| I1. Minimal Runtime Contract & Domain Spine | **CLOSED** |
| I2. State Transition & Persistence Design | **CLOSED** |
| I3. Capability Interfaces & End-to-End MVP Loop | **CLOSED** |
| I4. Coding Readiness Closure | **PASSED** |
| Implementation Contract / Runtime MVP Design | **CLOSED** |
| Coding Readiness | **PASS** |
| Implementation Governance Status | **AUTHORIZED FOR CONTROLLED IMPLEMENTATION** |

Coding Readiness PASS means the approved architecture and implementation contracts are sufficiently stable to allow controlled, repository-grounded implementation slices.

It does not mean:

- generate the complete MVP at once;
- bypass Reality Check or Human Governance;
- abandon staged implementation;
- implement deferred capabilities;
- freeze future architecture permanently.

```text
Architecture permits implementation
+
each implementation slice remains explicitly authorized
+
implementation remains Reality-driven
+
each slice is verified before expansion
```

> Ready for implementation does not mean ready for uncontrolled bulk generation.

This Runtime-level document did not itself authorize implementation slices. F3-D subsequently closed; explicit bounded tasks authorized S1-A and then S1-B without authorizing the Runtime domain lifecycle or later integrations.

## 3. Implementation reality evolution

The repository Reality Check established:

```text
docs/
    authoritative Markdown Source of Truth

src/
    exists but is empty / placeholder
```

Current implementation reality remains:

| Area | Reality |
| --- | --- |
| SPG Runtime code | S1-A and S1-B CLOSED / PASS; Runtime lifecycle NOT IMPLEMENTED |
| Runtime language/framework | Python 3.13.15 local validation; Modular Monolith foundation IMPLEMENTED; not a platform-wide mandate |
| Database | Real PostgreSQL 17.6 development/test path and non-destructive connectivity check IMPLEMENTED; no Runtime schema |
| ORM | SQLAlchemy 2.x engine/session, explicit Unit of Work, and optimistic update primitive IMPLEMENTED; no Runtime models/repositories |
| Migration framework | Alembic environment IMPLEMENTED and load/connect validation PASS; no Runtime revisions |
| API/CLI | CLI-first foundation IMPLEMENTED; no HTTP/Web API |
| Executor Adapter | NOT IMPLEMENTED |
| Context Assembly | NOT IMPLEMENTED |
| Verification Provider | NOT IMPLEMENTED |
| Tests | 5 S1-A tests PASS; 19 total tests PASS, including DB-01–DB-06 and Alembic against real PostgreSQL |
| CI | NOT IMPLEMENTED |
| Deployment | NOT IMPLEMENTED |

This is **S1-B Persistent Runtime Foundation CLOSED / PASS Reality**. It proves local persistence mechanics only and is not permission to invent the unimplemented Runtime lifecycle.

## 4. I1 — Minimal Runtime Contract and domain spine

The first SPG Lite implementation must preserve the logical semantics of:

1. Production Run;
2. Production Plan / Revision;
3. Production Work Unit;
4. Execution Attempt;
5. Work Product Reference;
6. Production Snapshot / Baseline Candidate;
7. Verification Record;
8. Governance Record;
9. Production Issue;
10. External Effect Record;
11. Transition History as a cross-cutting record.

These are implementation-contract concepts, not a requirement for one table, service, class hierarchy, or microservice per concept.

> Preserve semantic separability before physical separability.

## 5. Production Run and Production Horizon

### Production Run

> A Production Run is a governed production instance that advances an admitted Production Intent toward a defined Target Outcome.

Its logical contract preserves references to:

- production objective;
- admitted Production Intent;
- source Trusted Production Baseline;
- target outcome / Production Horizon;
- current Plan Revision;
- lifecycle condition;
- relevant Authority and Context references.

No physical schema is frozen.

### Production Horizon / Target Outcome

A Production Run has an authorized stopping boundary describing how far production is intended to advance. Conceptual horizons may include Analysis, Design, Documentation, Implementation, or Delivery, but these are not frozen physical enums.

> Production Planner must not extend a Production Run beyond its authorized Production Horizon merely because downstream work is technically possible.

Production Horizon is both a completion boundary and an Authority boundary. A Run authorized to produce a migration plan may complete with a Runbook, Risk Analysis, and required review; it must not automatically execute the migration.

## 6. Artifact-agnostic production guardrail

> SPG Lite Runtime is artifact-agnostic and must not assume Code Artifact as the universal production terminal.

A Production Run may legitimately terminate at governed Analysis, Design, Documentation, Implementation, or another explicitly admitted software-production Artifact outcome.

No Runtime Contract may require Code Artifact as a universal condition for:

- PWU Satisfaction;
- Plan Completion;
- Production Run Completion;
- Baseline Candidate formation;
- Trusted Production Baseline formation.

## 7. Production Plan / Revision

Production Plan / Revision represents the currently governed production path. Its contract preserves the Production Run, revision identity, source Trusted Baseline, production goal, PWUs, dependencies, Completion obligations, and current/revision status.

Material Plan change creates a new Revision:

```text
P12/R1
↓ replan
P12/R2
```

R1 remains historical fact and is not overwritten. At most one current active Plan Revision exists per Production Run.

## 8. Production Work Unit and Completion Contract

### Production Work Unit

> Production Work Unit is a generic governed production activity, not a Coding Task abstraction.

A PWU may perform analysis, architecture/design, documentation, Context preparation, implementation, Verification, or other admitted software-production work.

Its logical Contract preserves identity, objective / Intent, Plan Revision, source Baseline, dependencies, Context references, input obligations, output obligations, Completion Contract, and current governed condition.

### Completion Contract

Completion Contract is a first-class semantic Contract and may initially be physically embedded within PWU or Plan representation. It preserves:

- Required Outputs;
- Required Verification;
- Required Conditions;
- Blocking Conditions.

```text
Produced
!=
Satisfied
```

Existence of output does not establish Satisfaction.

## 9. Execution Attempt, generation, and fencing

### Execution Attempt

Execution Attempt is independently identifiable from PWU. It records one physical/logical execution attempt and preserves Attempt identity, PWU, Executor / Provider, Plan Revision, source Baseline, Context identity, execution generation, timing, workspace/provider reference, reported result, and retry/resume lineage.

Retry creates a new Attempt. Historical Attempt identity is immutable.

```text
Attempt SUCCESS
!=
PWU PRODUCED
!=
PWU SATISFIED
```

### Execution generation and fencing

A PWU preserves a monotonically advancing current execution generation. An Attempt is bound to one generation. At most one Attempt generation holds current execution Authority for a PWU by default in SPG Lite.

When an older generation returns after a newer generation becomes authoritative, Runtime preserves the late result as historical fact but prevents it from mutating current authoritative production state.

Speculative parallel execution is not part of MVP.

## 10. Work Product Reference and Artifact types

SPG governs Work Product identity, references, and lineage; it is not the universal Artifact content repository.

A Work Product Reference preserves Artifact identity, type, producer PWU, producer Attempt, content/revision identity, location/reference, and Manifest role. Artifact content may live in Git, filesystem, document store, Artifact store, or another Provider. Historical Work Product identity is not silently rewritten.

MVP must be able to represent artifact-agnostic conceptual categories such as Code, Design, Documentation, Analysis, Context, Verification, and Other without building a large inheritance hierarchy or ontology.

## 11. Production Snapshot, Baseline Candidate, and Trusted Baseline

Baseline Candidate is an exact proposed production-reality snapshot. Trusted Production Baseline is accepted authoritative production reality. They remain semantically distinct even if implementation shares one physical snapshot representation.

```text
Candidate
!=
Trusted Baseline
```

A sealed Candidate is materially immutable. Changed contents create a new Candidate revision rather than mutating the prior revision.

> Trusted Production Baseline is an accepted software-production-reality snapshot, not a wrapper around the latest Git commit.

A Trusted Baseline may contain Decision, Design, Documentation, Context / Contract, Code, Verification, and Governance references. A non-code Production Run may legally produce a Trusted Baseline containing no Code Artifact. Git revision is one possible reality reference, not the universal Baseline definition.

## 12. Verification Record and Governance Record

### Verification Record

A thin SPG-facing Verification representation preserves subject and revision, Verification requirement, method/provider, result, scope, basis, provenance, supporting Artifact/Evidence references, and freshness/applicability.

```text
Verification Result
!=
Verification Freshness
```

A historical PASS may later have INVALIDATED freshness. Historical Verification facts are not rewritten. Full Guardian Evidence Ontology remains deferred.

### Governance Record

A lightweight shared Governance Record may initially represent Intent Admission, Risk Acceptance, Exception, Candidate Authorization, and Effect Authorization while preserving their semantic distinctions.

It preserves Authority/actor, subject, decision, scope, basis, revision, rationale, and timestamp. Governance history is append-oriented; later decisions supersede or change applicability rather than rewriting prior decisions.

> Authority Changes Permission, Not Facts.

## 13. Production Issue and External Effect Record

### Production Issue

Production Issue is a lightweight first-class Runtime representation of a material production problem or Divergence requiring governance. Examples include stale work, missing expected Artifact, task-identity mismatch, uncertain Attempt state, Candidate invalidation, and External Reality Divergence.

Its logical Contract preserves classification, subject, observed facts, impact, blocking relevance, recovery disposition, resolution reference, and lifecycle.

> State describes governance condition; facts, Contracts, and Issues explain why.

Production Issue remains distinct from Guardian Finding.

### External Effect Record

A thin External Effect representation may physically consolidate Side-effect Intent, Permit reference, stable Effect Operation identity, target, environment, desired state, source PWU/Attempt, Candidate/Artifact reference, execution generation, lifecycle, observed external state, compensation relationship, and correlation while preserving their logical distinctions.

External Effect is optional, not a universal Production Run terminal requirement. Side-effect Gateway, Saga, Compensation Engine, and Effect Group Engine remain deferred.

## 14. Transition History and I2 persistence direction

SPG Lite uses:

> Materialized authoritative current state plus append-only Transition History.

Event Sourcing is not required.

Transition History preserves entity, prior condition, new condition, reason, actor/Runtime Authority, timestamp, and related facts/references. Important SPG-owned state mutation and its Transition History append are locally atomic.

The approved MVP persistence direction is:

```text
Relational transactional persistence
+
Materialized current state
+
Revisioned / append-oriented historical records
+
Transition History
+
Optimistic version checks
+
Execution generation
+
Local transactions
```

This remains Runtime-level architecture guidance. The later [FVS-1 Contract](spg-fvs-1-implementation-contract.md) selects PostgreSQL, SQLAlchemy 2.x, Alembic, and CLI-first for that controlled slice only. Physical schema and API remain unfrozen, and the selection is not a platform-wide mandate.

### Optimistic concurrency

Authoritative mutable records use version-aware transitions. An expected/current version mismatch rejects the transition and requires reload or reconciliation. Distributed locks are not required for MVP.

### Local transition atomicity

Where applicable, Runtime validates current state/version and transition invariants, mutates local authoritative state, increments version, and appends Transition History in one local transaction. This does not claim global external-system atomicity.

## 15. Runtime transition Authority and minimal lifecycle guidance

> Production Governance Runtime is the sole logical Authority for governed Runtime lifecycle transitions.

Planner, Executor, Guardian, Human UI, and Context providers contribute proposals, facts, Evidence, Authority Decisions, and observations. They do not bypass Runtime transition governance. Runtime does not own all production truth.

> No Actor Owns Production Truth Alone.

Minimal logical lifecycle directions, not frozen database enums:

- Production Run: OPEN, BLOCKED, COMPLETED, CANCELLED;
- Plan Revision: PROPOSED, ACTIVE, SUPERSEDED, COMPLETED;
- PWU: PROPOSED, READY, EXECUTING, PRODUCED, SATISFIED, BLOCKED, CANCELLED, SUPERSEDED;
- Execution Attempt: CREATED, ACTIVE, UNKNOWN, SUCCEEDED, FAILED, FENCED, CANCELLED.

Planning, execution, and Verification UI phases should normally be projections rather than an expanded Production Run state machine. `UNKNOWN` is not `FAILED`.

## 16. Commit semantics

Current Trusted Baseline advances only through governed Runtime Commit using expected-source / CAS-like semantics.

```text
Candidate source Baseline = B42
Current Trusted Baseline = B42
→ Commit may proceed

Candidate source Baseline = B42
Current Trusted Baseline = B43
→ Commit rejected
→ revalidate / reconcile
```

## 17. I3 capability interfaces

SPG consumes Capability Contracts rather than Provider identities. External/pluggable boundaries include:

- Decision / Production Intent boundary;
- Context Capability;
- Executor Capability;
- Verification / Guardian Capability;
- External Effect Capability;
- Repository / Artifact Infrastructure Adapter.

Production Planner remains a core SPG capability.

The [Runtime Profile, Provider Placement, and Containerized Deployment](runtime-profile-provider-deployment.md) clarification binds these logical capabilities to configured providers, models, adapters, and deployment placements without changing their contracts or Runtime semantics. Provider/model identity is configuration, not domain logic.

### Decision / Production Intent boundary

SPG consumes admitted Production Intent and does not depend directly on YiJue Product. Human Direct Intent and future Decision Intelligence Provider output pass through the same logical admission boundary.

Production Intent preserves goal, scope, constraints, Target Outcome / Production Horizon, source/reference Context, and Authority/admission.

### Production Planner

Production Planner consumes admitted Production Intent, Trusted Baseline, Context Package / Projection, constraints, and available execution capability. It produces structured Plan Revisions, PWUs, dependencies, Output Obligations, and Completion Contracts.

Conversational advice alone is not Runtime Plan state. Planner prompt/model implementation remains a physical choice.

## 18. Context Assembly Lite and Conversation-to-Contract

### Context Assembly Lite

Full ECF is deferred. Context Assembly Lite may consume admitted engineering Artifacts such as `AI_context.md`, approved architecture/documents, repository snapshot, approved Decision Artifacts, and approved constraints/Contracts.

A Context Package preserves Context identity, revision/content identity, included governed sources, and provenance. Every Execution Attempt must be able to answer which governed Context Package it executed against.

### Conversation-to-Contract Principle

> Raw conversation content is source material for extracting candidate engineering information, but it is never an authoritative execution basis.

Before conversational information influences execution, governed processing must transform it into an admitted, versioned, traceable Production Intent, PWU/Task Contract, approved Decision Artifact, approved Design/Specification, Constraint Set, Context Package, Verification Requirement, Trusted Baseline, or other admitted Engineering Artifact.

```text
Conversation
↓ extraction / refinement
Governed admission
↓
Artifact / Contract
↓
Context Package
↓
Execution
```

The following dependency is prohibited:

```text
Raw Conversation
────────────→ Executor
```

Conversation may remain provenance for an admitted Artifact. Conversation provenance is allowed; raw-conversation execution Authority is forbidden. A PWU may depend on an admitted Decision derived from a conversation, but it must not depend directly on a raw chat message.

Context Assembly / future ECF must not inject raw conversation excerpts as task Authority. Conversation may remain available for audit, provenance, Human review, later extraction, and interaction history.

Logical separation remains:

```text
Conversation / Interaction Store → what was said
Governed Engineering Artifacts   → what was admitted
Production State                 → what is authoritative
Context Package                  → what execution may rely upon
```

Conversation data does not belong in `AI_context.md` merely because it exists. No Conversation database or physical schema is defined here.

## 19. Executor, observation, Verification, and Human Governance

### Executor Contract

Executor Provider Contract remains provider-neutral. Codex is the initial likely Provider, not the Runtime abstraction. The Contract permits prepare, execute, observe, resume, and cancel/fence semantics, although MVP may implement a thinner subset initially.

Executor receives governed Attempt identity, generation, PWU objective, Context Package, Output Obligations, constraints, workspace/repository target, and allowed operations. It reports provider execution state, outcome, workspace/provider reference, diagnostics, and Artifact candidates.

Executor does not own PWU Satisfaction, Verification truth, Trusted Completion, Baseline Commit, or unrestricted external-effect Authority.

The Contract is artifact-agnostic and must not use `changed_code_files` as the universal Work Product concept.

### Repository / Artifact observation

```text
Expected Work
!=
Observed Work
!=
Executor Self-Reported Completion
```

Git/filesystem observation independently determines changed paths, Artifact existence, content identity, revision, and actual delta.

```text
Executor Report
↓
Repository / Artifact Observation
↓
Work Product Candidate
↓
Output Obligation Evaluation
↓
Admitted Work Product
```

### Verification Capability

A real Verification boundary is required in MVP; full Guardian is not. Verification Request/Result preserves exact subject and revision, obligation, scope, method/provider, basis, result, Evidence/Artifact references, and diagnostics.

MVP Verification may use targeted tests and repository checks for code, or required-Artifact, required-section, Markdown/link, constraint-consistency, and structured design review for documentation/design.

### Human Governance

Human interaction occurs at Authority points such as Intent admission, material Intent change, material replan, required Candidate authorization, risk/Exception, and high-risk External Effect authorization. Human-in-the-loop does not mean approval after every PWU.

## 20. Asynchronous Provider and failure boundary

Capability Contracts permit long-running/asynchronous Provider execution and preserve observe-style semantics. MVP may use a background worker, polling, or Provider execution reference; Kafka, Temporal, and a distributed workflow engine are not required.

Executor, Verification Provider, Context Provider, or External Effect Adapter failure must become Attempt state, Production Issue, recovery/retry semantics, or blocking state rather than uncontrolled Runtime-process collapse.

### FVS Runtime Profile and packaging clarification

The first FVS must preserve a provider-neutral Capability Contract, an Executor adapter boundary, and a Runtime/Profile configuration boundary. It may use one real provider path; multiple providers and simultaneous Global/Mainland profiles are not prerequisites.

Initial validation is local-first. Container-ready packaging, with Docker and Docker Compose as the preferred FVS/local deployment direction, is an infrastructure concern and does not redefine Production Run, PWU, Attempt, Completion, Governance, Commit, or Trusted Baseline semantics. No Dockerfile, Compose file, Provider Registry, adapter, provider integration, region selection, or deployment artifact is authorized by this documentation clarification.

## 21. End-to-End MVP production loop

```text
Admitted Production Intent
↓
Production Run
↓
Production Planner
↓
Production Plan Revision
↓
PWUs
↓
Context Assembly Lite
↓
Execution Attempt
↓
Real Executor
↓
Independent Repository / Artifact Observation
↓
Work Product References
↓
Completion Contract Evaluation
↓
Real Verification
↓
Baseline Candidate
↓
Governance / Authorization
↓
Runtime Commit
↓
Trusted Production Baseline
```

Effectful Runs may optionally continue to External Effect, Observed External Reality, and Convergence/Reconciliation. Artifact-only Runs may complete after governed Artifact, Verification, Candidate, Commit, and Trusted Baseline formation. Deployment is not universally required.

## 22. Controlled dogfood progression

### First dogfood: Governed Documentation Change

The documentation-only repository makes a governed documentation change the preferred first vertical slice. Its Completion Contract must name exact required architecture/documentation and related state/Context Artifacts.

When Executor reports SUCCESS but Runtime observes that a required Artifact is missing, PWU may not become PRODUCED or SATISFIED; Runtime records a Production Issue and leaves Trusted Baseline unchanged.

The real Codex wrong-task / false-success incident remains a future regression benchmark candidate. No dogfood implementation or test is created here.

### Second dogfood direction

After the documentation loop is validated, the same artifact-agnostic Runtime may govern a small code-change Run requiring Code, Test, and Documentation Artifacts. It is not implemented or authorized here.

Early future failure injection should cover missing expected Artifact, unrelated task result, lost Attempt observation, late stale generation, Baseline advancement, stale Verification, duplicate Attempt, and Runtime crash around transition. These tests are not created here.

## 23. I4 first-wave critical Runtime invariants

The first implementation wave must preserve:

1. Executor SUCCESS does not directly complete a PWU.
2. Required Artifact must be independently observed.
3. PWU PRODUCED and SATISFIED remain distinct.
4. Attempt identity is immutable and Retry creates a new Attempt.
5. Stale Attempt generation cannot mutate current authoritative state.
6. Plan Revision / Source Baseline binding is preserved.
7. Sealed Candidate cannot silently change material contents.
8. Current Trusted Baseline advances only through Runtime Commit.
9. Commit validates expected Source Baseline.
10. Verification result binds an exact subject/basis.
11. Material SPG-owned state transition and Transition History append are locally atomic.
12. Code Artifact is not universally required for completion.

These are the first implementation wave's safety floor and do not replace the broader A/B/C/D invariants.

## 24. Repository Reality Finding and governance lesson

The Pre-Implementation Repository Reality Check found:

```text
Technical Architecture Blockers: 0
Governance / Source-of-Truth Blockers: 1
```

The blocker was that approved Implementation Contract / Runtime MVP Design and Coding Readiness conclusions had not been admitted into Repository Source of Truth. This admission closes that specific blocker after validation. History remains explicit; it is not rewritten to imply the gap never occurred.

> A conversationally agreed architecture conclusion is not sufficient execution Authority until it is transformed into a governed, versioned Source-of-Truth Artifact.

The Reality Check correctly followed Conversation-to-Contract, Contract Before Implementation, Source of Truth over Conversation History, and Facts Before Claims. This is governance evidence, not a failure of Codex.

## 25. Deferred scope

The following remain deferred and are not prerequisites for the first controlled implementation:

- full Guardian and full ECF;
- Event Sourcing and Graph DB;
- microservices and distributed locks;
- Saga, 2PC, and distributed transactions;
- Policy DSL, Trust Score, and full Evidence Ontology / Graph;
- Capability Marketplace and Autonomy Engine;
- Semantic Conflict Engine and independent Production State Platform;
- universal Side-effect Gateway;
- Compensation Engine and Effect Group Engine;
- full deployment platform and complex role-specific UI/workspaces;
- advanced multi-model routing;
- multiple real provider chains and automatic provider capability discovery;
- Provider Registry, provider-management UI, and residency Policy Engine;
- distributed/cross-region worker topology, Kubernetes, and autoscaling;
- generalized Production Pattern / Effect Protocol engine.

## 26. Architecture Baseline and closure

Architecture Baseline remains **v0.1**. This Contract is an implementation refinement under the existing architecture, not a replacement Baseline.

Authoritative state after admission:

```text
Runtime Architecture Refinement
    CLOSED
Runtime Architecture Readiness
    PASS

SPG Lite Runtime
Implementation Contract / Runtime MVP Design
    CLOSED

I1 Minimal Runtime Contract & Domain Spine
    CLOSED
I2 State Transition & Persistence Design
    CLOSED
I3 Capability Interfaces & End-to-End MVP Loop
    CLOSED
I4 Coding Readiness Closure
    PASSED

Coding Readiness
    PASS
Implementation Governance
    AUTHORIZED FOR CONTROLLED IMPLEMENTATION
```

The later [FVS-1 Contract](spg-fvs-1-implementation-contract.md) admits the reviewed slice-specific design without changing this Contract's closure:

```text
F1. Slice Goal & Governance Contract                   REVIEWED / ADMITTED
F2. Minimal Technical Foundation                       REVIEWED / ADMITTED
F3-A. Runtime Slice Boundary & Physical Spine          REVIEWED / ADMITTED
F3-B. Repository Integration / Commit Semantics        REVIEWED / ADMITTED
F3-C. Executable Test & Failure Contract               REVIEWED / ADMITTED
F3-D. FVS Coding Authorization Closure                 CLOSED — FVS-1 AUTHORIZED FOR CONTROLLED IMPLEMENTATION
```

S1-A Runtime Project Foundation and S1-B Persistent Runtime Foundation are CLOSED / PASS. S1-C Bootstrap Baseline & Minimal Durable Runtime Spine is NEXT — NOT STARTED. The next governed step is Architecture Lead confirmation of S1-B SOT closure followed by explicit S1-C authorization; this closure does not begin S1-C.
