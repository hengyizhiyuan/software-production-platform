# Watt-native Executor Runtime — Implementation and Qualification Progress

Date: 2026-09-11. Repository basis before the uncommitted implementation:
`8d85100bac5505462d0866398bd076ecb21fcf39` on
`feature/spg-first-vertical-slice`.

DeepSeek migration continuation is recorded separately in
[watt-native-executor-deepseek-provider-migration.md](watt-native-executor-deepseek-provider-migration.md).
It preserves the OpenAI qualification history below rather than rewriting it.

## Status

```text
WATT-NATIVE EXECUTOR RUNTIME FOUNDATION
    IMPLEMENTED

FOCUSED VALIDATION
    PASS

QUALIFICATION CLOSURE
    IN PROGRESS; DEEPSEEK P1/P2 AND Q01 PASS

TECHNICALLY_QUALIFIED
    NO — NORMATIVE CONTINUITY AND REMAINING Q-CASE GATES REMAIN

RUNTIME_READY_FOR_HUMAN_ACCEPTANCE
    PRELIMINARY RUNTIME RUNNING; COMPLETE ACCEPTANCE SCRIPT NOT YET QUALIFIED

HUMAN ACCEPTANCE
    PENDING HUMAN DECISION
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

The final current-tree rerun used the corrected environment against an isolated
PostgreSQL qualification database. All 412 non-integration cases passed. The
integration suite collected 607 cases and exited successfully: 599 passed and
eight existing conditional cases skipped. The only warnings were known Pydantic
2.11 deprecations in the existing MVP application-flow test.

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

## DeepSeek continuation implementation delta

The DeepSeek continuation kept all earlier failed/UNKNOWN Attempts immutable
and completed Q01 through independent Verification, exact Candidate
authorization and isolated Trusted Baseline advancement. Exact IDs, Provider
requests and usage are in the companion DeepSeek evidence record.

Generic runtime closure added after Q01 now includes:

- supervised no-shell process groups with bounded output, exact delivery-owned
  cancellation, TERM/KILL receipts and mid-tool Pause/Stop/Cancel barriers;
- safe same-Attempt recovery before any effect, receipt rehydration after a
  worker crash, and `UNKNOWN / RECONCILING` fencing when an effect is unresolved;
- bounded context compaction that preserves the exact contract/source capsule,
  conservative quota/unknown-spend accounting across successor envelopes, and
  retained residual obligations on Provider resource failure;
- Session checkpoint inheritance, exact checkpoint fork and explicit close;
- at-least-once outbox claim/ack, cursor-expiry/ahead `RESET`, snapshot
  high-water, and bounded 256-event replay batches;
- five-class latency projection with measured spans and explicit unavailable
  fields instead of a fabricated aggregate duration;
- descriptor-anchored Tool Host reads/writes that reject traversal, symlinks,
  hardlinks, non-regular files and `.git` metadata; live remote process-tree
  cancellation left no child process behind;
- exact multi-repository `CandidateVector`, independent per-target Verification,
  digest-bound authorization, sorted per-target CAS, durable `PARTIAL` physical
  Reality, forward recovery and one atomic aggregate Runtime Commit; and
- explicit workspace pins plus crash-resumable 30-day hibernation to a verified
  content-addressed archive, restore, 180-day cold retirement tombstones and
  retention of the last recovery bundle.

The additive schema head is now `20260912_37`: CandidateVector and trusted
source pointers (`35`), retention actions/pins/tombstones (`36`), and exact
native vector Verification (`37`). These migrations do not rewrite legacy
rows.

## Open Mandatory Qualification

The following areas remain materially open:

- Q06, Q12–Q14, Q17–Q30 now have focused crash/control/Session/compaction
  coverage, but the complete prescribed cross-product and host-reboot rehearsal
  have not yet been recorded.
- Q15/Q45/Q46 now cover durable relay reclaim, `RESET`, snapshot high-water and
  bounded lossless replay. A measured slow-browser disconnect/coalescing run is
  still required.
- Q31–Q35 are implemented and pass real PostgreSQL plus two-real-Git-repository
  partial-convergence/forward-recovery tests. A Human-visible two-repository
  preview rehearsal remains part of acceptance preparation.
- Q38–Q40: traversal, one symlink escape, secret filtering, internal networking,
  and Docker-socket absence are proven only as a subset. Symlink race, hardlink,
  archive escape, metadata/control egress, per-Work host isolation, and warm
  reuse isolation remain unqualified. A shared Tool Host plus bearer token is
  not claimed as complete hostile-code isolation.
- Q41 cumulative PWU enforcement and unknown-spend retention pass focused
  tests. Q42 pin/hibernation/restore/retirement behavior passes focused tests;
  DB/disk-full and host-reboot fault injection remain open under Q43.
- Q44: no seeded exact-Candidate preview and Human authorization/delivery
  acceptance path has been qualified for the native backend.
- Q47 exposes the five latency classes with unavailable stages explicit. Q48
  still requires the prescribed cold/warm measurement set.
- Q49/Q50: legacy/native implementations coexist and the additive migration
  round trip passes, but controlled cutover/rollback readers and checkpoint
  schema-evolution qualification are incomplete.
- A 100-round two-scheduler allocation contention test passes, but the broader prescribed
  100 seeded transition matrix and the 36-run PWU continuity benchmark remain
  release gates.

## Acceptance Environment Reality

The earlier Q01 environment remains on `http://127.0.0.1:8040/app` with its
database and volumes unchanged. A separate current-tree Human environment is
running under Compose project `watt-native-human-acceptance-v32` at
`http://127.0.0.1:8042/app`. It has its own PostgreSQL, workspace, checkpoint
and application volumes, migration head `20260912_37`, and five independent
healthy processes (application, coordinator, Worker, Tool Host, PostgreSQL).

