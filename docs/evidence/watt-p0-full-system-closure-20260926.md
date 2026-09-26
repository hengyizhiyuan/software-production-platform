# Watt P0 full-system batch: qualified Reality and remaining gates

Date: 2026-09-26. Branch: `feature/production-environment-foundation`.
This record is a technical qualification, **not** Human Acceptance or a claim
that either full-system journey is complete.

## Reproducible source

- Starting P0 revision: `364f40fde5a22dbb2738b436f887cd7ad1e76ea5`;
  tree `f61ae4ba330aaa96b117f886ddbf1be028f27e93`.
- This committed and pushed baseline preserved the prior Self-Refine, Search
  and Multi-PWU implementation/evidence. Its migration head was
  `20260926_51`; backend regression was 1,400 passed and three explicit
  environment skips, with 75/75 JavaScript tests passed.
- P0 implementation revision: `726f9567f18598a2c7b9d7be4b6c5744a59c0457`;
  tree `5466eeeff7408d6feee08007654db26582e90ec8`. The schema-only
  follow-up is `9a74c19ed89484fe05d2266f57b3e4acb0fdd9fa`, tree
  `d7f10e9b5ef97eceaa0f35ab759ce45b0115f25f`; it removes a redundant
  uniqueness declaration already enforced by the composite primary key.
- P0 migration head: `20260926_54`.
- Full backend regression on the implementation revision: **PASS**, 1,416
  passed, three environment skips, zero failures in 55m43s. The first complete
  run exposed one stale WIC test assertion about external-only GitHub READ
  authorization; after aligning that assertion with the implemented scoped
  Access Grant, the full suite passed. The one-line schema metadata follow-up
  passed eight focused authenticated-authority/persistence tests. JavaScript:
  75/75 passed. The earlier invocation without `.venv/bin` on `PATH` was a
  test invocation error, not a product regression.
- Migration `20260926_54 (head)` is applied on the real PostgreSQL test
  database. Alembic autogenerate check still reports older index/check/unique
  constraint naming drift on pre-P0 tables; the new authority-table discrepancy
  was removed in `9a74c19`. No `alembic check` PASS is claimed. This historical
  schema naming drift is a non-blocking follow-up rather than an unreviewed
  automatic migration of unrelated tables.

## Implemented and observed scope

| Debt ID | Status | Evidence and precise limit |
| --- | --- | --- |
| TD-BASE-001 | CLOSED | Exact baseline above; resulting revision below after commit. |
| TD-IDENT-001 | CLOSED for single-owner profile | `/login` session and bearer token, server-derived `human:owner`, persisted organization membership and resource ACL, exact Work/repository checks, cookie Origin check, test-only auth bypass confined to pytest. Real HTTP smoke: unauthenticated goals 401, login 200, owner list 200, POST goal 201, read 200. No multi-actor IAM claim. |
| TD-REPO-002 | BLOCKED_EXTERNAL for live proof | GitHub READ/WRITE grants remain distinct from Human Delivery Authorization; credential references rather than tokens are persisted. Non-force push, branch-before/after observation, idempotent retry and optional exact PR are test-qualified. No approved live GitHub token or Human-accepted Candidate is available. Required full-system mode blocks push until Guardian returns an owner decision. |
| TD-REPO-003 | PARTIALLY_CLOSED | A complete Git bundle and checked SHA-256 are stored in PostgreSQL; real local Git/PostgreSQL tests removed worker checkouts, restored the exact history and exported the bundle, including a separate managed Work branch identity. Off-host backup/restore and machine-loss survival await infrastructure proof. |
| TD-CONT-001 | BLOCKED_EXTERNAL for independent-host proof | Compose overlay requires pre-provisioned off-host durable volumes and restart policies; queue, lease, checkpoint and receipt paths remain the existing owners. Local process/worker recovery tests pass, but client sleep/host replacement on independent infrastructure were not observed. |
| TD-PREV-001 | CLOSED for bounded Watt topology | Real Docker Candidate from the exact baseline revision started isolated PostgreSQL, Watt backend/frontend and gateway. Image verification checked 266 copied source/migration/runtime files; the final exact-revision Docker run is recorded below. A bounded declaration supports Redis; unsupported services/topologies fail explicitly. No universal topology claim. |
| TD-VERIFY-001 | CLOSED for Watt scenario | Preview READY requires served Git revision/tree, frontend HTML, backend health with database available, and a real goal POST/read-after-write via the isolated gateway. This is functional smoke evidence, not proof of every requirement. |
| TD-ECF-001 | PARTIALLY_CLOSED | In required owner mode, normal Work bootstrap wires the ECF owner runtime; Work consumes current owner repository Reality before creating each new governed attempt, and Control Room reobserves stale/revision-changed facts. A test uses separate Watt sessions and confirms supersession. Real native production integration hands off repository/change/delivery Reality. Full combined Journey A/B remains unproven. |
| TD-GUARD-001 | BLOCKED_EXTERNAL | Required owner mode wires Guardian owner intake and the real native production test confirms attributable intake. Inspected Guardian owner revision `371dfa7` exposes `admit`, `admit_payload`, `get`, but no findings/challenge/assurance decision or gate API. Watt must not manufacture a PASS; full-system remote push fails closed in this mode. |
| TD-SCOPE-001 | CLOSED | Human selected Journey A/B and the bounded frontend + backend + PostgreSQL + declared necessary support-service profile in this task. |

