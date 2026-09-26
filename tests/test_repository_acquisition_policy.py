"""REAL Git proof for governed single-branch repository acquisition."""

from datetime import UTC, datetime
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from spg.application.production_environment_contracts import workspace_reality_v1_payload
from spg.domain.production_environment import (
    EnvironmentConfiguration,
    EnvironmentLifecycleState,
    EnvironmentRuntimeState,
    ProductionEnvironmentV1,
    ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1,
    RepositoryAssetBinding,
    RuntimeConfiguration,
)
from spg.infrastructure.production_environment import GitIsolatedWorkspacePreparer


pytestmark = pytest.mark.cross_repository


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


def commit(repository: Path, path: str, content: str, message: str) -> str:
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    git(repository, "add", path)
    git(
        repository,
        "-c",
        "user.name=Watt Acquisition Test",
        "-c",
        "user.email=watt-acquisition@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(repository, "rev-parse", "HEAD")


def repository_with_branches(root: Path, name: str = "source") -> tuple[Path, dict[str, str]]:
    repository = root / name
    repository.mkdir()
    git(repository, "init", "-b", "main")
    base = commit(repository, "history.txt", "base", "base")
    main = commit(repository, "history.txt", "main", "main")
    git(repository, "switch", "-c", "develop")
    develop = commit(repository, "branch.txt", "develop", "develop")
    git(repository, "switch", "main")
    git(repository, "switch", "-c", "feature/unrelated")
    feature = commit(repository, "branch.txt", "feature", "feature")
    git(repository, "switch", "main")
    return repository, {
        "base": base,
        "main": main,
        "develop": develop,
        "feature/unrelated": feature,
    }


def ecf_runtime(root: Path):
    workspace_root = Path(__file__).resolve().parents[2]
    ecf_src = workspace_root / "engineering-context-fabric" / "src"
    if not ecf_src.is_dir():
        pytest.skip("sibling ECF repository is unavailable")
    if str(ecf_src) not in sys.path:
        sys.path.insert(0, str(ecf_src))
    from ecf.runtime import ECFRealityRuntime, JsonRealityStore

    return ECFRealityRuntime(JsonRealityStore(root))


def workspace_from_realities(*realities) -> ProductionWorkspaceV1:
    return ProductionWorkspaceV1(
        id=uuid4(),
        work_id=uuid4(),
        repository_assets=tuple(
            RepositoryAssetBinding(
                asset_id=uuid4(),
                repository_identity=reality.repository_identity,
                source=(Path("/") / reality.source.removeprefix("file:///")).as_posix()
                if reality.source.startswith("file:///")
                else reality.source,
                branch=reality.selected_branch,
                default_branch=reality.default_branch,
                requested_branch=reality.requested_branch,
                source_revision=reality.selected_revision,
                source_tree_identity=reality.tree_identity,
                acquisition_policy=RepositoryAcquisitionPolicyV1.model_validate(
                    reality.acquisition_policy.model_dump(mode="python")
                ),
                mount_path=f"/workspace/{reality.repository_identity.split(':')[-1]}",
                writable=True,
                provenance_reference=f"ecf:repository-reality:{reality.reality_id}",
            )
            for reality in realities
        ),
        environment_configuration=EnvironmentConfiguration(
            provider_profile="container-v1"
        ),
        runtime_configuration=RuntimeConfiguration(runtime_profile="test-v1"),
        created_at=datetime.now(UTC),
    )


def remote_branches(repository: Path) -> set[str]:
    return {
        item
        for item in git(
            repository,
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/remotes/origin",
        ).splitlines()
        if item and item != "origin/HEAD"
    }


def test_default_repository_reality_acquires_only_default_branch(tmp_path):
    source, revisions = repository_with_branches(tmp_path)
    reality = ecf_runtime(tmp_path / "ecf").discover_repository(
        source,
        repository_identity="repo:default",
    )
    workspace = workspace_from_realities(reality)

    prepared = GitIsolatedWorkspacePreparer(tmp_path / "workspaces").prepare(workspace)
    acquired = prepared.repository_mounts[0].host_path

    assert reality.default_branch == "main"
    assert reality.selected_branch == "main"
    assert reality.selected_revision == revisions["main"]
    assert git(acquired, "rev-parse", "HEAD") == revisions["main"]
    assert remote_branches(acquired) == {"origin/main"}
    assert git(acquired, "rev-parse", "--is-shallow-repository") == "false"


def test_human_requested_branch_is_exact_and_preserves_full_history(tmp_path):
    source, revisions = repository_with_branches(tmp_path)
    reality = ecf_runtime(tmp_path / "ecf").discover_repository(
        source,
        repository_identity="repo:requested",
        requested_branch="develop",
    )
    workspace = workspace_from_realities(reality)

    prepared = GitIsolatedWorkspacePreparer(tmp_path / "workspaces").prepare(workspace)
    acquired = prepared.repository_mounts[0].host_path
    parent = git(source, "rev-parse", f"{revisions['develop']}^")

    assert reality.requested_branch == "develop"
    assert reality.selected_revision == revisions["develop"]
    assert git(acquired, "rev-parse", "HEAD") == revisions["develop"]
    assert remote_branches(acquired) == {"origin/develop"}
    assert git(acquired, "cat-file", "-t", parent) == "commit"
    git(acquired, "merge-base", "--is-ancestor", parent, revisions["develop"])


def test_acquired_revision_and_tree_match_ecf_repository_reality(tmp_path):
    source, _ = repository_with_branches(tmp_path)
    runtime = ecf_runtime(tmp_path / "ecf")
    reality = runtime.discover_repository(
        source,
        repository_identity="repo:reality-bound",
        requested_branch="develop",
    )
    workspace = workspace_from_realities(reality)
    prepared = GitIsolatedWorkspacePreparer(tmp_path / "workspaces").prepare(workspace)
    acquired = prepared.repository_mounts[0].host_path

    assert workspace.repository_assets[0].provenance_reference.endswith(
        str(reality.reality_id)
    )
    assert git(acquired, "rev-parse", "HEAD^{commit}") == reality.selected_revision
    assert git(acquired, "rev-parse", "HEAD^{tree}") == reality.tree_identity


def test_multi_repository_workspace_keeps_independent_reality_and_acquisition(tmp_path):
    frontend, frontend_revisions = repository_with_branches(tmp_path, "frontend-source")
    backend, backend_revisions = repository_with_branches(tmp_path, "backend-source")
    runtime = ecf_runtime(tmp_path / "ecf")
    frontend_reality = runtime.discover_repository(
        frontend,
        repository_identity="repo:frontend",
        requested_branch="develop",
    )
    backend_reality = runtime.discover_repository(
        backend,
        repository_identity="repo:backend",
    )
    workspace = workspace_from_realities(frontend_reality, backend_reality)
    prepared = GitIsolatedWorkspacePreparer(tmp_path / "workspaces").prepare(workspace)
    environment = ProductionEnvironmentV1(
        id=uuid4(),
        work_id=workspace.work_id,
        workspace_id=workspace.id,
        lifecycle_state=EnvironmentLifecycleState.CREATED,
        runtime_state=EnvironmentRuntimeState.NOT_PROVISIONED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    references = {
        item.repository_identity: item.provenance_reference
        for item in workspace.repository_assets
    }
    admitted = runtime.admit_workspace_payload(
        workspace_reality_v1_payload(
            workspace,
            environment,
            reality_id=uuid4(),
            repository_reality_references=references,
            observed_at=datetime.now(UTC),
            source_reference=f"workspace:{workspace.id}",
            observed_by="watt:repository-acquisition-test",
        )
    )
    acquired = {
        item.repository_identity: item.host_path
        for item in prepared.repository_mounts
    }

    assert git(acquired["repo:frontend"], "rev-parse", "HEAD") == frontend_revisions[
        "develop"
    ]
    assert remote_branches(acquired["repo:frontend"]) == {"origin/develop"}
    assert git(acquired["repo:backend"], "rev-parse", "HEAD") == backend_revisions[
        "main"
    ]
    assert remote_branches(acquired["repo:backend"]) == {"origin/main"}
    assert {
        item["repository_identity"] for item in admitted["repository_bindings"]
    } == {"repo:frontend", "repo:backend"}
