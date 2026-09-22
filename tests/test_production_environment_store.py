from datetime import UTC, datetime
from uuid import uuid4

from spg.application.production_environment import ProductionEnvironmentLifecycle
from spg.domain.production_environment import (
    EnvironmentConfiguration,
    EnvironmentLifecycleState,
    EnvironmentRuntimeState,
    LifecycleDecisionContext,
    ProductionEnvironmentV1,
    ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1,
    RepositoryAssetBinding,
    RepositoryBranchSelection,
    RuntimeConfiguration,
)
from spg.infrastructure.production_environment_store import (
    JsonProductionEnvironmentStore,
)


def records():
    now = datetime.now(UTC)
    work_id, workspace_id = uuid4(), uuid4()
    workspace = ProductionWorkspaceV1(
        id=workspace_id,
        work_id=work_id,
        repository_assets=(
            RepositoryAssetBinding(
                asset_id=uuid4(),
                repository_identity="repo:brownfield",
                source="file:///repository",
                branch="main",
                default_branch="main",
                source_revision="a" * 40,
                source_tree_identity="b" * 40,
                acquisition_policy=RepositoryAcquisitionPolicyV1(
                    branch_selection=RepositoryBranchSelection.REPOSITORY_DEFAULT,
                ),
                mount_path="/workspace/repository",
                writable=True,
                provenance_reference="repository-reality:1",
            ),
        ),
        environment_configuration=EnvironmentConfiguration(
            provider_profile="container-v1"
        ),
        runtime_configuration=RuntimeConfiguration(runtime_profile="preview-v1"),
        created_at=now,
    )
    environment = ProductionEnvironmentV1(
        id=uuid4(),
        work_id=work_id,
        workspace_id=workspace_id,
        lifecycle_state=EnvironmentLifecycleState.CREATED,
        runtime_state=EnvironmentRuntimeState.NOT_PROVISIONED,
        created_at=now,
        updated_at=now,
    )
    return workspace, environment


def test_environment_and_transition_survive_store_restart(tmp_path):
    store = JsonProductionEnvironmentStore(tmp_path)
    workspace, environment = records()
    store.create_workspace(workspace)
    store.create_environment(environment)
    initializing, transition = ProductionEnvironmentLifecycle().transition(
        environment,
        target=EnvironmentLifecycleState.INITIALIZING,
        context=LifecycleDecisionContext(work_state="RUNNING"),
        actor_reference="system:vertical-slice",
        reason="prepare isolated Workspace",
        decided_at=environment.created_at,
    )
    store.apply_transition(environment, initializing, transition)

    reloaded = JsonProductionEnvironmentStore(tmp_path)
    assert reloaded.get_workspace(workspace.id) == workspace
    assert reloaded.get_environment(environment.id) == initializing
    assert (tmp_path / "environments" / str(environment.id) / "versions" / "1.json").exists()
    assert (tmp_path / "environments" / str(environment.id) / "versions" / "2.json").exists()
