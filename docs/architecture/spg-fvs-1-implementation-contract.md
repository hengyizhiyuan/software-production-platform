# SPG FVS-1 — Governed Documentation Production Loop Implementation Contract

## 1. Authority, status, and interpretation

This document is the single authoritative implementation contract for **FVS-1 — Governed Documentation Production Loop** under **Architecture Baseline v0.1**.

It admits the reviewed F1, F2, F3-A, F3-B, and F3-C conclusions into Repository Source of Truth. It refines the [SPG Lite Runtime Implementation Contract](spg-lite-runtime-implementation-contract.md), [Runtime Profile architecture](runtime-profile-provider-deployment.md), and closed A/B/C/D Runtime semantics without replacing or reopening them.

    FVS-1 Implementation Contract
        ADMITTED

    F1. Slice Goal & Governance Contract
        REVIEWED / ADMITTED
    F2. Minimal Technical Foundation
        REVIEWED / ADMITTED
    F3-A. Runtime Slice Boundary & Physical Spine
        REVIEWED / ADMITTED
    F3-B. Repository Integration / Commit Semantics
        REVIEWED / ADMITTED
    F3-C. Executable Test & Failure Contract
        REVIEWED / ADMITTED
    F3-D. FVS Coding Authorization Closure
        CLOSED — FVS-1 AUTHORIZED FOR CONTROLLED IMPLEMENTATION

> FVS-1 is AUTHORIZED FOR CONTROLLED IMPLEMENTATION through explicitly bounded slice tasks. S1-A, S1-B, and S1-C are CLOSED / PASS.

Overall Implementation Governance remains **AUTHORIZED FOR CONTROLLED IMPLEMENTATION**. Authorization remains slice-bounded: S1-C permits only Bootstrap Baseline and the minimum durable Runtime identity/lineage spine. It does not authorize provider execution, artifact production, repository integration, or dogfood execution.

The contract uses these classifications:

| Classification | Meaning |
| --- | --- |
| Confirmed Slice Contract | Required FVS-1 domain/governance behavior |
| Confirmed Technical Foundation | Reviewed technology choice scoped to FVS-1 |
| Confirmed Integration Protocol | Required repository-effect and Runtime Commit behavior |
| Confirmed Verification Contract | Mandatory executable scenario or invariant coverage obligation |
| Implementation Guidance | Permitted physical shaping that may be refined without changing semantics |
| Deferred Scope | Explicitly outside FVS-1 |
| Authorization State | Implementation requires an explicit bounded slice; S1-A, S1-B, and S1-C have been explicitly authorized while later slices remain unauthorized |

## 2. Slice identity and proof objective

**Formal name:** FVS-1 — Governed Documentation Production Loop.

**Confirmed Slice Contract — core proof objective:**

> SPG independently determines production completion from admitted contracts and observed repository reality rather than trusting Executor self-reported success.

The slice must prove this real governed loop:

    Admitted Production Intent
    ↓
    Production Run
    ↓
    Production Plan Revision
    ↓
    Production Work Unit
    ↓
    Completion Contract
    ↓
    Context Package
    ↓
    Execution Attempt
    ↓
    Real Executor
    ↓
    Isolated Repository Working State
    ↓
    Independent Artifact Observation
    ↓
    Work Product References
    ↓
    Completion Evaluation
    ↓
    Verification
    ↓
    Baseline Candidate
    ↓
    Human Authorization
    ↓
    Controlled Repository Integration
    ↓
    Observed Repository Convergence
    ↓
    SPG Runtime Commit
    ↓
    Trusted Production Baseline

## 3. Production Horizon and artifact-agnostic completion

    Production Horizon = DOCUMENTATION
    Code Artifact = none

The absence of a Code Artifact must not prevent PWU Satisfaction, Plan Completion, Candidate Formation, Runtime Commit, or Trusted Baseline advancement when the Documentation Completion Contract is satisfied.

> No Runtime contract may require Code Artifact as a universal terminal condition.

This is a direct executable proof of artifact-agnostic production semantics.

## 4. Controlled documentation scenario

The FVS-1 production objective requires exact modification of governed documentation artifacts. The preferred automated fixture shape is:

    docs/fvs/architecture-state.md
    docs/fvs/project-state.md

    initial:
    FVS_ARCHITECTURE_STATE=V0
    FVS_PROJECT_STATE=V0

    admitted target:
    FVS_ARCHITECTURE_STATE=V1
    FVS_PROJECT_STATE=V1

Implementation may adjust fixture names if repository structure requires it, but the semantic test shape must remain equivalent.

Automated tests use ephemeral repositories. Critical real architecture Source-of-Truth files must not become destructive failure-injection fixtures. Manual dogfood may later use a dedicated governed Git ref.

## 5. Conversation-to-Contract enforcement

FVS-1 must follow:

    Conversation
    → extraction / refinement
    → governed admission
    → Artifact / Contract
    → Context Package
    → execution

The following path is prohibited:

    Raw Conversation
    → Executor

Executor input comes from admitted Production Intent, PWU Contract, Completion Contract, Context Package, approved Constraints, and Source Baseline. Raw chat may remain provenance or audit material, but it is not authoritative execution input.

## 6. Confirmed Technical Foundation

These choices are scoped to SPG Lite FVS-1 and are not platform-wide mandates.

| Concern | FVS-1 choice | Boundary |
| --- | --- | --- |
| Runtime language | **Python** | Do not freeze an unnecessary minor version in architecture |
| Application shape | **Modular Monolith** | One deployable Runtime, clear internal boundaries, one transactional persistence boundary |
| Primary control surface | **CLI-first** | Runtime/Application layer must not depend on HTTP; no Web UI required |
| Structured contracts | **Pydantic** preferred | Validation/serialization boundary, not the governance engine |
| Persistence | **PostgreSQL** | Real transactional/concurrency semantics |
| ORM | **SQLAlchemy 2.x** | Domain semantics must not collapse into ORM semantics |
| Migration | **Alembic** | Physical schema evolution tool, not a Domain Contract |
| Test framework | **pytest** | Integration/E2E uses real infrastructure where semantics require it |
| Repository interaction | **Git CLI + filesystem observation + Git worktree** | Git is infrastructure, not the SPG domain model |
| First real Executor | **Codex CLI Executor Adapter** | SPG Core depends on Executor Capability Contract, not Codex identity |
| Process boundary | Python subprocess/process supervision may be used | Provider-neutral prepare/dispatch/observe semantics remain stable |
| FVS packaging direction | **Docker + Docker Compose** preferred | Local-first packaging/deployment, not domain architecture |

Microservices are not introduced. FVS-1 preserves:

> Semantic separability before physical separability.

Containerization is preferred but is not created by this documentation task. Final cloud region is not an FVS prerequisite.

## 7. Runtime Profile and Planner scope

FVS-1 preserves provider-neutral configuration. A minimal conceptual profile is:

    runtime_profile = local-global-fvs

    planner:
        adapter = deterministic_fvs

    executor:
        adapter = codex_cli

    verification:
        adapter = deterministic_repository

Provider/model identity remains configuration rather than SPG domain logic. Full Provider Registry, management UI, Global/Mainland dual-provider Runtime, and model routing remain deferred.

    Planner Contract
        REAL

    Planner Intelligence
        LITE / deterministic

A deterministic structured planner/plan constructor is permitted for the first documentation case. LLM Planner intelligence is not an FVS-1 blocker. The Runtime must still persist a real Production Plan Revision, PWU, applicable dependencies, Output Obligations, and Completion Contract.

## 8. Core persistent Runtime spine

FVS-1 physically persists the minimum structures necessary to preserve approved semantics:

    Production Run
    Plan Revision
    Production Work Unit
    Execution Attempt
    Work Product Reference
    Verification Record
    Production Snapshot / Baseline Candidate
    Governance Record
    Production Issue
    Transition History
    Repository Integration Effect Record

Logical distinctions do not require one microservice, package, class hierarchy, or database per architecture noun. Physical consolidation is allowed where semantics remain explicit.

## 9. Bootstrap Trusted Baseline

FVS-1 requires an explicit Bootstrap Trusted Baseline:

    spg bootstrap
    ↓
    observe current governed repository reality
    ↓
    capture exact repository revision/reference
    ↓
    create Bootstrap Production Snapshot / Trusted Baseline B0
    ↓
    record governance/bootstrap provenance
    ↓
    set Current Trusted Baseline Pointer

The following implicit rule is prohibited:

    Trusted Baseline = whatever Git HEAD happens to be right now

A Trusted Baseline may reference exact Git reality but is not equivalent to Git HEAD.

## 10. Production Run, Plan, PWU, and Completion Contract

FVS-1 creates and persists a real Production Run, Plan Revision R1, PWU, and Completion Contract. The PWU binds to:

- Production Run;
- Plan Revision;
- Source Trusted Baseline;
- Context Package;
- Output Obligations;
- Completion Contract.

The lifecycle preserves:

    Attempt SUCCESS
    !=
    PWU PRODUCED
    !=
    PWU SATISFIED

FVS-1 does not require a generic Completion DSL. A simple structured representation is sufficient when it can express semantic obligations equivalent to:

    required_artifacts
    required_changes
    required_markers
    forbidden_changes
    verification_obligations
    blocking_conditions

Completion is defined before Executor result evaluation.

## 11. Context Package Lite

Full ECF remains deferred. FVS-1 Context Package is real, versioned, and traceable. It binds:

- Context identity and content/revision identity;
- Source Baseline;
- PWU Contract;
- approved constraints;
- selected governed documents/repository references;
- provenance.

Every Execution Attempt records the exact Context Package identity/revision it consumed. Raw conversation must not enter the package as task Authority.

## 12. Execution Attempt and dispatch discipline

Execution Attempt is independently persisted from PWU and preserves:

- immutable Attempt identity;
- PWU and Plan Revision;
- execution generation;
- Source Baseline;
- Context identity;
- Executor/provider;
- workspace identity;
- provider/process reference;
- start/end facts and reported result;
- retry/resume lineage.

Retry creates a new Attempt. Historical Attempt identity and facts are immutable.

> Execution Attempt must be durably persisted before provider dispatch.

    create Attempt
    ↓
    commit Attempt state
    ↓
    dispatch Executor

If execution later becomes unobservable, the Attempt remains in production history.

Each authoritative execution generation is explicit:

    EA-1 generation=1
    EA-2 generation=2

Stale-generation results may be preserved as history but cannot mutate current production Authority. FVS-1 must provide an executable validation path for this semantic even if real zombie-process testing remains deferred.

## 13. Attempt isolation and Executor Contract

The preferred FVS-1 isolation mechanism is an Attempt-specific Git worktree derived from an exact source revision:

    EA-001 → workspace/EA-001
    EA-002 → workspace/EA-002

Codex must not directly mutate the authoritative FVS development branch.

The provider-neutral Executor Contract supports semantics equivalent to:

    prepare
    dispatch
    observe

with logical data shapes equivalent to ExecutionRequest, ExecutionHandle / Provider Reference, and ExecutionObservation.

The Runtime must not be designed around a provider-specific run-codex-prompt-to-text abstraction. Executor output is a fact/claim. Executor does not own PWU Satisfaction, Verification truth, Candidate acceptance, Trusted Baseline, or Repository Integration Authority.

## 14. Independent repository observation and Work Product References

Repository/Artifact Observation is independent from Executor self-report. The observer inspects real Git/filesystem facts:

- exact source revision;
- changed paths;
- required file existence;
- content identity/hash;
- diff;
- unexpected mutations.

    Expected Work
    !=
    Observed Work
    !=
    Executor Self-Reported Completion

SPG stores governed references and lineage rather than becoming the universal artifact-content store. A Work Product Reference may record artifact identity/type, path/location, content identity, origin PWU/Attempt, and repository/workspace revision. Historical references must not silently mutate.

## 15. Produced, Satisfied, and deterministic Verification

FVS-1 physically preserves:

    PRODUCED
    !=
    SATISFIED

If A and B are required but only A exists, Work Product exists but PWU remains unsatisfied. If A and B exist but Verification fails, PWU may be PRODUCED but not SATISFIED.

Primary Verification is deterministic and includes applicable checks such as:

- required file exists;
- required file changed;
- required marker/value exists;
- no forbidden path changed;
- git diff --check;
- optional lightweight Markdown validation already available.

Full Guardian and an LLM reviewer are not required.

Verification Record binds the exact subject and revision/tree, source Baseline/basis, scope, method, result, and diagnostics/evidence references.

    Verification Result
    !=
    Verification Applicability / Freshness

## 16. Exact proposed Git commit and three Commit concepts

After independent observation establishes sufficient work to prepare a Candidate, Repository Integration preparation creates an exact, non-authoritative proposed Git commit/tree:

    Authoritative ref = C100

    Attempt working state
        ↓

    Proposed Git Commit = C101

    Authoritative ref remains C100

The proposed commit uses the expected source revision as its parent/basis where applicable.

These concepts are distinct:

    Git Commit Object
    !=
    Repository Integration
    !=
    SPG Runtime Commit

- **Git Commit Object:** concrete repository snapshot.
- **Repository Integration:** governed advancement of an authoritative repository ref.
- **SPG Runtime Commit:** governed advancement of Trusted Production Baseline.

No ambiguous single commit operation may collapse these layers.

Final Verification used for Candidate eligibility binds the exact proposed repository commit/tree:

    source revision = C100
    subject commit = C101
    subject tree = T101

A PASS for C101 cannot automatically verify C102. **Validity Is Relational.**

## 17. Candidate Seal

A Baseline Candidate binds exact material contents:

    Candidate BC-001/R1

    source_baseline = B0
    plan_revision = P1/R1

    repository:
        repository identity
        authoritative target ref
        expected source revision = C100
        proposed revision = C101
        proposed tree = T101

    work products
    verification references
    completion basis

After Seal, material contents must not silently change. Any material change requires a new Candidate revision and re-verification.

## 18. Exact Human Authorization and Executor Authority boundary

Human Authorization binds the exact Candidate and explicitly scopes the permitted Repository Integration:

    subject = BC-001/R1
    decision = AUTHORIZE

    scope:
        target repository/ref
        expected old revision = C100
        proposed revision = C101

    basis:
        exact Verification Record(s)

One exact Candidate Authorization may authorize its declared narrow Repository Integration. Duplicate approval is not required merely because integration is a side effect, but authorization cannot be reused for another Candidate revision.

> Execution Capability Does Not Imply Side-effect Authority.

Codex may mutate Attempt Working State. It must not advance or force-update an authoritative repository ref, push authoritative state, decide Candidate acceptance, or commit Trusted Baseline. Those responsibilities belong to governed Runtime/Repository Integration capability.

## 19. Confirmed Integration Protocol — narrow repository effect

General External Effect infrastructure remains deferred. FVS-1 requires exactly one narrow effect type:

    REPOSITORY_REF_ADVANCE

Its record preserves semantics equivalent to:

- stable operation identity;
- Candidate;
- repository and target authoritative ref;
- expected source revision;
- desired target revision;
- Authorization reference;
- current execution/observation condition;
- observed repository reality.

Universal Side-effect Gateway, Saga, 2PC, Compensation Engine, Effect Group Engine, deployment effects, and remote-push effects are not implemented.

## 20. Repository ref CAS

Authoritative repository ref advancement uses expected-source / compare-and-swap semantics:

    expected old = C100
    desired new  = C101

Only when current authoritative ref equals C100 may it become C101. If actual ref is C150, integration is rejected, divergence/Production Issue is recorded, and the Runtime must not force overwrite.

## 21. Stable operation identity and recovery

Repository Integration uses a stable logical operation identity. If Runtime process continuity is lost, recovery observes repository reality before deciding whether to retry.

For intended C100 → C101:

| Observed ref | Meaning | Required response |
| --- | --- | --- |
| C100 | Effect has not converged | Dispatch/retry same logical operation only if still authorized/applicable |
| C101 | Effect has converged | Do not mutate Git again; continue governed eligibility/recovery |
| Anything else | Reality diverged | Block, record Production Issue, reconcile; never blind retry/overwrite |

> Recover knowledge before execution.

## 22. Git/PostgreSQL atomicity boundary

> Git repository mutation and PostgreSQL Runtime Commit do not form one global transaction.

FVS-1 must not claim distributed ACID across Git and PostgreSQL. It uses stable operation identity, observed reality, reconciliation, and local database transactions. External Git mutation must not be placed inside a SQL transaction as if globally atomic.

## 23. FVS Repository Integration ordering

The following effect-specific ordering is frozen for FVS-1:

    Candidate SEALED
    ↓
    Human Authorization
    ↓
    Repository Integration Effect PREPARED
    ↓
    Git ref CAS
    ↓
    Observe authoritative Git ref
    ↓
    Effect CONVERGED
    ↓
    Runtime Commit eligibility re-check
    ↓
    PostgreSQL local transaction
        Candidate → COMMITTED
        Current Trusted Baseline Pointer advances
        Transition History append
    ↓
    Trusted Production Baseline advances

This is **Repository Reality First, Trusted Baseline Commit Second** for FVS-1 Repository Integration only. It must not be generalized to every future External Effect.

## 24. Crash recovery window

FVS-1 supports safe recovery when Git ref advancement succeeds and Runtime crashes before Trusted Baseline Commit:

    restart / reconcile
    ↓
    observe authoritative ref
    ↓
    recognize same stable operation already converged
    ↓
    do not mutate Git again
    ↓
    re-check Candidate / Authorization / Verification / Baseline freshness
    ↓
    finish Runtime Commit if still eligible

If reality diverged, Runtime blocks, creates a Production Issue, and requires reconciliation. A generalized Recovery Engine is not required.

## 25. Runtime Commit eligibility and local atomicity

Immediately before Runtime Commit, Runtime re-checks:

- Candidate remains sealed;
- Authorization binds the exact Candidate;
- Verification remains applicable to the exact Candidate;
- Current Trusted Baseline equals Candidate Source Baseline;
- Repository Effect is CONVERGED;
- observed authoritative ref equals Candidate proposed revision;
- no blocking Production Issue exists.

    Authorization
    !=
    Eligibility

Where applicable, one PostgreSQL transaction:

1. validates expected Runtime state/version;
2. marks Candidate COMMITTED;
3. advances Current Trusted Baseline Pointer;
4. appends Transition History.

The local state change is all-or-none.

## 26. Trusted Baseline and Git revision

    Trusted Production Baseline
    !=
    Git revision

A Trusted Baseline may reference repository identity, authoritative ref, and exact Git revision C101, but remains a broader software-production-reality snapshot containing governed references.

## 27. Repository targets

Automated tests use an **ephemeral real Git repository**.

Manual dogfood uses a real project repository plus a **dedicated governed dogfood target ref/branch**. FVS automation must not directly mutate feature/spg-first-vertical-slice or another active Runtime development branch.

Remote push and pull-request workflow are not part of FVS-1. Authoritative repository reality is a local governed Git ref.

## 28. Minimal CLI and Candidate review surface

FVS-1 may expose a goal-oriented CLI conceptually equivalent to:

    spg bootstrap
    spg run create ...
    spg run execute <run>
    spg run inspect <run>
    spg candidate show <candidate>
    spg candidate authorize <candidate>
    spg candidate commit <candidate>

Exact command naming may be refined. Human Authority enters through Governance Records rather than direct database mutation; Human is not required to manually transition every internal state.

Candidate inspection exposes at minimum:

- Candidate ID;
- Run and PWU;
- Production Horizon;
- Source Baseline;
- target repository/ref;
- expected source and proposed Git revisions;
- changed and unexpected Artifacts;
- Verification result;
- blocking Issues.

No Web UI is required.

## 29. Testing architecture and real infrastructure

Executable verification is semantically separated into:

    Unit / invariant tests
    Persistence integration tests
    Repository integration tests
    Failure-injection tests
    FVS end-to-end tests

A possible physical layout is tests/unit, tests/integration, tests/failure_injection, and tests/e2e; implementation may refine directories while preserving semantic separation.

Unit tests may use isolated/fake dependencies. Integration/E2E tests that claim persistence or repository semantics use real PostgreSQL, Git, filesystem, and Git worktree where those semantics are under test. CAS, transactions, or worktree behavior must not be claimed proven only through mocks.

## 30. Deterministic Test Executor and real Codex dogfood

FVS-1 includes a test-only deterministic Executor adapter implementing the same Executor Capability Contract. It can reproducibly:

- produce all required Artifacts;
- produce only one required Artifact;
- produce unrelated output;
- report SUCCESS without required changes;
- produce forbidden mutation;
- fail;
- delay or provide a stale observation where required.

