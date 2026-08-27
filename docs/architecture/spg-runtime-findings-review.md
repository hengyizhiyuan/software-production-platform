# SPG Runtime Flow Findings and Failure-Mode Review

- **Record date:** 2026-08-26
- **Purpose:** Frozen findings record and A/B/C/D plus Final Readiness closure synchronization
- **Confirmed State Foundation semantics:** [State Foundation Closure](spg-state-foundation.md)
- **Confirmed recovery semantics:** [Reconciliation & Recovery Closure](spg-reconciliation-recovery.md)
- **Future verification only:** [Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md)
- **Governing architecture:** [Architecture Baseline v0.1](system-architecture-baseline-v0.1.md)
- **Domain and contract baseline:** [SPG Lite baseline](spg-lite-domain-contract-baseline.md)
- **Final closure:** [Runtime Architecture Final Closure and Readiness](spg-runtime-architecture-readiness.md)
- **Architecture Baseline:** remains v0.1; this record is not a new baseline

## 1. Interpretation and Evidence Boundary

This record preserves the user-reported Runtime Flow Tabletop Exercise and Runtime Failure-Mode Discovery and the supplied A/B/C/D closure conclusions. A, B, C, and D are CLOSED; Final Closure / Architecture Readiness Review is PASSED; Runtime Architecture Refinement is CLOSED; Runtime Architecture Readiness is PASS. It does not claim newly executed Runtime tests or implemented capabilities.

| Label | Meaning in this review |
|---|---|
| Confirmed Requirement | A production-runtime problem or required behavior identified by the review; not a selected implementation or a new MVP feature |
| Confirmed Architecture Semantics | A logical concept, responsibility, or invariant accepted by A/B/C closure; not a schema, deployed service, or implementation claim |
| Architecture Principle | A governing constraint used to assess future designs |
| Candidate Mechanism | A possible concept or mechanism pending formal confirmation; not a frozen domain object, schema, or implemented capability |
| Architecture Hypothesis | A proposed responsibility decomposition to validate during refinement; not final architecture |
| Future Design Question | An unresolved question for the bounded refinement agenda; not an invitation to expand discovery |
| Future Verification Requirement | An eventual executable verification obligation; not a test implemented here |
| Benchmark Candidate | A proposed future scenario, including incident-derived regressions; not an executed benchmark |

Candidate fields, event names, states, and pipelines below are conceptual illustrations, not APIs, persistence schemas, or final transition implementations. Existing capability ownership remains authoritative. A confirms Execution Attempt, State Transition Journal, Baseline Candidate, state / Commit semantics, and logical responsibility decomposition. B confirms Execution Lease, fencing, isolation, divergence/validity distinctions, Revalidate / Reconcile / Replan, Recovery Barrier, and idempotent recovery. Unpromoted labeled candidates remain unresolved. Concrete implementation mechanisms are not selected.

## 2. Review Closure and Current State

The reported prior work includes Responsibility Boundary Review, PWU Lifecycle Design, Autonomy Boundary Design, Human Governor Interaction Model, MVP Implementation Boundary, Domain Model Review, and Contract Boundary Review.

