"""C2: exact host-path diagnostics retain the original preflight gates."""

import errno
import os
import stat
from pathlib import Path

import pytest

from spg.domain.native_execution import SourceVector
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.production_evidence import (
    ProductionWorkspaceVerificationFailed, observe_production_workspace,
)
from tests.test_production_execution_runtime import _binding, _git


def test_exact_host_workspace_observation_is_durable_and_mount_scoped(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    storage = ContentAddressedStorage(tmp_path / "evidence")
    result = observe_production_workspace(binding, storage, require_change=False)
    diagnostic = result["workspace_diagnosis"]
    assert diagnostic["check"] == "WORKSPACE_OBSERVED"
    assert diagnostic["host_path"] == str(workspace)
    assert diagnostic["resolved_path"] == str(workspace.resolve())
    # The executor's container alias is recorded, never substituted for the
    # exact host path read in the Worker's own mount namespace.
    assert diagnostic["container_path"] == "/workspace/primary"
    assert diagnostic["mount_id"] == "primary"
    assert diagnostic["stat_kind"] == "DIRECTORY"
    assert diagnostic["stat_errno"] is None
    assert diagnostic["workspace_write_access"] is True
    assert diagnostic["expected_tree"] == diagnostic["observed_tree"]
    assert diagnostic["expected_revision"] == diagnostic["observed_revision"]
    assert diagnostic["source_vector_digest"] == binding.source_vector.digest
    assert diagnostic["attempt_id"] == str(binding.attempt_id)
    assert diagnostic["checked_at"]
    assert diagnostic["hostname"]
    assert "repository_identity" not in diagnostic
    assert not {"environment", "stderr", "stdout", "contents"}.intersection(diagnostic)
    saved = storage.get_json(f"execution/{binding.attempt_id}",
                             result["diff_reference"].removeprefix("sha256:"))
    assert saved["workspace_diagnosis"] == diagnostic


@pytest.mark.parametrize("replacement", ["missing", "file"])
def test_unavailable_workspace_identifies_the_exact_directory_predicate(
    tmp_path: Path, replacement: str,
) -> None:
    binding, workspace = _binding(tmp_path)
    workspace.rename(tmp_path / "retained-original")
    if replacement == "file":
        workspace.write_text("not a directory")
    with pytest.raises(ProductionWorkspaceVerificationFailed,
                       match="workspace unavailable") as failure:
        observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                     require_change=False)
    diagnostic = failure.value.diagnosis
    assert diagnostic["check"] == "WORKSPACE_DIRECTORY"
    assert diagnostic["host_path"] == str(workspace)
    assert diagnostic["availability_wait_ms"] >= 1900
    assert diagnostic["stat_kind"] == ("UNAVAILABLE" if replacement == "missing" else "OTHER")
    assert diagnostic["stat_errno"] == (errno.ENOENT if replacement == "missing" else None)
    assert not list((tmp_path / "evidence").rglob("*.json"))
    assert workspace.is_file() if replacement == "file" else not workspace.exists()


def test_root_symlink_rejection_does_not_acquire_another_workspace(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    retained = tmp_path / "retained-original"
    workspace.rename(retained)
    workspace.symlink_to(retained, target_is_directory=True)
    with pytest.raises(ProductionWorkspaceVerificationFailed,
                       match="workspace unavailable") as failure:
        observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                     require_change=False)
    diagnostic = failure.value.diagnosis
    assert diagnostic["check"] == "WORKSPACE_NOT_SYMLINK"
    assert diagnostic["stat_kind"] == "SYMLINK"
    assert diagnostic["availability_wait_ms"] == 0
    assert "observed_revision" not in diagnostic
    assert workspace.is_symlink()


def test_nested_symlink_remains_rejected(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    (workspace / "about.html").symlink_to(tmp_path / "outside.html")
    with pytest.raises(ProductionWorkspaceVerificationFailed,
                       match="workspace symlink found") as failure:
        observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                     require_change=False)
    assert failure.value.diagnosis["check"] == "NO_WORKSPACE_SYMLINKS"
    assert failure.value.diagnosis["failed_relative_path"] == "about.html"
    assert failure.value.diagnosis["checked_path"] == str(workspace / "about.html")
    assert failure.value.diagnosis["checked_stat_kind"] == "SYMLINK"