The P0 Multi-PWU sweep removed first-PWU-only software delivery assumptions:
Candidate preview reads the terminal Candidate snapshot and graph artifact
references; trusted delivery checks all satisfied units and requires passing
terminal-commit Verification; the Production Record computes the full base-to-
commit change set. The wider per-PWU measurement/economics gap stays under
`TD-PLAN-002` (P1).

The bounded complete-application delivery adapter now projects a full
application target from an exact Watt-style runtime tree, builds a bounded
runtime-source manifest for that commit, and routes the Human review link to the exact
Candidate preview. An `ACCEPT` decision is rejected unless that running
Candidate still has persisted served-runtime PASS evidence for the same
revision and tree. This is distinct from the older static-Web adapter and
does not imply that Human actually accepted this batch.

## Journey status

**A — Watt Managed Repository self-dogfood:** authenticated owner HTTP,
canonical managed Git, Work and native production substrates, exact real Watt
preview, database-backed served verification, ECF owner Reality and Guardian
intake have separate evidence. A single observed chain through all nodes,
Guardian decision, Human Acceptance and Delivery is **not** proven. Human
Acceptance is `PENDING`.

**B — external GitHub brownfield:** acquisition/branch/Work and GitHub provider
are implemented and test-qualified; a prior real native production test
exercised the local brownfield Work path with ECF/Guardian intake. No approved
live read/write GitHub credential, accepted Candidate, Guardian decision or
observed remote push/PR exists for this batch. Remote effect is
`NOT_EVALUATED`, not PASS.

## Real runtime evidence

- Baseline Watt Docker preview ID
  `d717cca0-658b-4441-a838-25ba300e1dab` used the exact baseline source,
  isolated `postgres:17.6-alpine`, backend and nginx gateway. Observed `/app`
  HTML 200, `/health` database `available`, goal creation 201 and read 200.
  Build/health logs were retained under
  `/private/tmp/watt-p0-real-preview/evidence/` on the qualification host;
  containers/volumes were stopped after the run. Initial BuildKit frontend
  retrieval failed due Docker Hub token timeout; using `DOCKER_BUILDKIT=0`
  built the same Dockerfile and passed. A read-only runtime path defect found
  on the first attempt was fixed before the passing attempt.
- Implementation revision Docker preview ID
  `4497f206-baad-4475-9848-924bd23ddf0d` verified 276 image files,
  started isolated frontend/backend/PostgreSQL and gateway, served the exact
  implementation revision/tree, returned `/app` 200 and database `available`,
  and completed goal create 201/read 200. This run passed and cleaned up all
  preview containers.
- Final code revision Docker preview ID
  `786a2a82-1004-42bb-a146-78355cbbb6c7` used exact commit
  `9a74c19ed89484fe05d2266f57b3e4acb0fdd9fa` and tree
  `d7f10e9b5ef97eceaa0f35ab759ce45b0115f25f`. It verified 276 image
  files, launched isolated frontend/backend/PostgreSQL and gateway, served
  `/app` 200 with database `available`, created a goal (201) and read it back
  (200). Qualification was **PASS**; containers and volumes were cleaned up.
  Build and service logs are under
  `/private/tmp/watt-p0-final-preview/evidence/786a2a82-1004-42bb-a146-78355cbbb6c7/`
  on the qualification host.