| Workflow item | Status |
|---|---|
| Runtime Flow Tabletop Exercise | CLOSED |
| Runtime Failure-Mode Discovery | CLOSED |
| Issue Discovery Scope | FROZEN |
| Runtime Architecture Refinement | CLOSED |
| A. State Foundation | CLOSED |
| A1. Core State Semantics | CLOSED — reviewed |
| A2. Transition & Commit Semantics | CLOSED — reviewed |
| A3. State Foundation Closure Review | PASSED |
| B. Reconciliation & Recovery | CLOSED |
| B1. Divergence & Recovery Semantics | CLOSED |
| B2. Execution Recovery | CLOSED |
| B3. Reconciliation & Replanning | CLOSED |
| B4. Recovery Closure | PASSED |
| C. Completion & Trust | CLOSED |
| C1. Completion Semantics | CLOSED — reviewed |
| C2. Verification & Trust Freshness | CLOSED — reviewed |
| C3. Acceptance & Trusted Completion | CLOSED — reviewed |
| C4. Completion & Trust Closure | PASSED |
| D. Side-effect Governance | CLOSED |
| D1. Side-effect Semantics & Boundary | CLOSED — reviewed |
| D2. Side-effect Authority & Execution Safety | CLOSED — reviewed |
| D3. Compensation & External Reality | CLOSED — reviewed |
| D4. Side-effect Governance Closure | PASSED |
| Final Closure / Architecture Readiness Review | PASSED |
| Runtime Architecture Readiness | PASS |
| SPG Lite Runtime — Implementation Contract / Runtime MVP Design | CLOSED |
| Coding Readiness | PASS |
| Architecture Lead Reality Review | COMPLETED |
| F1. Slice Goal & Governance Contract | REVIEWED / ADMITTED |
| F2. Minimal Technical Foundation | REVIEWED / ADMITTED |
| F3-A. Runtime Slice Boundary & Physical Spine | REVIEWED / ADMITTED |
| F3-B. Repository Integration / Commit Semantics | REVIEWED / ADMITTED |
| F3-C. Executable Test & Failure Contract | REVIEWED / ADMITTED |
| F3-D. FVS Coding Authorization Closure | CLOSED — FVS-1 AUTHORIZED FOR CONTROLLED IMPLEMENTATION |
| S1-A. Runtime Project Foundation | CLOSED / PASS |
| S1-B. Persistent Runtime Foundation | CLOSED / PASS |
| S1-C. Bootstrap Baseline & Minimal Durable Runtime Spine | CLOSED / PASS |

### Validated logical flow

```text
Human Intent
    ↓
Intent Classification / Governance
    ↓
Decision Intelligence
    ↓
Approved Decision Artifact
    ↓
Production Planner
    ↓
Production Plan
    ↓
Production Work Units
    ↓
Context Assembly
    ↓
Execution
    ↓
Work Product Artifacts
    ↓
Verification
    ↓
PWU obligations satisfied (detailed semantics remain for C)
    ↓
Exact Baseline Candidate / Commit Eligibility
    ↓
Human / Policy Final Acceptance (Commit Authorization)
    ↓
Governed Commit
    ↓
Trusted Production Baseline
```

This logical flow is clarified by the State Foundation closure: Final Acceptance targets an exact Baseline Candidate rather than each PWU by default. It is not an implementation pipeline, API sequence, or claim that providers are integrated. Decision Intelligence denotes the capability, not the YiJue product. Human Authority still governs admission of the Approved Decision Artifact.

The exercise confirmed architectural support for non-coding PWUs, Decision Intelligence → SPG separation, SPG → Executor separation, Verification → Acceptance separation, Human Authority Points rather than step-by-step approval, context preparation as governed production activity, artifact lineage, and replanning when production reality invalidates a plan.

## 3. Frozen Runtime Refinement Scope

The discovery backlog contains exactly these 12 areas:

1. Design Artifact
2. Production Issue
3. Completion Contract
4. Baseline / Documentation Synchronization
5. Exception & Recovery
6. Integration Atomicity
7. Duplicate Execution / Concurrency
8. Staleness & Invalidation
9. Verification / Acceptance Freshness
10. External Side Effects & Compensation
11. Partial Output / Artifact Manifest
12. Execution Reproducibility & Permission Boundary

Cancellation / Supersession belongs under Exception & Recovery. Dependency Cycle / invalid dependency structure belongs under Production Plan Qualification, not an additional discovery area. Do not expand this list during refinement unless real new evidence requires reopening discovery.

## 4. Runtime Findings

### 4.1 Design Artifact

**Confirmed Requirement:** Design is an engineering production output in its own right. Semantic purpose must be distinguished from physical storage format; a Markdown Design Artifact is not merely generic documentation.

**Candidate Mechanism — domain-model refinement:**

```text
Production Artifact
├── Code Artifact
├── Design Artifact
├── Documentation Artifact
├── Context Artifact
├── Analysis Artifact
└── Verification Artifact
```