Runtime logic must not special-case this Executor or bypass governance.

At least one manual/controlled FVS E2E run uses real Codex CLI against a controlled documentation target. The real run validates the actual provider boundary; deterministic failure cases primarily use the Test Executor.

## 31. Confirmed Verification Contract — mandatory T01–T18

The following scenarios are mandatory executable coverage obligations. They are **ADMITTED / NOT YET IMPLEMENTED / NOT YET PASSED**.

### T01 — Documentation Happy Path

Required A+B are produced and verified. Attempt success fact and observed Artifacts are recorded; Verification passes; PWU becomes SATISFIED; Candidate is SEALED; exact Human Authorization is recorded; Repository Integration converges; Runtime Commit succeeds; Trusted Baseline advances.

### T02 — Executor SUCCESS + Missing Required Artifact

Executor reports SUCCESS but only part of required output exists. Reported success remains historical fact; PWU is NOT SATISFIED; Candidate and integration are absent; Production Issue is OPEN; Trusted Baseline is unchanged.

### T03 — False / Unrelated Success

Executor reports success while required work is absent or unrelated work is observed.

    Expected Work != Observed Work != Executor Claim

PWU remains unsatisfied, a Production Issue is recorded, Candidate is absent, and Baseline is unchanged. This preserves the real wrong-task/false-success incident as a regression class.

### T04 — Forbidden Artifact Mutation

Required work exists but a disallowed path also changed. Verification/constraint evaluation blocks Satisfaction; Candidate is absent; Baseline is unchanged; Production Issue is recorded.

### T05 — Produced but Verification FAIL

Required Artifacts exist but Verification fails. Work Product is recorded and PWU may become PRODUCED, but it is NOT SATISFIED; Candidate is absent and Baseline remains unchanged.

### T06 — Candidate Immutability

After Candidate Seal, later workspace/working-repository changes cannot mutate sealed material identity. New material requires a new Candidate revision and re-verification.

### T07 — Verification Subject / Freshness Binding

Verification PASS for proposed C101 cannot authorize C102. Exact subject or basis mismatch rejects Candidate eligibility.

### T08 — Exact Human Authorization Binding

Authorization for BC1 cannot authorize BC2. Authority is exact, scoped, and relational.

### T09 — Repository CAS Conflict

Candidate expects C100 → C101 while authoritative ref is C150. CAS fails; C150 remains; Effect is not converged; Production Issue is recorded; Runtime Commit is rejected; Baseline is unchanged.

### T10 — Crash After Git Convergence Before Runtime Commit

Git reaches C101 and Runtime stops before Trusted Baseline advancement. Recovery observes C101, recognizes the same stable operation as converged, avoids a blind repeat, re-checks eligibility, and finishes Runtime Commit only if still valid.

### T11 — Crash Before Repository Effect Dispatch

Effect is PREPARED while Git remains C100. Recovery may dispatch the same logical operation only if Authorization and applicability remain valid.

### T12 — Recovery Finds Repository Divergence

Expected C100 → C101, observed C150. Runtime does not retry blindly or force overwrite; Effect becomes blocked/diverged, Production Issue is recorded, and Baseline remains unchanged.

### T13 — Runtime Baseline CAS Conflict

Candidate Source Baseline is B0 while Current Trusted Baseline has advanced. Runtime Commit rejects the Candidate even if Repository Integration converged; reconciliation is required.

### T14 — Retry Creates New Attempt

Retry creates EA2 distinct from EA1, preserves immutable EA1 history, and records explicit retry lineage.

### T15 — Stale Generation Cannot Mutate Current Authority

A historical stale-generation result may be stored but cannot advance current PWU Authority state.

### T16 — State Mutation + Transition History Atomicity

Injected local persistence failure results in both authoritative state mutation and Transition History append committing, or neither committing. Authoritative state without corresponding history is forbidden.

### T17 — Optimistic Version Conflict

A stale expected entity/row version rejects mutation rather than silently applying last-writer-wins behavior.

### T18 — Non-Code Run Reaches Trusted Baseline

A Documentation-only Production Run with no Code Artifact legally reaches PWU SATISFIED, Candidate SEALED, Runtime Commit, and advanced Trusted Baseline.

## 32. First-wave critical invariant coverage — 12/12

Target executable coverage is **12 / 12**. This is a coverage contract, not a claim that implementation already passes.

| # | Critical Runtime invariant | Mandatory executable path |
| --- | --- | --- |
| 1 | Executor SUCCESS does not directly complete PWU | T02, T03 |
| 2 | Required Artifact is independently observed | T01–T04 |
| 3 | PWU PRODUCED and SATISFIED remain distinct | T02, T05 |
| 4 | Attempt is immutable; Retry creates a new Attempt | T14 |
| 5 | Stale Attempt generation cannot mutate current Authority | T15 |
| 6 | Plan Revision / Source Baseline binding is preserved | T13 plus Candidate/Plan binding assertions |
| 7 | Sealed Candidate cannot silently mutate | T06 |
| 8 | Trusted Baseline advances only through Runtime Commit | T01, T09–T13 |
| 9 | Commit validates expected Source Baseline | T13 |
| 10 | Verification binds exact subject/basis | T07 |
| 11 | Material state mutation and Transition History append are locally atomic | T16, T17 |
| 12 | Code Artifact is not universally required | T18 |

Repository Integration cases additionally cover exact Human Authorization (T08), repository CAS (T09), stable-operation recovery (T10–T12), and optimistic mutation control (T17).

## 33. Production Issues and durable history

Failure cases must not merely return false. Where appropriate, Runtime creates a durable Production Issue for missing required Artifact, Output Obligation mismatch, forbidden mutation, repository divergence, or Baseline conflict.

FVS-1 uses the smallest classification necessary to preserve observed facts, impact, blocking status, and resolution/recovery relationship. It does not build a large Issue taxonomy.

Failure must not erase:

- Execution Attempts and observations;
- Verification failures;
- Production Issues;
- Governance history;
- Transition History.

> History Is Appended, Not Rewritten.

## 34. FVS-1 Definition of Done

> FVS-1 passes only if a real governed Documentation Production Run can travel from admitted Production Intent to a committed Trusted Production Baseline through persisted SPG Runtime governance, using a real Executor and independent repository observation, while missing-artifact, false-success, unauthorized/stale/conflicting, and repository-integration failure cases are prevented from incorrectly advancing Trusted Production Reality.

Closure requires at minimum:

    Mandatory executable suite PASS
    +
    real Codex documentation dogfood PASS
    +
    Architecture/Reality Review PASS

Passing pytest alone does not close FVS-1. Tests are evidence, not architecture truth.

## 35. Explicit FVS-1 non-goals and Deferred Scope

FVS-1 does not implement:

- Full Guardian or Full ECF;
- raw Conversation execution or a Conversation management system;
- AI Planner as a requirement;
- Provider management Web UI;
- Mainland provider integration or Global/Mainland dual-Runtime validation;
- multi-provider routing, Capability Marketplace, or advanced model routing;
- remote Executor Worker or cross-region execution;
- remote Git push or pull-request workflow;
- generic deployment effects or generalized External Effect Gateway;
- Saga, 2PC, Compensation Engine, or Effect Group Engine;
- Event Sourcing or Graph DB;
- microservices or Kubernetes;
- Policy DSL, Trust Score, or Evidence Graph;
- full generalized Recovery Engine;
- multi-user collaboration or complex role-specific UI;
- production SaaS authentication;
- automatic rollout/deployment;
- generalized autonomous replanning.

Future compatibility remains preserved without pre-implementing these capabilities.

## 36. Container and deployment scope

    Local-first
    Container-ready
    Docker / Docker Compose preferred

Docker artifacts may be created only during a later explicitly authorized implementation step. This documentation admission creates none and does not make final cloud region an FVS-1 completion requirement.

## 37. Architecture status preservation

    Architecture Baseline v0.1

    Runtime Architecture Refinement
        CLOSED

    Runtime Architecture Readiness
        PASS

    Implementation Contract / Runtime MVP Design
        CLOSED

    Coding Readiness
        PASS

    Implementation Governance
        AUTHORIZED FOR CONTROLLED IMPLEMENTATION

FVS-1 is a controlled implementation refinement under v0.1; it does not increment the Baseline.

## 38. Coding authorization closure and slice boundary

Admission of this Contract provides governed Source-of-Truth authority for F1/F2/F3-A/F3-B/F3-C conclusions. Explicit S1-A, S1-B, and S1-C tasks subsequently exercise that controlled, slice-bounded authorization.

    F3-D. FVS Coding Authorization Closure
        CLOSED — FVS-1 AUTHORIZED FOR CONTROLLED IMPLEMENTATION

S1-A permitted Python project metadata, package boundaries, typed Settings, application Bootstrap, CLI, dependency declaration, and smoke tests only. S1-B subsequently authorized PostgreSQL/SQLAlchemy/Alembic infrastructure and a PostgreSQL-only local Compose service, but no Runtime domain entity, production schema, Executor, Git integration, or deferred capability.

## 39. S1-A implementation reality

S1-A Runtime Project Foundation is **CLOSED / PASS**:

- CPython 3.13.15 was selected from the existing uv-managed local environment;
- project compatibility is declared as Python 3.12 or newer without freezing a minor version;
- pyproject.toml and uv.lock define the project and reproducible dependency set;
- src/spg provides minimal Modular Monolith boundaries, typed environment Settings, explicit Bootstrap, and CLI-first startup;
- five S1-A tests pass for import, Settings, Bootstrap, CLI status, and CLI help;
- its stable checkpoint authorized the next bounded persistence slice.

## 40. S1-B implementation reality

S1-B Persistent Runtime Foundation is **CLOSED / PASS**. The Architecture Lead independently reviewed and accepted the implementation Reality and its validation evidence:

- Python 3.13.15 runs the existing Python 3.12+ project contract;
- PostgreSQL 17.6 runs as the only Docker Compose service and is reached through `psycopg`;
- typed `SPG_DATABASE_URL` configuration rejects non-PostgreSQL URLs and commits no real secret;
- SQLAlchemy 2.x engine/session composition, explicit Unit of Work commit/rollback, disposal, and a reusable expected-version update primitive are implemented;
- Alembic loads configuration through typed Settings and connects to PostgreSQL, with empty production metadata and no speculative Runtime revision;
- the `spg db check` command provides non-destructive database reachability evidence while `spg status` remains database-independent;
- test-only schema remains under integration tests and is created/cleaned without touching unrelated data;
- DB-01 through DB-06 pass against real PostgreSQL; all 19 current tests pass, including the five S1-A regressions;
- no Runtime domain lifecycle, Bootstrap Baseline, Executor, Git integration, or Runtime Commit is implemented.

That S1-B closure admission changed implementation status only and did not change Architecture Baseline v0.1. A subsequent explicit bounded task authorized S1-C; its current result is recorded below.

## 41. S1-C implementation reality

S1-C Bootstrap Baseline & Minimal Durable Runtime Spine is **CLOSED / PASS**. Architecture Lead Reality Review accepted the repository evidence with zero architecture blockers, zero implementation blockers, and no scope leakage.

The implementation adds one substantive Alembic revision with exactly the admitted Snapshot, Current Trusted Baseline Pointer, Run, Plan Revision, PWU, Execution Attempt, Governance Record, and Transition History tables. An explicit application operation observes a clean repository and exact commit through read-only Git, then atomically admits Bootstrap Snapshot B0, authority provenance, pointer, and history. A deterministic application path atomically constructs an OPEN Documentation Run, active Plan Revision 1, and PROPOSED generic PWU with a typed durable Completion Contract. Lower-level application operations create immutable Attempt identities, advance retry generations, and detect stale Attempts without dispatching an Executor.

RS-01 through RS-17 pass against PostgreSQL 17.6 and ephemeral real Git repositories. The full suite passes **40/40**, retaining the accepted S1-A and S1-B evidence and adding an end-to-end bounded CLI proof. No Executor, Work Product, Completion evaluation, Verification, Candidate, Repository Integration, Runtime Candidate Commit, deferred schema, or active-development-repository bootstrap was introduced.

Architecture Baseline remains **v0.1**. S1 is CLOSED / PASS. The subsequently admitted S2 stage and its current implementation Reality are defined below.

## 42. S2 Governed Artifact Production stage contract

This section records the reviewed implementation-stage decomposition admitted into Repository Source of Truth. At contract-definition admission time it did not authorize or begin S2-A or S2-B implementation; subsequent governed implementation Reality is recorded in Sections 43 and 44.

```text
S2 — Governed Artifact Production
    CLOSED / PASS

S2-A — Context & Execution Preparation Foundation
    CLOSED / PASS

S2-B — Isolated Execution & Independent Artifact Observation
    CLOSED / PASS
```

S2 connects durable PWU state to governed artifact production while preserving the separation between execution preparation, actual execution, independent observation, completion evaluation, Verification, and trust. Its bounded outcome is:

```text
PWU
↓
prepared executable Attempt
↓
isolated execution
↓
independently observed Work Product References
```

S2 does not determine Completion Contract satisfaction, Verification, Candidate eligibility, Trusted Baseline advancement, or Repository Integration.

### 42.1 S2-A — Context and execution preparation

S2-A owns preparation prerequisites only:

- **Context Package Lite:** a durable, versioned execution context assembled from admitted engineering artifacts. It binds the relevant Source Trusted Baseline, approved documents and constraints, Completion Contract, and repository reality. It preserves the future ECF ownership boundary; it is not a replacement for ECF.
- **Executor Capability Contract:** SPG Runtime depends on a provider-neutral Executor Capability Contract, which is implemented by an Executor Adapter bound to an actual provider or tool. SPG Core does not depend directly on Codex, OpenAI, or model identity.
- **Attempt Preparation:** a prepared Attempt binds the exact PWU, Plan Revision, Source Trusted Baseline, Context Package, Executor binding, isolated workspace, and current execution generation.
- **Isolated Workspace:** the FVS-1 preference is an Attempt-specific Git worktree derived from exact repository reality. A later Executor may mutate only the Attempt workspace and may not mutate authoritative repository refs.
- **Execution readiness:** PWU existence is not execution readiness. Readiness requires the implemented preparation prerequisites; S2-A does not dispatch the Executor.

```text
Raw Conversation
MUST NOT
directly become Executor Context
```

### 42.2 S2-B — Isolated execution and independent observation

S2-B owns the actual bounded dispatch and observation lifecycle after S2-A produces an execution-ready Attempt:

- **Governed Dispatch:** Attempt identity and applicable prepared state must already be durable before provider dispatch.
- **Provider Report:** Executor/provider self-report is an observation or claim, not Production Truth.
- **Independent Repository / Artifact Observation:** SPG independently observes Attempt workspace reality, including applicable added, modified, and deleted files; exact repository/tree reality; artifact existence; and unexpected mutations. Observation does not depend solely on Executor prose.
- **Work Product References:** references derive from independently observed reality and preserve lineage to the Run, PWU, Attempt, Plan Revision, Source Baseline, workspace/repository reality, and observed artifact.
- **False-success foundation:** S2-B makes the state “Executor reports SUCCESS but a required artifact is absent” observable without deciding Completion Contract satisfaction.

```text
Executor SUCCESS
!=
Production Truth
```

The admitted dependency is:

```text
Durable PWU
↓
S2-A:
Context Package Lite
+ Executor Capability Binding
+ Attempt Preparation
+ Isolated Workspace
↓
Execution-ready Attempt
↓
S2-B:
Dispatch
+ Provider Report
+ Independent Repository / Artifact Observation
↓
Observed Work Product References
```

### 42.3 Explicit S2 boundaries

1. S2-A does not dispatch an Executor.
2. PWU existence alone does not imply `READY` or execution readiness.
3. S2-B owns the actual dispatch and observe lifecycle.
4. Provider self-report is not Production Truth.
5. Work Product References derive from independent observation.
6. Work Product observation does not imply Completion.
7. Completion evaluation remains later.
8. Verification remains later.
9. Candidate formation and Trusted Baseline advancement remain later.
10. Repository Integration remains later.
11. An Executor cannot mutate authoritative repository refs.
12. A stale Attempt generation cannot regain current execution authority.
13. Production Horizon `DOCUMENTATION` remains valid without Code Artifact assumptions.
14. Context Package Lite preserves the future ECF ownership boundary.
15. The Executor Capability Contract remains provider-neutral.

### 42.4 Governed implementation sequence

```text
S1 — Runtime Foundation & Persistent Spine
    CLOSED / PASS

S2 — Governed Artifact Production
    S2-A — Context & Execution Preparation Foundation
    S2-B — Isolated Execution & Independent Artifact Observation

S3 — Completion, Verification & Candidate Governance
    S3-A — Completion Evaluation & Produced Semantics
    S3-B — Verification Qualification & Satisfaction
    S3-C — Candidate Sealing & Human Governance
S4 — Repository Integration & Runtime Commit
S5 — Failure / Recovery Hardening
S6 — Real Codex Dogfood & FVS Closure
```

S3 is formally defined in Section 45. At contract admission it remained NEXT / NOT STARTED; the subsequently authorized S3-A implementation Reality is recorded in Section 46. S4 through S6 remain boundary labels only.

## 43. S2-A implementation reality

At S2-A closure, S2 was **IN PROGRESS**, S2-A Context & Execution Preparation Foundation was **CLOSED / PASS**, and S2-B was recorded as **NEXT / NOT STARTED**. Architecture Lead Reality Review accepted the S2-A repository evidence with zero architecture blockers, zero implementation blockers, and no scope leakage. Subsequent S2-B implementation and S2 closure Reality is recorded in Section 44.

Alembic revision `20260828_02` adds exactly two S2-A production tables: immutable/versioned `context_packages` and one authoritative `attempt_preparations` binding per Attempt. No Work Product, Verification, Candidate, Production Issue, External Effect, or Provider Registry table was added.

Context Package Lite is an execution-facing FVS projection rather than SPG ownership of universal Engineering Context. It records exact PWU/Run/Plan/Source Baseline lineage, a typed repository-artifact manifest with semantic role/path/source revision/blob identity, a stable package fingerprint, and the exact Completion Contract fingerprint. Assembly reads blobs from the Source Baseline commit rather than mutable HEAD or the working tree. The typed input has no raw-conversation path; material context change produces a new package identity/version, while identical assembly is idempotent.

The provider-neutral Executor Capability Contract defines a future dispatch boundary but S2-A provides no adapter and makes no dispatch call. Attempt preparation binds the exact Context Package, capability/profile binding, generation, repository identity, Source Baseline revision, and stable Attempt-specific detached Git worktree. The worktree is created outside the authoritative working tree from the exact Source Baseline without moving an authoritative ref. Existing matching workspace Reality is reconciled after failure; mismatched or stale preparation is rejected.

No unsupported PWU or Attempt lifecycle condition was introduced. PWU remains `PROPOSED`, Attempt remains `CREATED`, and execution readiness is represented by the durable preparation binding plus a revalidating `is_execution_ready` predicate. Transition History records Context Package assembly and Attempt preparation without rewriting Attempt history.

S2A-01 through S2A-18 pass using PostgreSQL 17.6, ephemeral real Git repositories, and real Git worktrees. The prior S1 regression suite remains **40/40 PASS**, and the full suite is **61/61 PASS**. Migration downgrade to `20260827_01` and re-upgrade to `20260828_02` pass.

No Executor dispatch, deterministic Test Executor execution, Work Product, post-execution Artifact Observation, Completion evaluation, Verification, Candidate, Repository Integration, or Runtime Commit was implemented.

The governed handoff recorded at S2-A closure was:

> Architecture Lead confirms S2-A SOT closure → authorize S2-B Isolated Execution & Independent Artifact Observation.

## 44. S2-B implementation reality

S2-B Isolated Execution & Independent Artifact Observation is **CLOSED / PASS**. Together, S2-A and S2-B satisfy the admitted S2 Governed Artifact Production contract, so S2 is **CLOSED / PASS**. S1 and S2-A remain CLOSED / PASS. S3 is **NEXT / NOT STARTED** and is not authorized.

Alembic revision `20260828_03` adds exactly four S2-B production tables: `execution_dispatches`, `provider_execution_reports`, `repository_observations`, and `work_product_references`. No Completion, Verification, Candidate, Production Issue, Repository Integration, Runtime Commit, External Effect, Provider Registry, or deferred-capability table was added.

Runtime revalidates the complete relational S2-A preparation binding under current-generation control, persists a stable dispatch identity/fact before invoking the provider-neutral Executor Capability Contract, and rejects duplicate normal dispatch for the same Attempt. The Deterministic Test Executor implements that same capability contract through structured file operations and makes no Codex, OpenAI, model, prompt, or raw-conversation dependency part of SPG Core.

