"""REAL_RUNTIME qualification for the first Brownfield delivery slice."""

from datetime import UTC, datetime
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen
from uuid import UUID, uuid4

import pytest

from spg.application.brownfield_delivery import BrownfieldFeatureDeliveryService
from spg.domain.brownfield_delivery import BrownfieldFeatureDeliveryRequest
from spg.domain.production_environment import (
    EnvironmentCommand,
    EnvironmentLifecycleState,
    HumanDeliveryAction,
    HumanDeliveryDecision,
    ProductionDeliveryState,
)
from spg.infrastructure.production_environment import (
    ContainerProductionEnvironmentProvider,
    DockerCliContainerRuntime,
    GitIsolatedWorkspacePreparer,
    StaticPreviewRuntime,
)
from spg.infrastructure.production_environment_store import JsonProductionEnvironmentStore


pytestmark = [pytest.mark.cross_repository, pytest.mark.real_container]
IMAGE = "watt-engineering-semantic-human-retest-app:latest"


def run(*arguments: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(arguments),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def load_runtime_owners():
    workspace_root = Path(__file__).resolve().parents[2]
    ecf_src = workspace_root / "engineering-context-fabric" / "src"
    guardian_src = workspace_root / "guardian" / "src"
    if not ecf_src.is_dir() or not guardian_src.is_dir():
        pytest.skip("sibling ECF and Guardian repositories are unavailable")
    sys.path[:0] = [str(ecf_src), str(guardian_src)]
    from ecf.runtime import ECFRealityRuntime, JsonRealityStore
    from guardian.runtime import JsonAssuranceIntakeStore

    return ECFRealityRuntime, JsonRealityStore, JsonAssuranceIntakeStore


def test_real_repository_container_preview_delivery_and_reality_refresh(tmp_path):
    if subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        check=False,
        capture_output=True,
    ).returncode:
        pytest.skip(f"qualified local image is unavailable: {IMAGE}")
    ECFRealityRuntime, JsonRealityStore, JsonAssuranceIntakeStore = load_runtime_owners()

    source = tmp_path / "source"
    source.mkdir()
    run("git", "init", "-b", "main", cwd=source)
    (source / "index.html").write_text(
        "<!doctype html><h1>Brownfield baseline</h1>", encoding="utf-8"
    )
    run("git", "add", "index.html", cwd=source)
    run(
        "git",
        "-c",
        "user.name=Test Human",
        "-c",
        "user.email=human@example.test",
        "commit",
        "-m",
        "baseline",
        cwd=source,
    )
    source_revision = run("git", "rev-parse", "HEAD", cwd=source)

    ecf_store = JsonRealityStore(tmp_path / "ecf")
    guardian_store = JsonAssuranceIntakeStore(tmp_path / "guardian")
    preview = StaticPreviewRuntime()
    service = BrownfieldFeatureDeliveryService(
        store=JsonProductionEnvironmentStore(tmp_path / "watt"),
        reality=ECFRealityRuntime(ecf_store),
        guardian=guardian_store,
        workspace_preparer=GitIsolatedWorkspacePreparer(tmp_path / "workspaces"),
        provider=ContainerProductionEnvironmentProvider(DockerCliContainerRuntime()),
        preview_runtime=preview,
        work_exists=lambda _work_id: True,
    )
    work_id = uuid4()
    python_change = (
        "from pathlib import Path; "
        "Path('index.html').write_text("
        "'<!doctype html><h1>Brownfield feature delivered</h1>', encoding='utf-8')"
    )
    request = BrownfieldFeatureDeliveryRequest(
        work_id=work_id,
        task_contract_reference="task-contract:brownfield-feature:1",
        repository_identity="repo:brownfield-real-runtime",
        repository_source=source,
        target_branch="watt/brownfield-feature",
        container_image=IMAGE,
        implementation_commands=(
            EnvironmentCommand(
                argv=("python", "-c", python_change),
                working_directory="/workspace/repository",
            ),
        ),
        verification_commands=(
            EnvironmentCommand(
                argv=(
                    "python",
                    "-c",
                    "from pathlib import Path; assert 'feature delivered' in Path('index.html').read_text(encoding='utf-8')",
                ),
                working_directory="/workspace/repository",
            ),
        ),
        artifact_paths=("/workspace/repository/index.html",),
        preview_entrypoint="index.html",
        commit_message="feat: deliver brownfield feature",
        commit_author_name="Watt Production Executor",
        commit_author_email="watt@example.test",
    )

    session = service.prepare_for_human_review(request)
    repository_asset = session.workspace.repository_assets[0]
    acquired_repository = session.prepared_workspace.repository_mounts[0].host_path
    assert repository_asset.default_branch == "main"
    assert repository_asset.requested_branch is None
    assert repository_asset.branch == "main"
    assert repository_asset.source_revision == source_revision
    assert repository_asset.acquisition_policy.ref_scope == "SINGLE_BRANCH"
    assert repository_asset.acquisition_policy.history == "FULL_HISTORY"
    assert {
        branch
        for branch in run(
            "git",
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/remotes/origin",
            cwd=acquired_repository,
        ).splitlines()
        if branch != "origin/HEAD"
    } == {"origin/main"}
    assert session.environment.lifecycle_state is EnvironmentLifecycleState.ACTIVE
    assert session.delivery_intent.state is ProductionDeliveryState.READY_FOR_HUMAN_ACCEPTANCE
    assert urlopen(session.preview.endpoint, timeout=5).read().decode("utf-8").endswith(
        "<h1>Brownfield feature delivered</h1>"
    )
    assert run("git", "rev-parse", "HEAD", cwd=source) == source_revision
    assert run("git", "branch", "--list", "watt/brownfield-feature", cwd=source) == ""

    accepted = service.accept_candidate(
        session.id,
        HumanDeliveryDecision(
            id=uuid4(),
            delivery_intent_id=session.delivery_intent.id,
            action=HumanDeliveryAction.ACCEPT,
            authority_identity="human:test-reviewer",
            rationale="automated fixture simulates an explicit Human review boundary",
            decided_at=datetime.now(UTC),
        ),
    )
    assert accepted.state is ProductionDeliveryState.ACCEPTED
    completion = service.authorize_delivery(
        session.id,
        HumanDeliveryDecision(
            id=uuid4(),
            delivery_intent_id=session.delivery_intent.id,
            action=HumanDeliveryAction.AUTHORIZE_DELIVERY,
            authority_identity="human:test-delivery-authorizer",
            rationale="automated fixture simulates a separate explicit authorization",
            decided_at=datetime.now(UTC),
        ),
    )

    assert completion.delivery_intent.state is ProductionDeliveryState.AUTHORIZED_FOR_DELIVERY
    assert completion.production_record.repository_revisions[0].before_revision == source_revision
    assert completion.production_record.repository_revisions[0].after_revision == session.candidate_revision
    assert completion.environment.lifecycle_state is EnvironmentLifecycleState.SUSPENDED
    assert ecf_store.latest("repository", request.repository_identity).revision == session.candidate_revision
    assert ecf_store.latest("change", f"work:{work_id}").changed_assets[0].path == "index.html"
    assert guardian_store.get(
        UUID(completion.guardian_intake_reference.rsplit(":", 1)[-1])
    ) is not None
    archived = service.archive_environment(session.id)
    assert archived.lifecycle_state is EnvironmentLifecycleState.ARCHIVED
    assert run("git", "rev-parse", "HEAD", cwd=source) == source_revision