Design examples include Architecture Decision, Domain Model, Interface Contract, Migration Design, and Data Model Design. The candidate classification does not transfer their authority to SPG.

**Deferred taxonomy question:** Design Artifact is not added to the approved v0.1 or SPG Lite domain taxonomy. Revisit it only through explicit future architecture review supported by implementation or Reality Check evidence.

### 4.2 Production Issue

**Confirmed Requirement:** Runtime needs to explain why production cannot safely continue under the current plan or work-unit assumptions. Examples include insufficient context, unavailable dependency, executor failure, environment failure, design infeasibility, scope ambiguity, stale baseline, and execution conflict.

**Candidate Mechanism — representation:** Production Issue represents that production-control problem. The closed State Foundation includes production issues in Working Production State, without finalizing their detailed model or schema.

| Concept | Responsibility boundary |
|---|---|
| Production Issue | SPG production control, recovery, or replan |
| Guardian Finding | Guardian assurance, trust, or gate decision |

Possible responses include Retry, Resume, Rework, Replan, Block, Escalate, and Cancel. A production-control record does not replace, reinterpret, or take ownership of a Guardian Finding.

**Remaining Design Question:** Production Issue representation remains unresolved. B closes the logical recovery responses without merging production-control and Assurance Truth ownership or selecting an issue schema.

### 4.3 Completion Contract

**Confirmed Requirement:** Completion cannot be inferred from executor completion:

```text
Execution Finished ≠ PWU Produced ≠ Production Complete ≠ Outcome Achieved
```

**Confirmed C Contract Semantics:** [Completion & Trust closure](spg-completion-trust.md) confirms versioned PWU Completion Contract and Plan Completion Contract semantics. PWU Contracts contain Output Obligations, Verification Obligations, Required Conditions, and Blocking Conditions; Plan completion is governed by Plan-level obligations, not green task rows. No schema or API is specified.

### 4.4 Baseline / Documentation Synchronization

**Architecture Principle:** Engineering documentation/design and implementation reality participate in two-sided baseline synchronization. Documentation is not only an activity after code implementation.

Pre-execution authoritative engineering artifacts include Approved Decision Artifact, Architecture / Design Artifact, Interface Contract, Constraints, and Acceptance Criteria. They provide the governed basis for implementation.

After implementation and verification, reality reconciliation aligns actual implementation reality, design deviations, documentation changes, artifact lineage, runtime discoveries, and canonical engineering context.

```text
Authoritative Engineering Baseline
        ↓
Implementation
        ↓
Verification
        ↓
Reality Reconciliation
        ↓
New Engineering Baseline
```

**Confirmed Requirement:** Code or other work products that physically exist but have not completed required reconciliation/integration must not automatically become Trusted Production State.

**Confirmed Requirement:** Artifact lineage and production identity must be established before, or durably associated with, execution. They must not be reconstructed only after execution. This prevents orphan output whose origin, plan, context, or lifecycle is unknown. SPG coordinates lineage without taking ownership of generated content or canonical ECF context.

**Confirmed B/C Semantics:** Revalidation, reconciliation, and Plan Revision carry-forward preserve still-valid production work and domain ownership. The [C closure](spg-completion-trust.md) confirms Completion / admission qualification semantics; no documentation synchronization or Completion engine is implemented.

### 4.5 Exception & Recovery

**Confirmed Requirement:** The happy-path PWU lifecycle is insufficient. Runtime must eventually support explicit semantics for interruption, retry, resume, rework, replan, cancellation, supersession, rollback, compensation, and crash recovery.

**Architecture Principle — Logical Rollback Does Not Erase History:** A later successful attempt must not erase an earlier failed attempt:

```text
Attempt #1 — FAILED
Attempt #2 — PASS
```

**Confirmed State Foundation Requirement:** State Transition Journal durably records material governance transitions. Conceptual information may include subject, from state, to state, reason, actor, timestamp, evidence, and attempt reference. Historical facts are preserved; current-state fields may coexist with transition history. This is not a frozen schema or commitment to full Event Sourcing.