Provider output is normalized and durably recorded with exact dispatch, Attempt, generation, Executor Binding, provider reference, reported outcome, timestamps, metadata, and summary lineage. A Provider `SUCCESS` remains only a claim and has no path to Completion, PWU `PRODUCED` / `SATISFIED`, Verification, Candidate, Trusted Baseline, or Repository Integration authority.

After provider execution, SPG independently inspects the real Attempt worktree relative to its exact Source Baseline. It preserves added, modified, deleted, and no-change Reality using structured manifests and exact Git blob identities where applicable. One stable observation fingerprint makes identical re-observation idempotent; a changed workspace after authoritative observation is rejected rather than silently rewriting history. Authoritative repository refs are observed before dispatch and required to remain unchanged through observation.

Work Product References are created only from independently observed change entries. Each reference preserves Run, PWU, Plan Revision, Attempt, generation, Source Baseline, Repository Observation, artifact path/change type, and source/observed fingerprint lineage. Deletions remain first-class factual changes without requiring current content.

No newly authorized Attempt lifecycle condition was available for actual dispatch/finish. S2-B therefore leaves PWU at `PROPOSED` and Attempt at `CREATED`, while preserving dispatch, report, and observation as independent appended facts. This is a bounded implementation Reality finding rather than a silent `ACTIVE` / `SUCCEEDED` / `FAILED` enum expansion. A stale post-execution generation retains its report, observation, and Work Product history but gains no current PWU authority.

The explicit local ordering is preparation persisted → dispatch fact persisted → provider execution → Provider Report persisted → independent observation and Work Product References persisted. It does not claim a global PostgreSQL/provider/filesystem/Git transaction or exactly-once provider execution. General crash/`UNKNOWN` reconciliation across these boundaries remains S5 work.

S2B-01 through S2B-19 and the S2-B migration validation pass against PostgreSQL 17.6, ephemeral real Git repositories, and real Attempt worktrees. S2B-20 Existing Regression is satisfied by the retained S1-A **5/5**, S1-B **14/14**, S1-C **21/21**, and S2-A **21/21** results. The full suite is **81/81 PASS**. Downgrade to `20260828_02` and re-upgrade to `20260828_03` pass.

The factual combinations Provider `SUCCESS` with expected work absent, Provider `SUCCESS` with unrelated work, Provider `SUCCESS` with no workspace change, and Provider `FAILURE` with real artifact changes are executable and durable. None is converted into a Completion judgment in S2-B.

The accepted S2 path is:

```text
Durable PWU
↓
Context Package Lite
↓
Executor Capability Binding
↓
Attempt-specific isolated workspace
↓
execution-readiness revalidation
↓
Runtime-controlled dispatch
↓
Provider Report
↓
independent Repository / Artifact Observation
↓
Observed Work Product References
```

The closure preserves `Provider SUCCESS != Observed Work Product != PWU Produced != PWU Satisfied != Verification PASS != Trusted Baseline`. Execution Reality remains represented by append-oriented Attempt, Preparation Binding, Dispatch Fact, Provider Report, Repository Observation, and Work Product Reference facts without adding unauthorized `PREPARED`, `RUNNING`, or `FINISHED` Attempt states. Provider Report and independently observed repository Reality remain separate dimensions. No arbitrary-crash exactly-once execution is claimed; general cross-system reconciliation/recovery remains later work.

The next bounded stage is the trust path from observed Work Product Reality through Completion evaluation, PWU Produced/Satisfaction semantics, Verification/Qualification, and Candidate/Governance. Section 45 defines that S3 contract. S3 remains **NEXT / NOT STARTED** and is not authorized for implementation.

The exact next governed step is:

> Architecture Lead Reality Review of the admitted S3 contract → if PASS, authorize S3-A Completion Evaluation & Produced Semantics implementation.

## 45. S3 Completion, Verification & Candidate Governance stage contract

This section admits the documentation-level contract for the governed trust path after S2. It defines semantic boundaries and future implementation evidence only. It does not authorize S3-A, S3-B, or S3-C implementation and changes no production code, schema, migration, repository ref, Runtime state, or Trusted Baseline.

```text
S3 — Completion, Verification & Candidate Governance
    NEXT / NOT STARTED

S3-A — Completion Evaluation & Produced Semantics
    NEXT / NOT STARTED

S3-B — Verification Qualification & Satisfaction
    BLOCKED BY S3-A / NOT STARTED

S3-C — Candidate Sealing & Human Governance
    BLOCKED BY S3-B / NOT STARTED
```

The admitted conceptual flow is:

```text
Observed Repository Reality
+ Work Product References
+ Completion Contract
↓
S3-A Completion Evaluation
↓
PWU Produced
↓
Exact Proposed Repository Snapshot
(non-authoritative Git commit/tree)
↓
S3-B Verification
↓
Qualification
↓
PWU Satisfied
↓
S3-C Candidate Sealing
↓
Human Candidate Authorization
↓
S4 Repository Integration & Runtime Commit
```

The stage preserves this hard boundary:

```text
Human Candidate Authorization
!=
Repository Integration
!=
Runtime Commit
```

S3 must not advance an authoritative Git ref, integrate a proposed snapshot, or advance the Current Trusted Baseline.

### 45.1 S3-A — Completion Evaluation & Produced Semantics

S3-A answers:

> Does the independently observed production output satisfy the PWU's production-output obligations?

It does not answer whether the output is independently verified, qualified, satisfied, trusted, accepted, integrated, or committed.

#### Exact Completion Evaluation basis

Every Completion Evaluation must bind the exact:

- PWU;
- Plan Revision;
- Source Trusted Baseline;
- Completion Contract version and fingerprint;
- Repository Observation identity and fingerprint;
- Work Product References;
- Attempt and execution-generation lineage.

Mutable current workspace Reality is not an admissible evaluation subject without an exact accepted Repository Observation. A materially different Observation requires a new Completion Evaluation or equivalent governed reconciliation. Historical evaluation facts are immutable and must not be rewritten.

#### Output-obligation evaluation

S3-A evaluates the already-admitted production-output obligations where present, including:

- `required_artifacts`;
- `required_changes`;
- `required_markers`;
- `forbidden_changes`;
- blocking output conditions.

`verification_obligations` are not Completion Evaluation inputs for the `Produced` judgment. They remain part of the full PWU Completion Contract and are evaluated through S3-B before Satisfaction.

#### Provider Report has no Completion authority

```text
Provider SUCCESS
!=
PWU Produced

Provider FAILURE
!=
PWU Not Produced
```

Completion derives from the exact Completion Contract production-output obligations plus independently observed Reality, not provider narrative. The required benchmark semantics are:

| Provider report / observed Reality | Completion judgment |
|---|---|
| `SUCCESS` + required artifact absent | NOT PRODUCED |
| `SUCCESS` + only unrelated artifact changed | NOT PRODUCED |
| `SUCCESS` + workspace unchanged | NOT PRODUCED |
| `FAILURE` + exact required output obligations satisfied | Provider failure remains historical fact; it does not by itself block factual Produced judgment |

The final case still requires independent Verification in S3-B.

#### Produced semantics

```text
Observed Work Product
!=
PWU Produced
```

`PWU Produced` means that the exact independently observed output satisfies the Completion Contract's production-output obligations. It does not mean `Verified`, `Satisfied`, `Trusted`, `Accepted`, `Integrated`, or `Committed`.

This contract reuses the existing admitted `PRODUCED != SATISFIED` lifecycle semantics. If its physical representation is not already sufficient, the exact representation remains a later S3-A implementation-review decision; this contract does not invent an incompatible state or schema.

### 45.2 S3-B — Verification Qualification & Satisfaction

S3-B answers:

> Is the produced result independently verified against the exact subject and required verification obligations?

SPG coordinates Verification requirements, evidence admissibility, and production-state eligibility. It does not become the permanent owner of generic Assurance truth. The capability boundary remains:

```text
SPG
↓
Verification / Assurance Capability Contract
↓
FVS Deterministic Verification Provider
or future Guardian
```

SPG Core must not depend on Guardian internals. FVS-1 may use deterministic Verification; full Guardian integration is not required.

#### Exact proposed repository snapshot

Before Verification, the exact produced repository Reality is frozen as a non-authoritative proposed repository snapshot. For FVS-1, this may be an exact Git commit object plus Git tree identity derived from the independently observed Attempt workspace.

```text
Git Commit Object
!=
Repository Integration
!=
Runtime Commit
```

Creating this proposed commit/tree must not advance a target ref, merge, push, change an authoritative branch, or advance the Trusted Baseline. It exists only as an immutable Verification and Candidate subject.

The proposed snapshot must correspond exactly to the Repository Observation accepted by S3-A. If workspace Reality changed after that Observation, Runtime must not create a new snapshot while reusing the old Completion Evaluation. It requires a new Observation followed by a new Completion Evaluation, or equivalent governed reconciliation.

#### Verification basis and admissibility

Every Verification Record must bind the exact:

- PWU;
- Completion Evaluation;
- proposed repository commit/tree;
- Source Trusted Baseline;
- Plan Revision;
- verification obligation;
- verification provider.

A PASS without an exact subject and basis is not admissible.

```text
Verification Result
!=
Verification Applicability / Freshness
```

A historically valid PASS must not automatically apply after the subject, proposed snapshot, Plan Revision, Source Baseline, obligation, or other relevant Verification basis changes. Historical Verification facts remain preserved even when no longer applicable.

#### Qualification

For S3-B, SPG production qualification is the governed admissibility determination that:

- required Verification obligations exist;
- all required admissible Verification Evidence is present;
- Evidence binds the exact subject;
- Evidence remains applicable and fresh;
- no required Verification result blocks qualification.

Production qualification is not a generic Trust Score. Guardian / Verification retains ownership of Evidence interpretation, Findings, assurance truth, assurance-level Qualification, Gate results, and assurance confidence or coverage semantics. SPG consumes those conclusions through the capability contract and determines whether the required exact-subject evidence is admissible and sufficient for the governed production-state transition.

#### PWU Satisfaction

```text
PWU Produced
!=
PWU Satisfied
```

A PWU may become Satisfied only when its production-output obligations are Produced and all required Verification / Qualification obligations are satisfied, together with any other applicable Completion Contract conditions. Provider `SUCCESS` cannot directly create Satisfaction.

### 45.3 S3-C — Candidate Sealing & Human Governance

S3-C answers:

> Can this satisfied production result be sealed as the exact candidate that Human Authority may authorize for later integration?

#### Candidate eligibility

For the intentionally narrow FVS-1 path, Candidate formation requires at minimum:

- current Plan Revision;
- exact Source Trusted Baseline;
- required PWU or PWUs Satisfied;
- exact Completion Evaluation;
- exact applicable Verification / Qualification;
- exact proposed repository snapshot;
- no known blocking eligibility condition.

Existing Plan Completion semantics remain authoritative where applicable. One PWU's Satisfaction must not be silently generalized into arbitrary future multi-PWU Plan completion. S3-C does not introduce a general policy engine.

#### Sealed Candidate content and immutability

A sealed Baseline Candidate binds the exact:

- Candidate identity;
- Source Trusted Baseline;
- Production Run;
- Plan Revision;
- target repository identity;
- target authoritative ref;
- expected source repository revision;
- proposed repository commit and tree;
- PWU and Work Product lineage;
- Completion Evaluation;
- Verification / Qualification records;
- creation timestamp;
- Candidate fingerprint or equivalent immutable identity.

Material Candidate contents must not silently mutate after sealing. Material change requires a new Candidate identity or revision and renewed applicable evaluation and Verification.

```text
Candidate SEALED
!=
Candidate Authorized
!=
Repository Integrated
!=
Runtime Committed
!=
Trusted Baseline
```

Candidate creation does not change the Current Trusted Baseline.

#### Exact Human Candidate Authorization

Human Candidate Authorization must bind at minimum:

- authority identity;
- exact Candidate identity and fingerprint;
- authorized scope;
- expected Source Baseline and repository source revision;
- target repository and ref scope;
- rationale or basis;
- timestamp.

Generic authorization such as `approve latest` is invalid. Authorization applies to one exact immutable Candidate and cannot silently carry forward to modified Candidate material.

> Authority changes governance permission, not engineering Reality.

Human Authorization cannot convert Verification `FAIL` to `PASS`, create a missing Artifact, or make stale Evidence fresh. Risk acceptance or exceptions, if later required, remain explicit and distinct; S3-C does not add broad exception machinery.

Authorization does not execute integration. S3-C stops after recording exact Candidate Authorization and must not advance a Git ref, perform repository CAS, merge, push, perform Runtime Commit, or change the Trusted Baseline pointer. Those operations belong exclusively to S4.

### 45.4 Relationship to S4

```text
S3 output:

SEALED Candidate
+ exact Human Authorization

↓

S4 input:

authorized exact Candidate
+ expected Source Baseline
+ expected source Git revision

↓

Repository Integration Effect
+ authoritative ref CAS
+ Runtime Commit
+ new Trusted Baseline
```

S3 defines no S4 execution behavior. Only later successful Runtime Commit may advance the Current Trusted Baseline.

### 45.5 S3 invariants

1. Executor Report does not determine Completion.
2. Completion binds the exact Completion Contract production-output obligations and independent Observation.
3. Completion Evaluation is immutable and history-preserving.
4. A changed Observation prevents silent reuse of an old Completion Evaluation.
5. Observed Work Product does not imply Produced.
6. Produced does not imply Satisfied.
7. Verification binds an exact immutable proposed repository subject.
8. A proposed Git commit/tree is not Repository Integration.
9. Verification PASS and applicability/freshness are distinct.
10. Verification for a changed subject cannot be silently reused.
11. SPG owns Verification requirements and admissibility use, not generic Assurance truth.
12. Future Guardian remains independently replaceable and integrable.
13. Satisfaction requires Produced plus required qualified Verification and applicable Completion Contract conditions.
14. Candidate formation requires exact satisfied production lineage.
15. A sealed Candidate is immutable; material change creates a new Candidate revision or identity.
16. A Candidate is not the Trusted Baseline.
17. Human Authorization binds an exact Candidate.
18. Human Authority changes permission, not facts.
19. Authorization does not perform Repository Integration.
20. Trusted Baseline advancement remains exclusively later Runtime Commit behavior.
21. Production Horizon `DOCUMENTATION` remains fully valid.
22. No Code Artifact is universally required.
23. Provider `FAILURE` does not erase independently satisfied production-output Reality.
24. Provider `SUCCESS` cannot create Produced or Satisfied by itself.
25. No Trust Score is required for FVS-1.

### 45.6 Future implementation evidence direction

Later separately authorized implementation must prove at minimum:

- `SUCCESS` plus missing required Artifact produces `NOT PRODUCED`;
- `SUCCESS` plus unrelated work produces `NOT PRODUCED`;
- `SUCCESS` plus no change produces `NOT PRODUCED`;
- `FAILURE` plus exact required output derives Completion from Reality rather than provider status;
- Produced plus missing Verification remains `NOT SATISFIED`;
- Verification PASS against an old snapshot is not applicable to a new snapshot;
- changing sealed Candidate content requires a new Candidate;
- authorization for Candidate C1 cannot authorize modified Candidate C2;
- an Authorized Candidate does not advance the repository ref or Trusted Baseline.

No tests are implemented by this contract-definition task.

### 45.7 Explicit non-goals and authorization boundary

This S3 contract does not authorize or implement:

- authoritative repository ref advancement;
- repository compare-and-swap;
- Repository Integration Effect;
- Runtime Commit;
- Trusted Baseline advancement;
- remote push or deployment;
- a general recovery engine, Saga, or 2PC;
- full Guardian implementation;
- Evidence Graph or Trust Score;
- general Policy DSL;
- AI Planner, full ECF, or Provider Registry;
- Web, API, or UI;
- real Codex dogfood.

Architecture Baseline remains **v0.1**. The required mainline state after this contract admission is:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    NEXT / NOT STARTED

S3-A
    NEXT / NOT STARTED

S3-B
    BLOCKED BY S3-A / NOT STARTED

S3-C
    BLOCKED BY S3-B / NOT STARTED

S4
    NOT STARTED
```

No S3 implementation authorization is granted. The exact next governed step is:

> Architecture Lead Reality Review of the admitted S3 contract → if PASS, authorize S3-A Completion Evaluation & Produced Semantics implementation.

## 46. S3-A implementation reality

S3-A Completion Evaluation & Produced Semantics is **CLOSED / PASS**. Architecture Lead Reality Review accepted the repository evidence with zero architecture blockers, zero implementation blockers, and no scope leakage. S3 remains **IN PROGRESS**. S3-B is now **NEXT / NOT STARTED** because the S3-A dependency is satisfied; S3-C remains **BLOCKED BY S3-B / NOT STARTED**. This closure admission does not authorize S3-B implementation.

Alembic revision `20260828_04` adds exactly one S3-A production table: `completion_evaluations`. The table stores immutable exact-basis Completion facts with Run, PWU, Plan Revision, Source Baseline, Attempt/generation, Completion Contract fingerprint, Repository Observation identity/fingerprint, exact Work Product lineage and set fingerprint, deterministic basis fingerprint, `PRODUCED` / `NOT_PRODUCED` outcome, structured obligation results, and creation time. The unique basis fingerprint and deterministic evaluation identity provide same-basis idempotency. No Verification, Qualification, Candidate, Authorization, Production Issue, External Effect, Repository Integration, or proposed-snapshot table was added.

The current PWU lifecycle now admits only the already-contracted `PRODUCED` condition in addition to `PROPOSED`. S3-A does not add `NOT_PRODUCED`, `VERIFYING`, `SATISFIED`, or `FAILED` states. A `NOT_PRODUCED` evaluation remains an append-only fact and leaves PWU condition unchanged. A current-generation `PRODUCED` evaluation atomically inserts the Completion Evaluation, advances the versioned PWU from `PROPOSED` to `PRODUCED` through optimistic concurrency, and appends Transition History in one PostgreSQL Unit of Work.

Completion derives only from the typed Completion Contract plus independently observed Reality. S3-A deterministically evaluates required output paths, required changed paths, required markers, forbidden path scopes, and declared blocking output conditions. `verification_obligations` are deliberately excluded. Provider Report outcome is not an input to the Produced judgment, so false-success cases remain `NOT_PRODUCED`, while Provider `FAILURE` plus exact satisfied output obligations may become `PRODUCED` without rewriting the historical failure report.

The accepted executable benchmark evidence is:

```text
Provider SUCCESS + missing required artifact → NOT_PRODUCED
Provider SUCCESS + unrelated work only       → NOT_PRODUCED
Provider SUCCESS + no required change        → NOT_PRODUCED
Provider FAILURE + exact required production-output obligations satisfied → PRODUCED
```

These judgments derive from the Completion Contract plus independent Repository Reality, never from provider narrative.

Before evaluation, Runtime re-observes the exact Attempt workspace with the S2-B Git observer and requires the resulting manifest/fingerprint to equal the bound Repository Observation. Content-dependent obligations additionally identify the bytes read through Git's path-aware blob identity, preserving Git clean-filter semantics and rejecting mutable workspace drift. A changed workspace cannot reuse an older Observation; the historical Observation and any prior Completion Evaluation remain unchanged.

The implemented S3-A path stops at:

```text
Completion Contract
+ exact Repository Observation
+ exact Work Product lineage
+ current PWU / Plan / Baseline / Attempt generation
↓
immutable Completion Evaluation
↓
PRODUCED or NOT_PRODUCED
↓
PWU PRODUCED only when exact output obligations pass
```

It does not execute Verification, create Verification Records or Guardian Findings, determine Qualification or Satisfaction, create a proposed Git snapshot, form or seal a Candidate, record Candidate Authorization, integrate a repository ref, perform Runtime Commit, or advance the Current Trusted Baseline.

```text
Observed Work Product
!=
PWU PRODUCED
!=
PWU SATISFIED
!=
Verification PASS
!=
Candidate
!=
Trusted Baseline
```

S3-A closes only Completion Evaluation and Produced semantics. It introduces no Verification, Satisfaction, Qualification, Candidate, or Authorization semantics.

S3A-01 through S3A-22 pass against PostgreSQL 17.6, ephemeral real Git repositories, real detached Attempt worktrees, the Deterministic Test Executor, and independent S2-B observation. The S3-A migration downgrade to `20260828_03` and re-upgrade to `20260828_04` pass. The S3-A module is **23/23 PASS**: 22 numbered scenarios plus migration validation. The pre-S3-A S1/S2 suite remains **81/81 PASS**, and the full suite is **104/104 PASS**.

Architecture Baseline remains **v0.1**. The mainline state at S3-A closure was:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    IN PROGRESS

S3-A
    CLOSED / PASS

S3-B
    NEXT / NOT STARTED

S3-C
    BLOCKED BY S3-B / NOT STARTED

S4
    NOT STARTED
```

