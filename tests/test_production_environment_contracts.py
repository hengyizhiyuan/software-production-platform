from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from spg.domain.production_environment import (
    DeliveryResultReference,
    EnvironmentConfiguration,
    EnvironmentLifecycleState,
    EnvironmentRuntimeState,
    PreviewRuntimeStatus,
    PreviewRuntimeV1,
    ProductionChangeReference,
    ProductionChangeType,
    ProductionDeliveryState,
    ProductionEnvironmentV1,
    ProductionRecordV1,
    ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1,
    RepositoryAssetBinding,
    RepositoryBranchSelection,
    RepositoryRevisionReference,
    ResourceKind,
    ResourceReferenceV1,
    ReferenceRelationship,
    RuntimeConfiguration,
    VerificationOutcome,
    VerificationResultReference,
)
from spg.application.production_environment import (
    preview_runtime_from_observation,
    production_resource_references,
)


def repository_binding(identity="repo:frontend", mount="/workspace/frontend"):
    return RepositoryAssetBinding(
        asset_id=uuid4(),
        repository_identity=identity,
        source=f"file:///{identity}",
        branch="feature/environment",
        default_branch="main",
        requested_branch="feature/environment",
        source_revision="a" * 40,
        source_tree_identity="b" * 40,
        acquisition_policy=RepositoryAcquisitionPolicyV1(
            branch_selection=RepositoryBranchSelection.HUMAN_REQUESTED,
        ),
        mount_path=mount,
        writable=True,
        provenance_reference=f"repository-reality:{identity}",
    )


def workspace(*bindings):
    return ProductionWorkspaceV1(
        id=uuid4(),
        work_id=uuid4(),
        repository_assets=bindings or (repository_binding(),),
        environment_configuration=EnvironmentConfiguration(
            provider_profile="container-v1",
            dependency_profile_reference="python:3.12",
            toolchain_references=("toolchain:python", "toolchain:git"),
            lifecycle_policy_references=("policy:retention:v1",),
        ),
        runtime_configuration=RuntimeConfiguration(
            runtime_profile="static-web-preview-v1",
            network_policy_reference="network:preview-local",
            resource_policy_reference="resource:small",
        ),
        generated_roots=("/workspace/generated",),
        created_at=datetime.now(UTC),
    )


def test_workspace_is_work_bound_and_supports_multiple_repositories():
    value = workspace(
        repository_binding("repo:frontend", "/workspace/frontend"),
        repository_binding("repo:backend", "/workspace/backend"),
    )

    restored = ProductionWorkspaceV1.model_validate_json(value.model_dump_json())

    assert restored == value
    assert len(restored.repository_assets) == 2
    assert restored.work_id is not None


def test_workspace_rejects_repository_or_mount_aliasing():
    with pytest.raises(ValidationError, match="repository identities must be unique"):
        workspace(
            repository_binding("repo:frontend", "/workspace/frontend"),
            repository_binding("repo:frontend", "/workspace/backend"),
        )
    with pytest.raises(ValidationError, match="mount paths must be unique"):
        workspace(
            repository_binding("repo:frontend", "/workspace/app"),
            repository_binding("repo:backend", "/workspace/app"),
        )


def test_active_environment_and_ready_preview_require_exact_runtime_binding():
    ws = workspace()
    now = datetime.now(UTC)
    environment = ProductionEnvironmentV1(
        id=uuid4(),
        work_id=ws.work_id,
        workspace_id=ws.id,
        lifecycle_state=EnvironmentLifecycleState.ACTIVE,
        runtime_state=EnvironmentRuntimeState.READY,
        provider_reference="container-v1:abc",
        artifact_references=("artifact:index",),
        evidence_references=("evidence:verification",),
        created_at=now,
        updated_at=now,
    )
    preview = PreviewRuntimeV1(
        id=uuid4(),
        environment_id=environment.id,
        workspace_id=ws.id,
        environment_lifecycle_state=environment.lifecycle_state,
        status=PreviewRuntimeStatus.READY,
        preview_reference="preview:1",
        endpoint="http://127.0.0.1:8123/index.html",
        artifact_references=environment.artifact_references,
        created_at=now,
        updated_at=now,
    )

    assert preview.environment_id == environment.id
    with pytest.raises(ValidationError, match="READY Preview requires an endpoint"):
        PreviewRuntimeV1(
            **preview.model_dump(exclude={"endpoint"}),
            endpoint=None,
        )


def test_production_record_is_digest_bound_and_json_round_trippable():
    record = ProductionRecordV1(
        id=uuid4(),
        work_reference="work:1",
        task_contract_reference="task-contract:1",
        repository_revisions=(
            RepositoryRevisionReference(
                repository_identity="repo:frontend",
                branch="feature/environment",
                before_revision="a" * 40,
                after_revision="c" * 40,
                diff_reference=f"{'a' * 40}..{'c' * 40}",
            ),
        ),
        environment_reference="production-environment:1",
        changes=(
            ProductionChangeReference(
                repository_identity="repo:frontend",
                path="index.html",
                change_type=ProductionChangeType.MODIFIED,
                artifact_reference="artifact:index",
            ),
        ),
        verification_results=(
            VerificationResultReference(
                reference="verification:1",
                outcome=VerificationOutcome.PASS,
            ),
        ),
        delivery_result=DeliveryResultReference(
            reference="delivery:1",
            state=ProductionDeliveryState.AUTHORIZED_FOR_DELIVERY,
        ),
        created_at=datetime.now(UTC),
    )

    restored = ProductionRecordV1.model_validate_json(record.model_dump_json())

    assert restored == record
    assert len(record.content_digest) == 64
    with pytest.raises(ValidationError, match="digest does not match"):
        ProductionRecordV1.model_validate(
            {**record.model_dump(), "content_digest": "0" * 64}
        )


def test_resource_reference_graph_foundation_rejects_self_edges():
    with pytest.raises(ValidationError, match="cannot point to themselves"):
        ResourceReferenceV1(
            id=uuid4(),
            source_kind=ResourceKind.WORKSPACE,
            source_reference="workspace:1",
            target_kind=ResourceKind.WORKSPACE,
            target_reference="workspace:1",
            relationship=ReferenceRelationship.CONTAINS,
            created_at=datetime.now(UTC),
        )


def test_preview_projection_and_resource_edges_bind_existing_runtime_evidence():
    ws = workspace()
    now = datetime.now(UTC)
    environment = ProductionEnvironmentV1(
        id=uuid4(),
        work_id=ws.work_id,
        workspace_id=ws.id,
        lifecycle_state=EnvironmentLifecycleState.ACTIVE,
        runtime_state=EnvironmentRuntimeState.READY,
        provider_reference="container-v1:abc",
        artifact_references=("artifact:index",),
        evidence_references=("verification:1",),
        created_at=now,
        updated_at=now,
    )
    preview = preview_runtime_from_observation(
        environment,
        preview_id=uuid4(),
        preview_reference="preview:1",
        artifact_references=environment.artifact_references,
        observation={"status": "READY", "url": "http://127.0.0.1:8123/index.html"},
        created_at=now,
        observed_at=now,
    )
    references = production_resource_references(
        environment,
        delivery_reference="delivery:1",
        created_at=now,
    )

    assert preview.status is PreviewRuntimeStatus.READY
    assert preview.endpoint == "http://127.0.0.1:8123/index.html"
    assert {edge.target_kind for edge in references} == {
        ResourceKind.ENVIRONMENT,
        ResourceKind.WORKSPACE,
        ResourceKind.ARTIFACT,
        ResourceKind.EVIDENCE,
        ResourceKind.DELIVERY,
    }
