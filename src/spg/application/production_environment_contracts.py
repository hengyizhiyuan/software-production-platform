"""Versioned JSON projections at the Watt ↔ ECF ↔ Guardian boundaries.

Watt emits plain data and does not import or own ECF/Guardian contracts. The
owning repositories validate these payloads in cross-repository qualification.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from spg.domain.production_environment import (
    CandidatePreviewSessionV1,
    GitContinuityV1,
    ProductionEnvironmentV1,
    ProductionRecordV1,
    ProductionWorkspaceV1,
    RepositoryAcquisitionPolicyV1,
    RepositoryBranchSelection,
)


def preview_reality_v1_payload(session: CandidatePreviewSessionV1) -> dict:
    """Project immutable, versioned runtime observation for ECF ownership."""

    from uuid import NAMESPACE_URL, uuid5

    record = next((item["reference"] for item in session.evidence
        if item["kind"] == "PRODUCTION_RECORD"), None)
    return {
        "schema_version": 1,
        "reality_id": uuid5(NAMESPACE_URL, f"watt:candidate-preview-reality:{session.id}:{session.version}"),
        "preview_identity": f"candidate-preview:{session.id}",
        "work_reference": f"work:{session.work_id}",
        "candidate_reference": f"candidate:{session.candidate_id}",
        "repository_identity": session.repository_identity,
        "candidate_revision": session.repository_revision,
        "candidate_tree_identity": session.repository_tree,
        "workspace_reference": f"workspace:{session.workspace_id}",
        "environment_reference": f"production-environment:{session.environment_id}",
        "runtime_definition_version": session.definition_version,
        "runtime_state": session.status.value,
        "preview_endpoint": session.endpoint,
        "runtime_service_references": session.service_identities,
        "production_record_reference": record,
        "provenance": {
            "source_system": "watt-production-environment",
            "source_reference": f"candidate-preview:{session.id}:v{session.version}",
            "observed_by": "watt:candidate-preview:v1",
        },
        "freshness": {
            "state": ("STALE" if session.status.value in {"STALE", "STOPPED"}
                else "UNKNOWN" if session.status.value == "FAILED" else "FRESH"),
            "observed_at": session.updated_at,
            "refresh_after": None,
        },
    }


def _metadata(
    *,
    observed_at: datetime,
    source_reference: str,
    observed_by: str,
    refresh_after: datetime | None,
) -> dict:
    return {
        "provenance": {
            "source_system": "watt-production-environment",
            "source_reference": source_reference,
            "observed_by": observed_by,
        },
        "freshness": {
            "state": "FRESH",
            "observed_at": observed_at,
            "refresh_after": refresh_after,
        },
    }


def repository_reality_v1_payload(
    continuity: GitContinuityV1,
    *,
    reality_id: UUID,
    source_reference: str,
    observed_by: str,
    refresh_after: datetime | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "reality_id": reality_id,
        "repository_identity": continuity.repository_identity,
        "revision": continuity.current_commit,
        "tree_identity": continuity.current_tree_identity,
        "branch": continuity.branch,
        "default_branch": continuity.branch,
        "requested_branch": None,
        "selected_branch": continuity.branch,
        "selected_revision": continuity.current_commit,
        "acquisition_policy": RepositoryAcquisitionPolicyV1(
            branch_selection=RepositoryBranchSelection.REPOSITORY_DEFAULT,
        ).model_dump(mode="json"),
        "source": continuity.source,
        **_metadata(
            observed_at=continuity.observed_at,
            source_reference=source_reference,
            observed_by=observed_by,
            refresh_after=refresh_after,
        ),
    }


def workspace_reality_v1_payload(
    workspace: ProductionWorkspaceV1,
    environment: ProductionEnvironmentV1,
    *,
    reality_id: UUID,
    repository_reality_references: dict[str, str],
    observed_at: datetime,
    source_reference: str,
    observed_by: str,
    refresh_after: datetime | None = None,
) -> dict:
    if workspace.id != environment.workspace_id or workspace.work_id != environment.work_id:
        raise ValueError("Workspace Reality requires exact Work and Environment binding")
    expected = {item.repository_identity for item in workspace.repository_assets}
    if set(repository_reality_references) != expected:
        raise ValueError("every Workspace repository requires exactly one Reality reference")
    return {
        "schema_version": 1,
        "reality_id": reality_id,
        "workspace_identity": f"workspace:{workspace.id}",
        "work_reference": f"work:{workspace.work_id}",
        "environment_reference": f"production-environment:{environment.id}",
        "repository_bindings": [
            {
                "repository_identity": item.repository_identity,
                "repository_reality_reference": repository_reality_references[
                    item.repository_identity
                ],
                "mount_path": item.mount_path,
            }
            for item in workspace.repository_assets
        ],
        **_metadata(
            observed_at=observed_at,
            source_reference=source_reference,
            observed_by=observed_by,
            refresh_after=refresh_after,
        ),
    }


def change_reality_v1_payload(
    record: ProductionRecordV1,
    *,
    reality_id: UUID,
    observed_at: datetime,
    source_reference: str,
    observed_by: str,
    refresh_after: datetime | None = None,
) -> dict:
    transitions = [
        {
            "repository_identity": item.repository_identity,
            "from_revision": item.before_revision,
            "to_revision": item.after_revision,
            "branch": item.branch,
        }
        for item in record.repository_revisions
    ]
    return {
        "schema_version": 1,
        "reality_id": reality_id,
        "work_reference": record.work_reference,
        "environment_reference": record.environment_reference,
        "revision_transitions": transitions,
        "changed_assets": [
            {
                "repository_identity": item.repository_identity,
                "path": item.path,
                "change_type": item.change_type.value,
                "artifact_reference": item.artifact_reference,
            }
            for item in record.changes
        ],
        "artifact_references": sorted(
            {
                item.artifact_reference
                for item in record.changes
                if item.artifact_reference is not None
            }
        ),
        **_metadata(
            observed_at=observed_at,
            source_reference=source_reference,
            observed_by=observed_by,
            refresh_after=refresh_after,
        ),
    }


def delivery_reality_v1_payload(
    record: ProductionRecordV1,
    *,
    reality_id: UUID,
    repository_identity: str,
    observed_at: datetime,
    source_reference: str,
    observed_by: str,
    refresh_after: datetime | None = None,
) -> dict:
    revision = next(
        (
            item
            for item in record.repository_revisions
            if item.repository_identity == repository_identity
        ),
        None,
    )
    if revision is None:
        raise ValueError("Delivery Reality repository is absent from Production Record")
    return {
        "schema_version": 1,
        "reality_id": reality_id,
        "work_reference": record.work_reference,
        "environment_reference": record.environment_reference,
        "repository_identity": repository_identity,
        "branch": revision.branch,
        "commit": revision.after_revision,
        "delivery_state": record.delivery_result.state.value,
        "production_record_reference": f"production-record:{record.id}",
        **_metadata(
            observed_at=observed_at,
            source_reference=source_reference,
            observed_by=observed_by,
            refresh_after=refresh_after,
        ),
    }


def guardian_assurance_intake_v1_payload(
    record: ProductionRecordV1,
    *,
    intake_id: UUID,
    submitted_by: str,
    submitted_at: datetime,
) -> dict:
    artifacts = sorted(
        {
            item.artifact_reference
            for item in record.changes
            if item.artifact_reference is not None
        }
    )
    if not artifacts:
        raise ValueError("Guardian intake requires attributable artifact references")
    return {
        "schema_version": 1,
        "intake_id": intake_id,
        "work_reference": record.work_reference,
        "task_contract_reference": {
            "kind": "TASK_CONTRACT",
            "reference": record.task_contract_reference,
        },
        "environment_reference": {
            "kind": "PRODUCTION_ENVIRONMENT",
            "reference": record.environment_reference,
        },
        "artifact_references": [
            {"kind": "ARTIFACT", "reference": reference}
            for reference in artifacts
        ],
        "verification_references": [
            {
                "kind": "VERIFICATION",
                "reference": item.reference,
            }
            for item in record.verification_results
        ],
        "production_record_reference": {
            "kind": "PRODUCTION_RECORD",
            "reference": f"production-record:{record.id}",
            "digest": record.content_digest,
        },
        "submitted_by": submitted_by,
        "submitted_at": submitted_at,
    }
