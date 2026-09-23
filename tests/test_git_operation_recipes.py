"""Bounded Git recipes cannot be widened into arbitrary shell or remote delivery."""

import pytest
import asyncio
from hashlib import sha256
from pathlib import Path
import subprocess
from uuid import uuid4

from spg.executor.git_operations import git_operation_commands, git_operation_is_read_only
from spg.domain.native_execution import (
    CapabilityGrant, EffectCondition, InferenceAction, InferenceRequest,
    NativeExecutionConflict, ToolCallProposal, WorkingPlan,
    ToolExecutionRequest, WorkspaceManifest, WorkspaceMount,
)
from spg.domain.production_environment import (
    EnvironmentCommandObservation, EnvironmentCommandResult, ProviderEnvironmentHandle,
)
from spg.infrastructure.executor_runtime.production_environment_tool_host import ProductionEnvironmentNativeToolHost
from spg.infrastructure.executor_runtime.git_inference import GovernedGitOperationInferenceAdapter


@pytest.mark.parametrize("operation", (
    "status", "branch.list", "branch.current", "diff", "log", "remote.inspect",
))
def test_git_read_recipes_are_fixed(operation: str) -> None:
    commands = git_operation_commands({"operation": operation})
    assert len(commands) == 1
    assert commands[0][0] == "git"
    assert git_operation_is_read_only(operation)


def test_git_branch_and_commit_recipes_have_bounded_inputs() -> None:
    branch = git_operation_commands({"operation": "branch.create", "branch": "test"})
    assert branch[0][-2:] == ("-c", "test")
    commit = git_operation_commands({
        "operation": "commit", "paths": ["src/app.py"], "message": "Implement feature",
    })
    assert len(commit) == 2
    assert commit[0][-2:] == ("--", "src/app.py")
    assert not git_operation_is_read_only("commit")


