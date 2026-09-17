# Repository Acquisition, Execution/Preview Sandbox, and Remote Integration

Status: **FUTURE ARCHITECTURE DIRECTION / NOT STARTED**

This is a documentation-only direction. It preserves a future productization
and research seam without changing current Repository Intake, Execution,
Preview, Candidate, Verification, Delivery, or Integration behavior.

## 1. Context and coherent problem

Watt currently accepts an external Git repository by cloning it into
Watt-managed storage, observes an exact revision/tree, registers an Engineering
Resource, binds Work and PWU/Attempt state to an exact Source Baseline, and uses
isolated Attempt-specific worktrees. Candidate, Verification, Authorization,
Integration, and Runtime Commit semantics already exist. Current static-Web
Preview projects an exact immutable Git blob.

Private repository authorization and complete GitHub/GitLab product integration
are not yet implemented. The current MVP behavior remains valid and is not
reinterpreted here.

The future concern is one governed flow:

```text
External Repository
  -> Acquisition / Admission
  -> Managed Source Reality
  -> Execution / Preview Sandbox
  -> Candidate -> Verification -> Human Authorization
  -> Remote Integration / PR / Push
  -> External Repository
```

Clone and fetch efficiency, isolated execution, and governed write-back should
be designed as connected boundaries for safely and economically moving code into
and out of Watt.

## 2. Repository acquisition direction

Full-history, full-repository cloning must not remain the assumed strategy for
every Work. Future policy should select among full, single-branch, shallow,
partial, sparse, on-demand hydration, incremental history fetch, and reusable
object-cache strategies based on Work needs, repository characteristics, Git
operations, assurance requirements, and resource budgets.

Acquisition research must cover branches and refs, large monorepositories,
large histories, file counts, very large blobs, Git LFS, submodules,
dependencies, build/cache/temp footprints, repeated Work, network transfer,
workspace disk, and admission failure behavior. Exact thresholds are future
policy/configuration, not architecture constants.

Before expensive materialization, Watt should eventually perform lightweight
observation where practical: provider metadata, `git ls-remote`, ref discovery,
tree/file and large-blob estimates, LFS and `.gitmodules` detection, language or
build-system detection, and dependency-manifest inspection. Exact clone pack
size is generally unknowable in advance because server-side pack/delta generation
is dynamic; admission therefore uses estimates and classes.

Admission separates at least:

- **Repository Intake Budget:** Git objects, current tree, file count, large
  blobs, history, LFS payloads, and submodules.
- **Execution Workspace Resource Budget:** checked-out source, dependencies,
  build outputs, caches, logs, checkpoints, preview artifacts, and runtime
  overhead.

LFS pointers and metadata should be inspected before hydrating required objects.
LFS size remains separate from ordinary Git blobs. Submodules are inspected
before use, materialized only when the Work needs them, and require explicit
authorization for their separate repository boundaries.

Shared Git objects or caches may reduce transfer and storage, but writable
Attempt workspaces remain isolated production realities. Optimization must not
collapse identity or isolation.

## 3. Exact baseline and remote drift

Every production Attempt remains bound to an exact Source Baseline. If `main`
moves from `A` to `B` while an Attempt is active, that Attempt remains based on
`A`; an observed `B` becomes new Source Reality only through explicit
reconciliation or baseline-advancement rules.

> Fetch may be automatic; baseline advancement must never be invisible.

Future integration uses compare-and-swap semantics. If a Candidate based on
expected target `A` meets remote `B`, Watt must detect the mismatch and choose a
bounded reconciliation, rebase/merge policy, renewed verification, new
Candidate, or Human decision. It must never silently force-push or implicitly
`pull && merge && push` while presenting the original Candidate as unchanged.

## 4. Execution and Preview Sandbox direction

The future cross-project study must cover filesystem and mount boundaries,
process supervision, CPU/memory/disk/process limits, network egress, secret
isolation, dependency and build isolation, retained or hibernated workspaces,
cache policy, preview startup, multi-service Web/backend/database/worker
scenarios, health checks, logs, temporary ports, authenticated reverse proxy,
URL lifecycle, browser/iframe isolation, teardown TTL, restart, and recovery.