def test_out_of_scope_change_is_rejected_before_effects(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    (workspace / "outside.html").write_text("outside admitted Task write scope")
    with pytest.raises(ProductionWorkspaceVerificationFailed,
                       match="outside Task scope") as failure:
        observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                     require_change=False)
    assert failure.value.diagnosis["check"] == "TASK_WRITE_SCOPE"
    assert failure.value.diagnosis["failed_relative_path"] == "outside.html"
    assert failure.value.diagnosis["checked_path"] == str(workspace / "outside.html")
    assert failure.value.diagnosis["checked_stat_kind"] == "OTHER"
    assert not list((tmp_path / "evidence").rglob("*.json"))


def test_changed_head_rejects_exact_source_revision_and_retains_both_identities(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    _git(workspace, "-c", "user.name=Runtime Test", "-c", "user.email=runtime@example.invalid",
         "commit", "--allow-empty", "-m", "other source revision")
    observed_revision = _git(workspace, "rev-parse", "HEAD")
    with pytest.raises(ProductionWorkspaceVerificationFailed,
                       match="repository basis changed") as failure:
        observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                     require_change=False)
    diagnostic = failure.value.diagnosis
    assert diagnostic["check"] == "EXACT_SOURCE_REVISION"
    assert diagnostic["expected_revision"] == binding.production_context.repository_revision
    assert diagnostic["observed_revision"] == observed_revision
    assert observed_revision != diagnostic["expected_revision"]
    assert not list((tmp_path / "evidence").rglob("*.json"))


def test_preflight_rejects_nonwritable_directory_for_actual_nonroot_worker(tmp_path: Path) -> None:
    assert hasattr(os, "geteuid") and os.geteuid() != 0, (
        "C2 permission qualification must run under a real nonroot Worker UID")
    binding, workspace = _binding(tmp_path)
    original_mode = stat.S_IMODE(workspace.stat().st_mode)
    workspace.chmod(0o500)  # New isolated fixture only; never an actual Work.
    try:
        with pytest.raises(ProductionWorkspaceVerificationFailed,
                           match="workspace is not writable") as failure:
            observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                         require_change=False)
        diagnostic = failure.value.diagnosis
        assert diagnostic["check"] == "WORKSPACE_WRITE_ACCESS"
        assert diagnostic["workspace_write_access"] is False
        assert diagnostic["uid"] == os.getuid()
        assert diagnostic["stat_kind"] == "DIRECTORY"
        assert diagnostic["checked_path"] == str(workspace)
        assert diagnostic["checked_stat_mode"] == workspace.lstat().st_mode
        assert "observed_revision" not in diagnostic
    finally:
        workspace.chmod(original_mode)


def test_declared_source_tree_must_match_exact_git_head_tree(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    original_tree = _git(workspace, "rev-parse", "HEAD^{tree}")
    declared_tree = "f" * len(original_tree)
    assert declared_tree != original_tree
    vector = SourceVector(members=(binding.source_vector.members[0].model_copy(
        update={"source_tree_oid": declared_tree}),))
    binding = binding.model_copy(update={
        "source_vector": vector,
        "workspace": binding.workspace.model_copy(update={"source_vector_digest": vector.digest}),
    })
    with pytest.raises(ProductionWorkspaceVerificationFailed,
                       match="repository basis changed") as failure:
        observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                     require_change=False)
    diagnostic = failure.value.diagnosis
    assert diagnostic["check"] == "EXACT_SOURCE_TREE"
    assert diagnostic["expected_revision"] == diagnostic["observed_revision"]
    assert diagnostic["expected_tree"] == declared_tree
    assert diagnostic["observed_tree"] == original_tree


def test_missing_required_artifact_diagnosis_names_actual_check_target(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    (workspace / "about.html").write_text("legal fixture change")
    with pytest.raises(ProductionWorkspaceVerificationFailed,
                       match="required artifact missing") as failure:
        observe_production_workspace(binding, ContentAddressedStorage(tmp_path / "evidence"),
                                     require_change=True, required_artifacts=("missing.html",))
    diagnostic = failure.value.diagnosis
    assert diagnostic["check"] == "REQUIRED_ARTIFACT"
    assert diagnostic["failed_relative_path"] == "missing.html"
    assert diagnostic["checked_path"] == str(workspace / "missing.html")
    assert diagnostic["checked_stat_kind"] == "UNAVAILABLE"
    assert diagnostic["checked_stat_errno"] == errno.ENOENT
