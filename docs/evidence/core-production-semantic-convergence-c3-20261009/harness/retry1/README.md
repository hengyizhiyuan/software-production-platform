# C3 retry-1 control package

Status: PREPARED_ONLY. Independent engineering agent; no Human Acceptance.

This package changes only control/evidence artifacts. No application source, Owner
contract, production checkout, historical Work or sealed Holdout was modified.
No remote command, build, service, database, model or Work has been executed by
this preparation task. The parent task owns upload and all explicit execution.

## Resource identities

- Exact allowed run root: `/data/watt/c3-semantic-convergence-20261009/retry-1`.
  Original root is recognized then rejected by retry controls. Other paths, dot
  components and symlink roots are rejected. There is no arbitrary run-root input.
- New business qualification DB: `spg_c3_retry1_qualification_20261009` in existing
  `watt-c3-postgres-20261009`. Creating it changes the shared cluster catalog but
  does not reset an old business DB.
- New fixture PostgreSQL: `watt-c3-retry1-fixture-postgres-20261009`, image
  `sha256:d741b376874687de90374fd34f55c6b2760e8f7bd7e4ae5cd47f50757fc08cf8`,
  no published port, new `retry-1/regression-postgres` directory, fresh password.
  Its DB remains `c1_contract_continuity` to satisfy the unmodified C1 fixture
  guard. Regression URLs use this container's loopback network namespace only.
- Four new roles: `watt-c3-retry1-{api,coordinator,worker,tool-host}-20261009`.
- New volume: `watt-c3-retry1-workspaces-20261009`; API loopback port `18301`.
- Existing C3 PG/Gitea/control/executor networks are verified and reused.
  They are never recreated, restarted or reset. Executor network remains internal;
  the existing control network retains its observed connectivity.
- API/operator and tool-host tokens are newly generated. Shared PG/Gitea values
  come only from original C3 `private/credentials.json`. The already Human-authorized
  test Provider key is read only from original C3 `private/watt-c3-api-20261009.env`
  and copied to retry private `provider.env`. No old N1 environment is inspected.
- Docker socket access is the inherited C3 isolated execution limitation; this
  package does not claim an independent daemon security boundary.

## Preservation of unrelated checkout work

Resource preparation observes `/data/watt/runtime/source` read only before and
again after preparing new resources. Required current expectation:

- HEAD `5de657f3cb65780adf50f6557b54171a6c3cfae5`;
- branch `codex/admin-work-ai-diagnostic-export-ecs`;
- clean status;
- independent `refs/heads/main` `ee5bd86a53891f9391785c91d0ccef81ad2d56c3`.

A difference stops the preparer and retains partial new resources for read-only
reconciliation. No checkout switch/reset/write occurs. The origin of that outside
checkout change is UNKNOWN; historical canonical main is not its observed HEAD.
The source build comes from the explicitly frozen C3 Git archives, not that checkout.

## Local freeze, then upload

All 12 Python controls must first be committed by the parent. Application revision
and control revision are separate exact inputs; Guardian must be at its supplied
exact revision and clean. These commands are instructions, not executed receipts:

```powershell
# From the C3 Watt worktree. Substitute exact committed IDs.
python docs/evidence/core-production-semantic-convergence-c3-20261009/harness/retry1/prepare_c3_freeze.py --watt-revision <APPLICATION_SHA> --guardian-revision <GUARDIAN_SHA> --control-revision <CONTROL_SHA>
# Above is a dry plan. Only the following flag writes local exact archives:
python docs/evidence/core-production-semantic-convergence-c3-20261009/harness/retry1/prepare_c3_freeze.py --watt-revision <APPLICATION_SHA> --guardian-revision <GUARDIAN_SHA> --control-revision <CONTROL_SHA> --build-attempt-id 1 --execute
```

New outputs are `.c3-development-inputs/retry-1/frozen-attempt-1/` and
`docs/evidence/core-production-semantic-convergence-c3-20261009/retry-1/frozen-inputs.json`.
The original local/remote freeze is not overwritten. The producer explicitly limits
Watt archive inputs to Docker COPY paths. It records physical archive file SHA256;
Git export line-ending transforms must be reported if observed, not treated as raw
Git Blob byte identity. No production or Holdout data is included in archives.

