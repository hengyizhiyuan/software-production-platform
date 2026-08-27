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

> FVS-1 is AUTHORIZED FOR CONTROLLED IMPLEMENTATION through explicitly bounded slice tasks. S1-A and S1-B are CLOSED / PASS; S1-C is NEXT — NOT STARTED.

Overall Implementation Governance remains **AUTHORIZED FOR CONTROLLED IMPLEMENTATION**. Authorization remains slice-bounded: S1-B permits only the persistent Runtime foundation and local PostgreSQL provisioning. It does not authorize Runtime lifecycle, provider execution, repository integration, or dogfood execution.

The contract uses these classifications:

| Classification | Meaning |
| --- | --- |
| Confirmed Slice Contract | Required FVS-1 domain/governance behavior |
| Confirmed Technical Foundation | Reviewed technology choice scoped to FVS-1 |
| Confirmed Integration Protocol | Required repository-effect and Runtime Commit behavior |
| Confirmed Verification Contract | Mandatory executable scenario or invariant coverage obligation |
| Implementation Guidance | Permitted physical shaping that may be refined without changing semantics |
| Deferred Scope | Explicitly outside FVS-1 |
| Authorization State | Implementation requires an explicit bounded slice; S1-A and S1-B have been explicitly authorized while later slices remain unauthorized |

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

Admission of this Contract provides governed Source-of-Truth authority for F1/F2/F3-A/F3-B/F3-C conclusions. Explicit S1-A and S1-B tasks subsequently exercise that controlled, slice-bounded authorization.

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

This admission changes implementation status only. It does not change Architecture Baseline v0.1, add an architecture requirement, or begin S1-C.

The exact next governed step is:

> Architecture Lead confirms S1-B SOT closure → authorize S1-C Bootstrap Baseline & Minimal Durable Runtime Spine.

S1-C is NEXT — NOT STARTED and remains subject to explicit bounded authorization.
