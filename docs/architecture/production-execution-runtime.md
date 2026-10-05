# Production Execution Runtime v1

Status: implemented runtime contract on `codex/production-execution-runtime-v1`.

## Lifecycle and authority

A Human Turn is interpreted by IRK/WIC and admitted as Product Work. Steering
forms an exact Task Contract and obtains an ECF Decision Context for supported
decision surfaces. The existing Work preparation service creates a PWU,
source snapshot and isolated Git attempt workspace. Native admission refuses a
Product execution with `EXECUTION_CONTEXT_NOT_READY` unless its binding matches
the current Work revision, IRK identity, Task Contract, ECF package fingerprint,
exact repository commit and verification obligations. ECF freshness is checked
again at queue admission. A Worker cannot execute the Human prose directly.

The queue persists `QUEUED → ALLOCATED → EXECUTING → COMPLETED` or a recoverable
failure. Worker lease fencing, heartbeat and coordinator reconciliation remain
the execution authority. The Work/Verification owners remain the authority for
`VERIFYING → VERIFIED → COMPLETED`: `RESULT_READY` alone never proves completion.
Failure of a required verification is projected as `VERIFICATION_FAILED`.

## Workspace

Each Attempt has a persisted WorkspaceManifest and exact source vector. The
existing Git attempt workspace acquires the approved source revision into a
separate directory; the main repository is not an execution workspace. The
Worker observes the exact Git HEAD before and after execution and rejects
changes outside the Task scope or forbidden paths. Workspace and direct
artifact byte ceilings are persisted in ResourceEnvelope. Workspace observation
also checks `git diff --check`, required created/updated files, and file count.
Workspace evidence is content addressed. The coordinator invokes existing
hot/cold retention cleanup; workspace cleanup status is persisted. Cleanup
never silently changes Work or verification state.

The size check is at observation boundaries, not a kernel filesystem quota.
For hard protection against a process that fills disk between observations,
future production deployment must add a per-workspace filesystem quota or
bounded volume before increasing Worker density.

## Evidence

- **Context:** `ExecutionRequestCreated` records Work, Task Contract, IRK,
  ECF fingerprint, repository commit, Workspace ID and verification obligations.
- **Execution:** Worker event records Worker/version, exact Workspace and
  change request; lease/effect/checkpoint journals record activity.
- **Result:** a content-addressed observation stores changed paths, bounded
  tracked diff, file SHA-256/size, workspace size and `diff_reference`.
  Existing VerificationRecords retain test/consistency outcomes and determine
  the public Execution projection. Untracked file bytes remain in the retained
  workspace; their hash and path are recorded in the result evidence.

Execution timeouts stop heartbeat and preserve uncertain effects for lease
reconciliation. Product execution without ECF, IRK, Task Contract, source or
verification basis fails before a Worker is allocated. Legacy synthetic/native
records retain read compatibility but do not gain Product authority.

## Current topology and scaling

On the current single ECS, API, coordinator, Worker, Tool Host and PostgreSQL
are separate containers. Managed Source/Gitea is an independent persistent
container. The API and Worker share persistent native executor state and a
workspace volume; owner runtimes are independent read-only mounts.
For a managed Web Task, ECF v0.1 requires exact `README.md` sections for
Product Intent, Product Invariant and Approved Decision. A missing section
blocks the Task Contract instead of silently bypassing ECF.
The same queue/lease contract permits later Worker ECS instances with shared
workspace/artifact storage and explicit capacity policy. This document does
not authorize that migration or change Cloud Delivery.
