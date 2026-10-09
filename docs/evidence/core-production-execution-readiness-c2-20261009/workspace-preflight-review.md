# C2-A — Workspace Preflight Review

## Scope and evidence boundary

The reviewed C2 base is Watt `e7c1b70ac30b89940a7596f835c6f0ccc928a9ba`
(C1 source `00e2a77e6b80ea79185d74a12db2cec8eeb9445e`). The focused
implementation is recorded by the final C2 source commit and qualification
report; this note does not substitute the base revision for that final identity.

This work adds metadata to the existing Workspace observation and durable
`ExecutionWorkspacePreflightRejected` event. It does not create a new Owner,
change C1 contracts, widen Task paths, rebuild a missing Workspace, retry a
production Work, or modify a historical container. The original two-second
pre-effect wait and all source/diff/scope/size checks remain. Preflight now also
requires actual process write/search access without creating a file and checks
the declared exact SourceVector tree against observed HEAD tree.

## Confirmed diagnostic defect; historical cause UNKNOWN

At the base revision, `observe_production_workspace` returned the same
`VERIFICATION_FAILED: workspace unavailable` for a root symlink and a missing
or non-directory Workspace. `NativeExecutionWorker.run_once` retained only the
exception string, and `NativeExecutorRuntimeService.record_production_preflight_rejection`
persisted only `failure`. No failed predicate, errno, filesystem identity or
Worker mount namespace was retained by that historical event. This is a
confirmed evidence gap in the rejection path, not proof that a particular
mount race caused the historical failure.

Historical attempt `e3addc05-7ee4-49f4-9043-c69b6466bcf8` and its rejection remain
unchanged. Their original root cause remains **UNKNOWN**. Present availability
or a successful future preflight must not be projected backward as an
explanation or historical PASS.

## Actual path mapping and current read-only observation

Code path at the reviewed base:

1. `NativeCompatibilityExecutor._admission` takes
   `execution.workspace.workspace_path`, resolves it, and uses that same
   isolated path for `WorkspaceManifest.host_storage_id` and the writable
   `primary` mount's `host_path`.
2. The primary SourceVector member and manifest mount both use
   `/workspace/primary` as the tool container path. That alias is not the path
   used for Worker-side Git preflight.
3. `observe_production_workspace` selects the SourceVector member's writable
   mount by `mount_id` and reads its `host_path` in the Worker process namespace.
   It requires the path to be a real directory, Git top level to equal the
   resolved workspace and HEAD to equal the admitted revision; the C2 change
   also verifies HEAD tree against the admitted SourceVector tree and requires
   `os.access(W_OK | X_OK)` for actual process write/search access.
4. `ProductionEnvironmentToolHost` consumes the manifest host repository path
   while executing governed tools in its environment's container workspace.
   The preflight does not substitute the tool alias for its host path.

At approximately `2026-10-09T06:51:44Z`, read-only SSH/Docker observations gave:

| Observed field | Value |
| --- | --- |
| Worker container | `watt-n1-worker-20261008` |
| Full container ID | `e942e5fc1f917edc6e90b35bb3965d679c3cc554cba4a0724b8509756b71041b` |
| Current container state / StartedAt | `running` / `2026-10-09T01:00:56.607016088Z` |
| Workspace volume source | `/data/docker/volumes/watt-n1-workspaces-20261008/_data` |
| Worker mount destination / mode | `/var/lib/spg/native-workspaces` / RW |
| Worker UID / GID | `10001` / `10001` |
| Worker hostname | `e942e5fc1f91` |
| Worker mount namespace | `mnt:[4026533515]` |
| Attempt host path | `/var/lib/spg/native-workspaces/e3addc05-7ee4-49f4-9043-c69b6466bcf8` |
| Current directory / symlink predicates | directory true / symlink false |
| Current device / inode | `64785` / `2137788` |
| Current mode / owner | `0o40755` / `10001:10001` |
| Current Git HEAD | `0bdd028418e0e7efea7675cfbbd6b6a3a008ceeb` |

### Existing configuration seam