The governed step at S3-A closure was:

> Architecture Lead confirms S3-A SOT closure → authorize S3-B Verification Qualification & Satisfaction.

That authorization was subsequently granted. The resulting S3-B implementation Reality is recorded below.

## 47. S3-B implementation reality

S3-B Verification Qualification & Satisfaction is **CLOSED / PASS**. Architecture Lead Reality Review accepted the implementation and local evidence with zero architecture blockers, zero implementation blockers, and no scope leakage. At S3-B closure, S3 remained **IN PROGRESS** and S3-C was **NEXT / NOT STARTED**. S3-C was subsequently authorized for controlled implementation; its resulting implementation Reality is recorded in Section 48.

Alembic revision `20260828_05` adds exactly three S3-B production tables: `proposed_repository_snapshots`, `verification_records`, and `production_admissibility_records`. No Candidate, Human Authorization, Repository Integration Effect, Runtime Commit, Production Issue, External Effect, Trust Score, Guardian Finding, or Evidence Graph table was added.

The Proposed Repository Snapshot is an immutable, non-authoritative Git commit/tree subject bound to the exact PWU, Plan Revision, Source Baseline, Attempt/generation, Completion Evaluation, Repository Observation, repository identity, and authoritative-ref revision. Runtime revalidates the accepted Observation before construction, builds the tree with a temporary Git index, verifies the commit delta against the exact observed change manifest, and proves the authoritative ref unchanged. Workspace drift rejects stale snapshot creation. Repeating the same exact basis returns the same durable snapshot; materially different Reality requires a new Observation, Completion Evaluation, and snapshot identity.

Verification runs through a provider-neutral Verification Capability Contract. The FVS deterministic provider uses that same seam and returns only `PASS`, `FAIL`, or `UNKNOWN` with lightweight structured evidence bound to the exact snapshot commit/tree and verification obligation. Verification Records also bind the Completion Evaluation, Plan Revision, Source Baseline, provider identity/version, and deterministic basis fingerprint. Same-basis/provider execution is idempotent; a deliberately different provider version creates a new immutable historical record rather than rewriting prior evidence.

Verification Result and applicability remain distinct. A historical `PASS` is preserved, while applicability is computed relationally against the exact current snapshot, Completion Evaluation, Plan Revision, Source Baseline, PWU, and obligation. A changed subject or basis makes old evidence non-applicable without changing its historical result. No arbitrary TTL is introduced.

Assurance / Verification capability owns evidence truth, verification execution/result, evidence interpretation, and assurance-level qualification. SPG separately owns the required verification obligations, exact production-context evidence admissibility, and PWU Satisfaction decision. For every required obligation, a Verification Record must exist, bind the exact subject, remain applicable, and return `PASS`; `FAIL`, `UNKNOWN`, missing, stale, partial, or wrong-subject evidence blocks production admissibility. No synthesized Trust Score or risk-acceptance shortcut is used.

When the complete required PASS set is admissible for the current production lineage, one PostgreSQL Unit of Work appends the production-admissibility fact, advances the versioned PWU from `PRODUCED` to `SATISFIED` through optimistic concurrency, and appends Transition History. Injected failure rolls the whole authoritative action back. Historical stale-generation evidence remains durable but cannot regain current Satisfaction authority.

The implemented S3-B path stops at:

```text
PWU PRODUCED
+ exact Completion Evaluation
+ exact non-authoritative Proposed Repository Snapshot
+ required exact Verification Records
+ relational applicability / freshness
↓
SPG production admissibility
↓
PWU SATISFIED
```

It preserves:

```text
PRODUCED
!=
Verification PASS
!=
Applicable Verification
!=
PWU SATISFIED
!=
Candidate
!=
Authorized
!=
Integrated
!=
Trusted Baseline
```

S3B-01 through S3B-27 pass against PostgreSQL 17.6, real ephemeral Git repositories and worktrees, actual detached commit/tree objects, the existing Deterministic Test Executor, S3-A Completion Evaluation, and the Deterministic Verification Provider. Migration downgrade to `20260828_04` and re-upgrade to `20260828_05` pass. The S3-B module is **28/28 PASS**: 27 numbered scenarios plus migration validation. The pre-S3-B suite remains **104/104 PASS**, and the full suite is **132/132 PASS**.

Architecture Baseline remains **v0.1**. The mainline state at S3-B closure was:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    IN PROGRESS

S3-A
    CLOSED / PASS

S3-B
    CLOSED / PASS

S3-C
    NEXT / NOT STARTED

S4
    NOT STARTED
```

The exact governed step at S3-B closure was:

> Architecture Lead review of S3-C implementation scope and explicit authorization of S3-C — Candidate Sealing & Human Governance.

That authorization was subsequently granted. The resulting S3-C implementation Reality is recorded below.

## 48. S3-C implementation reality

S3-C Candidate Sealing & Human Governance is **CLOSED / PASS**. Architecture Lead Reality Review accepted the implementation and local validation evidence with zero architecture blockers, zero implementation blockers, and no scope leakage. Because S3-A, S3-B, and S3-C are all CLOSED / PASS, S3 Completion, Verification & Candidate Governance is also **CLOSED / PASS**. S4 Repository Integration & Runtime Commit is **NEXT / NOT STARTED** and remains unauthorized.

Alembic revision `20260828_06` adds exactly two S3-C production tables: `baseline_candidates` and `human_authorizations`. Existing `governance_records` and `transition_history` are reused for exact Human permission and append-only lifecycle history. No Repository Integration, Runtime Commit, External Effect, Production Issue, Trust Score, Guardian Finding, Evidence Graph, authentication, RBAC, or workflow-engine table was added.

A Baseline Candidate is created only from one exact current FVS-1 production basis: a `SATISFIED` PWU; its current Run, Plan Revision, Source Trusted Baseline, Attempt generation, Completion Evaluation, Work Product References, Proposed Repository Snapshot, exact applicable Verification `PASS` records, and `ADMISSIBLE` Production Admissibility record. Candidate sealing locks the Current Trusted Baseline pointer, Run, and versioned PWU within the PostgreSQL Unit of Work, rejects stale expected versions and generations, and revalidates all relational lineage before writing.

The Candidate durably binds the repository identity, target authoritative ref, expected source revision, proposed commit/tree, satisfied PWU set, Completion Evaluation set, Work Product Reference set, exact selected Verification Record set, and Production Admissibility identity/basis. Its canonical SHA-256 fingerprint covers every authority-relevant identity and basis fingerprint. The Candidate ID is deterministically derived from that fingerprint. Repeating the same exact basis returns the same logical Candidate; any material basis change yields a different fingerprint and Candidate. The record is frozen and exposes no update-in-place application operation.

Before a new Candidate is sealed, Runtime validates that the current authoritative repository ref still equals the Candidate's expected source revision and that the stored proposed commit/tree objects remain exact. Divergence rejects new sealing without reset, merge, rebase, cherry-pick, push, or ref movement. A previously sealed Candidate remains immutable historical fact, while later S4 must independently revalidate whether it is still actionable.

Human Authorization requires an explicit Candidate ID, the exact 64-character Candidate fingerprint, an explicit authority identity, and a structured scope that exactly matches the Candidate's repository identity, target authoritative ref, expected source revision, and proposed repository revision. There is no `approve latest` or implicit-current lookup. The authorization record, exact Governance Record, and Transition History commit atomically. A deterministic basis fingerprint provides retry idempotency for the same authority/Candidate/fingerprint/scope, while a different authority or Candidate creates new append-only history.

Human Authorization changes permission only. It cannot create a Candidate that failed eligibility, convert Verification `FAIL` or `UNKNOWN` to `PASS`, manufacture missing or fresh evidence, move a PWU from `PRODUCED` to `SATISFIED`, repair a diverged repository source, integrate a ref, advance the Current Trusted Baseline, or perform Runtime Commit. The PWU remains `SATISFIED`; Candidate and Authorization are separate governed records.

The implemented S3-C path stops at:

```text
PWU SATISFIED
+ exact current production lineage
+ exact Proposed Repository Snapshot
+ exact applicable Verification / Production Admissibility
+ current repository-source guard
↓
immutable SEALED Baseline Candidate
↓
exact append-only Human Authorization
```

It preserves:

```text
SATISFIED
!=
SEALED Candidate
!=
Human Authorized
!=
Repository Integrated
!=
Runtime Committed
!=
Trusted Baseline
```

S3C-01 through S3C-32 pass against PostgreSQL 17.6, real ephemeral Git repositories and isolated worktrees, actual detached proposed commit/tree objects, the Deterministic Test Executor, S3-A Completion Evaluation, and S3-B Verification/Satisfaction. Migration downgrade to `20260828_05` and re-upgrade to `20260828_06` pass. The S3-C module is **33/33 PASS**: 32 numbered scenarios plus migration validation. The accepted pre-S3-C suite remains **132/132 PASS**, and the full suite is **165/165 PASS**. `git diff --check` passes. Architecture Lead Reality Review is **PASS**; architecture blockers are **0**, implementation blockers are **0**, and scope leakage is **NONE**.

Architecture Baseline remains **v0.1**. The mainline state at S3 closure was:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    CLOSED / PASS

S3-A
    CLOSED / PASS

S3-B
    CLOSED / PASS

S3-C
    CLOSED / PASS

S4
    NEXT / NOT STARTED
```

The exact governed step at S3 closure was:

> Architecture Lead review of S4 — Repository Integration & Runtime Commit implementation scope and explicit S4 authorization.

Architecture Lead subsequently split S4 into S4-A Authorized Repository Integration and S4-B Runtime Commit, and authorized only S4-A. The resulting implementation Reality is recorded below.

## 49. S4-A implementation reality

S4-A Authorized Repository Integration is **CLOSED / PASS**. Architecture Lead Reality Review accepted the implementation and local validation evidence with zero architecture blockers, zero implementation blockers, and no scope leakage. At S4-A closure, S4 remained **IN PROGRESS** and S4-B Runtime Commit was **NEXT / NOT STARTED**. S4-B was subsequently authorized for controlled implementation; its resulting implementation Reality is recorded in Section 50.

Alembic revision `20260829_07` adds exactly one S4-A production table: `repository_integration_effects`. It represents only `REPOSITORY_REF_ADVANCE` with the narrow states `PREPARED` and `CONVERGED`. No Runtime Commit, Trusted Baseline Candidate admission, generalized External Effect platform, Saga, compensation, recovery engine, remote-push, deployment, Production Issue, Guardian, ECF, authentication, RBAC, or UI table was added.

Repository Integration requires an exact `SEALED` Candidate and exact Human Authorization. Runtime revalidates Candidate fingerprint, Authorization Candidate/fingerprint and scope, repository identity, target authoritative ref, expected source revision, proposed commit/tree, Current Trusted Baseline relationship, current Run/Plan lineage, `SATISFIED` PWU set, exact Verification `PASS` records, and `ADMISSIBLE` Production Admissibility. Missing, wrong, stale, or mismatched authority or production basis rejects preparation.

The stable operation fingerprint binds effect type, Candidate identity/fingerprint, Human Authorization identity, repository identity, target ref, expected source revision, and proposed revision. The effect ID is deterministically derived from that fingerprint, and the database unique constraint prevents unrelated duplicate logical operations. Same-basis retries resolve to the same durable effect.

S4-A orders the effect as:

```text
validate exact Candidate + Authorization
↓
persist PREPARED effect + Transition History
↓
commit PostgreSQL Unit of Work
↓
Git authoritative-ref compare-and-swap
↓
independent authoritative-ref observation
↓
persist CONVERGED + Transition History
```

The Git adapter exposes only factual local operations: `read_ref`, `commit_exists`, `read_commit_tree`, and exact old-value `compare_and_swap_ref`. It uses the sealed Candidate's existing proposed commit and never reconstructs it. The mutation is equivalent to `git update-ref <target> <proposed> <expected-old>`; divergence blocks mutation without force update, reset, merge, rebase, cherry-pick, push, or overwrite.

Git command success is not convergence evidence. Only a separate ref observation equal to the exact proposed revision permits `CONVERGED`. Wrong or diverged observations leave the effect `PREPARED` with observed repository reality. Candidate, Authorization, Verification, Production Admissibility, and PWU facts remain unchanged; PWU remains `SATISFIED`.

S4-A preserves both non-atomic interruption windows. Failure before Git CAS leaves the ref unchanged and the durable effect `PREPARED`. Failure after Git CAS but before `CONVERGED` persistence can leave the authoritative ref at the proposed revision while the effect remains `PREPARED`. A same-operation retry does not blindly repeat CAS or claim exactly-once execution; the unresolved state remains available for later separately authorized S5 reconciliation. S4-A implements no general recovery algorithm.

After successful S4-A:

```text
authoritative repository ref = exact proposed commit
Repository Integration Effect = CONVERGED
Current Trusted Baseline Pointer = unchanged
Candidate = SEALED
PWU = SATISFIED
Runtime Commit = not executed
```

This preserves:

```text
Git Commit Object
!=
Repository Integration
!=
SPG Runtime Commit
```

S4A-01 through S4A-31 pass against PostgreSQL 17.6 and real ephemeral Git repositories, exact detached proposed commit/tree objects, real old-value guarded ref updates, independently observed refs, injected transaction/process interruption windows, and the completed S1–S3 production lineage. Migration downgrade to `20260828_06` and re-upgrade to `20260829_07` pass. The S4-A module is **32/32 PASS**: 31 numbered scenarios plus migration validation. The accepted pre-S4-A suite remains **165/165 PASS**, and the full suite is **197/197 PASS**. `git diff --check` passes. Architecture Lead Reality Review is **PASS**; architecture blockers are **0**, implementation blockers are **0**, and scope leakage is **NONE**.

Architecture Baseline remains **v0.1**. The mainline state at S4-A closure was:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    CLOSED / PASS

S4
    IN PROGRESS

S4-A
    CLOSED / PASS

S4-B
    NEXT / NOT STARTED
```

The exact governed step at S4-A closure was:

> Architecture Lead review and explicit authorization of S4-B — Runtime Commit.

That authorization was subsequently granted. The resulting S4-B implementation Reality is recorded below.

## 50. S4-B implementation reality

S4-B Runtime Commit is **CLOSED / PASS**. Architecture Lead Reality Review accepted the implementation and local validation evidence with zero architecture blockers, zero implementation blockers, and no scope leakage. Because S4-A and S4-B are both CLOSED / PASS, S4 Repository Integration & Runtime Commit is also **CLOSED / PASS**. S5 Failure / Recovery Hardening is **NEXT / NOT STARTED** and is not authorized.

Alembic revision `20260829_08` adds exactly one S4-B production table: `runtime_commits`. Existing immutable `production_snapshots`, the versioned singleton `current_trusted_baseline_pointer`, and append-only `transition_history` are reused. The Runtime Commit record links one exact Candidate, Human Authorization, `CONVERGED` Repository Integration Effect, Source and new Trusted Baselines, Run/Plan, repository commit/tree, SATISFIED PWU set, Completion set, Verification set, and Production Admissibility basis. No Candidate or PWU lifecycle state is added.

Runtime Commit revalidates the exact governed basis inside one PostgreSQL Unit of Work: `SEALED` Candidate and fingerprint; exact Human Authorization identity/fingerprint/scope; exact `CONVERGED REPOSITORY_REF_ADVANCE` operation; Current Trusted Baseline Pointer and Source Baseline; current Run/Plan and `SATISFIED` PWU lineage; exact `PRODUCED` Completion Evaluations and Work Product References; exact Verification `PASS` records; and exact `ADMISSIBLE` Production Admissibility. Validity remains relational rather than inferred from historical Candidate sealing.

The same transaction independently reads the authoritative repository ref and requires the exact proposed revision, then revalidates that commit object's exact tree. A persisted S4-A `CONVERGED` state alone is insufficient. S4-B performs only `read_ref`, `commit_exists`, and `read_commit_tree`; it never executes Git CAS, ref update, merge, rebase, reset, cherry-pick, force, repository repair, or push.

The locally atomic transition is:

```text
lock and revalidate Current Source Baseline Pointer
↓
independently observe exact repository ref / commit / tree
↓
create immutable next TRUSTED production Snapshot
↓
persist exact Runtime Commit linkage
↓
advance pointer with expected Source Baseline + expected version
↓
append Runtime Commit and pointer Transition History
↓
commit PostgreSQL Unit of Work
```

Any failure in that transaction rolls back the new Snapshot, Runtime Commit record, pointer advance, and history together. Repository Reality remains at the already-converged revision. Prior Trusted Baselines remain immutable historical production truth.

A canonical commit fingerprint binds every authority-relevant identity and exact production basis; deterministic Runtime Commit and Trusted Baseline IDs plus database uniqueness provide same-basis retry recognition. An uncertain-response retry returns the same logical commit and does not create duplicate baselines. Pointer locking, expected version, and exact expected Source Baseline prevent a second Candidate derived from the same source from overwriting a baseline committed first. This is local PostgreSQL idempotency and concurrency protection, not a cross-system exactly-once claim.

After successful S4-B:

```text
authoritative repository ref = Candidate proposed revision
Repository Integration Effect = CONVERGED
new Trusted Baseline = exact Candidate repository reality
Current Trusted Baseline Pointer = new Trusted Baseline
Candidate = SEALED
PWU = SATISFIED
```

This preserves:

```text
Git Commit Object
!=
Repository Integration
!=
SPG Runtime Commit
```

S4B-01 through S4B-32 pass against PostgreSQL 17.6 and real ephemeral Git repositories, independently re-read authoritative refs and commit trees, exact S1–S4-A lineage, injected transaction rollback, idempotent retry, and stale-source concurrency scenarios. Migration downgrade to `20260829_07` and re-upgrade to `20260829_08` pass. The S4-B module is **33/33 PASS**: 32 numbered scenarios plus migration validation. The accepted pre-S4-B suite remains **197/197 PASS**, and the full suite is **230/230 PASS**. `git diff --check` passes. Architecture Lead Reality Review is **PASS**; architecture blockers are **0**, implementation blockers are **0**, and scope leakage is **NONE**.

Architecture Baseline remains **v0.1**. The mainline state at S4 closure was:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    CLOSED / PASS

S4
    CLOSED / PASS

S4-A
    CLOSED / PASS

S4-B
    CLOSED / PASS

S5
    NEXT / NOT STARTED
```

The exact governed step at S4 closure was:

> Architecture Lead review of S5 — Failure / Recovery Hardening implementation scope and explicit S5 authorization.

Architecture Lead subsequently authorized only S5-A Recovery Classification & Reconciliation Foundation. The resulting implementation Reality is recorded below.

## 51. S5-A implementation reality

S5-A Recovery Classification & Reconciliation Foundation is **CLOSED / PASS** after Architecture Lead Reality Review **PASS**. At S5-A closure, S5 remained **IN PROGRESS**, and no later recovery slice or S6 work was authorized or started. The subsequently authorized S5-B and S5-C results are recorded below.

Alembic revision `20260829_09` adds exactly one S5-A production table: `recovery_assessments`. The governing order is **Classify Before Recover**: recover knowledge before execution. An assessment uses one of two narrow exact subjects: an Attempt identity plus expected PWU/generation, or a Repository Integration Effect identity plus expected operation fingerprint. Structured `governed_basis`, `observed_facts`, and `differences` retain only facts applicable to that subject rather than introducing a universal nullable incident record. Recovery Assessments are immutable and append-only. The canonical basis fingerprint and deterministic assessment ID make the same exact observed/governed basis idempotent; changed observed Reality creates a new immutable historical assessment. Transition History records each newly classified assessment.

The admitted classification vocabulary is `COHERENT`, `RECOVERABLE`, `UNKNOWN`, `DIVERGED`, `STALE`, and `BLOCKED`. It preserves `Failure != Divergence`, Provider Report is not Production Truth, `Historical Fact != Current Authority`, and stale generation evidence cannot regain current authority. Every assessment also records whether the subject remains current, whether recovery appears safely possible, whether Human Attention is required, whether a Recovery Barrier applies, and one advisory lowest-sufficient guidance class such as `NO_ACTION`, `REOBSERVE`, `RESUME_EXISTING_ATTEMPT`, `RETRY_WITH_NEW_ATTEMPT`, `RECORD_EXTERNAL_CONVERGENCE`, `RETRY_RUNTIME_COMMIT`, `REPLAN_SUPERSEDE`, or `ESCALATE_DIVERGENCE`. Guidance is not execution authorization, and unrelated work that remains valid is preserved.