**Confirmed Requirement — Durable Recovery / Recovery Reconciliation:** SPG must recover from platform/runtime failure using persisted governance state. Examples of durable governance boundaries include decision admitted, plan revision persisted, PWUs persisted, execution attempt registered, artifact registered, verification recorded, acceptance recorded, and integration recorded. These are semantic recovery boundaries, not mandated database transactions.

After restart, the system must determine what definitely completed, what was in progress, what is safe to resume, what requires reconciliation, and what requires retry or escalation.

**Confirmed B Semantics — CLOSED:** Failure and Divergence differ. Classify before recover; use the lowest sufficient recovery scope; preserve maximum valid work. Resume preserves Attempt identity while Retry creates history. Recovery reconstructs knowledge before execution, uses a logical Recovery Barrier, preserves unreconciled reality, and is idempotent. Recovery completion restores coherent authority/state, not product completion. See all 20 principles in [B Closure](spg-reconciliation-recovery.md). The subsequent [D Closure](spg-side-effect-governance.md) confirms Rollback / Compensation semantics; no recovery or compensation engine, Event Sourcing, or implementation is introduced.

### 4.6 Integration Atomicity

**Confirmed Requirement:** A governed commit boundary is needed between working production results / Working Production State and Trusted Production State. Physical output alone must not cross that boundary.

**Confirmed Architecture Semantics:** Baseline Candidate replaces the historical working term Integration Candidate. It is an exact sealed snapshot proposed as the next Trusted Production Baseline, referencing source Baseline, Plan Revision, artifacts, verification / assurance, lineage, and relevant Human Decision Records.

Commit Eligibility, Commit Authorization, and Commit Execution are separate. Acceptance and Commit bind to the exact candidate revision; material changes require a new revision. Only successful Commit changes Current Trusted Baseline authority, after validating its expected source Baseline.

Failure before authoritative Baseline switching leaves the previous Baseline authoritative. Derived projection, cache, UI, or follow-up synchronization failure after switching does not undo the committed Baseline. See [State Foundation](spg-state-foundation.md) for the closed semantics.

**Confirmed B Boundary:** A stale Candidate may not commit directly; revalidation, reconciliation, supersession, or replanning is required. Reconciled content creates a new exact Candidate revision rather than mutating an accepted snapshot. Full Candidate lifecycle and implementation mechanisms remain unselected; these conclusions introduce neither distributed transactions nor Event Sourcing.

### 4.7 Duplicate Execution / Concurrency

**Confirmed Requirement:** Runtime must distinguish a PWU from each execution attempt and identify which baseline, context, and plan revision an attempt used. Duplicate or overlapping execution cannot be treated as one undifferentiated completion.

**Confirmed Architecture Semantics:** Execution Attempt is a concrete immutable historical fact bound to PWU, Plan Revision, source Baseline, relevant Context, Executor / Capability Provider, and result. Attempts do not overwrite one another. Expected source-Baseline validation is a confirmed Commit requirement.

**Confirmed B Semantics:** Execution Lease expresses temporary Attempt authority. Expiry does not prove physical execution stopped. Fencing / generation prevents late or zombie results from regaining authoritative rights, while retaining observed facts in history. Attempts require sufficient isolation; deliberate parallel Attempts must be an explicit strategy. No lease, lock, or storage implementation is selected.

**Confirmed B Safety Boundary:** Observation loss is not proof of failure. Never retry under unresolved execution uncertainty without safe fencing/isolation; an old Attempt must be terminated, fenced, isolated, or otherwise unable to corrupt current authoritative work. Infrastructure-specific realization remains future work.

### 4.8 Staleness & Invalidation

**Confirmed Requirement:** Work must be evaluated against the engineering reality from which it was created. A PWU or execution attempt may depend on Plan Revision, Baseline Revision, Context Revision, and Contract Revision. Materially relevant dependency changes may make old work stale.

**Confirmed B Semantics:** Production Validity Basis may include source Trusted Baseline, Plan / Context / Contract revisions, design assumptions, and dependency artifacts. VALID, REVALIDATION_REQUIRED, and STALE are distinct; STALE is not FAILED. A successful execution may be stale.