- Authenticated HTTP and managed Git recovery: tested against real local
  PostgreSQL; test evidence paths are in the table above.
- Independent worker: local recovery exercised by the regression corpus;
  independent-host activation is not observed.
- ECF/Guardian: tests load the detached owner revisions (`1a8e75e` ECF,
  `371dfa7` Guardian), not an imitation of their contracts. Guardian has
  intake only; no assurance gate is reported as passing.

## Remaining external and Human actions

1. Provision and activate an independent always-on host with off-host durable
   PostgreSQL/workspace/checkpoint/receipt storage, restore-capable backups,
   and separately installed ECF/Guardian owner packages; run the host-loss,
   disconnect, lease reclaim and exact recovery exercise in
   [the operations runbook](../operations/independent-runtime-qualification.md).
2. Guardian owner must expose an attributable findings/challenge/decision gate
   for the selected evidence chain. Watt can then consume and qualify it;
   intake alone is insufficient.
3. Supply scoped GitHub read/write credentials only for an authorized test
   repository, perform Human Acceptance and distinct Delivery Authorization,
   then run [the remote qualification](../operations/github-remote-qualification.md).
4. Human reviews the actual final Candidate and records acceptance. The batch
   has no authority to mark `HUMAN_ACCEPTANCE = PASS` itself.

Web search live qualification still needs `SPG_WEB_SEARCH_API_KEY`; it is
separate from this P0 release gate. P1 `TD-PLAN-002` measurement and other
census P1/P2 findings were not silently expanded into this batch.

```text
REPRODUCIBLE_BASELINE = PASS
FULL_BACKEND_REGRESSION = PASS (1416 passed; 3 skipped)
FULL_FRONTEND_REGRESSION = PASS (75 passed)
MIGRATION_HEAD = 20260926_54
SCHEMA_AUTOGENERATE = HISTORICAL_NAMING_DRIFT (no new P0 table mismatch)
AUTHENTICATED_ACTOR = PASS (single-owner profile)
SERVER_DERIVED_AUTHORITY = PASS
MANAGED_REPOSITORY_DURABLE_SOURCE = PASS (PostgreSQL-backed; off-host activation pending)
REMOTE_GIT_ACCESS_GRANT = IMPLEMENTED; LIVE_AUTH_BLOCKED
REMOTE_GIT_PUSH_OBSERVED = BLOCKED_EXTERNAL
OPTIONAL_PR_PATH = IMPLEMENTED; LIVE_AUTH_BLOCKED
WORKER_INDEPENDENT_OF_HUMAN_DESKTOP = BLOCKED_INFRA_ACTIVATION
QUEUE_AND_LEASE_SURVIVE_CLIENT_DISCONNECT = LOCAL_TEST_PASS; REMOTE_NOT_EVALUATED
WORKSPACE_RECOVERY_IS_DURABLE = LOCAL_POSTGRESQL_PASS; HOST_LOSS_NOT_EVALUATED
FULL_APPLICATION_PREVIEW_REAL_BACKEND_DB = PASS (bounded Watt topology)
SERVED_RUNTIME_VERIFICATION = PASS (bounded goal round trip)
ECF_DEFAULT_RUNTIME_INTEGRATION = PARTIAL; OWNER_RUNTIME_TEST_PASS
GUARDIAN_DEFAULT_RUNTIME_GATE = BLOCKED_OWNER_DECISION_API
MULTI_PWU_P0_PATHS_HAVE_NO_STALE_SINGLE_PWU_ASSUMPTION = PASS (active delivery path; measurement remains P1)
HUMAN_ACCEPTANCE = PENDING
FULL_SYSTEM_JOURNEY_A = NOT_CLOSED
FULL_SYSTEM_JOURNEY_B = NOT_CLOSED
P0_CODE_COMPLETABLE_BATCH = QUALIFIED_WITH_STATED_LIMITS
FULL_SYSTEM_CLOSURE = BLOCKED_BY_EXTERNAL_OWNER_INFRA_AUTH_AND_HUMAN_ACCEPTANCE
```