Known S5-A classifications include:

| Observed window | Classification / guidance |
|---|---|
| interrupted dispatched Attempt with missing outcome/observation | `UNKNOWN / REOBSERVE` |
| Provider SUCCESS with no observed change | `BLOCKED / REOBSERVE` |
| Provider FAILURE with observed Work Products | `RECOVERABLE / REOBSERVE` |
| Provider UNKNOWN with observed changes | `UNKNOWN / REOBSERVE` |
| stale Attempt generation | `STALE / REPLAN_SUPERSEDE` |
| Effect PREPARED and ref at expected source | `RECOVERABLE / REOBSERVE` |
| Effect PREPARED and ref at proposed commit/tree | `RECOVERABLE / RECORD_EXTERNAL_CONVERGENCE` |
| Effect PREPARED and ref at unrelated third revision | `DIVERGED / ESCALATE_DIVERGENCE` |
| Effect CONVERGED, ref proposed, Runtime Commit absent, pointer at source | `RECOVERABLE / RETRY_RUNTIME_COMMIT` |
| Runtime Commit exists and pointer/ref match committed Reality | `COHERENT / NO_ACTION` |

An unresolved assessment exposes the minimum Recovery Barrier guard: a caller cannot silently treat `UNKNOWN`, `DIVERGED`, `STALE`, `BLOCKED`, or other unresolved recovery state as coherent forward progress. The guard performs no recovery action. S5-A does not dispatch or resume a provider, create a retry Attempt, alter a workspace, update a Git ref, mark an Effect `CONVERGED`, execute Runtime Commit, advance the Trusted Baseline, replan, compensate, schedule jobs, or run a background worker. Original Attempt, Provider Report, Observation, Work Product, Candidate, Effect, Runtime Commit, Baseline, Plan, and PWU facts remain unchanged.

Architecture Lead watch item: recovery classification must remain governed by expected obligations and Completion Contract semantics. Absence of Git changes is not a universal platform rule for abnormal production because valid non-code or non-repository PWUs may exist. This caution changes no S5-A implementation and creates no new authorization.

S5A-01 through S5A-32 pass against PostgreSQL 17.6, real ephemeral Git repositories/worktrees, known S2/S4 interruption windows, Provider outcome/Reality mismatches, stale generations, independently observed refs/trees, existing Runtime Commit recognition, idempotent reassessment, and Recovery Barrier enforcement. Migration downgrade to `20260829_08` and re-upgrade to `20260829_09` pass. The S5-A module is **33/33 PASS**: 32 numbered scenarios plus migration validation. The accepted pre-S5-A suite remains **230/230 PASS**, and the full suite is **263/263 PASS**. `git diff --check` passes. Architecture Lead Reality Review is **PASS**. Architecture blockers are **0**, implementation blockers are **0**, and scope leakage is **NONE**.

Architecture Baseline remains **v0.1**. The mainline state at S5-A closure was:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    CLOSED / PASS

S4
    CLOSED / PASS

S5
    IN PROGRESS

S5-A
    CLOSED / PASS
```

The exact governed step at S5-A closure was:

> Architecture Lead review of the next bounded S5 recovery slice.

That review does not authorize or start the slice.

## 52. S5-B implementation reality

S5-B Repository Integration & Runtime Commit Reconciliation is **CLOSED / PASS** after Architecture Lead Recovery Reality Review **PASS**. At S5-B closure, S5 remained **IN PROGRESS**, S5-A remained **CLOSED / PASS**, and no S5-C, other later recovery slice, or S6 work was authorized or started. Architecture Lead subsequently authorized the bounded S5-C slice recorded in section 53.

The original S5-B implementation Attempt remains **INTERRUPTED BY QUOTA / final outcome UNKNOWN**. It is not rewritten as success. Recovery inspection found the S5-B implementation intact, all six previously identified schema-baseline assertion updates present, no partial or corrupted edit, and no need for implementation repair. Lowest-sufficient recovery completed only the missing validation. The admitted history is therefore: Original Attempt **INTERRUPTED BY QUOTA**; Implementation Reality **COMPLETE**; Recovery Verification **PASS**; Architecture Lead Recovery Reality Review **PASS**. This is accepted dogfood evidence that Attempt outcome differs from implementation Reality, classification precedes recovery, Reality is recovered rather than history replayed, and recovery occurs at the lowest sufficient level.

Alembic revision `20260829_10` adds exactly one narrow table: `recovery_action_records`. Each append-only record binds one exact Recovery Assessment ID and basis fingerprint, one admitted action, the exact Repository Integration Effect and Candidate, the independently observed repository revision/tree, the stable action-basis fingerprint, outcome, optional exact Runtime Commit, and timestamp. It is resolution evidence separate from the immutable historical Assessment; it is not an incident platform, workflow engine, Saga, scheduler, or worker.

The application exposes only `record_external_convergence(...)` and `retry_runtime_commit_from_recovery(...)`, both requiring an explicit Assessment ID and exact 64-character assessment fingerprint. There is no recover-latest, fix-current, or project-wide recovery operation. Duplicate protection derives a stable action identity from the exact Assessment, action, integration/candidate lineage, and observed governed basis.

External-convergence reconciliation accepts only `RECOVERABLE / RECORD_EXTERNAL_CONVERGENCE`. It first regenerates the current exact Recovery Assessment, then locks and revalidates the current Candidate, Human Authorization, Source Baseline, Run/Plan, SATISFIED PWU, Verification PASS, Production Admissibility, Effect, repository identity, and target ref. Read-only Git operations independently require the exact proposed ref, existing commit, and exact proposed tree. Only then does one PostgreSQL transaction update `PREPARED → CONVERGED`, append Effect and Recovery Action history, and persist the Recovery Action. A failed transaction leaves the Effect `PREPARED`; Git Reality is never changed.

Runtime Commit reconciliation accepts `RECOVERABLE / RETRY_RUNTIME_COMMIT`, or recognizes an already coherent exact Runtime Commit as `NO_ACTION`. Before mutation it regenerates the current Assessment and rejects changed repository/runtime Reality. The operation constructs the ordinary exact S4-B request and calls the unchanged `RuntimeCommitService`, thereby retaining Candidate fingerprint, Human Authorization, CONVERGED Effect, Source Baseline locking/CAS, independently read repository ref/tree, Verification PASS, Production Admissibility, SATISFIED PWU, Plan/Run lineage, immutable Trusted Baseline, pointer advancement, rollback, concurrency, and idempotency rules. There is no weaker recovery-commit path. If the exact Runtime Commit already exists with coherent pointer and repository Reality, S4-B idempotency is recognized and a narrow `NO_ACTION` resolution is appended without duplicating a commit, baseline, or pointer advance.

Stale and divergent Reality remains protected:

| Current Reality | S5-B result |
|---|---|
| `PREPARED + expected source ref` | no Git CAS retry; remains unresolved / reobserve |
| `PREPARED + exact proposed ref/tree` | may record local convergence only |
| `PREPARED + unexpected third ref` | no convergence or Runtime Commit; remains diverged / escalated |
| assessment basis changed | selected historical Assessment is non-actionable; reassessment required |
| Source Trusted Baseline no longer current | Runtime Commit recovery blocked |
| exact coherent Runtime Commit already exists | `NO_ACTION`; no duplicate durable state |

Recovery never rewrites the originating Assessment to coherent, resolved, or successful. Its original Recovery Barrier and abnormal observation remain historical evidence. A future fresh Assessment may demonstrate `COHERENT / NO_ACTION`; only fresh coherence can permit normal continuation. This implements **History Is Appended, Not Rewritten**, **Classify Before Recover**, and lowest-sufficient recovery: local knowledge is repaired without replaying Git or the production chain.

S5B-01 through S5B-39 cover exact Assessment selection/fingerprint, immutable history, stale-basis detection, action/guidance eligibility, exact Candidate/Authorization and repository Reality, atomic convergence recording, injected rollback, duplicate safety, expected/proposed/third-ref distinctions, unchanged S4-B eligibility/atomicity/idempotency, existing-commit recognition, stale Source Baseline rejection, unchanged Candidate/PWU/Authorization, and all explicit non-goals. Together with migration downgrade/re-upgrade validation, the S5-B module is **40/40 PASS**. The accepted pre-S5-B suite remains **263/263 PASS**, and the full regression is **303/303 PASS**. Migration downgrade from `20260829_10` to `20260829_09` and re-upgrade pass. `git diff --check` passes. Architecture Lead Recovery Reality Review is **PASS**. Architecture blockers are **0**, implementation blockers are **0**, and scope leakage is **NONE**.

S5-B performs no Git update, CAS retry, merge, rebase, reset, cherry-pick, force update, push, repository repair, Attempt retry/resume, new Attempt generation, provider recovery, workspace mutation, replanning, Candidate regeneration, compensation, Saga, background reconciliation, S6, Codex integration, Guardian expansion, ECF expansion, or UI work.

Architecture Baseline remains **v0.1**. The mainline state at S5-B closure was:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    CLOSED / PASS

S4
    CLOSED / PASS

S5
    IN PROGRESS

S5-A
    CLOSED / PASS

S5-B
    CLOSED / PASS
```

The exact governed step at S5-B closure was:

> Architecture Lead review of the remaining bounded S5 recovery scope.

That was the governed state at S5-B closure. Architecture Lead subsequently authorized only S5-C; S6 remained unauthorized.

## 53. S5-C implementation reality

S5-C Execution Attempt & Workspace Recovery Hardening is **CLOSED / PASS** after Architecture Lead Reality Review **PASS**. S5-A and S5-B remain **CLOSED / PASS**. Because all three bounded recovery slices are closed, S5 Failure / Recovery Hardening is also **CLOSED / PASS**. S6 Real Codex Dogfood & FVS Closure is **NEXT / NOT STARTED** and is not authorized.

Alembic revision `20260829_11` extends the existing narrow `recovery_action_records` representation rather than adding a Runtime domain table. An Attempt recovery action binds the exact Recovery Assessment ID and fingerprint, old Attempt and generation, optional new Retry Attempt and generation, workspace identity, optional normal Repository Observation and Completion Evaluation, action-basis fingerprint, outcome, and timestamp. The historical Recovery Assessment, original Attempt, Provider Report, and existing workspace evidence remain unchanged. Same exact action basis has deterministic identity, so an uncertain repeated request does not create duplicate retry authority.

Every operation requires an explicitly selected ATTEMPT Recovery Assessment. That assessment is historical evidence, not permanent mutation authority. S5-C freshly reassesses the exact Attempt/PWU/generation and revalidates current Plan Revision, Current Trusted Baseline, PWU, Context Package, Source Baseline, and workspace existence before recovery mutation. Changed lineage, a stale generation, or workspace drift blocks mutation and requires a new exact assessment. A missing workspace is represented distinctly from an existing workspace with no relevant changes; no work is fabricated and the historical workspace is not recreated as original Reality.

**Salvage precedes retry.** For an existing prepared and dispatched Attempt workspace, S5-C reuses S2-B independent Repository Observation and the normal S3-A Completion Evaluation path against the admitted Completion Contract. Provider `SUCCESS`, `FAILURE`, or `UNKNOWN` does not establish production truth. If observed work is sufficient, it continues as ordinary `Observation → Completion Evaluation → PRODUCED` evidence and no Retry Attempt is created. There is no recovery-specific `PRODUCED` state. Absence of Git changes is not a universal failure or retry condition; the exact Completion Contract governs non-code and verification-only work as well as repository-producing work.

Only a current `RECOVERABLE / RETRY_WITH_NEW_ATTEMPT` assessment basis may create a Retry Attempt. The existing Runtime generation mechanism atomically locks and revalidates current authority, creates generation 2, advances only the PWU current-generation pointer, appends the exact Recovery Action and Transition History, and commits or rolls back those database facts together. Generation 1 remains immutable historical evidence and cannot regain authority or mutate generation 2 production state. S5-C then reuses S2-A Attempt preparation to provision a new clean isolated worktree bound to the exact Source Baseline, Plan, PWU, and new generation. It neither mutates nor blindly copies partial content from the old workspace.

Filesystem preparation remains outside the PostgreSQL transaction. A committed Retry Attempt and action with incomplete workspace provisioning therefore remain truthful and representable; an exact repeated request may idempotently complete the existing S2-A preparation. Attempt creation alone does not imply execution readiness. S5-C claims no PostgreSQL/filesystem exactly-once behavior.

`RESUME_EXISTING_ATTEMPT` is not silently converted to retry. S5-C records a governed unsupported/deferred result when generic provider Resume is unavailable. It performs no Executor dispatch, Provider reconnect/resume, Codex SDK/CLI call, automatic retry execution, partial workspace transplant, replanning, PWU supersession, Git mutation or reconciliation, Runtime Commit recovery, compensation, Saga, background recovery, Guardian/ECF expansion, UI work, or S6 work.

S5C-01 through S5C-41 cover exact Assessment selection and fingerprint, immutable history, stale-authority rejection, independent workspace reobservation, Provider outcome/Reality distinctions, Completion-governed salvage, the non-universal zero-diff rule, exact retry eligibility, new-generation authority, stale-generation protection, clean isolated retry workspaces, missing/drifted workspace behavior, local transaction rollback, duplicate safety, filesystem interruption truthfulness, no dispatch/resume/replanning, Recovery Barrier history, real interruption inspect-before-replay, documentation horizon, and explicit S6 non-goals. Together with migration downgrade/re-upgrade validation, the S5-C module is **42/42 PASS**. The accepted pre-S5-C suite remains **303/303 PASS**, and the full suite is **345/345 PASS**. Migration downgrade from `20260829_11` to `20260829_10` and re-upgrade pass. `git diff --check` passes. Architecture blockers are **0**, implementation blockers are **0**, and scope leakage is **NONE**.

Compilation is **PASS**, and Architecture Lead Reality Review is **PASS**.

S5 now supplies the sufficient FVS-level generic recovery foundation:

```text
Observe Reality
→ Classify
→ Preserve still-valid work
→ Reconcile at the lowest sufficient level
→ Re-enter the normal governed production path
```

S5-A supplies Recovery Classification & Reconciliation Foundation; S5-B supplies Repository Integration & Runtime Commit Reconciliation; S5-C supplies Execution Attempt & Workspace Recovery Hardening. Together they preserve **Classify Before Recover**, **Failure != Divergence**, **Attempt outcome != implementation reality**, **Recover knowledge before execution**, **Recover at the lowest sufficient level**, **History Is Appended, Not Rewritten**, and **No Actor Owns Production Truth Alone**. The real quota-interruption evidence admitted under S5-B remains historical Recovery Reality and is not rewritten by S5 closure.

Generic Provider Resume remains **NOT IMPLEMENTED**. Provider/session/thread-specific Resume is deferred until real Executor capability is observed during S6. This admitted boundary is not an S5 blocker and does not authorize S6.

Architecture Baseline remains **v0.1**. The current mainline state is:

```text
S1
    CLOSED / PASS

S2
    CLOSED / PASS

S3
    CLOSED / PASS

S4
    CLOSED / PASS

S5
    CLOSED / PASS

S5-A
    CLOSED / PASS

S5-B
    CLOSED / PASS

S5-C
    CLOSED / PASS

S6
    NEXT / NOT STARTED
```

The exact next governed step is:

> Architecture Lead S6 scope review: Real Codex Dogfood & FVS Closure.

S6 is not authorized or started by this closure admission.

## 54. S6-B1 Real Codex SDK Host Integration Spike reality

S6-B1 is **IMPLEMENTED — REAL SDK SPIKE PARTIAL** and **PENDING ARCHITECTURE LEAD REALITY REVIEW**. S6 is **IN PROGRESS**. S1 through S5 remain **CLOSED / PASS**. This result does not close S6-B1, S6, dogfood, or FVS-1.

The stable official Python package `openai-codex==0.147.0` and its pinned `openai-codex-cli-bin==0.147.0` runtime are exact project dependencies. A provider-neutral immutable Materialized Execution Input now durably binds the exact Attempt/generation, Run, PWU, Plan Revision, Source Baseline, Prepared Execution Request, Context Package identity/version/fingerprint, Completion Contract fingerprint, exact instruction, exact UTF-8 context projection, and canonical input fingerprint before dispatch. The Codex SDK Provider receives this complete input and has no database dependency.

`CodexSdkExecutor` preserves the existing synchronous Executor Capability Contract. It derives `cwd` only from the exact Attempt workspace, revalidates the registered detached worktree and Source Baseline, rejects the authoritative repository as workspace, uses `Sandbox.workspace_write` with deny-all interactive approval, and maps only a terminal completed SDK result to Provider `SUCCESS`. Provider output remains an untrusted claim without Completion, Verification, Candidate, Repository Integration, Runtime Commit, or Trusted Baseline authority. Provider Resume remains deferred.

The focused deterministic S6-B1 suite is **21/21 PASS**, comprising migration downgrade/re-upgrade plus S6B1-01 through S6B1-20. It covers exact input binding and stable fingerprint, workspace authority, conservative outcome mapping, public Provider identity mapping, independent observation disagreement, absence of downstream authority, no Provider database lookup, no Resume, no full-access sandbox, deterministic Executor regression, Documentation Horizon support, and no S6-C/FVS closure leakage.

Exactly one real ChatGPT-authenticated Codex SDK execution was launched against an ephemeral governed repository and exact detached Attempt worktree. No API-key environment was present. Codex changed only `docs/codex_real_execution_probe.md` from the admitted BEFORE marker to the admitted AFTER marker. The authoritative repository ref and working tree remained unchanged. After 120 seconds the stable SDK had not returned a terminal `TurnResult`, so the outer test conservatively interrupted the execution and did not retry. Consequently no terminal Provider Result, thread/turn correlation, or normal persisted Repository Observation was claimed.

A single post-failure diagnostic used the existing independent `GitWorkspaceObserver` without launching another Provider turn. It observed exactly one `MODIFIED` artifact with source blob `558faea8fb1d4500ad7dee71448c4a4f72c94c64`, observed blob `663dd481e013182bead5b8685de62c6b67ac9041`, and observation fingerprint `919193a22ea08df6c86947fc08ee55a648fd52664005d0de395701a0fbaf1f1c`. This diagnostic proves exact workspace mutation Reality but does not replace the missing governed Provider Result or persisted normal observation chain.

Architecture Baseline remains **v0.1**. At R2 implementation completion, the state was:

```text
S1–S5
    CLOSED / PASS

S6
    IN PROGRESS

S6-B1
    IMPLEMENTED — REAL SDK SPIKE PARTIAL
    PENDING ARCHITECTURE LEAD REALITY REVIEW
```

The next governed step is:

> Architecture Lead S6-B1 Reality Review and disposition of the stable SDK terminal-result limitation before any dedicated Executor boundary spike or additional real Provider execution.

## 55. S6-B1-R Provider Terminal & Identity Correlation Spike reality

S6-B1-R is **PARTIAL — PUBLIC LIFECYCLE MAPPING PASS / NEW REAL CORRELATION NOT EXECUTED**. S6-B1 remains **IMPLEMENTED — REAL SDK SPIKE PARTIAL / PENDING ARCHITECTURE LEAD REALITY REVIEW**; S6 remains **IN PROGRESS**. This spike does not close S6-B1 or authorize S6-B2, S6-C, Docker execution, Provider Resume, or FVS closure.

For stable `openai-codex==0.147.0`, the supported synchronous public surface exposes `Thread.id`, `Thread.turn(...)`, immediate `TurnHandle.id`, `TurnHandle.run()`, `TurnHandle.stream()`, `TurnHandle.interrupt()`, terminal `TurnResult`, `TurnCompletedNotification`, and `ErrorNotification`. `TurnResult` carries exact turn ID and status. The public terminal statuses are `completed`, `failed`, `interrupted`, and `inProgress`. The SDK exposes no timeout parameter on `Thread.run`, `Thread.turn`, `TurnHandle.run`, or `TurnHandle.stream`.

The prior probe used `Thread.run(...)`, which is a supported convenience call that waits for the complete terminal `TurnResult`. Repository Reality proves that the requested tool-side file mutation occurred before the outer 120-second boundary, while no `TurnResult` returned before interruption. The strongest evidence-backed classification is therefore: the public terminal lifecycle had not completed before the external timeout. The exact reason the Provider did not finalize after the mutation remains unknown; approval wait, runtime defect, or another internal cause is not claimed without evidence.