Baseline advancement triggers dependency-based impact evaluation, not automatic global invalidation. Work is directly invalidated, indirectly affected, or unaffected; valid work can carry forward. Revalidate / Reconcile / Replan are distinct, and replanning does not silently change the authorized destination. Cancelled means no longer required; Superseded means replaced while the objective remains relevant. Detailed impact algorithms are not frozen.

### 4.9 Verification / Acceptance Freshness

**Confirmed Requirement — Verification Freshness:** A PASS result is valid only for the production reality actually verified. Verification must be associated with its specific subject / engineering state; it is not permanently valid after relevant changes.

**Candidate Mechanism:** Evidence binding may include subject artifact, baseline, environment, verification scope, relevant dependencies, and timestamp. Detailed Guardian semantics remain outside SPG Lite's current implementation boundary.

**Confirmed Architecture Semantics — Acceptance Freshness:** Human / Policy Final Acceptance targets an exact sealed Baseline Candidate revision, not every PWU by default. Materially changing a sealed candidate creates a new revision; prior acceptance must not silently authorize it.

**Architecture Principle:** Human approval of one production snapshot must not authorize materially different later output.

**Confirmed C Semantics:** Verification PASS is contextual to an explicit Verification Basis. Evidence Quality and Freshness are distinct; relevant change may yield VALID, REVALIDATION_REQUIRED, or INVALIDATED logical conclusions. Baseline advancement triggers impact evaluation, not global invalidation. Human / Policy Acceptance is scoped to an exact Candidate and policy-driven. Guardian retains assurance truth; SPG governs Evidence use in transition eligibility.

### 4.10 External Side Effects & Compensation

**Confirmed Requirement:** Autonomy and recovery must account for effects beyond repository changes. Future PWUs may involve deployment, database migration, infrastructure mutation, external API calls, resource deletion, or publishing, with different reversibility characteristics.

**Confirmed D Semantics:** External Side Effects cross the disposable execution boundary. Logical classification considers repeatability, compensability / reversibility, durability, and blast radius. Side-effect Intent, scoped Permit / Authorization, and stable Effect Operation Identity remain distinct. Rollback differs from Compensation; Compensation is governed production that appends history.

Observed External Reality remains distinct from physical and Trusted Production Reality. Permit freshness, Attempt fencing at the external boundary, external preconditions, observation, reconciliation, and compensation govern safe effects. No deployment automation, compensation engine, schema, or authorization infrastructure is added to MVP. See [D Closure](spg-side-effect-governance.md).

### 4.11 Partial Output / Artifact Manifest

**Confirmed Requirement:** Executor completion alone cannot mark a PWU as Produced. All required output conditions must be satisfied; a PWU may require several outputs.

**Confirmed C Runtime Semantic:** Output Obligation Manifest (preferred term; earlier working term Artifact Manifest) describes REQUIRED, CONDITIONAL, and OPTIONAL production-output obligations. It is not a changed-file list. For example:

```text
Required Output
├── Code Artifact          REQUIRED
├── Test Artifact          REQUIRED
└── Migration Artifact     REQUIRED
```

These are illustrative output labels, not new approved taxonomy entries.

**Confirmed C Semantic:** Partial production preserves valid artifacts but does not satisfy a PWU while required obligations are missing. The Manifest is confirmed logically; DSL, schema, and physical representation remain deferred.

### 4.12 Execution Reproducibility & Permission Boundary

**Confirmed Requirement:** Every execution result must be traceable to the engineering environment in which it was produced. Governance authority must propagate to the execution boundary.

**Confirmed D Boundary:** External execution Intent and Context must be reproducibly inspectable, including Operation, target, parameters, Artifact / Candidate revision, production state, Authority, preconditions, Provider, and Operation Identity. Credential provenance may preserve reference, role, scope, and issuer, but never raw secrets. Physical execution need not be universally reproducible.

Future bounded Execution Request semantics may include allowed repository scope, allowed tools, allowed external side effects, credential boundary, and destructive-operation constraints.

**Deferred implementation-contract question:** Choose the minimum representation that preserves the confirmed reproducibility and Authority-propagation semantics. This review does not define an API or build a security platform.

