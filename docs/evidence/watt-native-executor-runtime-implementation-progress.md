# Watt-native Executor Runtime — Implementation and Qualification Progress

Date: 2026-09-11. Repository basis before the uncommitted implementation:
`8d85100bac5505462d0866398bd076ecb21fcf39` on
`feature/spg-first-vertical-slice`.

## Status

```text
WATT-NATIVE EXECUTOR RUNTIME FOUNDATION
    IMPLEMENTED

FOCUSED VALIDATION
    PASS

TECHNICALLY_QUALIFIED
    NO

RUNTIME_READY_FOR_HUMAN_ACCEPTANCE
    NO

HUMAN ACCEPTANCE
    NOT STARTED
```

This record deliberately separates implementation progress from qualification.
It does not weaken the Blueprint or convert partial evidence into release
closure.

## Implemented Reality

- Typed provider-neutral contracts for PWU contract versions, source vectors,
  workspaces, sessions, Attempts, queue entries, allocations, leases, Steps,
  Effects, receipts, checkpoints, evidence, result claims, controls, recovery,
  resource envelopes, and backend capabilities.
- Additive PostgreSQL migration `20260911_34` with 23 native execution tables,
  indexes, uniqueness rules, versioned projections, event/outbox storage, and a
  resource ledger.
- Database-backed fair round-robin scheduling between fairness groups, FIFO
  inside a group, starvation aging, resource/capability eligibility, fenced
  allocation leases, heartbeat, release, and provider-capacity requeue/park.
- A bounded native kernel that reconstructs working-plan Reality, requests
  inference through a replaceable port, validates capability-granted tool
  proposals, persists intent/receipt/evidence, checkpoints progress, and emits
  `RESULT_READY` without claiming Verification or trust.
- Private workspace/source-vector contracts with repository-optional and
  multi-mount representation, content-addressed checkpoint storage, and a
  recovery classifier that preserves `UNKNOWN`.
- A separate Tool Host process exposing explicit file, process, Git, test,
  build, locked dependency, and static-preview contracts. It uses no shell,
  bounds model-visible output, filters secret-shaped environment variables
  case-insensitively, denies direct `.git` file access, and resolves paths
  under the admitted workspace.
- Configuration-driven OpenAI Responses inference adapter with typed 429
  retryable-capacity and 402 non-retryable-resource handling. No real Provider
  request was made in this implementation run.
- Stable native backend and compatibility adapter alongside the retained legacy
  Codex backend. Existing Completion, Verification, Candidate, authorization,
  integration, Runtime Commit, and Trusted Baseline logic remain downstream.
- Native admission, queue, attempt inspection, control, and SSE event endpoints,
  plus a Human-visible queue/control/evidence projection in the existing Watt UI.
- Isolated Compose topology for PostgreSQL, application, coordinator, Tool Host,
  and an optional Provider Worker. Tool Host has no database/Provider credentials
  or Docker socket; the Provider Worker was not started during this evidence run.

## Focused Validation Evidence

- Native contract/kernel/tool/security tests: **16 passed**.
- Native PostgreSQL integration tests: **8 passed**. Coverage includes additive
  schema, idempotent admission, allocation/lease release, checkpoint/result
  durability, expired-worker fencing to `UNKNOWN`, provider-capacity requeue,
  monotonic event replay, cancel-before-allocation, and resource-reservation
  settlement.
- Existing affected API integration: **13 passed**.
- Existing UI HTTP/contracts: **7 passed**.
- Existing browser-state Node tests: **36 passed**.
- Python compileall and JavaScript syntax checks: **PASS**.
- Migration round trip on isolated PostgreSQL:
  `20260910_33 → 20260911_34 → 20260910_33 → 20260911_34`: **PASS**.
- Isolated Compose build: **PASS**. Application, PostgreSQL, coordinator, and
  Tool Host started; application `/health` and `/app` returned HTTP 200;
  Alembic current/head were both `20260911_34`.
- Real container Tool Host boundary: file read/write, no-shell process, and Git
  status settled; child process observed no SPG database URL, Provider key, or
  internal Tool Host token; a 40,000-byte read was truncated to 32,768 bytes;
  parent traversal and an `/etc` symlink escape were blocked.
- Tool Host container inspection: database credential absent, Provider key
  absent, Docker socket absent. Application has no route to the Tool Host-only
  internal network; only the optional Worker spans control and executor networks.

## Full Regression Attempts

The first full-regression command stopped during collection because its
operator-supplied `PYTHONPATH=src` omitted repository-root modules
`benchmarks` and `docker`. No tests ran; this is harness configuration evidence,
not a product failure.

The corrected command used `PYTHONPATH=src;.` and `PYTHONUTF8=1`. It reached
29% with no observed failure and one expected skip, then was intentionally
interrupted because the feature still had known mandatory qualification gaps.
This attempt is **NOT** a full-regression pass and must not be cited as one.

## Qualification Closure Attempt — Q01

The Provider configuration was supplied through the ignored local `.env` and
validated without exposing either credential or internal Tool Host token. The
admitted model identity was `gpt-5.6-sol`. Tool Host and Provider Worker
startup succeeded before execution admission.

