"""Consumer-driven contract proof across the three sibling repositories."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
from uuid import uuid4

import pytest

from spg.application.production_environment_contracts import (
    change_reality_v1_payload,
    delivery_reality_v1_payload,
    guardian_assurance_intake_v1_payload,
    preview_reality_v1_payload,
    repository_reality_v1_payload,
    workspace_reality_v1_payload,
)
from spg.domain.production_environment import (
    CandidatePreviewMode,
    CandidatePreviewSessionV1,
    DeliveryResultReference,
    EnvironmentConfiguration,
    EnvironmentLifecycleState,
    EnvironmentRuntimeState,
    GitContinuityV1,
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
    RuntimeConfiguration,
    VerificationOutcome,
    VerificationResultReference,
    PreviewRuntimeStatus,
)


pytestmark = pytest.mark.cross_repository


def load_sibling_contracts():
    watt_root = Path(__file__).resolve().parents[1]
    workspace_root = watt_root.parent
    ecf_src = workspace_root / "engineering-context-fabric" / "src"
    guardian_src = workspace_root / "guardian" / "src"
    if not ecf_src.is_dir() or not guardian_src.is_dir():
        pytest.skip("sibling ECF and Guardian repositories are not available")
    sys.path[:0] = [str(ecf_src), str(guardian_src)]
    from ecf.contracts.production_environment import (
        ChangeRealityV1,
        DeliveryRealityV1,
        RepositoryRealityV1,
        WorkspaceRealityV1,
    )
    from guardian.contracts.production_environment import AssuranceIntakeV1

    return (
        RepositoryRealityV1,
        WorkspaceRealityV1,
        ChangeRealityV1,
        DeliveryRealityV1,
        AssuranceIntakeV1,
    )


def watt_records():
    now = datetime.now(UTC)
    work_id, workspace_id, environment_id = uuid4(), uuid4(), uuid4()
    continuity = GitContinuityV1(
        repository_identity="repo:brownfield",
        source="file:///workspace/brownfield",
        branch="feature/environment",
        base_commit="a" * 40,
        current_commit="b" * 40,
        current_tree_identity="c" * 40,
        ancestry=("a" * 40, "b" * 40),
        diff_reference=f"{'a' * 40}..{'b' * 40}",
        observed_at=now,
    )
    workspace = ProductionWorkspaceV1(
        id=workspace_id,
        work_id=work_id,
        repository_assets=(
            RepositoryAssetBinding(
                asset_id=uuid4(),
                repository_identity=continuity.repository_identity,
                source=continuity.source,
                branch=continuity.branch,
                default_branch=continuity.branch,
                source_revision=continuity.base_commit,
                source_tree_identity="c" * 40,
                acquisition_policy=RepositoryAcquisitionPolicyV1(
                    branch_selection=RepositoryBranchSelection.REPOSITORY_DEFAULT,
                ),
                mount_path="/workspace/brownfield",
                writable=True,
                provenance_reference="repository-reality:source",
            ),
        ),
        environment_configuration=EnvironmentConfiguration(
            provider_profile="container-v1"
        ),
        runtime_configuration=RuntimeConfiguration(runtime_profile="preview-v1"),
        created_at=now,
    )
    environment = ProductionEnvironmentV1(
        id=environment_id,
        work_id=work_id,
        workspace_id=workspace_id,
        lifecycle_state=EnvironmentLifecycleState.ACTIVE,
        runtime_state=EnvironmentRuntimeState.READY,
        provider_reference="container-v1:1",
        artifact_references=("artifact:index",),
        evidence_references=("verification:1",),
        created_at=now,
        updated_at=now,
    )
    record = ProductionRecordV1(
        id=uuid4(),
        work_reference=f"work:{work_id}",
        task_contract_reference="task-contract:1",
        repository_revisions=(
            RepositoryRevisionReference(
                repository_identity=continuity.repository_identity,
                branch=continuity.branch,
                before_revision=continuity.base_commit,
                after_revision=continuity.current_commit,
                diff_reference=continuity.diff_reference,
            ),
        ),
        environment_reference=f"production-environment:{environment_id}",
        changes=(
            ProductionChangeReference(
                repository_identity=continuity.repository_identity,
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
        created_at=now,
    )
    return now, continuity, workspace, environment, record


def test_watt_payloads_are_admitted_by_ecf_and_guardian_contract_owners():
    (
        RepositoryRealityV1,
        WorkspaceRealityV1,
        ChangeRealityV1,
        DeliveryRealityV1,
        AssuranceIntakeV1,
    ) = load_sibling_contracts()
    now, continuity, workspace, environment, record = watt_records()
    repository_reality = RepositoryRealityV1.model_validate(
        repository_reality_v1_payload(
            continuity,
            reality_id=uuid4(),
            source_reference="git-observation:1",
            observed_by="git-continuity-inspector-v1",
            refresh_after=now + timedelta(minutes=5),
        )
    )
    workspace_reality = WorkspaceRealityV1.model_validate(
        workspace_reality_v1_payload(
            workspace,
            environment,
            reality_id=uuid4(),
            repository_reality_references={
                continuity.repository_identity: (
                    f"repository-reality:{repository_reality.reality_id}"
                )
            },
            observed_at=now,
            source_reference="workspace-observation:1",
            observed_by="workspace-observer-v1",
        )
    )
    change_reality = ChangeRealityV1.model_validate(
        change_reality_v1_payload(
            record,
            reality_id=uuid4(),
            observed_at=now,
            source_reference="production-record:1",
            observed_by="change-observer-v1",
        )
    )
    delivery_reality = DeliveryRealityV1.model_validate(
        delivery_reality_v1_payload(
            record,
            reality_id=uuid4(),
            repository_identity=continuity.repository_identity,
            observed_at=now,
            source_reference="delivery-observation:1",
            observed_by="delivery-observer-v1",
        )
    )
    assurance_intake = AssuranceIntakeV1.model_validate(
        guardian_assurance_intake_v1_payload(
            record,
            intake_id=uuid4(),
            submitted_by="watt-production-environment",
            submitted_at=now,
        )
    )

    assert workspace_reality.environment_reference == record.environment_reference
    assert change_reality.revision_transitions[0].to_revision == continuity.current_commit
    assert delivery_reality.commit == continuity.current_commit
    assert assurance_intake.production_record_reference.digest == record.content_digest
    assert assurance_intake.environment_reference.reference == record.environment_reference


def test_candidate_preview_current_and_stale_reality_is_ecf_admissible(tmp_path):
    load_sibling_contracts()
    from ecf.contracts.production_environment import PreviewRealityState, PreviewRealityV1
    from ecf.runtime import ECFRealityRuntime, JsonRealityStore

    now = datetime.now(UTC)
    session = CandidatePreviewSessionV1(
        id=uuid4(), work_id=uuid4(), candidate_id=uuid4(),
        candidate_fingerprint="f" * 64, repository_identity="repo:one",
        repository_revision="a" * 40, repository_tree="b" * 40,
        workspace_id=uuid4(), environment_id=uuid4(),
        mode=CandidatePreviewMode.FULL_APPLICATION_RUNTIME,
        status=PreviewRuntimeStatus.READY, definition_version="watt-compose-topology-v1",
        endpoint="http://127.0.0.1:8001/app", image_reference="sha256:" + "c" * 64,
        service_identities=("app", "db"), created_at=now, updated_at=now,
    )
    runtime = ECFRealityRuntime(JsonRealityStore(tmp_path / "ecf"))
    ready = runtime.admit_preview_payload(preview_reality_v1_payload(session))
    assert PreviewRealityV1.model_validate(ready).runtime_state is PreviewRealityState.READY
    stale = session.model_copy(update={"status": PreviewRuntimeStatus.STALE,
        "endpoint": None, "version": 2})
    stopped = runtime.admit_preview_payload(preview_reality_v1_payload(stale))
    assert PreviewRealityV1.model_validate(stopped).runtime_state is PreviewRealityState.STALE
    assert runtime.store.latest("preview", f"work:{session.work_id}").preview_endpoint is None