## 5. Non-Normative Architecture Note: React Fiber Analogy

This is an analogy discussed in the review, not a dependency, implementation mechanism, or normative design source.

| React Fiber analogy | SPG concept |
|---|---|
| Current Tree | Trusted Production Baseline |
| Work-in-Progress Tree | Working Production State |
| Reconciliation | Production Reconciliation |
| interrupt / stale / discard | interrupt / stale / supersede / discard |
| Commit | Integration / Baseline Commit |
| New Current Tree | New Trusted Production Baseline |

SPG additionally deals with persistent artifacts and external side effects, requiring durable lineage, recovery, verification, and compensation semantics. This note does not state that SPG uses React Fiber internally.

## 6. Runtime Architecture Refinement Order

| Layer | Status | Scope |
|---|---|---|
| A. State Foundation | CLOSED | Trusted / Working State; Plan Revision; Execution Attempt; State Transition Journal; Baseline Candidate; Commit and logical authority |
| A1. Core State Semantics | CLOSED — reviewed | Core state semantics recorded |
| A2. Transition & Commit Semantics | CLOSED — reviewed | Transition and Commit semantics recorded |
| A3. State Foundation Closure Review | PASSED | Supplied closure result recorded |
| B. Reconciliation & Recovery | CLOSED | Confirmed divergence, execution recovery, validity, reconciliation/replanning, and crash recovery semantics |
| B1. Divergence & Recovery Semantics | CLOSED | Classification and recovery scope |
| B2. Execution Recovery | CLOSED | Resume / Retry, observation uncertainty, Lease, fencing, isolation |
| B3. Reconciliation & Replanning | CLOSED | Validity basis, impact propagation, Candidate staleness, carry-forward |
| B4. Recovery Closure | PASSED | Barrier, anchor, orphan reality, idempotence, coherent recovery completion |
| C. Completion & Trust | CLOSED; C1/C2/C3 CLOSED; C4 PASSED | Output Obligation Manifest; PWU/Plan Completion Contracts; Produced/Satisfied; Verification Basis; Evidence Freshness; Trusted Completion; exact Candidate Authority |
| D. Side-effect Governance | CLOSED; D1/D2/D3 CLOSED; D4 PASSED | External Side Effect; Intent / Permit / Operation Identity; fencing; External Reality; Compensation; Governed Integration Atomicity |

**Current next governed step: Architecture Lead confirms S2 SOT closure → define the bounded S3 contract for Completion evaluation, Verification/Qualification, Candidate formation, and Governance.**

The [Final Closure and Readiness Review](spg-runtime-architecture-readiness.md) is PASSED, and the [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md) is CLOSED with Coding Readiness PASS. S1-A, S1-B, and S1-C are CLOSED / PASS; later slices remain outside this findings record. Future benchmark candidates do not reopen the frozen discovery scope.

## 7. SPG Core Logical Responsibility Model — Confirmed

Promoted from Architecture Hypothesis by the supplied State Foundation closure:

```text
Production Planner
        ↓
Production Governance Runtime
        ↓
Production State Projection
```

| Confirmed logical responsibility | Governing question |
|---|---|
| Production Planner | How should production proceed? Owns planning and adaptive plan evolution. |
| Production Governance Runtime | What transitions are allowed, what actually happened, and what authoritative state transitions may occur? |
| Production State Projection | What is the current understandable production reality? |

Production Governance Runtime is the only logical authority validating, admitting, and performing authoritative SPG state transitions. Planner proposes; Executor reports execution facts / artifacts; Verification / Guardian reports verification / assurance facts; Human Governor issues authority decisions. None directly mutate authoritative production reality.

The model is frozen only as logical responsibility decomposition, not physical services, microservices, or required runtime modules. Projection may be rebuilt from authoritative facts and is not final authority. The [SPG Core capability model](SPG_Core_Architecture_Model.md) is interpreted under this confirmed boundary; no state ownership transfers to ECF.

### Human–Machine governance clarification