@pytest.mark.parametrize("arguments", (
    {"operation": "branch.create", "branch": "--force"},
    {"operation": "checkout", "branch": "../main"},
    {"operation": "tag", "tag": "v1", "revision": "HEAD"},
    {"operation": "commit", "paths": ["../outside"], "message": "unsafe"},
    {"operation": "push", "branch": "main"},
))
def test_git_recipe_rejects_widening(arguments: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        git_operation_commands(arguments)


def test_connector_resolved_native_git_operation_changes_isolated_workspace(tmp_path: Path) -> None:
    repository = tmp_path / "workspace"
    repository.mkdir()
    for command in (
        ("git", "init", "-b", "main"),
        ("git", "config", "user.name", "Watt Test"),
        ("git", "config", "user.email", "watt-test@example.invalid"),
    ):
        subprocess.run(command, cwd=repository, check=True, capture_output=True)
    (repository / "README.md").write_text("# Baseline\n", encoding="utf-8")
    subprocess.run(("git", "add", "README.md"), cwd=repository, check=True, capture_output=True)
    subprocess.run(("git", "commit", "-m", "baseline"), cwd=repository, check=True, capture_output=True)
    original = subprocess.run(("git", "rev-parse", "HEAD"), cwd=repository, check=True, capture_output=True, text=True).stdout.strip()

    class LocalProductionEnvironmentProvider:
        def execute_observed(self, _handle, command):
            assert command.working_directory == "/workspace/primary"
            completed = subprocess.run(command.argv, cwd=repository, capture_output=True, text=True)
            return EnvironmentCommandObservation(
                result=EnvironmentCommandResult(
                    command=command,
                    exit_code=completed.returncode,
                    stdout_reference=f"sha256:{sha256(completed.stdout.encode()).hexdigest()}",
                    stderr_reference=f"sha256:{sha256(completed.stderr.encode()).hexdigest()}",
                ),
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

    attempt_id = uuid4()
    manifest = WorkspaceManifest(
        workspace_id=uuid4(), work_id=uuid4(), pwu_id=uuid4(), attempt_id=attempt_id,
        source_vector_digest="0" * 64, host_storage_id=str(repository),
        environment_profile_digest="0" * 64,
        mounts=(WorkspaceMount(
            mount_id="primary", host_path=str(repository),
            container_path="/workspace/primary", writable=True,
            write_scope=(), forbidden_paths=(".git",),
        ),),
        evidence_namespace=f"git-operation:{attempt_id}", retention_policy="test",
    )
    host = ProductionEnvironmentNativeToolHost(
        provider=LocalProductionEnvironmentProvider(),
        handle=ProviderEnvironmentHandle(
            provider_identity="test:production-environment",
            environment_id=uuid4(), opaque_reference="test-environment",
        ),
        environment_reference="production-environment:test",
        workspace_reference="production-workspace:test",
        host_repository_path=repository,
    )
    request = ToolExecutionRequest(
        delivery_id=uuid4(), attempt_id=attempt_id, worker_epoch=1,
        step_id=uuid4(),
        proposal=ToolCallProposal(
            proposal_index=0, tool_identity="git.operation",
            arguments={"operation": "branch.create", "branch": "test"},
        ),
        capability_grants=(CapabilityGrant(
            identity="git.operation", version="1",
            scope={"capabilities": ["git.branch.create"]},
        ),),
        workspace=manifest,
    )
    unauthorized = request.model_copy(update={"capability_grants": ()})
    with pytest.raises(NativeExecutionConflict, match="not granted"):
        asyncio.run(host.registry().execute(unauthorized))
    result = asyncio.run(host.registry().execute(request))
    assert result.condition is EffectCondition.SETTLED
    assert result.output["resulting_branch"] == "test"
    assert result.output["resulting_revision"] == original
    assert len(result.evidence) == 3
    assert subprocess.run(("git", "branch", "--show-current"), cwd=repository, check=True, capture_output=True, text=True).stdout.strip() == "test"
    current = request.model_copy(update={
        "delivery_id": uuid4(),
        "proposal": ToolCallProposal(
            proposal_index=0, tool_identity="git.operation",
            arguments={"operation": "branch.current"},
        ),
        "capability_grants": (CapabilityGrant(
            identity="git.operation", version="1",
            scope={"capabilities": ["git.branch.current"]},
        ),),
    })
    current_result = asyncio.run(host.registry().execute(current))
    assert current_result.condition is EffectCondition.SETTLED
    assert current_result.output["stdout"].strip() == "test"

    def execute(operation: str, **arguments):
        selected = request.model_copy(update={
            "delivery_id": uuid4(),
            "proposal": ToolCallProposal(
                proposal_index=0, tool_identity="git.operation",
                arguments={"operation": operation, **arguments},
            ),
            "capability_grants": (CapabilityGrant(
                identity="git.operation", version="1",
                scope={"capabilities": [f"git.{operation}"]},
            ),),
        })
        return asyncio.run(host.registry().execute(selected))

    (repository / "feature.txt").write_text("feature\n", encoding="utf-8")
    committed = execute("commit", paths=["feature.txt"], message="Add feature")
    assert committed.condition is EffectCondition.SETTLED
    changed = committed.output["resulting_revision"]
    assert changed != original
    assert execute("ancestry", ancestor=original, descendant=changed).output["is_ancestor"] is True
    assert execute("ancestry", ancestor=changed, descendant=original).output["is_ancestor"] is False
    assert changed in execute("log").output["stdout"]
    assert execute("tag", tag="v1", revision=changed).condition is EffectCondition.SETTLED
    assert execute("checkout", branch="main").output["resulting_branch"] == "main"
    detached = execute("revision.checkout", revision=changed)
    assert detached.condition is EffectCondition.SETTLED
    assert detached.output["resulting_branch"] == ""
    assert detached.output["resulting_revision"] == changed
    assert execute("remote.inspect").condition is EffectCondition.SETTLED
    remote = tmp_path / "remote.git"
    subprocess.run(("git", "clone", "--bare", str(repository), str(remote)), check=True, capture_output=True)
    subprocess.run(("git", "--git-dir", str(remote), "update-ref", "refs/heads/newremote", original), check=True, capture_output=True)
    subprocess.run(("git", "remote", "add", "origin", str(remote)), cwd=repository, check=True, capture_output=True)
    fetched = execute("fetch", branch="newremote")
    assert fetched.condition is EffectCondition.SETTLED
    assert fetched.output["fetched_revision"] == original

    def filesystem(operation: str, *, permission: bool = False, **arguments):
        selected = request.model_copy(update={
            "delivery_id": uuid4(),
            "proposal": ToolCallProposal(
                proposal_index=0, tool_identity="filesystem.operation",
                arguments={"operation": operation, **arguments},
            ),
            "capability_grants": (CapabilityGrant(
                identity="filesystem.operation", version="1",
                scope={
                    "capabilities": [f"filesystem.{operation}"],
                    "permissions": ["work.filesystem.delete"] if permission else [],
                },
            ),),
        })
        return asyncio.run(host.registry().execute(selected))

    assert filesystem("search", path=".", query="Baseline").output["result"]["matches"] == ["README.md"]
    assert filesystem("stat", path="README.md").output["result"]["is_file"] is True
    assert filesystem("mkdir", path="docs").condition is EffectCondition.SETTLED
    assert filesystem("move", path="feature.txt", destination="docs/feature.txt").condition is EffectCondition.SETTLED
    with pytest.raises(NativeExecutionConflict, match="permission"):
        filesystem("delete", path="docs/feature.txt")
    assert filesystem("delete", path="docs/feature.txt", permission=True).condition is EffectCondition.SETTLED
    assert not (repository / "docs/feature.txt").exists()
    (repository / "README.md").write_text("# Changed\n", encoding="utf-8")
    assert filesystem("diff", path="README.md").condition is EffectCondition.SETTLED
    with pytest.raises(NativeExecutionConflict, match="workspace"):
        filesystem("move", path="README.md", destination="../escape")


def test_governed_git_inference_only_claims_observed_exact_result() -> None:
    adapter = GovernedGitOperationInferenceAdapter(
        operation="branch.create", arguments={"branch": "test"}, expected_revision="a" * 40,
    )
    request = InferenceRequest(
        attempt_id=uuid4(), session_id=uuid4(), step_sequence=1,
        objective="Create admitted branch test",
        working_plan=WorkingPlan(
            version=1, objective_reference="task-contract:test",
            chosen_approach="Execute one Git operation", approach_rationale="Human approved it",
        ),
        context_facts=(), available_tools=(), residual_obligations=(),
    )
    proposed = asyncio.run(adapter.infer(request))
    assert proposed.action is InferenceAction.CONTINUE
    assert proposed.tool_calls[0].arguments == {"operation": "branch.create", "branch": "test"}
    wrong = asyncio.run(adapter.infer(request.model_copy(update={
        "previous_results": ({
            "tool_identity": "git.operation", "condition": "SETTLED",
            "output": {"operation": "branch.create", "resulting_branch": "other", "resulting_revision": "a" * 40},
        },),
    })))
    assert wrong.action is InferenceAction.UNABLE_TO_COMPLETE
    correct = asyncio.run(adapter.infer(request.model_copy(update={
        "previous_results": ({
            "tool_identity": "git.operation", "condition": "SETTLED",
            "output": {"operation": "branch.create", "resulting_branch": "test", "resulting_revision": "a" * 40},
            "output_digest": "f" * 64,
        },),
    })))
    assert correct.action is InferenceAction.RESULT_READY
    assert correct.result_claim["branch"] == "test"
