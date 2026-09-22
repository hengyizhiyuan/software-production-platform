"""REAL_RUNTIME proof: existing Native Executor tools run through PE Provider."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import subprocess
from uuid import uuid4

import pytest

from spg.application.native_production_environment import NativeProductionEnvironmentRuntime
from spg.domain.native_execution import (
    AttemptTerminalOutcome,
    CapabilityGrant,
    CheckpointBundleRecord,
    CheckpointCondition,
    ExecutionBindingV2,
    InferenceAction,
    InferenceResponse,
    KernelCheckpoint,
    PWUContractVersionRecord,
    ResourceEnvelope,
    SourceMember,
    SourceVector,
    ToolCallProposal,
    WorkingPlan,
    WorkspaceManifest,
    WorkspaceMount,
    canonical_digest,
)
from spg.domain.preparation import ExecutorBinding, PreparedExecutionRequest
from spg.domain.production_environment import EnvironmentLifecycleState
from spg.executor.kernel import NativeExecutorKernel
from spg.infrastructure.executor_runtime.inference import ScriptedInferenceAdapter
from spg.infrastructure.executor_runtime.production_environment_tool_host import (
    ProductionEnvironmentNativeToolHost,
)
from spg.infrastructure.git_workspace import GitCloneAttemptWorkspace
from spg.infrastructure.production_environment import (
    ContainerProductionEnvironmentProvider,
    DockerCliContainerRuntime,
)
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


pytestmark = pytest.mark.real_container
IMAGE = "watt-engineering-semantic-human-retest-app:latest"


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class Checkpoints:
    def __init__(self) -> None:
        self.items = []

    async def commit(self, checkpoint: KernelCheckpoint) -> CheckpointBundleRecord:
        self.items.append(checkpoint)
        now = datetime.now(UTC)
        return CheckpointBundleRecord(
            id=uuid4(),
            session_id=uuid4(),
            attempt_id=uuid4(),
            step_sequence=checkpoint.step_sequence,
            worker_epoch=1,
            condition=CheckpointCondition.COMMITTED,
            source_vector_digest=checkpoint.source_vector_digest,
            repository_manifest={},
            execution_manifest={
                "tool_results": [item.model_dump(mode="json") for item in checkpoint.tool_results]
            },
            semantic_manifest={
                "working_plan": checkpoint.working_plan.model_dump(mode="json")
            },
            content_digest=canonical_digest(checkpoint),
            consistency_class="REAL_CONTAINER_TEST",
            created_at=now,
            committed_at=now,
        )


def plan(version: int) -> WorkingPlan:
    return WorkingPlan(
        version=version,
        objective_reference="task-contract:native-pe-test",
        chosen_approach="Use admitted Native tools in assigned Production Environment",
        approach_rationale="PWU owns HOW while Production Environment owns WHERE",
    )


def test_native_executor_runs_tools_through_real_production_environment(tmp_path):
    if subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        check=False,
        capture_output=True,
    ).returncode:
        pytest.skip(f"qualified local image is unavailable: {IMAGE}")

    repository = tmp_path / "source"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    (repository / "index.html").write_text("<h1>baseline</h1>", encoding="utf-8")
    git(repository, "add", "index.html")
    git(repository, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "baseline")
    parent_revision = git(repository, "rev-parse", "HEAD")
    (repository / "history.txt").write_text("second commit", encoding="utf-8")
    git(repository, "add", "history.txt")
    git(repository, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "history")
    revision = git(repository, "rev-parse", "HEAD")
    tree = git(repository, "rev-parse", "HEAD^{tree}")
    git(repository, "branch", "develop")
    git(repository, "branch", "feature/unrelated")
    work_id, pwu_id, attempt_id = uuid4(), uuid4(), uuid4()
    workspace = GitCloneAttemptWorkspace().prepare(
        repository_path=repository,
        workspace_root=tmp_path / "workspaces",
        attempt_id=attempt_id,
        repository_identity="repo:native-pe",
        source_revision=revision,
        repository_ref="refs/heads/main",
    )
    assert {
        branch
        for branch in git(
            workspace.workspace_path,
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/remotes/origin",
        ).splitlines()
        if branch != "origin/HEAD"
    } == {"origin/main"}
    assert git(workspace.workspace_path, "cat-file", "-t", parent_revision) == "commit"
    assert git(workspace.workspace_path, "rev-parse", "--is-shallow-repository") == "false"
    execution = PreparedExecutionRequest(
        attempt_id=attempt_id,
        generation=1,
        production_run_id=uuid4(),
        work_unit_id=pwu_id,
        plan_revision_id=uuid4(),
        source_baseline_id=uuid4(),
        context_package_id=uuid4(),
        context_package_version=1,
        completion_contract_fingerprint="a" * 64,
        executor_binding=ExecutorBinding(
            binding_ref="binding:watt-native-queue-v2",
            capability_identity="capability:watt-native-executor",
            profile_identity="local-container-v1",
        ),
        workspace=workspace,
    )
    store = JsonProductionEnvironmentStore(tmp_path / "production-environments")
    provider = ContainerProductionEnvironmentProvider(DockerCliContainerRuntime())
    environments = NativeProductionEnvironmentRuntime(
        store=store,
        provider=provider,
        image_reference=IMAGE,
    )
    environment_binding = environments.ensure(
        execution,
        work_id=work_id,
        task_contract_reference="task-contract:native-pe-test",
        selected_branch="main",
    )
    vector = SourceVector(
        members=(
            SourceMember(
                mount_id="primary",
                repository_identity="repo:native-pe",
                source_baseline_ref="refs/heads/main",
                source_commit_oid=revision,
                source_tree_oid=tree,
                container_path="/workspace/primary",
                write_scope=("index.html",),
                forbidden_paths=(".git",),
            ),
        )
    )
    manifest = WorkspaceManifest(
        workspace_id=uuid4(),
        work_id=work_id,
        pwu_id=pwu_id,
        attempt_id=attempt_id,
        source_vector_digest=vector.digest or "",
        host_storage_id=str(workspace.workspace_path),
        environment_profile_digest=canonical_digest({"profile": "local-container-v1"}),
        mounts=(
            WorkspaceMount(
                mount_id="primary",
                host_path=str(workspace.workspace_path),
                container_path="/workspace/primary",
                writable=True,
                write_scope=("index.html",),
                forbidden_paths=(".git",),
            ),
        ),
        service_resources=environments.service_resources(environment_binding),
        evidence_namespace=f"native:{attempt_id}",
        retention_policy="test",
    )
    payload = {"objective": "modify the existing page", "task_contract": "native-pe-test"}
    contract = PWUContractVersionRecord(
        id=uuid4(),
        pwu_id=pwu_id,
        revision=1,
        objective="modify the existing page",
        contract_payload=payload,
        contract_digest=canonical_digest(payload),
        created_at=datetime.now(UTC),
    )
    binding = ExecutionBindingV2(
        work_id=work_id,
        steering_decision_id=execution.plan_revision_id,
        pwu_id=pwu_id,
        pwu_contract_version_id=contract.id,
        pwu_contract_digest=contract.contract_digest,
        attempt_id=attempt_id,
        generation=1,
        session_id=uuid4(),
        source_vector=vector,
        workspace=manifest,
        context_package_ref=f"context-package:{execution.context_package_id}",
        materialized_input_digest=canonical_digest(execution),
        backend_implementation="watt-native",
        backend_version="2",
        inference_profile="scripted-real-container",
        capability_grants=(
            CapabilityGrant(identity="file.write", version="1", scope={"paths": ["index.html"]}),
            CapabilityGrant(identity="git.status", version="1", scope={}),
        ),
        resource_envelope=ResourceEnvelope(
            envelope_id=uuid4(),
            policy_version="test",
            max_inference_submissions=3,
            max_tool_effects=3,
            max_active_seconds=120,
            provider_profile="scripted-real-container",
        ),
        obligation_references=("task-contract:native-pe-test",),
    )
    inference = ScriptedInferenceAdapter(
        (
            InferenceResponse(
                action=InferenceAction.CONTINUE,
                summary="implement admitted page change",
                working_plan=plan(2),
                tool_calls=(
                    ToolCallProposal(
                        proposal_index=0,
                        tool_identity="file.write",
                        arguments={
                            "path": "index.html",
                            "content": "<h1>Native Executor via Production Environment</h1>",
                        },
                    ),
                ),
                residual_obligations=("observe repository change",),
            ),
            InferenceResponse(
                action=InferenceAction.CONTINUE,
                summary="collect repository evidence",
                working_plan=plan(3),
                tool_calls=(
                    ToolCallProposal(
                        proposal_index=0,
                        tool_identity="git.status",
                        arguments={"cwd": "."},
                    ),
                ),
                residual_obligations=(),
            ),
            InferenceResponse(
                action=InferenceAction.RESULT_READY,
                summary="bounded change and evidence are ready",
                working_plan=plan(4),
                result_claim={"output_vector": {"files": ["index.html"]}},
                residual_obligations=(),
            ),
        )
    )
    checkpoints = Checkpoints()
    tools = ProductionEnvironmentNativeToolHost.from_manifest(
        manifest,
        provider=provider,
    )
    assert tools is not None
    result = asyncio.run(
        NativeExecutorKernel(
            inference=inference,
            tools=tools.registry(),
            checkpoints=checkpoints,
        ).run(
            binding=binding,
            contract=contract,
            worker_epoch=1,
            working_plan=plan(1),
        )
    )

    assert result.terminal_outcome is AttemptTerminalOutcome.RESULT_READY
    assert "Production Environment" in (workspace.workspace_path / "index.html").read_text(encoding="utf-8")
    receipts = [item for checkpoint in checkpoints.items for item in checkpoint.tool_results]
    assert any(
        evidence.get("environment_reference")
        == f"production-environment:{environment_binding.environment.id}"
        for receipt in receipts
        for evidence in receipt.evidence
    )
    suspended = environments.suspend(
        attempt_id,
        artifact_references=("artifact:index.html",),
        evidence_references=(f"native-attempt:{attempt_id}",),
    )
    assert suspended.lifecycle_state is EnvironmentLifecycleState.SUSPENDED