**Human Authority Does Not Imply Runtime Bypass.** Human Agency First preserves strategic, risk, exception, and applicable final-acceptance authority, not unrestricted runtime privilege. Human, AI, Executor, Guardian, and other actors are governed participants with different Responsibility / Authority. Equal submission to governance does not imply equal authority.

See the [State Foundation Closure](spg-state-foundation.md) for the complete definitions, 20 invariants, and commit-failure boundaries.

### Distributed governance and future verification

**No Actor Owns Production Truth Alone; Distributed Responsibility, Governed Adjudication.** Runtime admits domain-owned inputs through explicit contracts and transition rules rather than inventing or solely owning all truth. This is not majority voting or a reduction of Human authority. Physical provider consolidation must not collapse logical Responsibility / Contract / Authority boundaries. **Replaceable Intelligence, Durable Governance** permits policy-bounded autonomy to evolve without assuming identical model capability or unrestricted production authority.

The [B Closure](spg-reconciliation-recovery.md), [C Closure](spg-completion-trust.md), and [D Closure](spg-side-effect-governance.md) preserve their respective 20-principle / invariant sets. The [Runtime Verification and Benchmark Strategy](spg-runtime-verification-benchmarks.md) maps them toward future verification and preserves the incident-derived regression candidate. No tests or benchmarks are implemented or executed here; Final Closure / Architecture Readiness Review is PASSED.

## 8. Baseline and Boundary Consistency

- Architecture Baseline remains **v0.1**. State Foundation clarification and the PWU Acceptance correction are explicitly linked from the existing baselines; no new Architecture Baseline is created.
- Design Artifact taxonomy remains a proposed refinement. References to Design revisions in a Trusted Baseline do not finalize the taxonomy.
- PWU **Satisfied** describes meeting production obligations. Human / Policy Final Acceptance primarily targets an exact Baseline Candidate, not every PWU. **Integrated** is derived lineage/integration state; detailed completion remains for C while logical recovery paths are closed by B.
- PWU / Plan Completion Contracts and Output Obligation Manifest are confirmed C logical semantics. Their schema / DSL / physical representations remain deferred. Production Issue representation remains pending. Execution Lease and fencing are confirmed B logical semantics, not chosen infrastructure.
- Execution Attempt, State Transition Journal, Baseline Candidate, state / commit invariants, and the three-part logical responsibility model are now confirmed architecture semantics, not implementation claims.
- Decision Intelligence Domain owns Decision Artifact semantics; YiJue remains an independent Consumer Product / possible Provider.
- SPG owns production planning, PWU coordination, lineage relationships, and production-governance state. Producers retain artifact content ownership; Git retains code history.
- Guardian retains Assurance Evidence, Findings, Gates, and qualification authority. Production Issue concerns SPG production control/recovery/replan, not Guardian Assurance Truth.
- ECF retains canonical engineering context and Context Projection authority; it does not own SPG Production State.
- Human Governance retains Decision approval, Risk Acceptance, and applicable Final Acceptance. Verification does not automatically grant acceptance, and Human Authority does not bypass governed state-transition or Commit rules.

The former hypothesis/candidate labels and simplified PWU Acceptance path are explicitly corrected, including Execution Lease's promotion by B. No capability-ownership conflict is introduced. Remaining taxonomy and concrete implementation choices are not resolved here. New Trusted Production Baseline denotes production reality, not a new version of this repository's Architecture Baseline.

## 9. Scope Guard

This record does not expand MVP scope or create Feature IDs, production code, runtime modules, database schemas, or APIs. Confirmed semantics do not require Event Sourcing, distributed transactions, a distributed state store, complex workflow engine, graph database, distributed locking, Production State Branching, or microservices. Guardian and ECF are not redesigned.

A/B/C/D and Runtime Architecture Refinement are CLOSED; Runtime Architecture Readiness is PASS; the Runtime Implementation Contract is CLOSED; Coding Readiness is PASS. The [FVS-1 Contract](spg-fvs-1-implementation-contract.md) records F3-D CLOSED and S1-A/S1-B/S1-C CLOSED / PASS. Remaining candidates and deferred mechanisms retain their labels.