`CodexSdkExecutor` now starts the turn through public `Thread.turn(...)`, records public thread and turn identity before waiting, and waits once for the public terminal result. An optional bounded wait requests public `interrupt()` after timeout and always maps the timed-out Provider fact to `UNKNOWN`, even if independent observation proves that work exists. A terminal `completed` result with matching handle/result identity maps to Provider `SUCCESS`; terminal `failed` maps to `FAILURE`; `interrupted`, `inProgress`, timeout, exception, missing identity, or identity mismatch maps to `UNKNOWN`. These are Provider facts only and grant no `PRODUCED`, Verification, Satisfaction, Candidate, Runtime Commit, or Trusted Baseline authority.

TERM-01 through TERM-08 and the affected S6-B1 deterministic suite are **29/29 PASS**, with the gated real probe deselected. They cover terminal success, terminal failure, timeout, `UNKNOWN` plus independently observed work, exact dispatch/thread/turn correlation, truthful missing identity, absence of Completion authority, and absence of Resume semantics. No full regression was rerun, as required by the bounded spike contract; the previously accepted S6-B1 full regression remains historical evidence.

Real Probe #2 subsequently launched exactly one authenticated Provider Turn under explicit bounded repository-context egress authority. Public `Thread.id` and `TurnHandle.id` were available, and a public terminal object returned before the 120-second timeout; the timeout/interrupt path was not invoked. The authoritative repository and exact isolated Attempt workspace both remained unchanged, with the target marker still `BEFORE`. Exact IDs, terminal status, and lifecycle timestamps were not retained because evidence printing followed downstream artifact assertions and fixture cleanup truncated the temporary Runtime facts. Provider Outcome therefore remains `UNKNOWN`; no `SUCCESS` or `FAILURE` is inferred.

Architecture Baseline remains **v0.1**. Current state:

```text
S1–S5
    CLOSED / PASS

S6
    IN PROGRESS

S6-B1
    IMPLEMENTED — REAL SDK SPIKE PARTIAL
    PENDING ARCHITECTURE LEAD REALITY REVIEW

S6-B1-R
    PARTIAL — LIFECYCLE CAPABILITY PROVEN
    DURABLE REAL EVIDENCE INCOMPLETE
```

The next governed step is:

> Architecture Lead review of durable Provider evidence-capture hardening before any further real correlation authority.

## 56. S6-B1-R2 Durable Provider Evidence Capture Hardening reality

S6-B1-R2 is **IMPLEMENTED — DETERMINISTIC VALIDATION PASS** and **PENDING ARCHITECTURE LEAD REALITY REVIEW**. S6-B1-R and S6-B1 remain **PARTIAL**. This task launches no real Provider turn and does not close S6-B1 or authorize S6-B2, S6-C, Provider Resume, Docker, or FVS closure.

The exact Probe #2 historical truth remains:

```text
Real Probe #2

Provider Turn launched           = YES
Thread identity available        = YES
Turn identity available          = YES
Public terminal object returned  = YES
Timeout/interruption             = NO

Exact Thread ID retained         = NO
Exact Turn ID retained           = NO
Exact terminal status retained   = NO

Provider Outcome                 = UNKNOWN

Observed Workspace Change        = NONE
Expected marker                  = BEFORE

Probe Result                     = PARTIAL
```

The loss boundary was test instrumentation, not Provider lifecycle capability or Provider Report durability. `ExecutionService` committed the Provider Report before independent Repository Observation, but the real-probe test emitted its evidence only after artifact assertions. The failed marker assertion triggered fixture teardown, which truncated the temporary Runtime records before their exact values were reported externally.

R2 preserves the existing domain and persistence architecture. `CodexSdkExecutor` now includes public SDK `started_at`, `completed_at`, and `duration_ms` in terminal metadata, alongside dispatch ID, public thread/turn IDs, identity state, adapter start/finish timestamps, terminal status, mapped Provider outcome, timeout/interruption facts, and exception type where available. It fabricates no unavailable value.

The real-probe instrumentation now exports a standalone `S6B1_PROVIDER_EVIDENCE` JSON record immediately after the durable Provider Report is available and before any workspace/artifact assertion. It separately exports `S6B1_PRODUCTION_EVIDENCE` from independent observation. If observation raises after Provider Report commit, the exception path reloads and exports the durable Provider Report before re-raising. Cleanup remains after capture and is not evidence storage.

This ordering is now explicit:

```text
Observe Provider Fact
→ commit Provider Report
→ export Provider Evidence
→ independently observe/export Production Reality
→ artifact assertions/adjudication
→ cleanup
```

EVID-01 through EVID-08 prove thread identity, turn identity, terminal status, lifecycle timestamps, Provider outcome independence, observation-failure preservation, absence of invented artifact reality, and capture-before-cleanup ordering. Together with the affected S6-B1 and TERM tests, the focused deterministic suite is **37/37 PASS**, with the real probe explicitly deselected. Compilation/import is **PASS** and `git diff --check` is **PASS**. No full regression was run.

Architecture Baseline remains **v0.1**. Current state:

```text
S1–S5
    CLOSED / PASS

S6
    IN PROGRESS

S6-B1
    PARTIAL
    PENDING ARCHITECTURE LEAD REALITY REVIEW

S6-B1-R
    PARTIAL

S6-B1-R2
    IMPLEMENTED — DETERMINISTIC VALIDATION PASS
    PENDING ARCHITECTURE LEAD REALITY REVIEW
```

The next governed step is:

> Architecture Lead review → decide whether one final explicitly authorized correlation probe is justified.

## 57. S6-B1 final closure hardening and current-tree validation

S6-B1-R2 is **CLOSED / PASS**. S6-B1 is **CLOSED / PARTIAL** by Architecture Lead decision. S6 remains **IN PROGRESS**; this closure does not authorize S6-B2, S6-C, Provider Resume, Docker, or FVS closure.

`CLOSED / PARTIAL` means the bounded host-local real Codex SDK integration experiment is complete. It proved stable SDK integration, authenticated real Provider execution, isolated Attempt workspace execution, public Thread/Turn lifecycle identity, bounded timeout/interruption, conservative Provider Outcome mapping, durable Provider evidence capture, independent Production observation, and Provider Reality / Production Reality separation. It did not prove reliable real end-to-end production execution in one fully correlated Turn, consistently terminal Provider execution within the bounded window, or reliable expected workspace mutation on subsequent real probes. This is a known Provider integration/reliability limitation, not an implementation failure.

The historical Final Probe remains immutable:

```text
Provider turns launched          = 1
Retries                          = 0

Dispatch ID                      = 87e79294-36dc-49ed-8f5c-58c059b85f95
Workspace identity               = attempt-worktree:06c599cd-5f36-4758-b3b2-b686fd3e8d59
Thread ID                        = 01a05064-6f34-7063-b056-a9ceeb8747d3
Turn ID                          = 01a05064-703d-7eb0-940b-4d843535a8da

Terminal within timeout         = NO
Interrupt requested             = YES
Post-timeout status             = interrupted
Provider Outcome                = UNKNOWN

Observed Workspace Change       = NONE
Observed Work                   = NONE
Expected marker remained        = BEFORE
Probe Result                    = PARTIAL
```

Final deterministic hardening adds no schema or migration. Evidence export now includes the already-durable Materialized Execution Input ID and fingerprint alongside exact dispatch, workspace, thread, and turn identity. The real-probe contract no longer requires the preferred `marker == AFTER` outcome: `NONE` and `MODIFIED` remain independently observable Production Reality, while unexpected workspace paths or any authoritative repository mutation remain failures.

CLOSE-01 through CLOSE-08 cover exact input ID/fingerprint export, `UNKNOWN + NONE`, `SUCCESS + NONE`, `UNKNOWN + MODIFIED`, absence of a preferred-mutation requirement, unexpected workspace paths, and authoritative repository mutation. The focused S6-B1/R/R2 closure suite is **45/45 PASS**, with the real Provider test deselected. Compilation/import is **PASS** against `openai-codex==0.147.0`. The current-tree serial deterministic suite collected 391 tests and completed **390/390 PASS**, with zero failures, zero skips, and one real Provider test deselected, in **921.61 seconds (00:15:21)**. Alembic is at `20260829_12 (head)`; no downgrade/re-upgrade was necessary. `git diff --check` is **PASS**.

Current state:

```text
S1–S5
    CLOSED / PASS

S6
    IN PROGRESS

S6-B1
    CLOSED / PARTIAL

S6-B1-R
    PARTIAL — HISTORICAL

S6-B1-R2
    CLOSED / PASS
```

No additional S6-B1 real Provider probe is authorized. Any future real Codex execution must belong to a separately admitted governed task, not an extension of S6-B1.

## 58. S6-B2-A Dedicated Executor Boundary deterministic spike reality

S6-B2-A is **CLOSED / PASS** after Architecture Lead decision. S6 remains **IN PROGRESS**. S6-B1 stays **CLOSED / PARTIAL** and is not reopened. This result does not close S6-B2, start S6-B2-B or S6-C, or prove dedicated real Codex execution.

The physical spike uses the smallest admitted separation: a provider-neutral SPG client performs a single JSON request/response exchange with a dedicated local Python process. The transport projection is infrastructure rather than a new domain contract. It carries exact Attempt/generation, dispatch ID, Materialized Execution Input ID/fingerprint, canonical workspace identity, executor-local path mapping, and exact materialized Provider input. It deliberately excludes Provider/test configuration, the authoritative repository path, SPG database configuration, Provider credentials, Completion authority, and transport-specific state from durable domain models. The deterministic fixture Provider is selected and configured only in the Executor process environment.

Logical ownership remains unchanged. SPG validates and persists dispatch authority, owns Materialized Execution Input and production state, and independently observes the exact Attempt workspace through `GitWorkspaceObserver`. The dedicated Executor owns only invocation mechanics and deterministic workspace operations. Its Provider result remains an untrusted claim and cannot create PRODUCED, Verification, Satisfaction, Candidate, Runtime Commit, or Trusted Baseline authority.

Canonical `Attempt Workspace Identity` is mapped by infrastructure to an Executor-local writable path. Local-process execution currently maps the host Attempt workspace directly; deterministic symlink/path-escape coverage proves operations cannot escape into the authoritative repository, and translated mount paths do not replace the canonical domain path or identity. The child process runs with the exact workspace as its current directory and a minimal environment that excludes inherited SPG database configuration and credentials. The current transport exposes no credential channel; any future Provider credential must be provisioned independently in the dedicated Executor environment and must never enter the request or SPG persistence.

Transport unavailability, timeout, process error, malformed response, and exact-correlation mismatch map conservatively to Provider Outcome `UNKNOWN` with distinct transport metadata and no fabricated Provider result. Normal responses must echo exact request fingerprint, Attempt/generation, dispatch, Materialized Input, and workspace identity before SPG accepts their Provider fact. Provider outcome and Production Reality remain independent: `SUCCESS + MODIFIED`, `SUCCESS + NONE`, `FAILURE + NONE`, `UNKNOWN + MODIFIED`, and `UNKNOWN + NONE` are representable, while Work Product References derive only from SPG's independent observation.

B2A-01 through B2A-15 are **15/15 PASS** in **34.18 seconds**. B2A-01 is the dedicated boundary smoke: governed dispatch crossed the real local process, the deterministic Provider modified only the exact Attempt workspace, and SPG independently observed the change. Compilation/import and `git diff --check` are **PASS**. No schema or migration changed. No full regression was run because no shared Runtime semantic changed, as required by the bounded authorization.

Current state:

```text
S6
    IN PROGRESS

S6-B1
    CLOSED / PARTIAL

S6-B1-R2
    CLOSED / PASS

S6-B2-A
    CLOSED / PASS
```

The next governed step is:

> Architecture Lead S6-B2-A review → determine whether an S6-B2-B real authentication/workspace boundary probe is justified.

## 59. S6-B2-B1 Codex Adapter Binding and Authentication Boundary preflight reality

The S6-B2-B1 implementation result was **IMPLEMENTED — DETERMINISTIC/PREFLIGHT VALIDATION PASS / PENDING ARCHITECTURE LEAD REVIEW**. Architecture Lead subsequently admitted S6-B2-B1 as **CLOSED / PASS** before authorizing S6-B2-B2. S6-B2-A remains **CLOSED / PASS**, S6-B1 remains **CLOSED / PARTIAL**, and S6 remains **IN PROGRESS**. The B1 task launched zero real Provider Turns and did not itself close S6-B2 or start S6-B2-B2/S6-C.

The existing provider-neutral transport remains unchanged in ownership. SPG sends exact Attempt/generation, dispatch ID, Materialized Execution Input ID/fingerprint, Prepared Execution Request lineage, canonical workspace identity, infrastructure-translated workspace path, request fingerprint, and materialized Provider input. The payload contains no Provider binding selection, credential field, authoritative repository path, SPG database configuration, or deterministic Provider outcome. Child-side infrastructure selects `codex-sdk-preflight` from its own environment and reconstructs the exact adapter binding with a non-authoritative repository sentinel.

The child reuses the existing `CodexSdkExecutor` and its dispatch validation/evidence metadata. A new local `preflight()` seam validates exact Materialized Input, dispatch, Attempt/generation, and translated Git workspace binding without constructing `Codex`, invoking `thread_start`, calling `Thread.turn()`/`run()`, or executing a model. No Codex lifecycle mapping is duplicated in transport. Stable `openai-codex==0.147.0` import and adapter construction are proven. Because constructing the SDK runtime itself starts its client, this bounded preflight deliberately stops before that operation.

At the B1 preflight stage, authentication responsibility belonged to the dedicated Executor infrastructure but authentication readiness was intentionally not proven. No authentication file was read, no secret was inspected or copied, and no credential value entered transport, domain objects, persistence, Provider Reports, fixtures, or logs. The child environment policy admitted only the classes HOME location, executable/Python search paths, locale, temporary-directory location, and UTF-8 process configuration. It excluded inherited `SPG_DATABASE_URL` and unrelated credential variables. This was host-process filtering, not an OS-level credential isolation claim.

```text
PROVEN
    stable SDK import
    existing CodexSdkExecutor child-side selection/construction
    exact request/input/workspace correlation
    narrow child environment filtering
    zero Codex runtime construction / zero Provider Turn

NOT PROVEN
    authenticated Codex runtime readiness
    real Provider execution through Dedicated Executor
    OS-level credential isolation

AUTH_READINESS
    REQUIRES REAL B2-B2 PROBE
```

Binding failures remain infrastructure facts with Provider Outcome `UNKNOWN`: `SDK_UNAVAILABLE`, `ADAPTER_INITIALIZATION_FAILED`, `MISSING_RUNTIME_PREREQUISITE`, `UNSUPPORTED_PROVIDER_BINDING`, transport failure, malformed response, and correlation mismatch cannot become Provider SUCCESS/FAILURE or Produced.

Final B2B1-01 through B2B1-15 are **15/15 PASS** in **70.39 seconds**. Final affected B2A-01 through B2A-15 are **15/15 PASS** in **62.30 seconds**. Affected S6-B1/R/R2 deterministic tests are **45/45 PASS**, with the real Codex test explicitly deselected, in **140.69 seconds**. Compilation/import against `openai-codex==0.147.0` and `git diff --check` are **PASS**. No full regression ran because no shared Runtime/domain semantic changed. No schema, migration, Docker, authentication, Completion, Verification, Candidate, or Trusted Baseline change occurred.

The state immediately after B1 implementation, before Architecture Lead admission, was:

```text
S6
    IN PROGRESS

S6-B1
    CLOSED / PARTIAL

S6-B2-A
    CLOSED / PASS

S6-B2-B1
    IMPLEMENTED — DETERMINISTIC/PREFLIGHT VALIDATION PASS
    PENDING ARCHITECTURE LEAD REVIEW
```

The next governed step is:

> Architecture Lead S6-B2-B1 review → determine whether exactly one S6-B2-B2 real Codex Turn through the Dedicated Executor boundary is justified.

## 60. S6-B2-B2 single real Codex through Dedicated Executor boundary reality

S6-B2-B2 is **REAL PROBE COMPLETE / PARTIAL / PENDING ARCHITECTURE LEAD REVIEW**. S6-B2-B1 is **CLOSED / PASS**, S6-B2-A remains **CLOSED / PASS**, S6-B1 remains **CLOSED / PARTIAL**, and S6 remains **IN PROGRESS**. Exactly one real Provider Turn was launched and no retry occurred. S6-B2 is not closed and S6-C1 is CLOSED / PASS; S6-C remains in progress and S6-C2 is not authorized.

The real topology was proven end to end: SPG persisted one governed dispatch, `DedicatedExecutorClient` projected the exact Materialized Execution Input into provider-neutral JSON, a dedicated child process selected the Codex binding from its own environment, and the child reused the existing `CodexSdkExecutor` against the exact translated Attempt workspace. The request retained Attempt `8a3571d3-763c-4013-8682-8569a213fc98`, generation `1`, dispatch `e8d20081-685a-4a8a-813a-05ed0d1313d2`, Materialized Execution Input `fd59eadb-a5fa-572b-a16c-0c399dfb512a`, input fingerprint `cad6b3959ec66f93ad0fd4b2d69da5c33104b3b5c8845a31441d39d795fcc02a`, request fingerprint `a366aeee14bff0ee1913d7d3d2e29324cf08bf2beb554203a2145e573a8877da`, and canonical workspace identity `attempt-worktree:8a3571d3-763c-4013-8682-8569a213fc98`.

Authenticated child-side Provider execution is **PROVEN** without inspecting or transmitting credential values. The child returned Thread `01a050c1-566e-7220-afb0-0ee59715973f` and Turn `01a050c1-579d-7a43-bfd3-5f98486b89de`; the public terminal result returned within the existing 120-second Provider wait as `completed`, the terminal Turn identity matched, no timeout or interrupt occurred, and the conservative mapped Provider Outcome was `SUCCESS`. The dedicated transport returned a correlated response with `provider_result_present = true` and status `COMPLETED`. This proves only the authenticated Provider fact, not Produced, Verification, Satisfaction, Candidate, Runtime Commit, or Trusted Baseline authority.

SPG persisted Provider evidence before independently observing Production Reality. The authoritative fixture ref stayed exactly `95437027213eb02f48292e2c840efa7b8cfa6481`, its working-tree status stayed clean, the Attempt workspace stayed on the same HEAD, its status stayed clean, the admitted marker remained `S6-B2-A marker: BEFORE`, observed changed paths were empty, and Work Product References were empty. Therefore the truthful combination is:

```text
Provider Reality
    SUCCESS

Production Reality
    NONE
```

The PARTIAL classification is limited to post-evidence harness validation. After both Provider and Production evidence were exported, the real probe test's broad `"codex" not in payload` assertion falsely matched `codex` in pytest's generated temporary directory name. It did not identify Provider selection in the transport schema or an authoritative-repository escape. Per authorization, no repair and no second Provider Turn occurred. Existing B2-A/B2-B1 deterministic coverage subsequently passed **30 tests** with the gated real test skipped; compilation, critical imports, and `git diff --check` passed. No full regression ran.

Current state:

```text
S6
    IN PROGRESS

S6-B1
    CLOSED / PARTIAL

S6-B2-A
    CLOSED / PASS

S6-B2-B1
    CLOSED / PASS

S6-B2-B2
    REAL PROBE COMPLETE / PARTIAL
    PENDING ARCHITECTURE LEAD REVIEW

S6-C
    NOT STARTED
```

No additional S6-B2-B2 real Provider Turn is authorized. The next governed step is:

> Architecture Lead S6-B2 final review.

## 61. S6-B2 final deterministic closure hardening and admission

S6-B2 Dedicated Executor & Real Provider Boundary is **CLOSED / PASS**. S6-B2-A and S6-B2-B1 remain **CLOSED / PASS**. The S6-B2-B2 historical real probe remains **COMPLETE / PARTIAL** exactly as observed; closing the aggregate capability does not relabel or rewrite that experiment. S6 remains **IN PROGRESS** and S6-C remains **NOT STARTED**.

The historical false positive came from testing the full serialized payload as undifferentiated text. The assertion searched every admitted string value for `codex`, so pytest's generated temporary-directory name was mistaken for a Provider-specific transport field after Provider and Production evidence had already been captured. It was not evidence of Provider leakage.