The sandbox is an execution boundary, not a new Work or Repository identity.
Current immutable static Git-blob Preview remains the current reality. A generic
isolated full-stack Preview Sandbox is `IMPLEMENTATION = NOT_STARTED`.

## 5. Remote integration and authorization

Future Git productization distinguishes technical **Connection Capability** from
per-Work **Candidate Authorization**. A credential permitting `READ`,
`CREATE_BRANCH`, `PUSH_BRANCH`, `CREATE_PR`, `MERGE`, or protected-branch write
does not itself authorize a mutation for this Work.

Candidate/Integration state should eventually bind the exact Candidate
fingerprint, target repository and ref, expected remote baseline, permitted
effect, and Human/Policy authority. Existing lifecycle semantics should evolve
to carry this exact target/effect information rather than creating an unnecessary
parallel lifecycle.

Candidate write-back modes are future product options:

1. No write-back: Watt delivers governed artifacts for manual integration.
2. Branch plus PR/MR: create a Watt branch, push the authorized Candidate, and
   open a request against the target branch. This is the likely safe commercial
   default.
3. Direct integration: allowed only under explicit repository policy and Human
   authority; direct writes to protected or production branches are never the
   default assumption.

Provider integration should study GitHub App, GitLab OAuth/App, short-lived
scoped credentials, and a trusted credential broker. Credentials must not be
embedded in Git URLs or handed to the Executor as long-lived authority.
Executor produces the engineering result; a trusted Integration capability
performs authorized external effects.

## 6. Future horizontal study

Record an explicit future study covering repository acquisition, sandbox/runtime,
and remote integration mechanisms. Candidate evidence sources include E2B,
DevPod, OpenHands Runtime, Tilt, Railpack, and documented GitHub Codespaces
mechanisms, plus other relevant systems discovered later. They are pattern and
evidence sources only; Watt owns the final architecture.

The study should compare large-repository handling, partial/shallow/sparse Git,
LFS, submodules, object caching, workspace materialization, isolation, retained
environments, quotas, network policy, preview proxies, multi-service runtime,
hibernation, branch/commit/PR integration, protected branches, stale-remote
detection, credentials, CAS, and integration receipts.

Future ECF may reduce the need to fully materialize every repository artifact for
context assembly. Repository acquisition and model context assembly remain
distinct concerns; this direction does not depend on or redesign ECF. Guardian
and Verification retain their independent assurance ownership.

## 7. Invariants and non-goals

- Repository is an optional Work Asset; Repository URL is not Repository Access.
- Workspace is not synonymous with Repository and may later contain multiple
  repositories, generated files, runtime resources, context, and evidence.
- Remote movement cannot silently redefine an active Attempt's baseline.
- Connection capability never substitutes for Work/Candidate authorization.
- Executor authority to produce code is separate from trusted authority to mutate
  an external Git system.
- External integration must preserve provenance, expected remote state, and
  reconciliation evidence.

This document does not authorize new clone/fetch strategies, size limits, object
caching, LFS or submodule handling, OAuth/GitHub App, PR creation, push-back,
branch management, generic Preview Sandbox, distributed storage, scheduling,
ECF, or Guardian implementation. It does not invent technical stacks or change
current Work, PWU, Runtime, Candidate, Verification, Delivery, or Human
Authority behavior.

## 8. Canonical status

```text
REPOSITORY_ACQUISITION_PRODUCTIZATION = NOT_STARTED
GENERIC_PREVIEW_SANDBOX = NOT_STARTED
REMOTE_GIT_INTEGRATION = NOT_STARTED
CURRENT_MVP_REPOSITORY_INTAKE = PRESERVED
CURRENT_EXACT_SOURCE_BASELINE / ATTEMPT_ISOLATION = PRESERVED
FUTURE_HORIZONTAL_STUDY = RECORDED
```