`Application.work` constructs `DockerCliContainerRuntime` with
`workspace_volume_root=settings.workspace_root` (`application/bootstrap.py:291`;
`Application.repository_asset_service` at line 140 has the same provider binding).
Worker/runtime operations also use `settings.native_executor_workspace_root`.
`DockerCliContainerRuntime` shared-volume handling requires each prepared host
mount to lie within its configured root and projects its root-relative suffix
under `/watt-workspaces`, linked to the tool container's declared mount path.
These separately configured roots require explicit consistency; the manifest
and live provider/container mounts must be checked on the new actual C2 Attempt.

At approximately `2026-10-09T07:03:27Z`, a read-only query of exactly two safe
path keys in the current N1 Worker returned both `SPG_WORKSPACE_ROOT` and
`SPG_NATIVE_EXECUTOR_WORKSPACE_ROOT` as `/var/lib/spg/native-workspaces`. No other
environment keys were queried or printed. Current equality does not establish
the historical configuration or cause. Parent C2 isolation preparation will
set both keys explicitly to that path using a new Workspace volume; this note
neither modifies those keys nor asserts a future mount is already qualified.

These are E1 observations of this current container and directory, not a new
Work qualification, completeness of the historical audit, or proof of
historical visibility. The inspect/stat/Git calls made no changes. Two failed
read commands were classified as command construction failures (an inspect
quote and a trailing PowerShell pipeline CR in a Git argument); the corrected
read-only commands produced the values above. Those failures were not Runtime
or repository failures.

## Minimal implementation

- `production_evidence.py`: fixed check codes with exact binding/source/mount
  references; host/tool paths; checked-at time; bounded wait; hostname, PID,
  UID/GID and mount namespace; lstat kind/errno/device/inode/owner/mode;
  expected and observed Git revision/root/tree. Scope, symlink, artifact and
  path rejections identify the actual checked path and relative path with
  applicable lstat metadata. An already rejected absolute/traversal/escaped
  path is recorded without probing outside the permitted workspace. Metadata
  contains no source URL,
  file contents, environment, credentials, or Git stderr. A failed later stat
  clears earlier stat values rather than presenting stale inode data as a
  final observation. `WORKSPACE_WRITE_ACCESS` checks write plus search access
  without writing a probe; `EXACT_SOURCE_TREE` rejects a mismatched declared
  tree even when the admitted commit matches. Successful observation remains
  content addressed.
- `worker.py`: passes the verifier's structured metadata alongside the
  unchanged failure string before terminal settlement. No failed preflight
  reaches the kernel.
- `executor_runtime.py`: optional metadata on the existing rejection event,
  with a fixed scalar-field allowlist, 16 KiB total string ceiling, exact
  binding comparison and existing Worker epoch fence. Worker ID comes from
  the allocation. Old message-only callers remain supported and do not gain
  invented structured evidence.

## Focused qualification inputs

New path/Git cases cover the correct directory and durable evidence, persistent
absence, a non-directory path, a root symlink without waiting or acquiring
another workspace, a nested symlink, an out-of-scope existing change before
effects, and a changed HEAD retaining both expected and observed revisions.
Three review follow-ups cover actual nonroot write-access rejection, an incorrect
source tree with an unchanged exact commit, and the specific path/errno of a
missing required artifact. Total new cases: 10 path/Git and 2 real-PostgreSQL.
New real-PostgreSQL cases check durable rejection before terminal settlement,
no kernel execution, exact Worker/binding identity, rejection of metadata for
another attempt or arbitrary fields, and old-call compatibility.

AST parsing of the five changed/new Python files passed locally. No local
Runtime test was claimed. Execute these tests only in the authorized new C2
qualification runtime and dedicated disposable database, under the real
nonroot Worker UID (the permission test fails explicitly under root rather than
being silently skipped):

```text
python -m pytest tests/test_c2_workspace_preflight.py tests/test_production_execution_runtime.py tests/integration/test_c2_workspace_preflight.py tests/integration/test_native_executor_runtime.py::test_production_preflight_failure_keeps_exact_diagnostic_before_terminal
```

The final report must attach actual test exit/result and exact source/image/
database identities. This note supplies neither a G0 PASS nor historical cause
resolution.