Closure hardening replaces that check with structural validation of the actual SPG-to-Executor request contract. The serialized payload must contain exactly the fields declared by frozen `DedicatedExecutorRequest`; its nested `ExecutorBinding` must contain exactly its provider-neutral binding-ref/capability/profile fields; both structures must exclude Provider binding, SDK/model/runtime configuration, Thread/Turn handles, Provider lifecycle objects, credentials, API keys, tokens, and authentication-file fields. Pydantic `extra = forbid` rejects every tested unauthorized Provider-specific or credential-like field. Admitted string values are not semantically reinterpreted, so filesystem paths, fixture names, repository identities, and documentation text may contain `codex` without false leakage classification. Provider binding selection remains child-side infrastructure configuration and is absent from the governed JSON request.

B2CLOSE-01 through B2CLOSE-08 are **8/8 PASS**. They prove structural Provider neutrality, safe `codex`-named paths and fixtures, rejection of actual unauthorized Provider and credential fields, child-only binding selection, representable `SUCCESS + NONE`, and absence of Produced/Completion authority. Existing safe combinations remain representable, and no preferred `marker == AFTER` rule was introduced.

Focused deterministic validation is **PASS**:

```text
S6-B2 complete deterministic module
    38/38 PASS
    1 real Provider test deselected

Affected S6-B1/R/R2 integration module
    45/45 PASS
    1 real Provider test deselected

Real Provider Turns during closure
    0
```

The single serial current-tree deterministic regression collected **430** tests: **428/428 selected tests PASS**, **0 failed**, **0 skipped**, and **2 real Provider tests deselected**. The repository's configured `-q` plus the command's explicit `-q` suppressed pytest's internal duration line; the suite was not rerun merely to recover that presentation-only datum. Migration repository head and database current revision are both `20260829_12 (head)`. Compilation, critical imports, and `git diff --check` are **PASS**. No schema or migration changed.

Historical S6-B2-B2 evidence remains immutable:

```text
Provider Turns launched
    1

Retries
    0

Authenticated child-side execution
    PROVEN

Thread
    01a050c1-566e-7220-afb0-0ee59715973f

Turn
    01a050c1-579d-7a43-bfd3-5f98486b89de

Terminal
    completed / no timeout / no interrupt

Provider Reality
    SUCCESS

Production Reality
    NONE

Observed Work
    NONE

Marker
    BEFORE

Authoritative repository
    unchanged

Historical probe classification
    COMPLETE / PARTIAL
```

This real governance benchmark proves `Provider SUCCESS != PRODUCED`. It is neither normalized into a failed Provider call nor promoted into a successful production result.

S6-B2 closure proves the real physical dedicated process boundary, provider-neutral SPG transport, exact governed correlation, infrastructure-owned workspace translation, authoritative repository isolation, child-side Provider binding, credential-free SPG contracts/transport/persistence, authenticated real Codex execution from the Executor process, public Thread/Turn lifecycle correlation, transport-failure versus Provider-outcome separation, independent SPG Production Observation, and Provider/Production Reality independence.

Known limitations remain explicit: OS-level credential isolation, container isolation, Provider reliability, expected Production Work from Provider SUCCESS, and reliable end-to-end governed production completion are not proven.

Current state:

```text
S6
    IN PROGRESS

S6-B1
    CLOSED / PARTIAL

S6-B2
    CLOSED / PASS

S6-B2-A
    CLOSED / PASS

S6-B2-B1
    CLOSED / PASS

S6-B2-B2 Historical Real Probe
    COMPLETE / PARTIAL

S6-C
    NOT STARTED
```

The next governed step is:

> Architecture Lead S6-B2 closure review → determine exact S6-C Real Governed Dogfood Loop scope.

## 62. S6-C1 Real Governed Dogfood Requirement and Contract Admission

S6-C1 is **CLOSED / PASS** as a contract-admission step. It admits one real, bounded, independently verifiable documentation change as the first S6-C dogfood target. It does not execute the change, create an Attempt, launch a Codex Provider Turn, create production output, or authorize S6-C2.

### 62.1 Selected target and Production Intent

The repository contains authoritative Runtime, Executor, Completion, Verification, and Recovery contracts, but no single operational/governance artifact consolidating the real Executor boundary, Provider lifecycle versus independently observed Production Reality, `UNKNOWN` handling, retry rules, and operator handling for a governed dogfood run. The admitted target is not a duplicate and is not a synthetic marker task.

```text
Target artifact: docs/operations/spg-governed-dogfood-operator-guide.md
Production Intent ID: PI-S6C-DOGFOOD-001
Title: First real governed documentation dogfood operator guide
Production Horizon: one documentation artifact in this repository
```

Purpose: provide a bounded operational projection of admitted S6-B1/B2 and S2-S5 rules for the first real S6-C loop.

In scope: Executor boundary; Provider lifecycle versus Production Reality; Completion and Verification prerequisites; UNKNOWN, divergence, salvage-before-retry and new-Attempt retry; Human authority points; operator escalation; links to authoritative contracts.

Non-goals: no new Runtime, Provider, Guardian, ECF, UI, API, Docker, schema, migration, recovery architecture, Provider Resume, blind replay, or Continuous Production Orchestration.

### 62.2 One PWU

```text
PWU ID: PWU-S6C-DOGFOOD-001
Category: Documentation / Engineering Governance Artifact
Source Trusted Baseline: HEAD 273e901b3ef6514b0c35159736cb7f7aa17cc38e
Plan Revision: S6C-DOGFOOD-PLAN-R1
Allowed workspace scope: docs/operations/spg-governed-dogfood-operator-guide.md only
Execution objective: produce the one target artifact from the admitted Context Package
```

Exactly one PWU is admitted; no second PWU is silently introduced.

### 62.3 Completion and Verification Contract

The artifact is `PRODUCED` only when independent observation establishes the exact path and verifies semantic anchors for Executor boundary, Provider/Production Reality separation, UNKNOWN and recovery handling, Completion/Verification, Human Authority, and escalation; all introduced Markdown links resolve; the document states `Provider SUCCESS != Production Reality`, `UNKNOWN != FAILURE`, salvage precedes retry, retry uses a new Attempt, and S6-C1 does not authorize S6-C2; and no unapproved path changes.

It is `NOT_PRODUCED` if absent, incomplete, contradictory, unreferenced, or accompanied by out-of-scope changes. Provider SUCCESS, self-report, word count, or file existence alone is insufficient.

Minimum deterministic Verification: exact target existence; required semantic-anchor checks; introduced-link resolution; allowed-scope and forbidden-path checks; consistency checks against S6-B1/B2 and S2-S5; and `git diff --check`. Full regression, Guardian, migration, and Docker validation are not required because the target is documentation-only. Verification Evidence must bind the exact observed target and PWU basis before Satisfaction.

### 62.4 Context Package and recovery policy

The approved Context Package Lite is limited to the relevant `AI_context.md` projection; this contract; `spg-lite-runtime-implementation-contract.md`; Runtime readiness/findings; Completion/Trust; Reconciliation/Recovery; exact target context; and the Intent, PWU, Completion Contract, constraints, and source baseline. It must use the existing Context Package identity/version/content-fingerprint mechanism. Raw conversation and the entire repository are not execution context.

Existing S5 semantics apply: preserve Provider lifecycle separately from Production Reality; classify before recover; salvage before retry; use a new Attempt for retry; never blind replay or Provider Resume. SUCCESS/NONE remains a mismatch; UNKNOWN/MODIFIED is classified before salvage; UNKNOWN/NONE remains unresolved; FAILURE/MODIFIED preserves both facts; unexpected paths or workspace divergence block and require a governed assessment. S6-C1 performs no recovery action.

### 62.5 Human authority and intended handoff

Human Governor / Architecture Lead separately admits the Production Intent and the PWU/Completion/Verification Contract. Candidate authorization and Repository Integration authorization are later explicit authority points and are not granted here. Human authority cannot manufacture Verification, Production Reality, Produced/Satisfied state, Candidate eligibility, or Trusted Baseline.

```text
Admitted Intent → Plan / PWU → Prepared Execution → Attempt → Dedicated Executor
→ Real Codex → Provider Report → Independent Observation → Completion Evaluation
→ Verification → Satisfaction → Candidate → Human Authorization
→ Repository Integration → Runtime Commit → Trusted Baseline
```

S6-C2 is real governed execution and observation; S6-C3 is Completion/Verification/Satisfaction; S6-C4 is Candidate, Authorization, Integration, Runtime Commit, and Trusted Baseline closure. None is executed or authorized by S6-C1.

### 62.6 SOT status

```text
S6-C1: CLOSED / PASS
S6-C: IN PROGRESS
Dogfood Production Intent: ADMITTED
Dogfood PWU Contract: ADMITTED
Execution: NOT STARTED
Production Output: NOT PRODUCED
PWU Satisfaction: NOT ESTABLISHED
```

Next step: Architecture Lead S6-C1 review → authorize S6-C2 real governed execution only if the admitted contract is sound.
## 63. S6-C1/S6-C2 Baseline-Binding Semantic Calibration

The S6-C1 admission is calibrated to separate two exact bases that must not be conflated:

```text
Production Source Baseline
    exact clean repository revision from which the Attempt workspace is created

Governance Contract Snapshot
    exact admitted Intent / Plan / PWU / Completion / Verification / Recovery /
    Authority contract revision governing that Attempt

Context Package
    governed composition of Engineering Context projected from the Production
    Source Baseline and Governance Execution Contract projected from the exact
    admitted Governance Contract Snapshot
```

Engineering Context is projected from the exact Production Source Baseline. Governance Execution Contract is projected from the exact admitted Governance Contract Snapshot. Raw conversation, dynamic dirty-working-tree facts, and an entire-repository dump remain prohibited. Existing Context Package identity, version, and content-fingerprint mechanisms are sufficient; no new schema or migration is required.

### 63.1 Same-ref integration consistency

S6-C1 governance/SOT changes must be finalized in a clean repository checkpoint before S6-C2 execution. The resulting exact clean checkpoint revision is observed only after it exists; it is not predicted inside the commit that creates it. The intended FVS sequence is:

```text
admit/finalize S6-C1 governance contract
→ create clean repository checkpoint
→ observe exact resulting commit X
→ bind Runtime Production Source Baseline = X
→ create Attempt workspace from X
→ produce dogfood artifact
→ proposed production commit based on X
→ later S4 integration expects authoritative ref X
```

This preserves exact source-ref CAS semantics. The current S6-C2 authorization naming `273e901...` is therefore stale while S6-C1 governance edits remain uncommitted and must not be used to create Runtime objects.

### 63.2 Historical S6-C2 preflight block

The prior S6-C2 start was a governance preflight block, not a Provider or production Attempt failure:

```text
Human authorized execution
→ Contract / Baseline coherence check failed before Runtime creation
→ Provider Turns: 0
→ Production side effects: 0
```

Human Authorization is not permission to execute against incoherent Reality. No Run, PWU, Attempt, Context Package, MaterializedExecutionInput, Provider Report, or Production Observation was created by that blocked preflight.

### 63.3 Calibrated status

```text
S6-C1
    CLOSED / PASS — baseline-binding semantic calibration recorded

S6-C2
    PRE-EXECUTION BLOCKED — NO ATTEMPT CREATED

S6-C
    IN PROGRESS
```

The next governed step is Architecture Lead review, authorization of a bounded S6-C1 checkpoint commit, observation of the resulting exact clean revision, binding that revision as the S6-C2 Production Source Baseline, and only then reauthorization of S6-C2. This record does not create the checkpoint commit or execute S6-C2.

## 64. S6-C2-HR1 Windows execution-host repair closure

S6-C2-HR1R and S6-C2-HR1 are CLOSED / PASS. This closure repairs and validates only the reproducible Windows Dedicated Executor host. It does not execute or authorize S6-C2, create production Runtime objects, launch a real Provider, produce the dogfood artifact, bind a new Production Source Baseline, or close S6-C.

The initial HR1 environment sync Attempt remains immutable failed historical evidence:

    Initial HR1 sync Attempt
        FAILED — Windows OS error 32 while removing a temporary uv-trampoline executable

    Post-failure environment Reality
        openai-codex 0.147.0 present
        openai-codex-cli-bin 0.147.0 present
        spg-runtime 0.1.0 present

HR1R confirmed no stale project-owned installer, pytest, or virtual-environment child process and then performed the one authorized lock-preserving retry. The exact test plus codex-executor profile sync passed without changing pyproject.toml or uv.lock. The provider-specific codex-executor profile keeps exact openai-codex 0.147.0 and openai-codex-cli-bin 0.147.0 dependencies outside SPG Core.

Executor infrastructure resolves Codex state through explicit CODEX_HOME, native Windows USERPROFILE plus .codex, or POSIX HOME plus .codex. It does not persist or globally manufacture HOME. The Dedicated Executor child receives only a narrow cross-platform runtime allowlist; Windows lookup is case-insensitive, and SPG database configuration, Provider API keys, unrelated credentials, tokens, and application secrets are excluded. CODEX_HOME remains Executor infrastructure configuration and is absent from provider-neutral SPG domain, transport, and persistence contracts.

The actual Dedicated Executor child-process no-Turn preflight selected CodexSdkExecutor, imported stable SDK/runtime lifecycle surfaces, preserved exact Materialized Execution Input and canonical workspace identity, and confirmed no SPG database configuration in the child. Authentication readiness is AVAILABLE based only on safe state-marker existence; no authentication contents were read, printed, copied, modified, or persisted. Provider Threads created: 0. Provider Turns created: 0.

HOST-01 through HOST-17 plus exact installed-distribution validation pass 18/18. That evidence is reused for final closure because no relevant Executor environment or binding implementation changed afterward. The deferred focused regression initially exposed Windows host test portability rather than a Runtime semantic defect: B2-A-03 could not create a directory symbolic link without OS privilege, with WinError 1314. The narrow test-only correction uses a Windows directory junction for the same directory-alias, canonical-identity, and path-escape semantics while POSIX retains directory symlinks. Production code and assertions remain unchanged.

After that correction, the final affected regression passes:

    S6-B2-A
        15/15 PASS

    S6-B2-B1
        15/15 PASS

    Total
        30/30 PASS

    Real Provider Threads
        0

    Real Provider Turns
        0

Compilation/import, uv lock validation, and git diff validation pass. PostgreSQL remains healthy at Alembic 20260829_12; post-test cleanup leaves zero PI-S6C-DOGFOOD-001 Runs and zero Current Trusted Baseline Pointer rows, and docs/operations/spg-governed-dogfood-operator-guide.md remains absent.

Full Regression Attempt 1 remains immutable interrupted historical evidence. Execution-host resource contention and a host restart ended that run after partial progress with no observed failure; its final outcome is UNKNOWN / NOT RETAINED, and it created no checkpoint. The bounded follow-up diagnostic measured the Windows localhost IPv6-first fallback at approximately 5.1 seconds per connection against the IPv4-only local Docker PostgreSQL binding. The equivalent process-local 127.0.0.1 endpoint with SSL disabled measured approximately 28 milliseconds median connection latency.

Replacement Full Regression Attempt 2 used the process-scoped IPv4 test endpoint, remained serial, excluded real Codex tests, and reached terminal PASS. It collected 448 tests: 446/446 selected tests PASS, 0 failed, 0 skipped, and 2 real Provider tests deselected in 5078.33 seconds (1:24:38). Real Provider Threads created: 0. Real Provider Turns created: 0. Post-regression cleanup leaves no active test transaction, waiting lock, test fixture table, dogfood Run, Current Trusted Baseline Pointer, or target production artifact. Execution-host deterministic closure evidence is complete.

The historical production-source revision 27c2220291d1727be38a124efac7afff0bcaed33 remains evidence only and must not be reused for S6-C2 after these code/configuration changes. This task does not predict or bind a replacement SHA.

    S6-C2-HR1R
        CLOSED / PASS

    S6-C2-HR1
        CLOSED / PASS

    S6-C2
        PRE-EXECUTION BLOCKED
        NOT STARTED

    S6-C
        IN PROGRESS

The next governed step is Architecture Lead review of the resulting exact clean repair checkpoint revision, admission of that revision as the new S6-C2 Production Source Baseline, and only then S6-C2 Authorization 3.

## 65. S6-C2-DB1 local Dogfood Runtime database isolation

S6-C2 Authorization #3 remains immutable pre-execution evidence. Repository, Contract, and execution-host readiness passed, but Production Runtime database isolation failed with `PRODUCTION_RUNTIME_DATABASE_NOT_CONFIGURED`. No Run, Plan, PWU, Attempt, Context Package, Materialized Execution Input, Provider Thread, Provider Turn, production artifact, or other production side effect was created. This is not a Provider, Attempt, PWU, or Runtime recovery failure.

The admitted local FVS topology is one existing PostgreSQL service and volume with two logically distinct databases:

```text
spg_runtime
    local real Dogfood Runtime state

spg_test
    pytest and deterministic test state
```

The application already accepts the Runtime URL through `SPG_DATABASE_URL`; PostgreSQL fixtures require `SPG_TEST_DATABASE_URL` and do not fall back to Runtime configuration. `spg_runtime` was provisioned non-destructively in the existing service and migrated once from an uninitialized state to repository head `20260829_12`. `spg_test` remained a distinct database at the same migration revision. This proves logical database separation only, not separate containers, roles, servers, or physical isolation.

After migration, all Runtime and governance fact tables in `spg_runtime` contain zero rows: Run, Plan Revision, PWU, Context Package, Materialized Execution Input, Attempt, Preparation, Dispatch, Provider Report, Observation, Work Product Reference, Completion, Verification, Candidate, Human Authorization, Integration Effect, Runtime Commit, Recovery Assessment, Recovery Action, transition history, snapshots, governance records, and the Current Trusted Baseline Pointer are empty. `PI-S6C-DOGFOOD-001` is absent from both databases. No Trusted Baseline was bootstrapped and no new execution authorization was created.

```text
S6-C2 Authorization #3
    PRE-EXECUTION BLOCKED
    PRODUCTION_RUNTIME_DATABASE_NOT_CONFIGURED
    no Runtime objects
    no Provider Turn

S6-C2-DB1
    CLOSED / PASS

S6-C2
    PRE-EXECUTION BLOCKED
    NOT STARTED

S6-C
    IN PROGRESS
```

This change does not create a new Production Source Baseline or authorize S6-C2. The remaining pre-execution requirement is a clean database-isolation checkpoint, observation and admission of its exact revision as the Production Source Baseline, and only then S6-C2 Authorization #4.

## 66. S6-C2-R1 recovery assessment and R2 explicit UTF-8 transport repair

S6-C2 Authorization #4 created immutable Attempt generation 1 at Production Source Baseline `bed7b2f1eb3a1e0036d14bda1b8ef1f4ffc72066`. Its Dispatch reached Dedicated Executor infrastructure, but locale-dependent parent encoding (`cp936`) conflicted with the child UTF-8 stdin/stdout contract. Parsing failed at byte offset 2984 before Provider binding. No Provider Thread or Turn was created, Provider Outcome remains UNKNOWN, Production Reality remains NONE, and the PWU remains PROPOSED.

S6-C2-R1 is CLOSED / PASS. Recovery Assessment `18e1a39b-3133-591f-9364-50a5766fc8d2`, basis fingerprint `696e9c963172e7fde5c935e72b13e1391c5defe6ec61792223b8a5eb67e575dd`, classifies the exact generation-1 Attempt as `UNKNOWN` with `REOBSERVE` guidance. Current authority is true, safe recoverability is false, Human Attention is required, and the Recovery Barrier remains active. The assessment and its audit transition remain immutable; no Recovery Action exists.

S6-C2-R2 defines the Dedicated Executor wire as UTF-8 with strict error handling. The parent serializes the provider-neutral request to explicit UTF-8 bytes and strictly decodes child stdout and stderr bytes. Correctness no longer depends on host locale, Windows ACP, global Python UTF-8 mode, or parent `PYTHONUTF8`. `PYTHONIOENCODING=utf-8` remains a narrow child-stream setting. Malformed child bytes are rejected and map to `MALFORMED_RESPONSE` with Provider Outcome UNKNOWN; lossy replacement or ignored data is prohibited.

Focused deterministic evidence:

```text
UTF8 transport tests
    14/14 PASS

Affected S6-B2-A
    15/15 PASS

Affected S6-B2-B1
    15/15 PASS

Windows HOST
    18/18 PASS

Real Provider Threads / Turns
    0 / 0
```

