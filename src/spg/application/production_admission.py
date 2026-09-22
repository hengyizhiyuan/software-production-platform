"""Explicit Human production requests trigger the existing admission chain."""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from spg.application.assets import RepositoryAssetService
from spg.application.interaction import WorkInteractionService
from spg.application.post_admission import WorkPostAdmissionService
from spg.application.work import WorkApplicationService
from spg.domain.assets import RepositoryIntakeRequest
from spg.domain.interaction import (
    InteractionAssessment,
    InteractionRecord,
    ProductionAdmissionExecutionState,
    RepositoryAcquisitionState,
    WorkAdmissionReadinessStatus,
)
from spg.domain.response_contract import production_intent_evidence


class ProductionAdmissionTrigger:
    """Translate explicit Human authority into existing Work admission actions.

    The Human request authorizes Work formation and read-only acquisition of an
    explicitly supplied repository source. It does not grant private repository
    access, delivery authority, or Human acceptance.
    """

    def __init__(
        self,
        interactions: WorkInteractionService,
        work: WorkApplicationService,
        assets: RepositoryAssetService,
        post_admission: WorkPostAdmissionService,
    ) -> None:
        self.interactions = interactions
        self.work = work
        self.assets = assets
        self.post_admission = post_admission

    def execute(
        self,
        interaction_id: UUID,
        assessment: InteractionAssessment,
        request_record: InteractionRecord,
    ) -> None:
        evidence = production_intent_evidence(request_record.content)
        projection = self.interactions.get_shared_understanding(interaction_id)
        if (
            not evidence.production_request
            or not evidence.repository_relevant
            or not evidence.action_requested
            or assessment.readiness.status is not WorkAdmissionReadinessStatus.READY
            or projection.latest_assessment is None
            or not projection.latest_assessment_current
            or projection.latest_assessment.id != assessment.id
            or projection.latest_assessment.basis_fingerprint
            != assessment.basis_fingerprint
        ):
            self.interactions.clear_production_admission_progress(interaction_id)
            return
        if projection.governed_work_id is not None:
            self.interactions.clear_production_admission_progress(interaction_id)
            return

        resource_id = None
        if evidence.repository_source is not None:
            self.interactions.record_production_admission_progress(
                interaction_id,
                admission_state=ProductionAdmissionExecutionState.ADMISSION_RUNNING,
                repository_state=(
                    RepositoryAcquisitionState.REPOSITORY_ACQUISITION_RUNNING
                ),
                next_step="Resolve the repository branch and exact revision.",
            )
            intake = self.assets.intake(
                RepositoryIntakeRequest(
                    request_id=uuid5(
                        NAMESPACE_URL,
                        "watt:auto-production-repository:"
                        f"{interaction_id}:{assessment.id}:"
                        f"{evidence.repository_source}",
                    ),
                    source=evidence.repository_source,
                    title=(
                        projection.interpreted_motive
                        or "Repository production Work"
                    )[:200],
                    description=(
                        projection.desired_outcome
                        or "Acquire repository Reality for the requested production Work."
                    )[:4000],
                    authority_identity=request_record.source,
                )
            )
            if intake.get("resource_id") is not None:
                resource_id = UUID(intake["resource_id"])

        admitted = self.work.admit_interaction_work(
            interaction_id,
            engineering_resource_id=resource_id,
            use_default_resource=False,
            assessment_id=assessment.id,
            basis_fingerprint=assessment.basis_fingerprint,
            authority_identity=request_record.source,
            rationale=(
                "The Human explicitly requested repository acquisition and software "
                "production. That request authorizes Work formation and read-only "
                "baseline acquisition; private access, delivery, and final acceptance "
                "remain separately governed."
            ),
        )
        if resource_id is not None:
            self.post_admission.activate(admitted.work_id)
        self.interactions.clear_production_admission_progress(interaction_id)