Upload the 12 Python controls into the exact new remote root, the new manifest to
that root's `frozen-inputs.json`, and exact archives under its `input-archives/`.
Retained test dependency archive must be copied, not moved, into that child directory
and match `beefa9671df14d21f2763a4e85841962f10af824a37caf6c679555166b13b9a6`.
Do not upload README/static receipts as extra files at root before preparation;
resource preparer admits only manifest, input-archives and frozen Python controls.
Original G0 input is copied byte-for-byte by the preparer from original C3 evidence
into new evidence, recording its SHA without printing its text.

## Explicit remote execution order (parent only)

Set `PYTHONDONTWRITEBYTECODE=1` for all SSH/host control runs (for example
`PYTHONDONTWRITEBYTECODE=1 python3 ROOT/prepare_c3_retry1_resources.py --execute`).
Every control entry also sets `sys.dont_write_bytecode=True` before importing the
scope helper. No arbitrary `__pycache__` contents are admitted or deleted.
All host action controls default to a dry plan before filesystem/Docker/DB access.
The exact root is default; `--run-root` accepts only the scoped child. Do not pass
`--execute` until the parent has inspected frozen revisions and resource identities.

```text
python3 ROOT/prepare_c3_retry1_resources.py                  # dry plan
python3 ROOT/prepare_c3_retry1_resources.py --execute        # new resources only
python3 ROOT/build_c3_image.py --execute                    # frozen archives only
python3 ROOT/run_final_image_regression.py --execute        # no model key/calls
python3 ROOT/launch_c3_runtime.py --execute                  # exact built image
python3 ROOT/run_c3_normal_entry.py --execute                # one original G0 entry
python3 ROOT/c3_export_owner_records.py --execute-read-only # new state Work only
python3 ROOT/scan_public_evidence.py --execute               # known-value scan
```

Here `ROOT` means the exact retry-1 root above, never the original root.
Preparation is exclusive: existing new DB/role/volume/private/app/evidence paths
are not overwritten. Migration and role names also remain after any failure.
There is no automatic cleanup or reset. Partial preparation requires read-only
reconciliation, not blind rerun. Shared fixture PG may need readiness inspection
before starting regression; no fallback to an old DB is allowed.

Regression verifies actual imports and all frozen Owner source identities. It uses
baked Watt tests, exact frozen Guardian tests only (no Guardian source overlay),
no model credential, and the separate new fixture server. Groups are Watt unit,
Guardian unit, C1 chain, C3 durable carrier and C2 PostgreSQL preflight. Requested
source-facet and Guardian adapter tests are included. Counts/exit/image/sources
must be recorded; earlier original-image failures and supplements remain history.

Launch validates frozen control SHA, build source equality and exact Watt/GN/ECF
labels, migrates only the new business DB, verifies migration `20261007_72`, creates
four isolated roles and records actual role imports. Provider READY is configuration
only, never proof of a model request or Work PASS. Native/Delivery behavior and
budgets remain the frozen application's governed implementation.

Normal entry requires actual import PASS plus all five new regression receipts
with nonzero tests, no failures/errors/skips, same exact image and sources. It checks
actual new Worker image/user before its scoped write probe. Single-submit driver
preserves IN_FLIGHT/UNKNOWN and state; no ambiguous-response repeat, manual
progression/recovery, Human Integration/Acceptance or Delivery authorization.

Collector consumes only the new normal-entry state's Work ID, exact DB, source
and isolated role; reads Owner facts in a READ ONLY transaction. Raw data remains
retry private mode0600. Public release performs known-value redaction only and
retains UNKNOWN sensitive-value coverage; root must review before publishing.
Absent evidence is UNKNOWN, and no report or artifact alone implies Work PASS.

## Static verification scope

`static-preparation-receipt.json` records AST validity, seven default no-contact
plans, strict root rejection checks and current control SHA256. These observations
are local control checks only, not Runtime Conformance or real G0 qualification.
No Holdout specification was opened; its seal and approval boundary remain intact.
