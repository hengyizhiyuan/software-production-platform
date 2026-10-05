from pathlib import Path
import subprocess
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.domain.native_execution import (
    CapabilityGrant, ExecutionBindingV2, ProductionExecutionContext,
    ResourceEnvelope, SourceMember, SourceVector, WorkspaceManifest,
    WorkspaceMount,
)
from spg.infrastructure.executor_runtime.local_storage import ContentAddressedStorage
from spg.infrastructure.executor_runtime.production_evidence import (
    ProductionWorkspaceVerificationFailed, observe_production_workspace,
)


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(path), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _binding(tmp_path: Path, *, max_artifact_bytes: int = 4096) -> tuple[ExecutionBindingV2, Path]:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.name", "Runtime Test")
    _git(source, "config", "user.email", "runtime@example.invalid")
    (source / "index.html").write_text("<h1>Home</h1>\n")
    _git(source, "add", "index.html")
    _git(source, "commit", "-m", "baseline")
    revision = _git(source, "rev-parse", "HEAD")
    workspace = tmp_path / "workspace"
    subprocess.run(["git", "clone", str(source), str(workspace)], check=True,
                   capture_output=True)
    _git(workspace, "checkout", "--detach", revision)
    work_id, pwu_id, attempt_id, workspace_id = (uuid4() for _ in range(4))
    vector = SourceVector(members=(SourceMember(
        mount_id="primary", repository_identity=str(source),
        source_baseline_ref="refs/heads/main", source_commit_oid=revision,
        source_tree_oid=_git(source, "rev-parse", "HEAD^{tree}"),
        container_path="/workspace/primary", read_scope=("index.html",),
        write_scope=("index.html", "about.html"), forbidden_paths=(".git",),
    ),))
    manifest = WorkspaceManifest(
        workspace_id=workspace_id, work_id=work_id, pwu_id=pwu_id,
        attempt_id=attempt_id, source_vector_digest=vector.digest or "",
        host_storage_id=str(workspace), environment_profile_digest="b" * 64,
        mounts=(WorkspaceMount(mount_id="primary", host_path=str(workspace),
                               container_path="/workspace/primary", writable=True,
                               write_scope=("index.html", "about.html"),
                               forbidden_paths=(".git",)),),
        evidence_namespace="test", retention_policy="test",
    )
    context = ProductionExecutionContext(
        work_id=work_id, task_contract_id=uuid4(),
        ecf_context_fingerprint="a" * 64, irk_semantic_ir_id=uuid4(),
        repository_identity=str(source), repository_revision=revision,
        workspace_id=workspace_id,
        verification_requirements=("repository consistency", "artifact exists"),
        work_reality_revision_id=uuid4(),
    )
    binding = ExecutionBindingV2(
        work_id=work_id, steering_decision_id=uuid4(), pwu_id=pwu_id,
        pwu_contract_version_id=uuid4(), pwu_contract_digest="c" * 64,
        attempt_id=attempt_id, generation=1, session_id=uuid4(),
        source_vector=vector, workspace=manifest,
        context_package_ref="context:test", materialized_input_digest="d" * 64,
        backend_implementation="watt-native", backend_version="1",
        inference_profile="scripted", capability_grants=(CapabilityGrant(
            identity="file.write", version="1", scope={"paths": ["about.html"]}),),
        resource_envelope=ResourceEnvelope(
            envelope_id=uuid4(), policy_version="test", provider_profile="scripted",
            max_artifact_bytes=max_artifact_bytes, max_workspace_bytes=1048576,
        ),
        production_context=context,
    )
    return binding, workspace


def test_production_context_rejects_wrong_work_and_workspace(tmp_path: Path) -> None:
    binding, _workspace = _binding(tmp_path)
    payload = binding.model_dump(mode="python")
    payload["production_context"]["work_id"] = uuid4()
    with pytest.raises(ValidationError, match="Work/Workspace differs"):
        ExecutionBindingV2.model_validate(payload)


def test_workspace_result_records_bounded_change_and_diff(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path)
    store = ContentAddressedStorage(tmp_path / "evidence")
    with pytest.raises(ProductionWorkspaceVerificationFailed, match="no repository change"):
        observe_production_workspace(binding, store, require_change=True)
    (workspace / "about.html").write_text("<h1>About</h1>\n")
    observed = observe_production_workspace(
        binding, store, require_change=True, required_artifacts=("about.html",)
    )
    assert observed["files_changed"] == ["about.html"]
    assert observed["diff_reference"].startswith("sha256:")
    digest = observed["diff_reference"].removeprefix("sha256:")
    saved = store.get_json(f"execution/{binding.attempt_id}", digest)
    assert saved["artifacts"][0]["path"] == "about.html"
    assert saved["repository_revision"] == binding.production_context.repository_revision


def test_workspace_verification_rejects_missing_artifact_scope_and_size(tmp_path: Path) -> None:
    binding, workspace = _binding(tmp_path, max_artifact_bytes=1024)
    store = ContentAddressedStorage(tmp_path / "evidence")
    (workspace / "about.html").write_text("<h1>About</h1>\n")
    with pytest.raises(ProductionWorkspaceVerificationFailed, match="required artifact missing"):
        observe_production_workspace(binding, store, require_change=True,
                                     required_artifacts=("missing.html",))
    (workspace / "outside.html").write_text("outside\n")
    with pytest.raises(ProductionWorkspaceVerificationFailed, match="outside Task scope"):
        observe_production_workspace(binding, store, require_change=True)
    (workspace / "outside.html").unlink()
    (workspace / "about.html").write_text("x" * 2048)
    with pytest.raises(ProductionWorkspaceVerificationFailed, match="artifact size limit"):
        observe_production_workspace(binding, store, require_change=True)