The UTF-8 evidence model contains 15 obligations. UTF8-01 through UTF8-14 are represented by 14 executable pytest functions. UTF8-15 is the operational pre/post `spg_runtime` immutable-snapshot assertion; it intentionally remains outside pytest so deterministic tests cannot consume or clean production Runtime state.

The single serial full current-tree deterministic regression completed with terminal PASS:

```text
Collected
    462

Selected / Passed
    460 / 460

Failed / Skipped / Deselected
    0 / 0 / 2

Runtime
    5440.85 seconds (1:30:40)

Production Runtime pre/post snapshot
    IDENTICAL

Real Provider Threads / Turns
    0 / 0
```

The repair changes only Dedicated Executor transport infrastructure, focused tests, and this minimum SOT. It does not change domain contracts, child environment allow-list, persistence, schema, migrations, Codex SDK version, or any historical Runtime fact. It does not create generation 2, resolve the Recovery Barrier, bind a new Production Source Baseline, create a Recovery Action, or authorize execution.

```text
S6-C2-R1
    CLOSED / PASS

S6-C2-R2
    CLOSED / PASS

S6-C2 Authorization #4 / Attempt generation 1
    HISTORICAL EXECUTOR TRANSPORT FAILURE
    Provider Turn 0
    Provider Outcome UNKNOWN
    Production Reality NONE

S6-C2
    IN PROGRESS
    RECOVERY BARRIER ACTIVE
```

The resulting clean repository checkpoint is eligible only as an `S6-C2 PLATFORM-REPAIR CHECKPOINT` and remains `PENDING PRODUCTION-LINEAGE RECOVERY REVIEW`. It is not an admitted Production Source Baseline. The next governed step is Architecture Lead production-lineage recovery review, followed by separate authority to bind an exact clean revision and decide whether Attempt generation 2 may be created. No checkpoint identity is written or predicted here.

## 67. S6-C2-R3 closure and R4-A Verified Maintenance Baseline and Production-Lineage Recovery contract

S6-C2-R3 is **CLOSED / PASS**. Its repository-grounded and Runtime-grounded Reality Check determined that existing capabilities are insufficient to continue the active self-hosted dogfood lineage lawfully and classified the gap as **NARROW PRODUCTION-LINEAGE RECOVERY CAPABILITY REQUIRED**. Execution compatibility remains distinct from Repository Integration eligibility: a newer SPG implementation can technically execute against an older target-project commit, but a Candidate based on that old Source Baseline cannot pass current exact-baseline and authoritative-ref CAS rules after the ref has advanced.

At R4-A contract admission, S6-C2-R4 was **DEFINED / NOT STARTED**. S6-C2-R4-A is **CLOSED / PASS** as contract admission only. R4-A did not implement or execute recovery and did not itself authorize R4-B. The current post-implementation state is recorded in Section 68.

### 67.1 Capability boundary

The bounded capability is **Verified Maintenance Baseline & Production-Lineage Recovery**. It applies only when an independently verified platform repair has advanced the same authoritative self-hosted repository beyond the Source Baseline bound to an exact blocked production lineage.

Conceptually, one governed recovery operation binds:

```text
exact blocked old production lineage
+ immutable Recovery Assessment
+ exact Current Trusted Baseline and pointer version
+ exact final verified maintenance checkpoint
+ exact Human / Architecture Authority
+ exact deterministic verification evidence
        ↓
new immutable maintenance Trusted Baseline
+ Current Trusted Baseline Pointer advancement
+ old-lineage supersession
+ append-only Recovery resolution
+ new authoritative Run / Plan / PWU lineage
```

The operation must not expose unsafe generic mutations such as `adopt_latest_baseline()`, `reset_current_run()`, or `rebind_current_pwu()`. It must not redispatch generation 1, mutate any old lineage binding, silently rebase the old PWU, fabricate the ordinary Candidate path, reset `spg_runtime`, or rewrite the historical Recovery Assessment.

The current verified UTF-8 repair checkpoint is historical input evidence only. The eventual maintenance target is an exact clean checkpoint qualified only after complete R4-B implementation and Linux promotion-gate full-regression acceptance. Its SHA is bound only by a separately authorized Runtime recovery step. This contract does not hardcode, predict, or self-reference that future identity.

### 67.2 Verified maintenance qualification

A maintenance checkpoint is eligible only when the recovery request binds all of the following exact, current facts:

- Current Trusted Baseline identity and repository revision;
- Current Trusted Baseline Pointer version;
- target repository identity and authoritative ref;
- exact target maintenance commit and tree identity;
- proof that the target commit is a linear descendant of the old Trusted Baseline;
- independent observation that the authoritative ref currently equals the exact target commit;
- approved maintenance purpose and approved changed-path / repair scope;
- immutable deterministic verification evidence and its canonical fingerprint;
- exact Human / Architecture Authority.

Qualification must reject `latest HEAD`, `latest commit`, administrator narrative alone, raw conversation, and Provider success as authority or evidence substitutes.

### 67.3 Maintenance verification evidence

The minimum immutable evidence contract supports exact audit of:

- verification command or suite identity;
- collected, selected, passed, failed, skipped where reported, and deselected counts;
- focused repair evidence;
- migration, compile/import, lock, and diff evidence where applicable;
- exact changed-path scope;
- evidence timestamp;
- canonical evidence fingerprint.

The eventual evidence must validate the complete recovery-capability implementation and final clean checkpoint, not merely the earlier UTF-8 transport repair. This FVS path does not require Guardian and does not create a general metrics platform.

### 67.4 Human authority contract

The exact Human / Architecture Authority binds:

- old Trusted Baseline;
- final maintenance commit and tree;
- authoritative repository and ref;
- maintenance purpose;
- verification evidence fingerprint;
- old blocked Run / Plan / PWU / Attempt lineage;
- exact Recovery Assessment;
- new-lineage objective;
- authorization scope and timestamp.

Human Authority changes permission only. It cannot manufacture Provider `SUCCESS`, Production Work, Completion, Verification `PASS`, ordinary Candidate eligibility, or repository convergence. Candidate-specific Human Authorization semantics must not be reused. A later implementation may use or narrowly extend generic Governance authority semantics, subject to Reality Review.

### 67.5 Baseline admission and Git boundary

Successful admission creates a new immutable Trusted Baseline with provenance equivalent to `MAINTENANCE / RECOVERY ADMISSION`. The old Trusted Baseline remains immutable. The Current Trusted Baseline Pointer advances only through exact expected-source identity and version CAS.

The admission must not claim provenance from an ordinary Candidate, Provider execution, Repository Integration Effect, or Runtime Commit. Missing ordinary production records must not be fabricated retroactively.

Git is read-only external Reality for this operation. The capability may read the authoritative ref, confirm commit existence, read commit and tree identities, confirm linear-descendant ancestry, and inspect the exact diff/path scope. It must not update a ref, merge, rebase, reset, cherry-pick, force-update, push, or repair the repository.

### 67.6 Old production-lineage supersession

The old Run, Plan, PWU, Attempt generation 1, Dispatch, Provider Report, Observation, and Recovery Assessment remain historically intact. The old Attempt is never rewritten.

The contract requires explicit material state and audit semantics by which the old production lineage loses current authority. Preferred logical transitions are:

```text
Run:  OPEN     → SUPERSEDED
Plan: ACTIVE   → SUPERSEDED
PWU:  PROPOSED → SUPERSEDED
```

R4-B Reality Review may determine that a separate immutable supersession record is safer than one or more condition transitions. Regardless of physical representation, the old lineage must not remain apparently current after authority is handed to the new lineage, and historical executable meaning must not be mutated.

### 67.7 Recovery Assessment and barrier resolution

Recovery Assessment `18e1a39b-3133-591f-9364-50a5766fc8d2` remains immutable with `recovery_barrier = true`. It must not be changed to resolved, false, or coherent.

Barrier handling requires a new append-only Recovery Action / Resolution fact binding:

- exact Recovery Assessment and basis fingerprint;
- old Run / Plan / PWU / Attempt lineage;
- maintenance baseline admission;
- supersession decision;
- new Run / Plan / PWU lineage;
- exact Human Authority;
- result and timestamp.

The current production projection may regard the old barrier as handled only when the exact successful supersession/resolution fact exists. Historical evidence remains unchanged.

### 67.8 New production-lineage admission

The recovery creates new internal Run, Plan Revision, and PWU identities. The same external Production Intent may be retained, but no old internal identity is reused. The new lineage binds both the new maintenance Trusted Baseline and the exact admitted dogfood Governance Contract Snapshot.

The operator-guide objective and Completion / Verification Contract remain unchanged unless a separately admitted contract revision exists. The new PWU begins at `PROPOSED`. The maintenance recovery creates no Attempt and is not generation 2 of the old PWU.

### 67.9 Atomicity, idempotency, and concurrency

Where existing architecture permits, one local PostgreSQL UnitOfWork must atomically:

```text
verify old pointer identity and version
→ persist maintenance admission
→ create new immutable Trusted Baseline
→ advance the Current Trusted Baseline Pointer
→ supersede old Run / Plan / PWU authority
→ persist Recovery resolution
→ create new Run / Plan / PWU
→ append Governance and Transition History
```

All local state commits or all rolls back. Git remains read-only external Reality; no distributed transaction is introduced.

The complete recovery basis has one canonical fingerprint. An exact duplicate request returns the same logical result without duplicate Baselines, recovery records, supersession, or new lineage. A stale expected pointer identity/version is rejected. Competing maintenance recoveries cannot overwrite each other.

### 67.10 Eligibility and outcome boundaries

The narrow operation is eligible only while the exact old lineage has an active Recovery Barrier, a PWU that is neither `PRODUCED` nor `SATISFIED`, no Completion, Verification, Candidate, Integration Effect, Runtime Commit, or material Work Product requiring preservation, and the exact failed/blocked Attempt plus Recovery Assessment.

If material production work exists, the operation stops. General in-flight work migration is future work.

Successful maintenance recovery means only:

```text
new maintenance Trusted Baseline admitted
old blocked lineage superseded
new governed production lineage admitted
```

It does not mean that the operator guide is produced, the PWU is satisfied, the Provider recovered, the old Attempt succeeded, a new Attempt exists, or S6-C2 is complete.

### 67.11 Required future executable evidence — MR-01 through MR-34

| ID | Required executable obligation |
|---|---|
| MR-01 | Exact old Trusted Baseline is required. |
| MR-02 | Exact Current Trusted Baseline Pointer identity and version CAS are required. |
| MR-03 | Exact target repository, authoritative ref, commit, and tree are required. |
| MR-04 | Target commit must be a linear descendant of the old Baseline. |
| MR-05 | Authoritative ref must currently equal the exact target commit. |
| MR-06 | Exact approved maintenance purpose and changed-path scope are required. |
| MR-07 | Exact immutable deterministic verification evidence is required. |
| MR-08 | Exact Human / Architecture Authority is required. |
| MR-09 | Raw conversation cannot serve as authority. |
| MR-10 | Ordinary Candidate records are not fabricated. |
| MR-11 | Git is not mutated. |
| MR-12 | A new Trusted Baseline is created with maintenance/recovery provenance. |
| MR-13 | The old Trusted Baseline remains immutable. |
| MR-14 | The pointer advances exactly once. |
| MR-15 | The old Run loses current authority. |
| MR-16 | The old Plan loses current authority. |
| MR-17 | The old PWU loses current authority. |
| MR-18 | The old Attempt, Dispatch, Report, and Observation remain immutable. |
| MR-19 | The historical Recovery Assessment remains immutable. |
| MR-20 | Append-only Recovery resolution binds old and new lineages. |
| MR-21 | New internal Run, Plan, and PWU identities are created. |
| MR-22 | The same external Production Intent may be retained. |
| MR-23 | The new lineage binds the exact new Trusted Baseline. |
| MR-24 | The new lineage binds the exact Governance Contract Snapshot. |
| MR-25 | The new PWU starts at `PROPOSED`. |
| MR-26 | No Attempt is created automatically. |
| MR-27 | Atomic rollback leaves old authority unchanged. |
| MR-28 | An exact duplicate request is idempotent. |
| MR-29 | Concurrent or stale-pointer recovery is rejected. |
| MR-30 | Existing material Work Product blocks narrow supersession. |
| MR-31 | No Completion, Verification, or Candidate side effect is created. |
| MR-32 | No Provider Thread or Turn is created. |
| MR-33 | No destructive Runtime reset occurs. |
| MR-34 | Existing S1–S6 deterministic regression remains valid. |

These are future executable obligations. R4-A creates no tests and claims none of them as implemented or passed.

### 67.12 Governed sequencing and admitted state

```text
S6-C2-R4-A
    Contract Admission

S6-C2-R4-B
    Controlled implementation and focused validation
    NO Runtime recovery execution

S6-C2-R4-C
    Windows full deterministic regression Attempt
    INTERRUPTED / FINAL RESULT UNKNOWN

Linux Dogfood Promotion Gate
    Full deterministic regression
    + promotion checkpoint
    + exact SHA observation

S6-C2-R4-D
    Architecture Lead-authorized Runtime recovery execution
    against the exact final checkpoint
    NO Provider Turn

Later
    separately authorize the first Attempt under the new lineage
```

Maintenance recovery must never execute against an intermediate implementation checkpoint. R4-A does not freeze deeper implementation subdivision and does not authorize R4-B.

```text
S6-C2-R3
    CLOSED / PASS

S6-C2-R4
    IN PROGRESS

S6-C2-R4-A
    CLOSED / PASS

S6-C2-R4-B
    CLOSED / PASS

S6-C2-R4-C
    WINDOWS ATTEMPT INTERRUPTED
    FINAL RESULT UNKNOWN / NOT RETAINED
    CHECKPOINT NOT CREATED

S6-C2
    IN PROGRESS
    RECOVERY BARRIER ACTIVE
```

Architecture Baseline remains `v0.1`. R4-B implementation evidence is recorded below. The Windows R4-C full regression was interrupted without a retained terminal result; full-system regression is deferred to the Linux server promotion gate.

## 68. S6-C2-R4-B Verified Maintenance Recovery implementation and focused validation

S6-C2-R4-B implements the generic capability only. It does not execute the real S6-C2 maintenance recovery and does not migrate or mutate `spg_runtime`.

### 68.1 Persistence placement and capability boundary

One immutable `maintenance_recovery_admissions` record is the narrow maintenance admission and append-only Recovery resolution representation. It binds exact old/new Trusted Baselines, repository/ref/commit/tree, canonical verification evidence, Human / Architecture Authority, immutable Recovery Assessment, old and new Run/Plan/PWU identities, old Attempt, Governance Contract Snapshot, external Production Intent, operation fingerprint, outcome, and timestamp. It is not an ordinary Candidate, Repository Integration Effect, Runtime Commit, or Provider execution record.

Run, Plan, and PWU gain only the exact `SUPERSEDED` terminal state required by this contract. Plan gains an optimistic version so all three old-lineage authority objects are revalidated by expected identity/version. The original Recovery Assessment and all Attempt/Dispatch/Report/Observation facts remain immutable. The generic Governance Record supplies the authority audit entry; evidence and Authority remain typed, canonical, fingerprinted content in the immutable admission.

### 68.2 Domain, application, and Git contracts

The provider-neutral contracts are `MaintenanceVerificationEvidence`, `MaintenanceRecoveryAuthority`, `VerifiedMaintenanceRecoveryRequest`, and `VerifiedMaintenanceRecoveryResult`, with a typed new-lineage admission input and immutable admission record. The only public authority-handoff operation is `recover_lineage_after_verified_maintenance(...)`; no partial public baseline-adoption, reset, supersession, or rebinding primitive is exposed.

`GitMaintenanceObserver` is read-only. It requires a clean exact repository root, reads the authoritative ref, verifies commit and tree, proves old revision ancestry with `merge-base --is-ancestor`, and computes the exact changed paths. The operation observes the target before mutation and again before local commit. It contains no ref update, merge, rebase, reset, cherry-pick, force, push, or repository-repair path.

### 68.3 Local atomicity, idempotency, and concurrency

One PostgreSQL UnitOfWork locks and revalidates the exact baseline pointer and old Run/Plan/PWU, revalidates the exact Recovery Assessment and narrow zero-material-work eligibility, creates the maintenance Baseline, advances the pointer by expected-source/version CAS, supersedes the old lineage, creates the new Run/Plan/PWU, appends Governance/Transition facts, and persists the immutable admission/resolution. The new PWU starts `PROPOSED` with execution generation zero. No Attempt, Context Package, Materialized Execution Input, Completion, Verification, Candidate, Integration Effect, Runtime Commit, or Provider call is created.

The complete typed basis has one canonical operation fingerprint and deterministic logical identities. Exact replay returns the same admission and lineage without duplicates. A different operation using a stale pointer or stale lineage/Assessment basis is rejected. Eleven injected material mutation boundaries prove complete transaction rollback; Git remains external read-only Reality and no distributed transaction is claimed.

### 68.4 Executable evidence and migration Reality

MR-01 through MR-34 map to named executable tests. The focused R4-B module collects and passes 23/23 cases, including eleven atomic rollback parameters. Unique affected PostgreSQL persistence, Runtime spine, S4-B pointer/Runtime Commit, S5 recovery, and directly adjusted schema-inventory cases pass 175/175. Persistence foundation and migration-head checks pass 6/6. Compile/import validation, `uv lock --check`, and `git diff --check` pass.

Linear migration `20260902_13` adds only the immutable maintenance admission table and Plan optimistic version. Downgrade to `20260829_12` and re-upgrade pass on `spg_test`. The real `spg_runtime` remains at `20260829_12`; its pre/post whole-database fingerprint is identical, its Current Trusted Baseline Pointer and generation-1 history are unchanged, Recovery Action count remains zero, generation 2 remains absent, and the R4-B table is not present there.

### 68.5 Resulting governed state

```text
S6-C2-R4
    IN PROGRESS

S6-C2-R4-A
    CLOSED / PASS

S6-C2-R4-B
    CLOSED / PASS

S6-C2-R4-C
    WINDOWS ATTEMPT INTERRUPTED
    FINAL RESULT UNKNOWN / NOT RETAINED
    CHECKPOINT NOT CREATED

S6-C2
    IN PROGRESS
    RECOVERY BARRIER ACTIVE
```

Architecture Baseline remains `v0.1`. R4-B is CLOSED / PASS after Architecture Lead Reality Review. No real maintenance Baseline was admitted, no real lineage was superseded or created, and no Attempt generation 2 or Provider Thread/Turn exists. The Windows R4-C full regression was interrupted without a retained terminal result; full-system regression is deferred to the Linux server promotion gate.

## 69. Interrupted Windows R4-C regression and Linux Dogfood deployment replan

The Windows workstation is retained as a bootstrap/development host and will no longer perform full deterministic promotion regression, Trusted Baseline promotion, or long-term SPG Dogfood Runtime operation. The interrupted R4-C regression log retained progress through 59% with no known failure, but no terminal pytest result was retained. The Attempt is **STALLED / INTERRUPTED**, its result is **UNKNOWN / NOT RETAINED**, and no checkpoint was created.

The complete frozen validation subject remained byte-identical before and after interruption. Existing R4-B evidence remains admitted: focused tests 23/23 PASS, MR-01 through MR-34 mapped and PASS, affected regression 175/175 PASS, persistence foundation 6/6 PASS, migration 20260902_13 round-trip PASS on spg_test, compile/import PASS, uv lock validation PASS, and Git diff validation PASS. This is not a full-system regression PASS.

The Windows spg_runtime remains at Alembic 20260829_12 and is archived as **WINDOWS BOOTSTRAP DOGFOOD EVIDENCE — NOT AN ACTIVE SERVER RUNTIME TO BE CONTINUED**. Backup C:\Users\yuchunbo\Documents\SPG-backups\spg_runtime_windows_bootstrap_20260902T061522Z.dump has SHA-256 64ebae40cbea8589f3b1c988422329d4f52e9b5200729ca67c19f31c1a0045b0 and passed restore-list validation. The archive preserves Authorization #1–#4 history, Attempt generation 1, Dispatch, Provider Report UNKNOWN, Observation NONE, Recovery Assessment, and the active historical Recovery Barrier. It is not migrated as the active Linux Runtime.

The Linux development server is the next authoritative Dogfood Execution Host. The current repository checkpoint may be classified only as a **LINUX DOGFOOD DEPLOYMENT CANDIDATE — NOT YET A TRUSTED BASELINE**. Full-system regression is deferred to the Linux server promotion gate. Real maintenance recovery remains unexecuted; the old lineage is not superseded, no new lineage exists, and the Recovery Barrier historical fact is not rewritten.
