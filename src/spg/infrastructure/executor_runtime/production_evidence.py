"""Bounded observation of one governed production workspace result."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import socket
import stat
import subprocess
import time

from spg.domain.native_execution import ExecutionBindingV2
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage


class ProductionWorkspaceVerificationFailed(RuntimeError):
    code = "VERIFICATION_FAILED"

    def __init__(self, message: str, *, diagnosis: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.diagnosis = diagnosis


def _path_diagnosis(path: Path) -> dict[str, object]:
    """Observe metadata only; never record file bytes, environment or stderr."""
    try:
        observed = path.lstat()
    except OSError as error:
        return {"stat_kind": "UNAVAILABLE", "stat_errno": error.errno,
                "stat_device": None, "stat_inode": None, "stat_uid": None,
                "stat_gid": None, "stat_mode": None}
    return {
        "stat_kind": ("SYMLINK" if stat.S_ISLNK(observed.st_mode)
                      else "DIRECTORY" if stat.S_ISDIR(observed.st_mode) else "OTHER"),
        "stat_errno": None, "stat_device": observed.st_dev, "stat_inode": observed.st_ino,
        "stat_uid": observed.st_uid, "stat_gid": observed.st_gid,
        "stat_mode": observed.st_mode,
    }


def _process_diagnosis() -> dict[str, object]:
    try:
        namespace = os.readlink("/proc/self/ns/mnt")
    except OSError:
        namespace = None
    return {
        "hostname": socket.gethostname(), "pid": os.getpid(),
        "uid": os.getuid() if hasattr(os, "getuid") else None,
        "gid": os.getgid() if hasattr(os, "getgid") else None,
        "mount_namespace": namespace,
    }


def _git(workspace: Path, *args: str, diagnosis: dict[str, object]) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(workspace), *args], capture_output=True, check=False,
        timeout=30, env={"PATH": os.environ.get("PATH", ""), "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode:
        raise ProductionWorkspaceVerificationFailed(
            f"VERIFICATION_FAILED: Git observation {args[0]} failed",
            diagnosis={**diagnosis, "check": "GIT_OBSERVATION",
                       "git_operation": args[0], "git_returncode": result.returncode,
                       "checked_at": datetime.now(timezone.utc).isoformat()},
        )
    return result.stdout


def observe_production_workspace(
    binding: ExecutionBindingV2,
    storage: ContentAddressedStorage,
    *,
    require_change: bool,
    required_artifacts: tuple[str, ...] = (),
) -> dict[str, object]:
    """Check exact source, path, size and diff; retain bounded immutable evidence."""

    context = binding.production_context
    diagnosis: dict[str, object] = {
        "schema_version": 1, "require_change": require_change,
        "attempt_id": str(binding.attempt_id), "work_id": str(binding.work_id),
        "pwu_id": str(binding.pwu_id), "workspace_id": str(binding.workspace.workspace_id),
        "source_vector_digest": binding.source_vector.digest,
        "expected_tree": (binding.source_vector.members[0].source_tree_oid
                          if len(binding.source_vector.members) == 1 else None),
        "expected_revision": None if context is None else context.repository_revision,
        "work_reality_revision_id": None if context is None else str(context.work_reality_revision_id),
        "availability_wait_ms": 0, **_process_diagnosis(),
    }

    def reject(
        message: str, check: str, *, checked_path: Path | None = None,
        failed_relative_path: str | None = None, observe_checked_path: bool = True,
    ) -> ProductionWorkspaceVerificationFailed:
        observed: dict[str, object] = {}
        if checked_path is not None:
            observed["checked_path"] = str(checked_path)
            observed["failed_relative_path"] = failed_relative_path
            if observe_checked_path:
                observed.update({f"checked_{key}": value
                                 for key, value in _path_diagnosis(checked_path).items()})
        return ProductionWorkspaceVerificationFailed(
            message, diagnosis={**diagnosis, **observed, "check": check,
                                "checked_at": datetime.now(timezone.utc).isoformat()})

    if context is None or len(binding.source_vector.members) != 1:
        raise reject("VERIFICATION_FAILED: exact source missing", "EXACT_SOURCE_BINDING")
    member = binding.source_vector.members[0]
    mount = next((item for item in binding.workspace.mounts
                  if item.mount_id == member.mount_id and item.writable), None)
    if mount is None:
        raise reject("VERIFICATION_FAILED: writable mount missing", "WRITABLE_MOUNT_BINDING")
    raw_workspace = Path(mount.host_path)
    diagnosis.update({"mount_id": mount.mount_id, "host_path": mount.host_path,
                      "checked_path": str(raw_workspace),
                      "container_path": mount.container_path, **_path_diagnosis(raw_workspace)})
    if diagnosis["stat_kind"] == "SYMLINK":
        raise reject("VERIFICATION_FAILED: workspace unavailable", "WORKSPACE_NOT_SYMLINK")
    # A prepared workspace may briefly be invisible to a separately mounted
    # Worker. Wait only before the first effect; every exact Git/source check
    # below still runs and a persistently absent workspace remains a failure.
    availability_started = time.monotonic()
    if not require_change:
        while not raw_workspace.is_dir() and time.monotonic() - availability_started < 2:
            time.sleep(0.1)
    availability_wait_ms = int((time.monotonic() - availability_started) * 1000)
    diagnosis.update({"availability_wait_ms": availability_wait_ms,
                      **_path_diagnosis(raw_workspace)})
    if diagnosis["stat_kind"] == "SYMLINK":
        raise reject("VERIFICATION_FAILED: workspace unavailable", "WORKSPACE_NOT_SYMLINK")
    if diagnosis["stat_kind"] != "DIRECTORY":
        raise reject("VERIFICATION_FAILED: workspace unavailable", "WORKSPACE_DIRECTORY")
    workspace = raw_workspace.resolve()
    diagnosis["resolved_path"] = str(workspace)
    effective_ids = os.access in os.supports_effective_ids
    writable = os.access(workspace, os.W_OK | os.X_OK, effective_ids=effective_ids)
    diagnosis.update({"workspace_write_access": writable, "access_effective_ids": effective_ids})
    if not writable:
        raise reject("VERIFICATION_FAILED: workspace is not writable", "WORKSPACE_WRITE_ACCESS",
                     checked_path=workspace)
    top = _git(workspace, "rev-parse", "--show-toplevel", diagnosis=diagnosis).decode().strip()
    baseline = _git(workspace, "rev-parse", "--verify", "HEAD^{commit}", diagnosis=diagnosis).decode().strip()
    tree = _git(workspace, "rev-parse", "--verify", "HEAD^{tree}", diagnosis=diagnosis).decode().strip()
    diagnosis.update({"observed_repository_root": top, "observed_revision": baseline,
                      "observed_tree": tree})
    if Path(top).resolve() != workspace:
        raise reject("VERIFICATION_FAILED: repository basis changed", "EXACT_REPOSITORY_ROOT")
    if baseline != context.repository_revision:
        raise reject("VERIFICATION_FAILED: repository basis changed", "EXACT_SOURCE_REVISION")
    if tree != member.source_tree_oid:
        raise reject("VERIFICATION_FAILED: repository basis changed", "EXACT_SOURCE_TREE")
    _git(workspace, "diff", "--check", context.repository_revision, diagnosis=diagnosis)

    total_bytes = 0
    artifact_limit = binding.resource_envelope.max_artifact_bytes
    for root, dirs, files in os.walk(workspace, followlinks=False):
        for name in dirs:
            path = Path(root) / name
            if path.is_symlink():
                raise reject("VERIFICATION_FAILED: workspace symlink found", "NO_WORKSPACE_SYMLINKS",
                             checked_path=path, failed_relative_path=path.relative_to(workspace).as_posix())
        for name in files:
            path = Path(root) / name
            if path.is_symlink():
                raise reject("VERIFICATION_FAILED: workspace symlink found", "NO_WORKSPACE_SYMLINKS",
                             checked_path=path, failed_relative_path=path.relative_to(workspace).as_posix())
            size = path.stat().st_size
            if ".git" not in path.relative_to(workspace).parts and size > artifact_limit:
                raise reject("VERIFICATION_FAILED: artifact size limit exceeded", "ARTIFACT_SIZE_LIMIT",
                             checked_path=path, failed_relative_path=path.relative_to(workspace).as_posix())
            total_bytes += size
            if total_bytes > binding.resource_envelope.max_workspace_bytes:
                raise reject("VERIFICATION_FAILED: workspace size limit exceeded", "WORKSPACE_SIZE_LIMIT")

    tracked = _git(workspace, "diff", "--name-only", context.repository_revision, diagnosis=diagnosis).decode().splitlines()
    untracked = _git(workspace, "ls-files", "--others", "--exclude-standard", diagnosis=diagnosis).decode().splitlines()
    changed = tuple(sorted(set(tracked + untracked)))
    if len(changed) > 256:
        raise reject("VERIFICATION_FAILED: too many changed files", "CHANGED_FILE_COUNT")
    if require_change and not changed:
        raise reject("VERIFICATION_FAILED: no repository change observed", "REPOSITORY_CHANGE_REQUIRED")
    for relative in changed:
        candidate = PurePosixPath(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise reject("VERIFICATION_FAILED: unsafe changed path", "SAFE_CHANGED_PATH",
                         checked_path=workspace / relative, failed_relative_path=relative,
                         observe_checked_path=False)
        if not any(
            relative == allowed or relative.startswith(allowed.rstrip("/") + "/")
            for allowed in member.write_scope
        ) or any(
            relative == forbidden or relative.startswith(forbidden.rstrip("/") + "/")
            for forbidden in member.forbidden_paths
        ):
            raise reject("VERIFICATION_FAILED: changed file outside Task scope", "TASK_WRITE_SCOPE",
                         checked_path=workspace / relative, failed_relative_path=relative)
    if require_change:
        for relative in required_artifacts:
            candidate = PurePosixPath(relative)
            if candidate.is_absolute() or ".." in candidate.parts or not (workspace / relative).is_file():
                raise reject("VERIFICATION_FAILED: required artifact missing", "REQUIRED_ARTIFACT",
                             checked_path=workspace / relative, failed_relative_path=relative,
                             observe_checked_path=not candidate.is_absolute() and ".." not in candidate.parts)
    diff = _git(workspace, "diff", "--binary", context.repository_revision, diagnosis=diagnosis)
    if len(diff) > min(artifact_limit, 1048576):
        raise reject("VERIFICATION_FAILED: diff evidence limit exceeded", "DIFF_EVIDENCE_LIMIT")
    artifacts = []
    for relative in changed:
        path = (workspace / relative).resolve()
        if workspace not in path.parents:
            raise reject("VERIFICATION_FAILED: changed path escapes workspace", "CHANGED_PATH_CONTAINMENT",
                         checked_path=path, failed_relative_path=relative, observe_checked_path=False)
        if path.is_file():
            artifacts.append({"path": relative, "sha256": sha256(path.read_bytes()).hexdigest(),
                              "size_bytes": path.stat().st_size})
    diagnosis.update({"check": "WORKSPACE_OBSERVED",
                      "checked_at": datetime.now(timezone.utc).isoformat()})
    evidence = {
        "workspace_diagnosis": diagnosis,
        "execution_id": str(binding.attempt_id),
        "workspace_id": str(binding.workspace.workspace_id),
        "repository_revision": context.repository_revision,
        "files_changed": list(changed),
        "workspace_bytes": total_bytes,
        "workspace_availability_wait_ms": availability_wait_ms,
        "tracked_diff": diff.decode("utf-8", errors="replace"),
        "artifacts": artifacts,
    }
    digest, _path = storage.put_json(f"execution/{binding.attempt_id}", evidence)
    return {"workspace_diagnosis": diagnosis,
            "workspace_id": str(binding.workspace.workspace_id),
            "repository_revision": context.repository_revision,
            "files_changed": list(changed), "workspace_bytes": total_bytes,
            "workspace_availability_wait_ms": availability_wait_ms,
            "diff_reference": f"sha256:{digest}", "artifacts": artifacts}