The first Q01 production Attempt
`dec4ddfd-9bc3-46c1-b9fe-6ec48cb2c452` exposed a Worker wiring defect before
inference: the persisted `NativeAttemptBindingRecord.resource_envelope_id` was
incorrectly read as a nested `resource_envelope`. The Worker exited with zero
Steps, Effects, evidence records, checkpoints, and Provider requests. Lease
expiry fenced the Attempt as `UNKNOWN / RECONCILING`; that history was not
rewritten or replayed. The field access was corrected, and a rebuilt Worker
crossed that boundary successfully.

The successor Q01 production Attempt
`29f15bc1-26aa-4b78-baf6-8ef024025832` reached the OpenAI Responses endpoint.
The endpoint rejected the request before model execution with HTTP 400
`invalid_json_schema`: the response schema contained intentional dynamic JSON
maps for tool arguments/result claims that are outside the API strict-schema
subset. The Attempt retained one inference Step, zero Effects, zero evidence
records, and no checkpoint, then truthfully became `UNKNOWN / RECONCILING`.
No repository mutation occurred. The adapter now uses best-effort JSON Schema
formatting for those dynamic maps and retains Pydantic validation as the
authoritative provider-neutral response boundary. Focused adapter regression
for success parsing plus typed 429/402 behavior passes.

The explicitly authorized single real Provider flow was consumed by that
request. Q01 remains **BLOCKED**, not PASS, pending a separate Human
authorization for another real Provider call after review of these fixes.

The attempt also proved a Runtime wiring distinction: the normal application
container activated source from the older Trusted Baseline
`8d85100bac5505462d0866398bd076ecb21fcf39`, while the uncommitted qualification
implementation existed only in the newly built image. A separately named
current-tree technical qualification process was therefore used on port 8041
against the same isolated database/workspace volumes. This process is not a
Trusted Baseline admission and must not be represented as the Human acceptance
Runtime.

## Open Mandatory Qualification

The following areas remain materially open:

- Q01 and provider-level cases: no real native Provider Turn, multi-round real
  code production, live model identity/usage, or repair proof.
- Q06, Q12–Q14, Q17–Q30: complete Session fork/update races, quiescent process
  pause, process-tree termination, worker/API/host crash frontiers, effect
  reconciliation, checkpoint publication failures, compaction, salvage, and
  host-reboot recovery are not qualified.
- Q10/Q26: the current bounded subprocess call does not yet provide the required
  supervised process identity, descendant termination receipts, or mid-tool
  control barrier semantics.
- Q15/Q45/Q46: direct PostgreSQL-backed SSE replay exists, but durable relay
  publish/ack, cursor expiry `RESET`, snapshot high-water, and subscriber
  backpressure qualification do not.
- Q31–Q35: `SourceVector` and multi-mount Workspace are first-class, but
  per-target Verification, Candidate vector integration, partial convergence,
  forward recovery, and aggregate multi-repository Runtime Commit are not
  implemented by this slice.
- Q38–Q40: traversal, one symlink escape, secret filtering, internal networking,
  and Docker-socket absence are proven only as a subset. Symlink race, hardlink,
  archive escape, metadata/control egress, per-Work host isolation, and warm
  reuse isolation remain unqualified. A shared Tool Host plus bearer token is
  not claimed as complete hostile-code isolation.
- Q41–Q43: durable reservations exist, but cumulative PWU-pool enforcement,
  unknown-spend policy, retention/hibernation/pins, cleanup crash safety, and
  DB/disk outage behavior remain open.
- Q44: no seeded exact-Candidate preview and Human authorization/delivery
  acceptance path has been qualified for the native backend.
- Q47/Q48: no five-class latency instrumentation or cold/warm benchmark.
- Q49/Q50: legacy/native implementations coexist and the additive migration
  round trip passes, but controlled cutover/rollback readers and checkpoint
  schema-evolution qualification are incomplete.
- The prescribed 100 seeded race interleavings and PWU continuity benchmark
  have not run.

## Acceptance Environment Reality

The isolated technical environment is named
`watt-native-executor-runtime-qualification`. Its Trusted-Baseline application
is exposed at `http://127.0.0.1:8040/app`; a temporary current-tree technical
qualification application is exposed at `http://127.0.0.1:8041/app`. PostgreSQL,
the baseline application, lease coordinator, and Tool Host remain available.
The Provider Worker exited after the recorded Q01 defects. One Provider request
reached schema validation, but no model result or production Effect was
created, and no seeded Human acceptance PWU exists.

Therefore this environment is suitable for no-Provider technical inspection,
not for the Blueprint's Human acceptance journey. A later acceptance admission
must bind an exact clean checkpoint, configure an authorized Provider without
leaking credentials, seed a governed PWU through normal authority, and prove
queue, interruption, recovery, artifact inspection, preview, authorization,
Runtime Commit, and delivery.

## Current Classification

```text
WATT-NATIVE EXECUTOR RUNTIME
    IMPLEMENTATION IN PROGRESS

CURRENT FOUNDATION
    FOCUSED VALIDATION PASS

RELEASE / CUTOVER
    BLOCKED ON MANDATORY QUALIFICATION AND MISSING RUNTIME CAPABILITIES
```

Legacy Codex remains the admitted operational backend unless a later governed
qualification and cutover explicitly changes that fact.