The acceptance startup overlay is tracked in
`compose.native-executor.human-acceptance.yaml` and
`docker/start_human_acceptance.py`; every application process loads the current
working source read-only rather than silently switching to the old activated
checkout. DeepSeek readiness is exact `deepseek-flash / high`, with no request
issued during readiness.

Seed Work `e49b7a20-f6f6-4dd3-8831-e3af98c22547` is visible in the UI and
intentionally remains DRAFT. It has zero PWUs, Steps and Effects, so the Human
owns admission and no Provider spend was consumed by environment preparation.
Browser inspection confirmed the UI, health state, Work detail and execution
queue render. Human product acceptance remains pending.

## Current Classification

```text
WATT-NATIVE EXECUTOR RUNTIME
    IMPLEMENTATION IN PROGRESS

CURRENT FOUNDATION / DEEPSEEK Q01
    PASS

DETERMINISTIC CLOSURE
    BROAD REGRESSION PASS; NORMATIVE CONTINUITY BENCHMARK REMAINS

RELEASE / CUTOVER
    BLOCKED ON CONTINUITY QUALIFICATION AND HUMAN ACCEPTANCE
```

Legacy Codex remains the admitted operational backend unless a later governed
qualification and cutover explicitly changes that fact.

## 2026-09-12 qualification closure addendum

The resumed frozen continuity benchmark is complete. It contains all 18 A/B
pairs and all 36 executions under plan digest
`e57d664eb9dbe2988949c0cecf1bb37ab010ecdaf07808dc1921d93bcac91c57`.
Only 8/18 B executions passed, so `CONTINUITY_QUALIFIED` is **NO**. Known spend
was RMB 2.26231347 and the conservative total including response-unknown
reservations was RMB 3.69511347 of the RMB 100 cap. The three assigned
`deepseek-v4-pro / high` executions ran across T3, T4 and T5 task types and all
remain failed outcomes.

Closure continued after the benchmark: Q29 retained-volume reboot passed with
zero Provider requests; Q38 symlink-race/archive/disk-full negative coverage
was added; Q48 completed 30 cold and 30 warm measurements; and migration
`20260912_39` added fail-closed checkpoint schema versioning with a successful
38→39→38→39 data-preserving rehearsal.

Q40 failed a real warm-reuse isolation probe because the shared Tool Host can
see another Work's private workspace. This violates a zero-tolerance invariant
and requires an architecture-owned per-Work execution/mount boundary. Together
with the immutable failed continuity result, it prevents
`TECHNICALLY_QUALIFIED` and `RUNTIME_READY_FOR_HUMAN_ACCEPTANCE`.

The complete current result, Q-case ledger, performance figures, fixes,
cutover/rollback limits and Human runtime identity are recorded in
[watt-native-executor-qualification-closure-20260912.md](watt-native-executor-qualification-closure-20260912.md).
