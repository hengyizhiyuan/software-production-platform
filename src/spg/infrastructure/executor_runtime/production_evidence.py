"""Bounded observation of one governed production workspace result."""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import subprocess

from spg.domain.native_execution import ExecutionBindingV2
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage


class ProductionWorkspaceVerificationFailed(RuntimeError):
    code = "VERIFICATION_FAILED"


def _git(workspace: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(workspace), *args], capture_output=True, check=False,
        timeout=30, env={"PATH": os.environ.get("PATH", ""), "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode:
        raise ProductionWorkspaceVerificationFailed(
            f"VERIFICATION_FAILED: Git observation {args[0]} failed"
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
    if context is None or len(binding.source_vector.members) != 1:
        raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: exact source missing")
    member = binding.source_vector.members[0]
    mount = next((item for item in binding.workspace.mounts
                  if item.mount_id == member.mount_id and item.writable), None)
    if mount is None:
        raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: writable mount missing")
    raw_workspace = Path(mount.host_path)
    workspace = raw_workspace.resolve()
    if raw_workspace.is_symlink() or not workspace.is_dir():
        raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: workspace unavailable")
    top = _git(workspace, "rev-parse", "--show-toplevel").decode().strip()
    baseline = _git(workspace, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if Path(top).resolve() != workspace or baseline != context.repository_revision:
        raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: repository basis changed")
    _git(workspace, "diff", "--check", context.repository_revision)

    total_bytes = 0
    artifact_limit = binding.resource_envelope.max_artifact_bytes
    for root, dirs, files in os.walk(workspace, followlinks=False):
        if any((Path(root) / item).is_symlink() for item in dirs):
            raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: workspace symlink found")
        for name in files:
            path = Path(root) / name
            if path.is_symlink():
                raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: workspace symlink found")
            size = path.stat().st_size
            if ".git" not in path.relative_to(workspace).parts and size > artifact_limit:
                raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: artifact size limit exceeded")
            total_bytes += size
            if total_bytes > binding.resource_envelope.max_workspace_bytes:
                raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: workspace size limit exceeded")

    tracked = _git(workspace, "diff", "--name-only", context.repository_revision).decode().splitlines()
    untracked = _git(workspace, "ls-files", "--others", "--exclude-standard").decode().splitlines()
    changed = tuple(sorted(set(tracked + untracked)))
    if len(changed) > 256:
        raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: too many changed files")
    if require_change and not changed:
        raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: no repository change observed")
    for relative in changed:
        candidate = PurePosixPath(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: unsafe changed path")
        if not any(
            relative == allowed or relative.startswith(allowed.rstrip("/") + "/")
            for allowed in member.write_scope
        ) or any(
            relative == forbidden or relative.startswith(forbidden.rstrip("/") + "/")
            for forbidden in member.forbidden_paths
        ):
            raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: changed file outside Task scope")
    if require_change:
        for relative in required_artifacts:
            candidate = PurePosixPath(relative)
            if candidate.is_absolute() or ".." in candidate.parts or not (workspace / relative).is_file():
                raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: required artifact missing")
    diff = _git(workspace, "diff", "--binary", context.repository_revision)
    if len(diff) > min(artifact_limit, 1048576):
        raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: diff evidence limit exceeded")
    artifacts = []
    for relative in changed:
        path = (workspace / relative).resolve()
        if workspace not in path.parents:
            raise ProductionWorkspaceVerificationFailed("VERIFICATION_FAILED: changed path escapes workspace")
        if path.is_file():
            artifacts.append({"path": relative, "sha256": sha256(path.read_bytes()).hexdigest(),
                              "size_bytes": path.stat().st_size})
    evidence = {
        "execution_id": str(binding.attempt_id),
        "workspace_id": str(binding.workspace.workspace_id),
        "repository_revision": context.repository_revision,
        "files_changed": list(changed),
        "workspace_bytes": total_bytes,
        "tracked_diff": diff.decode("utf-8", errors="replace"),
        "artifacts": artifacts,
    }
    digest, _path = storage.put_json(f"execution/{binding.attempt_id}", evidence)
    return {"workspace_id": str(binding.workspace.workspace_id),
            "repository_revision": context.repository_revision,
            "files_changed": list(changed), "workspace_bytes": total_bytes,
            "diff_reference": f"sha256:{digest}", "artifacts": artifacts}
