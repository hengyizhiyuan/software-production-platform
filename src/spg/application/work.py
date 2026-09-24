"""Goal-centric MVP application flow composed over governed Runtime services."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Callable, Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.engineering_semantics import admit_semantic_facts
from spg.application.governance import CandidateGovernanceService
from spg.application.integration import RepositoryIntegrationService
from spg.application.interaction import interaction_basis_fingerprint
from spg.application.planning import ProductionPlanningService
from spg.application.production_intelligence import (
    TaskContractRequest,
    default_task_contract_builder,
)
from spg.application.preparation import PreparationService
from spg.application.repository_branch_authority import (
    BRANCH_FACT_SUBJECTS,
    governed_branch_creation_target,
)
from spg.application.runtime import RuntimeService
from spg.application.runtime_commit import RuntimeCommitService
from spg.application.verification import VerificationService
from spg.application.refinement import RepositoryChangeProposalService
from spg.domain.change import (
    ChangeOperation,
    ChangeTargetShape,
    CodeChangeContract,
    CodeChangeTarget,
    CodeVerificationKind,
    CodeVerificationObligation,
    ProductionTargetKind,
)
from spg.domain.executor import ExecutorCapabilityContract
from spg.domain.engineering_semantics import (
    current_semantic_facts,
    semantic_fact_reference,
)
from spg.domain.governance import (
    CandidateAuthorizationScope,
    CandidateSealRequest,
    HumanAuthorizationRequest,
)
from spg.domain.integration import RepositoryIntegrationRequest
from spg.domain.interaction import (
    InteractionAssessment,
    InteractionCondition,
    InteractionInvariantViolation,
    InteractionRecordNotFound,
    WorkEvolutionCandidateChange,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkTransitionChoice,
    WorkAdmissionReadinessStatus,
)
from spg.domain.preparation import (
    ContextArtifactSelection,
    ContextPackageRequest,
    ExecutorBinding,
)
from spg.domain.planning import (
    OnePwuFitClassification,
    PlannedArtifactOperation,
    ProductionPlanArtifactTarget,
    ProductionPlanProposal,
    ProductionPlanner,
    ProductionPlanningRequest,
)
from spg.domain.refinement import (
    RepositoryChangeProposal,
    RepositoryChangeProposalProvider,
    RepositoryChangeProposalRequest,
)
from spg.domain.product import (
    ArtifactTargetConfidence,
    ArtifactTargetOperation,
    ArtifactTargetProposal,
    AttentionAction,
    AttentionItem,
    AttentionKind,
    AttentionResolutionRequest,
    EngineeringContextReference,
    EngineeringResourceKind,
    EngineeringResourceRecord,
    EngineeringScopeCondition,
    GoalCondition,
    GoalProjection,
    GoalRecord,
    ProductInvariantViolation,
    ProductRecordNotFound,
    ProductionCycleBindingCondition,
    ResourceBindingCondition,
    RuntimeFactSummary,
    WorkCondition,
    WorkMode,
    WorkProjection,
    WorkRecord,
    WorkRefinementRequest,
    WorkResultProjection,
    WorkStatus,
)
from spg.domain.runtime import (
    ArtifactContract,
    ArtifactOperation,
    CompletionContract,
    InitialRunRequest,
    ProductionHorizon,
)
from spg.domain.production_intelligence import EngineeringActivity
from spg.domain.runtime_commit import RuntimeCommitRequest
from spg.domain.verification import (
    ProductionAdmissibilityOutcome,
    VerificationResultValue,
)
from spg.domain.verifier import VerificationCapabilityContract
from spg.domain.steering import (
    RealityReference,
    RealityReferenceKind,
    SteeringAttentionReason,
    SteeringOutcome,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore
from spg.providers.rule_based_planner import RuleBasedProductionPlanner
from spg.providers.repository_change_proposal import (
    RepositoryAwareChangeProposalProvider,
)


WORK_ACTOR = "spg-product:work-application"
DEFAULT_BINDING = ExecutorBinding(
    binding_ref="binding:configured-mvp-executor",
    capability_identity="capability:executor",
    profile_identity="profile:local-mvp",
)
WORK_REALITY_SCHEMA_VERSION = "wic-work-reality-v3"
WORK_EVOLUTION_SCHEMA_VERSION = "wic-work-reality-v3"


_HUMAN_ACTION_COPY: dict[
    SteeringAttentionReason,
    tuple[str, str, str, str],
] = {
    SteeringAttentionReason.MOTIVE_OR_OUTCOME_AMBIGUITY: (
        "Clarify a material Work outcome",
        "A Human-owned choice would materially change the current governed step.",
        "Choose the intended outcome or narrow the current step.",
        "Steering will continue from the recorded choice.",
    ),
    SteeringAttentionReason.MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION: (
        "Choose a material product or architecture direction",
        "The available directions materially change the current result or its acceptance basis.",
        "Select the direction that should govern this Work.",
        "The decision will govern subsequent design and production.",
    ),
    SteeringAttentionReason.SCOPE_OR_AUTHORITY_EXPANSION: (
        "Authorize or reject a scope change",
        "Continuing as proposed would exceed the authority currently admitted for this Work.",
        "Authorize the bounded expansion or keep the existing scope.",
        "No out-of-scope production will occur before the decision.",
    ),
    SteeringAttentionReason.MATERIAL_RISK_OR_COST_DECISION: (
        "Choose how to handle a material risk or cost",
        "The choice materially changes risk, cost, or an irreversible effect for this step.",
        "Select the acceptable bounded trade-off.",
        "The selected risk or cost boundary will constrain continuation.",
    ),
    SteeringAttentionReason.PRODUCT_ACCEPTANCE_REQUIRED: (
        "Accept or continue the current Work outcome",
        "Only the Human can decide whether the current outcome satisfies the Motive.",
        "Accept the outcome or state what still needs to change.",
        "The Work will close or continue according to the acceptance decision.",
    ),
    SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED: (
        "Review the bounded production proposal",
        "Production requires explicit Human admission of its scope and verification basis.",
        "Approve the proposal or request a bounded refinement.",
        "No production authority is created until this review is resolved.",
    ),
}


class AuthorizedProductionRecorder(Protocol):
    def record_authorized_work(self, work_id: UUID) -> object: ...


class WorkApplicationService:
    """Public Python product API; Runtime services retain transition authority."""

    def __init__(
        self,
        database: Database,
        *,
        workspace_root: Path | None = None,
        executor: ExecutorCapabilityContract | None = None,
        verifier: VerificationCapabilityContract | None = None,
        planner: ProductionPlanner | None = None,
        change_proposal_provider: RepositoryChangeProposalProvider | None = None,
        executor_binding: ExecutorBinding = DEFAULT_BINDING,
        preparation: PreparationService | None = None,
        production_recorder: AuthorizedProductionRecorder | None = None,
    ) -> None:
        self.database = database
        self.workspace_root = (workspace_root or Path(".spg/workspaces")).resolve()
        self.executor = executor
        self.verifier = verifier
        self.planning = ProductionPlanningService(
            planner or RuleBasedProductionPlanner()
        )
        self.change_proposals = RepositoryChangeProposalService(
            change_proposal_provider or RepositoryAwareChangeProposalProvider()
        )
        self.executor_binding = executor_binding
        self.production_recorder = production_recorder
        self.runtime = RuntimeService(database)
        self.preparation = preparation or PreparationService(database)
        self.execution = ExecutionService(database, preparation=self.preparation)
        self.completion = CompletionService(database, observer=self.execution.observer)
        self.verification = VerificationService(
            database,
            observer=self.execution.observer,
        )
        self.governance = CandidateGovernanceService(database)
        self.candidate_authorization_guard: Callable[[UUID, UUID], None] | None = None
        self.integration = RepositoryIntegrationService(database)
        self.runtime_commit = RuntimeCommitService(database)

    def configure_candidate_authorization_guard(
        self, guard: Callable[[UUID, UUID], None],
    ) -> None:
        self.candidate_authorization_guard = guard

    def create_goal(self, title: str, description: str | None = None) -> GoalRecord:
        title = title.strip()
        if not title:
            raise ProductInvariantViolation("Goal title is required")
        goal_id = uuid4()
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            store.insert_goal(
                {
                    "id": goal_id,
                    "title": title,
                    "description": description,
                    "condition": GoalCondition.ACTIVE.value,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            result = store.goal(goal_id)
            unit_of_work.commit()
        if result is None:
            raise ProductInvariantViolation("Goal was not constructed")
        return result

    def get_goal(self, goal_id: UUID) -> GoalRecord:
        with self.database.unit_of_work() as unit_of_work:
            goal = ProductStore(unit_of_work.session).goal(goal_id)
        if goal is None:
            raise ProductRecordNotFound(f"Goal not found: {goal_id}")
        return goal

    def list_goals(self) -> tuple[GoalRecord, ...]:
        with self.database.unit_of_work() as unit_of_work:
            return ProductStore(unit_of_work.session).list_goals()

    def register_engineering_resource(
        self,
        *,
        repository_identity: str,
        location_ref: str,
        authoritative_ref: str,
        context_references: tuple[EngineeringContextReference, ...],
        is_default: bool = True,
    ) -> EngineeringResourceRecord:
        if not repository_identity.strip() or not location_ref.strip():
            raise ProductInvariantViolation("Engineering Resource identity/location required")
        if not context_references:
            raise ProductInvariantViolation(
                "MVP repository resource requires at least one Context reference"
            )
        resource_id = uuid4()
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            store.insert_resource(
                {
                    "id": resource_id,
                    "kind": EngineeringResourceKind.REPOSITORY.value,
                    "repository_identity": repository_identity,
                    "location_ref": location_ref,
                    "authoritative_ref": authoritative_ref,
                    "context_references": [
                        item.model_dump(mode="json") for item in context_references
                    ],
                    "is_default": is_default,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            result = store.resource(resource_id)
            unit_of_work.commit()
        if result is None:
            raise ProductInvariantViolation("Engineering Resource was not constructed")
        return result

    def submit_work(
        self,
        raw_user_requirement: str,
        *,
        goal_id: UUID | None = None,
        tags: tuple[str, ...] = (),
        mode: WorkMode = WorkMode.IMMEDIATE_PRODUCTION,
    ) -> WorkProjection:
        if not raw_user_requirement.strip():
            raise ProductInvariantViolation("Work requirement is required")
        timestamp = datetime.now(UTC)
        work_id = uuid4()
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            if goal_id is not None and store.goal(goal_id) is None:
                raise ProductRecordNotFound(f"Goal not found: {goal_id}")
            normalized_tags = tuple(
                sorted({item.strip() for item in tags if item.strip()})
            )
            store.insert_work(
                {
                    "id": work_id,
                    "goal_id": goal_id,
                    "work_mode": mode.value,
                    "raw_user_requirement": raw_user_requirement,
                    "refined_title": None,
                    "desired_outcome": None,
                    "constraints": [],
                    "tags": list(normalized_tags),
                    "condition": WorkCondition.DRAFT.value,
                    "scope_summary": None,
                    "production_objective": None,
                    "expected_artifact_path": None,
                    "artifact_operation": None,
                    "artifact_placement_rationale": None,
                    "artifact_target_confidence": None,
                    "artifact_source_baseline_id": None,
                    "artifact_source_revision": None,
                    "verification_expectation": None,
                    "code_change_proposal": None,
                    "production_plan_proposal": None,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    def admit_interaction_work(
        self,
        interaction_id: UUID,
        *,
        assessment_id: UUID,
        basis_fingerprint: str,
        authority_identity: str,
        rationale: str | None = None,
        engineering_resource_id: UUID | None = None,
        use_default_resource: bool = True,
    ) -> WorkProjection:
        """Atomically admit one exact READY interpretation as long-lived Work."""

        identity = authority_identity.strip()
        if not identity:
            raise ProductInvariantViolation("Human authority identity is required")
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            interactions = InteractionStore(unit_of_work.session)
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            interaction = interactions.interaction(interaction_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(
                    f"Interaction not found: {interaction_id}"
                )
            if interaction.condition is not InteractionCondition.OPEN:
                raise InteractionInvariantViolation(
                    "Only an open Interaction can admit governed Work"
                )
            records = interactions.records(interaction_id)
            if not records:
                raise InteractionInvariantViolation(
                    "Interaction has no Work admission basis"
                )
            assessment = interactions.assessment(assessment_id)
            if assessment is None or assessment.interaction_id != interaction_id:
                raise InteractionRecordNotFound(
                    f"Interaction assessment not found: {assessment_id}"
                )
            pre_work = (
                None
                if interaction.current_work_id is None
                else product.work(interaction.current_work_id, for_update=True)
            )
            work_id = (
                interaction.current_work_id
                if interaction.current_work_id is not None
                else uuid5(
                    NAMESPACE_URL,
                    f"spg:wic-work:{interaction_id}:{assessment.id}:{basis_fingerprint}",
                )
            )
            if interaction.current_work_id is not None:
                if pre_work is None:
                    raise ProductInvariantViolation(
                        "Interaction Work focus no longer exists"
                    )
                if pre_work.condition is WorkCondition.DISCARDED:
                    raise InteractionInvariantViolation(
                        "Discarded PRE_WORK cannot be admitted"
                    )
                if pre_work.condition is WorkCondition.PRE_WORK:
                    pass
                elif interaction.current_work_id != work_id:
                    raise InteractionInvariantViolation(
                        "Interaction already focuses a different governed Work"
                    )
                else:
                    revision = product.current_work_reality_revision(work_id)
                    if (
                        revision is None
                        or revision.source_assessment_id != assessment.id
                        or revision.basis_fingerprint != basis_fingerprint
                    ):
                        raise ProductInvariantViolation(
                            "Interaction focus and governed Work revision diverged"
                        )
                    unit_of_work.rollback()
                    return self.get_work(work_id)

            current_basis = interaction_basis_fingerprint(interaction, records)
            if current_basis != basis_fingerprint:
                raise InteractionInvariantViolation(
                    "READY assessment is stale against current Interaction Reality"
                )
            latest = interactions.latest_assessment(interaction_id)
            if (
                latest is None
                or latest.id != assessment.id
                or assessment.basis_fingerprint != current_basis
                or assessment.basis_last_sequence != records[-1].sequence
            ):
                raise InteractionInvariantViolation(
                    "Only the exact current assessment may admit governed Work"
                )
            if (
                assessment.readiness.status
                is not WorkAdmissionReadinessStatus.READY
                or assessment.readiness.basis_fingerprint != current_basis
                or assessment.readiness.profile != WorkMode.LONG_LIVED_STEERING.value
            ):
                raise InteractionInvariantViolation(
                    "Interaction is not READY for long-lived Work admission"
                )
            motive = (assessment.interpreted_motive or "").strip()
            desired_outcome = (assessment.desired_outcome or "").strip()
            if not motive or not desired_outcome:
                raise InteractionInvariantViolation(
                    "READY assessment lacks a valid Motive or desired outcome"
                )

            resource = (product.resource(engineering_resource_id) if engineering_resource_id else
                        product.default_resource() if use_default_resource else None)
            if engineering_resource_id is not None and resource is None:
                raise ProductInvariantViolation("Selected Repository Asset does not exist")
            pointer = None if resource is None else runtime.current_pointer(
                repository_identity=(resource.repository_identity if resource else None), repository_ref=(resource.authoritative_ref if resource else None),
                for_update=True,
            )
            baseline = None if pointer is None else runtime.snapshot(pointer.snapshot_id)
            if resource is not None and baseline is None:
                raise ProductInvariantViolation("Selected Repository Asset requires its own Trusted Baseline")

            scope_id = uuid5(NAMESPACE_URL, f"spg:wic-scope:{work_id}")
            governance_id = uuid5(NAMESPACE_URL, f"spg:wic-governance:{work_id}")
            revision_id = uuid5(NAMESPACE_URL, f"spg:wic-work-revision:1:{work_id}")
            admitted_semantic_facts = admit_semantic_facts(
                assessment.engineering_semantic_facts,
                work_revision_id=revision_id,
            )
            scope_summary = (
                "Long-lived Work authority envelope for "
                + (f"{(resource.repository_identity if resource else None)} at {(resource.authoritative_ref if resource else None)}" if resource else "design before repository binding")
            )
            scope_fingerprint = self._fingerprint(
                {
                    "work_id": str(work_id),
                    "assessment_id": str(assessment.id),
                    "basis_fingerprint": current_basis,
                    "resource_id": (str(resource.id) if resource else None),
                    "repository_identity": (resource.repository_identity if resource else None),
                    "repository_ref": (resource.authoritative_ref if resource else None),
                    "source_baseline_id": (str(baseline.id) if baseline else None),
                    "source_revision": (baseline.repository_revision if baseline else None),
                    "constraints": list(assessment.candidate_constraints),
                }
            )
            admission_rationale = (
                rationale.strip()
                if rationale is not None and rationale.strip()
                else "Human admitted the exact READY Shared Understanding as governed long-lived Work."
            )
            supporting_references = [
                f"INTERACTION_RECORD:{record.id}"
                for record in records
                if record.sequence <= assessment.basis_last_sequence
            ]
            revision_payload = {
                "work_id": str(work_id),
                "revision_number": 1,
                "previous_revision_id": None,
                "basis_fingerprint": current_basis,
                "source_interaction_id": str(interaction_id),
                "source_assessment_id": str(assessment.id),
                "source_record_ids": [
                    str(record.id)
                    for record in records
                    if record.sequence <= assessment.basis_last_sequence
                ],
                "motive": motive,
                "desired_outcome": desired_outcome,
                "context_facts": list(assessment.candidate_context),
                "constraints": list(assessment.candidate_constraints),
                "requests": list(assessment.current_requests),
                "engineering_semantic_facts": [
                    item.model_dump(mode="json") for item in admitted_semantic_facts
                ],
                "engineering_scope_id": str(scope_id),
                "engineering_resource_id": (str(resource.id) if resource else None),
                "scope_basis_fingerprint": scope_fingerprint,
                "repository_identity": (resource.repository_identity if resource else None),
                "repository_ref": (resource.authoritative_ref if resource else None),
                "source_baseline_id": (str(baseline.id) if baseline else None),
                "source_revision": (baseline.repository_revision if baseline else None),
                "governance_record_id": str(governance_id),
                "supporting_references": supporting_references,
                "change_set": [],
                "rationale": admission_rationale,
                "admitted_by": identity,
                "schema_version": WORK_REALITY_SCHEMA_VERSION,
            }
            revision_fingerprint = self._fingerprint(revision_payload)

            existing = product.work(work_id)
            admitted_values = {
                        "id": work_id,
                        "goal_id": None,
                        "work_mode": WorkMode.LONG_LIVED_STEERING.value,
                        "raw_user_requirement": motive,
                        "refined_title": self._default_title(motive),
                        "desired_outcome": desired_outcome,
                        "constraints": list(assessment.candidate_constraints),
                        "tags": [],
                        "condition": WorkCondition.READY.value,
                        "scope_summary": scope_summary,
                        "production_objective": desired_outcome,
                        "expected_artifact_path": None,
                        "artifact_operation": None,
                        "artifact_placement_rationale": None,
                        "artifact_target_confidence": None,
                        "artifact_source_baseline_id": None,
                        "artifact_source_revision": None,
                        "verification_expectation": (
                            "Verify the requested outcome against independent repository Reality"
                        ),
                        "code_change_proposal": None,
                        "production_plan_proposal": None,
                        "current_work_reality_revision_id": None,
                        "current_engineering_scope_id": None,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    }
            if existing is None:
                product.insert_work(admitted_values)
            elif existing.condition is WorkCondition.PRE_WORK:
                product.update_work(
                    work_id,
                    {
                        key: value
                        for key, value in admitted_values.items()
                        if key not in {"id", "created_at"}
                    },
                )
            if existing is None or existing.condition is WorkCondition.PRE_WORK:
                product.insert_scope(
                    scope_values={
                        "id": scope_id,
                        "work_id": work_id,
                        "summary": scope_summary,
                        "fingerprint": scope_fingerprint,
                        "condition": EngineeringScopeCondition.ADMITTED.value,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                    binding_values=() if resource is None else (
                        {
                            "id": uuid5(
                                NAMESPACE_URL,
                                f"spg:wic-scope-binding:{scope_id}:{resource.id}",
                            ),
                            "engineering_scope_id": scope_id,
                            "resource_id": resource.id,
                            "condition": ResourceBindingCondition.ACTIVE.value,
                            "created_at": timestamp,
                        },
                    ),
                )
                runtime.insert_governance(
                    {
                        "id": governance_id,
                        "decision_type": "ADMIT_LONG_LIVED_WORK",
                        "authority_identity": identity,
                        "subject_type": "PRODUCT_WORK",
                        "subject_identity": str(work_id),
                        "scope": {
                            "work_mode": WorkMode.LONG_LIVED_STEERING.value,
                            "source_interaction_id": str(interaction_id),
                            "source_assessment_id": str(assessment.id),
                            "assessment_basis_fingerprint": current_basis,
                            "work_reality_revision_id": str(revision_id),
                            "engineering_scope_id": str(scope_id),
                            "scope_fingerprint": scope_fingerprint,
                            "resource_id": (str(resource.id) if resource else None),
                            "repository_identity": (resource.repository_identity if resource else None),
                            "repository_ref": (resource.authoritative_ref if resource else None),
                            "source_baseline_id": (str(baseline.id) if baseline else None),
                            "source_revision": (baseline.repository_revision if baseline else None),
                            "desired_outcome": desired_outcome,
                            "constraints": list(assessment.candidate_constraints),
                            "artifact_target": None,
                            "source_change_proposal_fingerprint": None,
                        },
                        "rationale": admission_rationale,
                        "created_at": timestamp,
                    }
                )
                product.insert_work_reality_revision(
                    {
                        "id": revision_id,
                        "work_id": work_id,
                        "revision_number": 1,
                        "previous_revision_id": None,
                        "basis_fingerprint": current_basis,
                        "revision_fingerprint": revision_fingerprint,
                        "source_interaction_id": interaction_id,
                        "source_assessment_id": assessment.id,
                        "source_record_ids": [
                            str(record.id)
                            for record in records
                            if record.sequence <= assessment.basis_last_sequence
                        ],
                        "motive": motive,
                        "desired_outcome": desired_outcome,
                        "context_facts": list(assessment.candidate_context),
                        "constraints": list(assessment.candidate_constraints),
                        "requests": list(assessment.current_requests),
                        "engineering_semantic_facts": [
                            item.model_dump(mode="json")
                            for item in admitted_semantic_facts
                        ],
                        "engineering_scope_id": scope_id,
                        "engineering_resource_id": (resource.id if resource else None),
                        "scope_basis_fingerprint": scope_fingerprint,
                        "repository_identity": (resource.repository_identity if resource else None),
                        "repository_ref": (resource.authoritative_ref if resource else None),
                        "source_baseline_id": (baseline.id if baseline else None),
                        "source_revision": (baseline.repository_revision if baseline else None),
                        "governance_record_id": governance_id,
                        "supporting_references": supporting_references,
                        "change_set": [],
                        "rationale": admission_rationale,
                        "admitted_by": identity,
                        "schema_version": WORK_REALITY_SCHEMA_VERSION,
                        "created_at": timestamp,
                    }
                )
                product.update_work(
                    work_id,
                    {
                        "current_work_reality_revision_id": revision_id,
                        "current_engineering_scope_id": scope_id,
                        "updated_at": timestamp,
                    },
                )
            else:
                revision = product.current_work_reality_revision(work_id)
                if (
                    revision is None
                    or revision.source_assessment_id != assessment.id
                    or revision.revision_fingerprint != revision_fingerprint
                ):
                    raise ProductInvariantViolation(
                        "Existing governed Work does not match exact admission basis"
                    )

            interactions.set_current_work(
                interaction_id,
                work_id=work_id,
                updated_by=identity,
                updated_at=timestamp,
            )
            transition = interactions.latest_transition(interaction_id)
            if (
                transition is not None
                and transition.choice is WorkTransitionChoice.START_NEW_WORK
                and transition.target_work_id is None
            ):
                interactions.bind_transition_target(
                    transition.id,
                    target_work_id=work_id,
                )
            unit_of_work.commit()
        return self.get_work(work_id)

    def decide_interaction_work_revision(
        self,
        interaction_id: UUID,
        *,
        assessment_id: UUID,
        basis_fingerprint: str,
        expected_previous_revision_id: UUID,
        action: AttentionAction,
        authority_identity: str,
        rationale: str | None = None,
        branch_only: bool = False,
    ) -> WorkProjection:
        """Govern one exact active-Work interpretation without rewriting history."""

        if action not in {
            AttentionAction.APPROVE,
            AttentionAction.REJECT,
            AttentionAction.REQUEST_REFINEMENT,
        }:
            raise ProductInvariantViolation("Unsupported Work revision decision")
        identity = authority_identity.strip()
        if not identity:
            raise ProductInvariantViolation("Human authority identity is required")
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            interactions = InteractionStore(unit_of_work.session)
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            steering = SteeringStore(unit_of_work.session)
            interaction = interactions.interaction(interaction_id, for_update=True)
            if interaction is None or interaction.current_work_id is None:
                raise InteractionInvariantViolation(
                    "Active Work revision requires a focused Interaction"
                )
            work = product.work(interaction.current_work_id, for_update=True)
            if work is None or work.mode is not WorkMode.LONG_LIVED_STEERING:
                raise ProductInvariantViolation(
                    "Work evolution requires an admitted long-lived Work"
                )
            records = interactions.records(interaction_id)
            assessment = interactions.assessment(assessment_id)
            latest = interactions.latest_assessment(interaction_id)
            current_revision = product.current_work_reality_revision(work.id)
            if assessment is None or assessment.interaction_id != interaction_id:
                raise InteractionRecordNotFound(
                    f"Interaction assessment not found: {assessment_id}"
                )
            if current_revision is None:
                raise ProductInvariantViolation("Focused Work has no Reality revision")
            decision_type = {
                AttentionAction.APPROVE: "ADMIT_WORK_REALITY_REVISION",
                AttentionAction.REJECT: "REJECT_WORK_REALITY_REVISION",
                AttentionAction.REQUEST_REFINEMENT: "REQUEST_WORK_REALITY_REFINEMENT",
            }[action]
            subject = f"interaction-assessment:{assessment.id}"
            prior_decisions = runtime.governance_for_subject(subject)
            if prior_decisions:
                if prior_decisions[-1].decision_type != decision_type:
                    raise ProductInvariantViolation(
                        "Work revision candidate already has a different Human decision"
                    )
                existing_revision = product.work_reality_revision_for_assessment(
                    assessment.id
                )
                if action is AttentionAction.APPROVE and existing_revision is None:
                    raise ProductInvariantViolation(
                        "Approved Work revision decision has no admitted revision"
                    )
                unit_of_work.rollback()
                return self.get_work(work.id)
            if (
                latest is None
                or latest.id != assessment.id
                or assessment.basis_fingerprint != basis_fingerprint
                or assessment.basis_last_sequence != records[-1].sequence
                or assessment.basis_work_revision_id != current_revision.id
                or current_revision.id != expected_previous_revision_id
            ):
                raise InteractionInvariantViolation(
                    "Work revision assessment is stale against current governed Reality"
                )
            plan = steering.plan_for_work(work.id)
            active_plan = None if plan is None else steering.active_revision(plan.id)
            current_step = None
            if active_plan is not None:
                current_step = next(
                    (
                        step
                        for step in steering.steps(active_plan.id)
                        if step.state.value == "CURRENT"
                    ),
                    None,
                )
            latest_plan_decision = (
                None
                if active_plan is None
                else steering.latest_decision(active_plan.id)
            )
            binding = product.runtime_binding(work.id)
            binding_summary = (
                None if binding is None else product.runtime_summary(binding)
            )
            was_currently_satisfied = bool(
                current_step is not None
                and current_step.type.value == "COMPLETE"
                and latest_plan_decision is not None
                and latest_plan_decision.steering_outcome is SteeringOutcome.COMPLETE
                and binding is not None
                and binding.work_reality_revision_id == current_revision.id
                and binding_summary is not None
                and binding_summary.runtime_commit_id is not None
                and binding_summary.completion_outcome == "PRODUCED"
                and binding_summary.verification_results
                and all(
                    result == "PASS"
                    for result in binding_summary.verification_results
                )
                and binding_summary.integration_state == "CONVERGED"
                and any(
                    reference.kind is RealityReferenceKind.RUNTIME_COMMIT
                    and reference.identity == binding_summary.runtime_commit_id
                    for reference in latest_plan_decision.reality_refs
                )
            )
            active_binding = (
                binding
                if binding is not None
                and binding.condition is ProductionCycleBindingCondition.ADMITTED
                else None
            )
            if (
                assessment.basis_steering_plan_revision_id
                != (None if active_plan is None else active_plan.id)
                or assessment.basis_steering_step_id
                != (None if current_step is None else current_step.id)
                or assessment.basis_active_runtime_binding_id
                != (None if active_binding is None else active_binding.id)
            ):
                raise InteractionInvariantViolation(
                    "Work revision assessment Plan or production basis is stale"
                )
            if assessment.focus_classification in {
                WorkFocusClassification.MATERIAL_BRANCH,
                WorkFocusClassification.UNRELATED_NEW_DEMAND,
            } or assessment.impact_disposition is WorkImpactDisposition.NEW_WORK_RECOMMENDED:
                raise ProductInvariantViolation(
                    "A branch or unrelated demand cannot be merged into current Work"
                )
            if assessment.candidate_change is None:
                raise ProductInvariantViolation(
                    "Assessment contains no governed Work change candidate"
                )
            candidate = assessment.candidate_change
            if branch_only:
                target = governed_branch_creation_target(
                    assessment.engineering_semantic_facts,
                    record_for_id=interactions.record,
                )
                prior_ids = {fact.id for fact in current_revision.engineering_semantic_facts}
                branch_facts = tuple(
                    fact for fact in assessment.engineering_semantic_facts
                    if fact.id not in prior_ids
                    and (
                        (fact.subject in BRANCH_FACT_SUBJECTS and fact.value == target)
                        or (
                            fact.subject == "repository.branch_action"
                            and fact.value == "创建新分支"
                        )
                    )
                    and records[-1].id in fact.provenance.source_record_ids
                )
                if (
                    target is None
                    or len(branch_facts) != 2
                    or {fact.subject for fact in branch_facts} != {
                        "repository.branch_name", "repository.branch_action"
                    }
                ):
                    raise ProductInvariantViolation(
                        "Branch-only revision requires one exact Human branch command"
                    )
                candidate = WorkEvolutionCandidateChange(
                    changed_fields=("requests", "semantic_facts"),
                    motive=current_revision.motive,
                    desired_outcome=current_revision.desired_outcome,
                    context_facts=current_revision.context_facts,
                    constraints=current_revision.constraints,
                    requests=tuple(dict.fromkeys((
                        *current_revision.requests, records[-1].content,
                    ))),
                    semantic_facts=(
                        *current_revision.engineering_semantic_facts, *branch_facts,
                    ),
                    scope_change_required=False,
                )

            governance_id = uuid5(
                NAMESPACE_URL,
                f"spg:wic-work-revision-decision:{assessment.id}:{action.value}",
            )
            decision_rationale = (
                rationale.strip()
                if rationale is not None and rationale.strip()
                else f"Human {action.value.casefold()} decision for proposed Work evolution."
            )
            runtime.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": decision_type,
                    "authority_identity": identity,
                    "subject_type": "WORK_REALITY_REVISION_CANDIDATE",
                    "subject_identity": subject,
                    "scope": {
                        "work_id": str(work.id),
                        "interaction_id": str(interaction.id),
                        "assessment_id": str(assessment.id),
                        "basis_fingerprint": assessment.basis_fingerprint,
                        "previous_revision_id": str(current_revision.id),
                        "changed_fields": list(
                            candidate.changed_fields
                        ),
                        "focus_classification": (
                            None
                            if assessment.focus_classification is None
                            else assessment.focus_classification.value
                        ),
                        "impact_disposition": (
                            None
                            if assessment.impact_disposition is None
                            else assessment.impact_disposition.value
                        ),
                        "active_runtime_binding_id": (
                            None if active_binding is None else str(active_binding.id)
                        ),
                    },
                    "rationale": decision_rationale,
                    "created_at": timestamp,
                }
            )
            if action is not AttentionAction.APPROVE:
                unit_of_work.commit()
                return self.get_work(work.id)

            current_scope = product.scope(current_revision.engineering_scope_id)
            resource = product.resource_for_work(work.id)
            pointer = None if resource is None else runtime.current_pointer(
                repository_identity=(resource.repository_identity if resource else None), repository_ref=(resource.authoritative_ref if resource else None), for_update=True)
            baseline = None if pointer is None else runtime.snapshot(pointer.snapshot_id)
            if current_scope is None or (resource is not None and baseline is None):
                raise ProductInvariantViolation("Current Work scope or repository baseline is missing")

            revision_number = current_revision.revision_number + 1
            revision_id = uuid5(
                NAMESPACE_URL,
                f"spg:wic-work-revision:{work.id}:{revision_number}:{assessment.id}",
            )
            admitted_semantic_facts = admit_semantic_facts(
                candidate.semantic_facts,
                work_revision_id=revision_id,
            )
            scope = current_scope
            if candidate.scope_change_required:
                scope_id = uuid5(
                    NAMESPACE_URL,
                    f"spg:wic-scope:{work.id}:revision:{revision_number}:{assessment.id}",
                )
                scope_summary = (
                    "Long-lived Work revision "
                    f"{revision_number} authority envelope for "
                    f"{(resource.repository_identity if resource else None)} at {(resource.authoritative_ref if resource else None)}"
                )
                scope_fingerprint = self._fingerprint(
                    {
                        "work_id": str(work.id),
                        "revision_number": revision_number,
                        "assessment_id": str(assessment.id),
                        "previous_scope_id": str(current_scope.id),
                        "resource_id": (str(resource.id) if resource else None),
                        "constraints": list(candidate.constraints),
                    }
                )
                product.insert_scope(
                    scope_values={
                        "id": scope_id,
                        "work_id": work.id,
                        "summary": scope_summary,
                        "fingerprint": scope_fingerprint,
                        "condition": EngineeringScopeCondition.ADMITTED.value,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                    binding_values=tuple({
                        "id": uuid5(NAMESPACE_URL, f"spg:wic-scope-binding:{scope_id}:{item.resource_id}"),
                        "engineering_scope_id": scope_id, "resource_id": item.resource_id,
                        "condition": ResourceBindingCondition.ACTIVE.value, "created_at": timestamp,
                    } for item in current_scope.bindings),
                )
                scope = product.scope(scope_id)
                assert scope is not None

            source_record_ids = tuple(
                record.id
                for record in records
                if record.sequence <= assessment.basis_last_sequence
            )
            supporting_references = tuple(
                dict.fromkeys(
                    (
                        *(f"INTERACTION_RECORD:{record_id}" for record_id in source_record_ids),
                        *assessment.supporting_references,
                    )
                )
            )
            revision_payload = {
                "work_id": str(work.id),
                "revision_number": revision_number,
                "previous_revision_id": str(current_revision.id),
                "basis_fingerprint": assessment.basis_fingerprint,
                "source_interaction_id": str(interaction.id),
                "source_assessment_id": str(assessment.id),
                "source_record_ids": [str(item) for item in source_record_ids],
                "motive": candidate.motive,
                "desired_outcome": candidate.desired_outcome,
                "context_facts": list(candidate.context_facts),
                "constraints": list(candidate.constraints),
                "requests": list(candidate.requests),
                "engineering_semantic_facts": [
                    item.model_dump(mode="json") for item in admitted_semantic_facts
                ],
                "engineering_scope_id": str(scope.id),
                "engineering_resource_id": (str(resource.id) if resource else None),
                "scope_basis_fingerprint": scope.fingerprint,
                "repository_identity": (resource.repository_identity if resource else None),
                "repository_ref": (resource.authoritative_ref if resource else None),
                "source_baseline_id": (str(baseline.id) if baseline else None),
                "source_revision": (baseline.repository_revision if baseline else None),
                "governance_record_id": str(governance_id),
                "supporting_references": list(supporting_references),
                "change_set": [
                    *candidate.changed_fields,
                    f"impact:{assessment.impact_disposition.value}",
                    *(
                        ("satisfaction:REOPENED",)
                        if was_currently_satisfied
                        else ()
                    ),
                ],
                "rationale": decision_rationale,
                "admitted_by": identity,
                "schema_version": WORK_EVOLUTION_SCHEMA_VERSION,
            }
            product.insert_work_reality_revision(
                {
                    **revision_payload,
                    "id": revision_id,
                    "work_id": work.id,
                    "previous_revision_id": current_revision.id,
                    "source_interaction_id": interaction.id,
                    "source_assessment_id": assessment.id,
                    "source_record_ids": [str(item) for item in source_record_ids],
                    "engineering_scope_id": scope.id,
                    "engineering_resource_id": (resource.id if resource else None),
                    "source_baseline_id": (baseline.id if baseline else None),
                    "governance_record_id": governance_id,
                    "revision_fingerprint": self._fingerprint(revision_payload),
                    "created_at": timestamp,
                }
            )
            compatibility_update = {
                "raw_user_requirement": candidate.motive,
                "desired_outcome": candidate.desired_outcome,
                "constraints": list(candidate.constraints),
                "production_objective": candidate.desired_outcome,
                "scope_summary": scope.summary,
                "current_work_reality_revision_id": revision_id,
                "current_engineering_scope_id": scope.id,
                "updated_at": timestamp,
            }
            if set(candidate.changed_fields) - {"context_facts"}:
                compatibility_update.update(
                    {
                        "code_change_proposal": None,
                        "production_plan_proposal": None,
                        "expected_artifact_path": None,
                        "artifact_operation": None,
                        "artifact_placement_rationale": None,
                        "artifact_target_confidence": None,
                        "artifact_source_baseline_id": None,
                        "artifact_source_revision": None,
                    }
                )
            product.update_work(work.id, compatibility_update)
            unit_of_work.commit()
        return self.get_work(work.id)

    def admit_asset_scope(
        self,
        work_id: UUID,
        request,
        observation: dict,
        *,
        managed_execution_workspace: bool = False,
    ) -> WorkProjection:
        """Admit an exact observed asset or allocate Watt's local execution substrate."""
        from spg.domain.interaction import WorkRealityRevision
        if observation.get("resource_id") != str(request.resource_id) or observation.get("fingerprint") != request.observation_fingerprint:
            raise ProductInvariantViolation("Repository observation does not match the exact asset decision")
        if managed_execution_workspace and (
            request.authority_identity != "system:watt-managed-execution-workspace"
            or observation.get("source") is not None
            or not str(observation.get("repository_identity", "")).startswith(
                "watt://repositories/"
            )
        ):
            raise ProductInvariantViolation(
                "Managed execution allocation accepts only Watt-owned local workspace Reality"
            )
        binding_kind = (
            "MANAGED_EXECUTION_WORKSPACE"
            if managed_execution_workspace
            else "HUMAN_REPOSITORY_ASSET"
        )
        basis = self._fingerprint(
            {
                "work_id": str(work_id),
                "binding_kind": binding_kind,
                **request.model_dump(mode="json"),
            }
        )
        revision_id = uuid5(
            NAMESPACE_URL,
            ("spg:managed-execution-workspace:" if managed_execution_workspace else "spg:asset-scope:")
            + basis,
        )
        with self.database.unit_of_work() as uow:
            product = ProductStore(uow.session)
            runtime = RuntimeStore(uow.session)
            work = product.work(work_id, for_update=True)
            if work is None:
                raise ProductRecordNotFound(f"Work not found: {work_id}")
            if product.work_reality_revision(revision_id) is not None:
                return self._projection(product, work)
            previous = product.current_work_reality_revision(work_id)
            if (work.condition is not WorkCondition.READY or previous is None
                    or previous.id != request.expected_work_revision_id):
                raise ProductInvariantViolation("Asset admission requires the exact current admitted Work Reality")
            resource = product.resource(request.resource_id)
            if resource is None:
                raise ProductInvariantViolation("Repository Asset is missing")
            pointer = runtime.current_pointer(repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
            baseline = None if pointer is None else runtime.snapshot(pointer.snapshot_id)
            if baseline is None:
                raise ProductInvariantViolation("Repository Asset has no Trusted Baseline")
            from spg.infrastructure.git_repository import GitRepositoryObserver
            reality = GitRepositoryObserver().observe(Path(resource.location_ref), resource.repository_identity, resource.authoritative_ref)
            if reality.exact_revision != baseline.repository_revision:
                raise ProductInvariantViolation("Repository Reality differs from its Trusted Baseline; reconcile before binding")
            old_scope = product.scope_for_work(work_id)
            resource_ids = {request.resource_id}
            if old_scope is not None:
                resource_ids.update(item.resource_id for item in old_scope.bindings)
            timestamp = datetime.now(UTC)
            scope_id, governance_id = uuid4(), uuid4()
            scope_fingerprint = self._fingerprint({"work_id": str(work_id), "resources": sorted(str(item) for item in resource_ids), "selected": str(resource.id), "basis": basis})
            scope_summary = (
                f"Watt-managed execution workspace {resource.repository_identity}"
                if managed_execution_workspace
                else f"Work assets; production target {resource.repository_identity}"
            )
            product.insert_scope(scope_values={"id": scope_id, "work_id": work_id,
                "summary": scope_summary,
                "fingerprint": scope_fingerprint, "condition": EngineeringScopeCondition.ADMITTED.value,
                "created_at": timestamp, "updated_at": timestamp}, binding_values=tuple({
                    "id": uuid4(), "engineering_scope_id": scope_id, "resource_id": resource_id,
                    "condition": ResourceBindingCondition.ACTIVE.value, "created_at": timestamp
                } for resource_id in sorted(resource_ids, key=str)))
            payload = previous.model_dump(mode="json")
            payload.update(id=str(revision_id), revision_number=previous.revision_number+1,
                previous_revision_id=str(previous.id), source_kind="ASSET_SCOPE_ADMISSION", source_assessment_id=None,
                basis_fingerprint=basis, engineering_scope_id=str(scope_id), engineering_resource_id=str(resource.id),
                scope_basis_fingerprint=scope_fingerprint, repository_identity=resource.repository_identity,
                repository_ref=resource.authoritative_ref, source_baseline_id=str(baseline.id), source_revision=baseline.repository_revision,
                governance_record_id=str(governance_id), change_set=[
                    "execution-workspace:ALLOCATED"
                    if managed_execution_workspace
                    else "asset:PRODUCTION_TARGET_ADMITTED"
                ],
                supporting_references=[
                    *previous.supporting_references,
                    ("MANAGED_EXECUTION_WORKSPACE:" if managed_execution_workspace else "REPOSITORY_OBSERVATION:")
                    + request.observation_fingerprint,
                ],
                rationale=request.rationale, admitted_by=request.authority_identity, schema_version="wic-work-reality-v3", created_at=timestamp.isoformat())
            payload.pop("revision_fingerprint")
            payload["revision_fingerprint"] = self._fingerprint(payload)
            revision = WorkRealityRevision.model_validate(payload)
            runtime.insert_governance({"id": governance_id, "decision_type": (
                    "ALLOCATE_MANAGED_EXECUTION_WORKSPACE"
                    if managed_execution_workspace
                    else "ADMIT_WORK_ASSET_SCOPE"
                ),
                "authority_identity": request.authority_identity, "subject_type": "PRODUCT_WORK", "subject_identity": str(work_id),
                "scope": {"previous_work_revision_id": str(previous.id), "work_reality_revision_id": str(revision.id),
                    "resource_id": str(resource.id), "observation_fingerprint": request.observation_fingerprint,
                    "source_baseline_id": str(baseline.id),
                    "source_revision": baseline.repository_revision,
                    "scope_fingerprint": scope_fingerprint,
                    "binding_kind": binding_kind},
                "rationale": request.rationale, "created_at": timestamp})
            values = revision.model_dump(mode="python")
            for field in ("source_record_ids", "supporting_references", "change_set", "context_facts", "constraints", "requests"):
                values[field] = [str(item) for item in values[field]]
            values["engineering_semantic_facts"] = [
                item.model_dump(mode="json")
                for item in revision.engineering_semantic_facts
            ]
            product.insert_work_reality_revision(values)
            product.update_work(work_id, {"current_work_reality_revision_id": revision.id,
                "current_engineering_scope_id": scope_id, "scope_summary": scope_summary,
                "production_plan_proposal": None, "code_change_proposal": None,
                "expected_artifact_path": None, "artifact_operation": None,
                "artifact_source_baseline_id": None, "artifact_source_revision": None, "updated_at": timestamp})
            uow.commit()
        return self.get_work(work_id)

    def refine_work(
        self,
        work_id: UUID,
        request: WorkRefinementRequest | None = None,
    ) -> WorkProjection:
        request = request or WorkRefinementRequest()
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            work = self._required_work(store, work_id)
            if work.condition not in {
                WorkCondition.DRAFT,
                WorkCondition.NEEDS_REFINEMENT,
                WorkCondition.AWAITING_APPROVAL,
            }:
                raise ProductInvariantViolation("Only a draft Work may be refined")
            resource = store.resource_for_work(work_id) or (store.default_resource() if store.scope_for_work(work_id) is None else None)
            if resource is None:
                raise ProductInvariantViolation(
                    "A configured default Engineering Resource is required"
                )
            title = request.title or self._default_title(work.raw_user_requirement)
            desired_outcome = request.desired_outcome or work.raw_user_requirement.strip()
            scope_summary = (
                request.scope_summary
                or f"Change {resource.repository_identity} at {resource.authoritative_ref}"
            )
            objective = request.production_objective or desired_outcome
            baseline = self.runtime.current_baseline(repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
            if baseline.repository_identity != resource.repository_identity:
                raise ProductInvariantViolation(
                    "Engineering Resource does not match current governed Baseline"
                )
            constraints = self._merge_constraints(
                work.constraints,
                request.constraints,
                self._extract_constraints(work.raw_user_requirement),
            )
            long_lived = work.mode is WorkMode.LONG_LIVED_STEERING
            code_work = self._is_code_work(work.raw_user_requirement, request)
            existing_proposal = work.code_change_proposal
            explicit_code_boundary = bool(
                request.code_exact_targets
                or request.code_allowed_areas
                or self._explicit_repository_paths(work.raw_user_requirement)
                or self._explicit_repository_areas(work.raw_user_requirement)
            )
            change_proposal = (
                self._repository_change_proposal(
                    work_id=work.id,
                    raw=work.raw_user_requirement,
                    request=request,
                    existing=existing_proposal,
                    resource=resource,
                    baseline_id=baseline.id,
                    source_ref=baseline.repository_ref,
                    source_revision=baseline.repository_revision,
                    desired_outcome=desired_outcome,
                    constraints=constraints,
                )
                if code_work and (not long_lived or explicit_code_boundary)
                else None
            )
            explicit_documentation_target = bool(
                request.expected_artifact_path
                or re.search(
                    r"(?<![\w.-])(?:docs/)[A-Za-z0-9_./-]+\.md(?![\w.-])",
                    work.raw_user_requirement,
                    flags=re.IGNORECASE,
                )
            )
            proposal = (
                None
                if code_work or (long_lived and not explicit_documentation_target)
                else self._artifact_target_proposal(
                    raw=work.raw_user_requirement,
                    explicit_path=request.expected_artifact_path,
                    resource=resource,
                    baseline_id=baseline.id,
                    source_revision=baseline.repository_revision,
                )
            )
            verification = (
                request.verification_expectation
                or (
                    self._proposal_verification_summary(change_proposal)
                    if change_proposal is not None
                    else "Verify the requested outcome against independent repository Reality"
                )
            )
            envelope_refinement_reasons: list[str] = []
            if self._is_too_broad(work.raw_user_requirement):
                envelope_refinement_reasons.append(
                    "The long-lived Work authority envelope is too broad to admit safely."
                    if long_lived
                    else "The admitted Work is too broad for a trustworthy single-PWU plan."
                )
            production_refinement_reasons = list(envelope_refinement_reasons)
            if code_work and (
                change_proposal is None
                or (
                    not change_proposal.required_targets
                    and not change_proposal.allowed_areas
                )
            ):
                production_refinement_reasons.append(
                    "A safely bounded exact target set or repository area is required for code production."
                )
            if code_work and change_proposal is not None:
                production_refinement_reasons.extend(
                    change_proposal.unresolved_scope_questions
                )
            elif not code_work and proposal is None:
                production_refinement_reasons.append(
                    "An exact authorized artifact target is required before production."
                )
            production_request = ProductionPlanningRequest(
                work_id=work.id,
                target_kind=(
                    ProductionTargetKind.CODE_WORK
                    if code_work
                    else ProductionTargetKind.DOCUMENTATION_WORK
                ),
                admitted_requirement=work.raw_user_requirement,
                desired_outcome=desired_outcome,
                production_objective=objective,
                artifact_targets=(
                    ()
                    if proposal is None
                    else (
                        ProductionPlanArtifactTarget(
                            path=proposal.path,
                            operation=PlannedArtifactOperation(
                                proposal.operation.value
                            ),
                        ),
                    )
                ),
                change_proposal=change_proposal,
                change_contract=None,
                constraints=constraints,
                verification_expectation=verification,
                engineering_scope_summary=scope_summary,
                engineering_resource_id=resource.id,
                repository_identity=resource.repository_identity,
                source_baseline_id=baseline.id,
                source_revision=baseline.repository_revision,
                context_references=tuple(
                    item.repository_relative_path
                    for item in resource.context_references
                ),
                refinement_reasons=tuple(production_refinement_reasons),
            )
            concrete_production_boundary = bool(proposal or change_proposal)
            plan = (
                self.planning.propose(production_request)
                if not long_lived or concrete_production_boundary
                else None
            )
            condition = (
                WorkCondition.NEEDS_REFINEMENT
                if long_lived and envelope_refinement_reasons
                else WorkCondition.AWAITING_APPROVAL
                if long_lived
                else WorkCondition.AWAITING_APPROVAL
                if plan is not None
                and plan.fit_classification is OnePwuFitClassification.ONE_PWU_FIT
                else WorkCondition.NEEDS_REFINEMENT
            )
            scope_id = uuid4()
            timestamp = datetime.now(UTC)
            fingerprint = self._fingerprint(
                {
                    "work_id": str(work.id),
                    "summary": scope_summary,
                    "resource_ids": [str(resource.id)],
                }
            )
            store.replace_scope(
                scope_values={
                    "id": scope_id,
                    "work_id": work.id,
                    "summary": scope_summary,
                    "fingerprint": fingerprint,
                    "condition": EngineeringScopeCondition.PROPOSED.value,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                },
                binding_values=(
                    {
                        "id": uuid4(),
                        "engineering_scope_id": scope_id,
                        "resource_id": resource.id,
                        "condition": ResourceBindingCondition.PROPOSED.value,
                        "created_at": timestamp,
                    },
                ),
            )
            store.update_work(
                work.id,
                {
                    "refined_title": title,
                    "desired_outcome": desired_outcome,
                    "constraints": list(constraints),
                    "condition": condition.value,
                    "scope_summary": scope_summary,
                    "production_objective": objective,
                    "expected_artifact_path": (
                        None if proposal is None else proposal.path
                    ),
                    "artifact_operation": (
                        None if proposal is None else proposal.operation.value
                    ),
                    "artifact_placement_rationale": (
                        None if proposal is None else proposal.placement_rationale
                    ),
                    "artifact_target_confidence": (
                        None if proposal is None else proposal.confidence.value
                    ),
                    "artifact_source_baseline_id": (
                        None if proposal is None else proposal.source_baseline_id
                    ),
                    "artifact_source_revision": (
                        None if proposal is None else proposal.source_revision
                    ),
                    "verification_expectation": verification,
                    "code_change_proposal": (
                        None
                        if change_proposal is None
                        else change_proposal.model_dump(mode="json")
                    ),
                    "production_plan_proposal": (
                        None if plan is None else plan.model_dump(mode="json")
                    ),
                    "updated_at": timestamp,
                },
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    create_work_draft = refine_work

    def update_work_tags(
        self,
        work_id: UUID,
        tags: tuple[str, ...],
    ) -> WorkProjection:
        normalized = tuple(sorted({item.strip() for item in tags if item.strip()}))
        if len(normalized) > 20:
            raise ProductInvariantViolation("MVP Work supports at most 20 tags")
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            self._required_work(store, work_id)
            store.update_work(
                work_id,
                {"tags": list(normalized), "updated_at": datetime.now(UTC)},
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    def approve_work(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
        rationale: str | None = None,
    ) -> WorkProjection:
        if not authority_identity.strip():
            raise ProductInvariantViolation("Human authority identity is required")
        if self.get_work(work_id).mode is WorkMode.LONG_LIVED_STEERING:
            return self._approve_long_lived_work(
                work_id,
                authority_identity=authority_identity,
                rationale=rationale,
            )
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            work = self._required_work(store, work_id)
            work_revision = store.current_work_reality_revision(work_id)
            existing = store.runtime_binding(work_id)
            if existing is not None:
                return self._projection(store, work)
            if work.condition is not WorkCondition.AWAITING_APPROVAL:
                raise ProductInvariantViolation(
                    "Work must await Human approval before Runtime admission"
                )
            scope = store.scope_for_work(work_id)
            if scope is None:
                raise ProductInvariantViolation("Work has no Engineering Scope")
            active = tuple(
                item
                for item in scope.bindings
                if item.condition is ResourceBindingCondition.PROPOSED
            )
            self._require_mvp_scope(active)
            resource = store.resource(active[0].resource_id)
            if resource is None:
                raise ProductInvariantViolation("Scope Resource is missing")
            plan = self._required_production_plan(work)
            artifact = self._artifact_target(work)
            change_proposal = work.code_change_proposal
            change_contract = plan.change_contract

        semantic_facts = (
            ()
            if work_revision is None
            else tuple(
                semantic_fact_reference(fact, work_revision_id=work_revision.id)
                for fact in current_semantic_facts(
                    work_revision.engineering_semantic_facts
                )
            )
        )
        work_reality_references = [f"work:{work.id}"]
        if work_revision is not None:
            work_reality_references.append(
                f"work-reality-revision:{work_revision.id}"
            )

        baseline = self.runtime.current_baseline(repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
        if (
            baseline.repository_identity != resource.repository_identity
            or baseline.repository_ref != resource.authoritative_ref
        ):
            raise ProductInvariantViolation(
                "Engineering Resource does not match current governed Baseline"
            )
        if plan.fit_classification is not OnePwuFitClassification.ONE_PWU_FIT:
            raise ProductInvariantViolation(
                "Work Production Plan is not fit for the single-PWU MVP"
            )
        if sum(
            (
                artifact is not None,
                change_proposal is not None,
                change_contract is not None,
            )
        ) != 1:
            raise ProductInvariantViolation(
                "Work must contain exactly one documentation target, Code Proposal, or legacy Code Contract"
            )
        expected_plan_targets = ()
        if artifact is not None:
            if (
                artifact.source_baseline_id != baseline.id
                or artifact.source_revision != baseline.repository_revision
            ):
                raise ProductInvariantViolation(
                    "Artifact Target Proposal is stale against the current Source Baseline"
                )
            expected_plan_targets = (
                ProductionPlanArtifactTarget(
                    path=artifact.path,
                    operation=PlannedArtifactOperation(artifact.operation.value),
                ),
            )
        if change_proposal is not None:
            if (
                plan.change_proposal != change_proposal
                or change_proposal.engineering_resource_id != resource.id
                or change_proposal.repository_identity != resource.repository_identity
                or change_proposal.source_baseline_id != baseline.id
                or change_proposal.source_ref != baseline.repository_ref
                or change_proposal.source_revision != baseline.repository_revision
            ):
                raise ProductInvariantViolation(
                    "Code Change Proposal is stale against the current Source Baseline"
                )
            change_contract = self._admit_change_contract(
                change_proposal,
                desired_outcome=(
                    work.desired_outcome or work.raw_user_requirement.strip()
                ),
                constraints=work.constraints,
            )
            plan = self.planning.propose(
                ProductionPlanningRequest(
                    work_id=work.id,
                    target_kind=ProductionTargetKind.CODE_WORK,
                    admitted_requirement=work.raw_user_requirement,
                    desired_outcome=(
                        work.desired_outcome or work.raw_user_requirement.strip()
                    ),
                    production_objective=(
                        work.production_objective or work.desired_outcome or ""
                    ),
                    change_contract=change_contract,
                    constraints=work.constraints,
                    verification_expectation=work.verification_expectation or "",
                    engineering_scope_summary=scope.summary,
                    engineering_resource_id=resource.id,
                    repository_identity=resource.repository_identity,
                    source_baseline_id=baseline.id,
                    source_revision=baseline.repository_revision,
                    context_references=tuple(
                        item.repository_relative_path
                        for item in resource.context_references
                    ),
                )
            )
            if plan.fit_classification is not OnePwuFitClassification.ONE_PWU_FIT:
                raise ProductInvariantViolation(
                    "Admitted Code Change Contract did not produce a one-PWU Plan"
                )
        if change_contract is not None and (
            change_contract.engineering_resource_id != resource.id
            or change_contract.repository_identity != resource.repository_identity
            or change_contract.source_baseline_id != baseline.id
            or change_contract.source_revision != baseline.repository_revision
            or change_contract.desired_outcome
            != (work.desired_outcome or work.raw_user_requirement.strip())
            or change_contract.constraints != work.constraints
        ):
            raise ProductInvariantViolation(
                "Code Change Contract no longer matches the admitted Work authority envelope"
            )
        if (
            plan.desired_outcome
            != (work.desired_outcome or work.raw_user_requirement.strip())
            or plan.objective
            != (work.production_objective or work.desired_outcome or "")
            or plan.target_kind
            is not (
                ProductionTargetKind.CODE_WORK
                if change_contract is not None
                else ProductionTargetKind.DOCUMENTATION_WORK
            )
            or plan.artifact_targets != expected_plan_targets
            or plan.change_contract != change_contract
            or plan.inherited_constraints != work.constraints
            or plan.verification_approach
            != (work.verification_expectation or "")
            or plan.engineering_resource_id != resource.id
            or plan.repository_identity != resource.repository_identity
            or plan.source_baseline_id != baseline.id
            or plan.source_revision != baseline.repository_revision
        ):
            raise ProductInvariantViolation(
                "Production Plan no longer matches the admitted Work authority envelope"
            )
        authority_lineage = tuple(
            (
                *work_reality_references,
                f"engineering-scope:{scope.id}",
                f"engineering-resource:{resource.id}",
                f"human-authority:{authority_identity}",
            )
        )
        ecf_references = (
            f"engineering-resource:{resource.id}",
            f"repository:{resource.repository_identity}",
            f"source-baseline:{baseline.id}@{baseline.repository_revision}",
        )
        decision_reference = f"work-admission:{work.id}:{authority_identity}"
        if artifact is not None:
            verification_obligation = (
                work.verification_expectation
                or "Verify the admitted artifact against independent repository Reality"
            )
            artifact_contract = ArtifactContract(
                engineering_resource_id=resource.id,
                repository_identity=resource.repository_identity,
                source_baseline_id=baseline.id,
                source_revision=baseline.repository_revision,
                artifact_path=artifact.path,
                operation=ArtifactOperation(artifact.operation.value),
                constraints=work.constraints,
                expected_outcome=work.desired_outcome or work.raw_user_requirement.strip(),
                verification_obligation=verification_obligation,
            )
            objective = self._artifact_objective(artifact_contract)
            horizon = ProductionHorizon.DOCUMENTATION
            task_contract = default_task_contract_builder().build(
                TaskContractRequest(
                    activity=EngineeringActivity.FEATURE_DELIVERY,
                    objective=objective,
                    scope=(f"{artifact.operation.value}:{artifact.path}",),
                    constraints=work.constraints,
                    acceptance_meaning=(verification_obligation,),
                    out_of_scope=(
                        f"Any repository path other than {artifact.path}",
                    ),
                    authority_lineage=authority_lineage,
                    work_reality_references=tuple(work_reality_references),
                    ecf_references=ecf_references,
                    semantic_facts=semantic_facts,
                    decision_reference=decision_reference,
                )
            )
            completion_contract = CompletionContract(
                required_outputs=(artifact.path,),
                required_changes=(artifact.path,),
                verification_obligations=(verification_obligation,),
                semantic_fact_obligations=semantic_facts,
                task_contract=task_contract,
                artifact_contract=artifact_contract,
                production_plan=plan,
            )
        else:
            assert change_contract is not None
            objective = self._code_change_objective(change_contract)
            horizon = ProductionHorizon.CODE
            exact_paths = tuple(target.path for target in change_contract.exact_targets)
            scope_entries = tuple(
                f"{target.operation.value}:{target.path}"
                for target in change_contract.exact_targets
            ) + tuple(
                f"BOUNDED_AREA:{area}" for area in change_contract.allowed_areas
            )
            task_contract = default_task_contract_builder().build(
                TaskContractRequest(
                    activity=EngineeringActivity.FEATURE_DELIVERY,
                    objective=objective,
                    scope=scope_entries,
                    constraints=work.constraints,
                    acceptance_meaning=change_contract.verification_identities,
                    out_of_scope=tuple(change_contract.forbidden_areas)
                    + (
                        "Any repository path outside the admitted exact targets or bounded areas",
                    ),
                    authority_lineage=authority_lineage,
                    work_reality_references=tuple(work_reality_references),
                    ecf_references=ecf_references,
                    semantic_facts=semantic_facts,
                    decision_reference=decision_reference,
                )
            )
            completion_contract = CompletionContract(
                required_outputs=exact_paths,
                required_changes=exact_paths,
                verification_obligations=change_contract.verification_identities,
                semantic_fact_obligations=semantic_facts,
                task_contract=task_contract,
                change_contract=change_contract,
                production_plan=plan,
            )
        spine = self.runtime.create_initial_runtime_spine(
            InitialRunRequest(
                intent_ref=f"work:{work.id}",
                goal=work.desired_outcome or work.refined_title or "Governed Work",
                production_horizon=horizon,
                initial_work_unit_objective=objective,
                completion_contract=completion_contract,
            )
        )
        timestamp = datetime.now(UTC)
        governance_id = uuid5(
            NAMESPACE_URL,
            f"spg:work-admission:{work.id}:{scope.fingerprint}:{authority_identity}",
        )
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            current = self._required_work(product, work_id)
            if product.runtime_binding(work_id) is not None:
                unit_of_work.rollback()
                return self.get_work(work_id)
            runtime.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": "ADMIT_WORK_DRAFT",
                    "authority_identity": authority_identity,
                    "subject_type": "PRODUCT_WORK",
                    "subject_identity": str(work.id),
                    "scope": {
                        "engineering_scope_id": str(scope.id),
                        "scope_fingerprint": scope.fingerprint,
                        "resource_id": str(resource.id),
                        "production_run_id": str(spine.run.id),
                        "work_unit_id": str(spine.work_unit.id),
                        "production_plan_proposal_id": str(plan.proposal_id),
                        "production_plan_fingerprint": self._fingerprint(
                            plan.model_dump(mode="json")
                        ),
                        "production_plan_fit": plan.fit_classification.value,
                        "source_change_proposal_id": (
                            None
                            if change_proposal is None
                            else str(change_proposal.proposal_id)
                        ),
                        "source_change_proposal_fingerprint": (
                            None
                            if change_proposal is None
                            else change_proposal.proposal_fingerprint
                        ),
                    },
                    "rationale": rationale,
                    "created_at": timestamp,
                }
            )
            product.insert_runtime_binding(
                {
                    "id": uuid4(),
                    "work_id": current.id,
                    "cycle_number": 1,
                    "steering_step_id": None,
                    "steering_decision_id": None,
                    "work_reality_revision_id": (
                        current.current_work_reality_revision_id
                    ),
                    "engineering_scope_id": scope.id,
                    "resource_id": resource.id,
                    "production_run_id": spine.run.id,
                    "plan_revision_id": spine.plan_revision.id,
                    "work_unit_id": spine.work_unit.id,
                    "governance_record_id": governance_id,
                    "admitted_by": authority_identity,
                    "condition": ProductionCycleBindingCondition.ADMITTED.value,
                    "created_at": timestamp,
                }
            )
            product.set_scope_condition(
                scope.id,
                EngineeringScopeCondition.ADMITTED,
                updated_at=timestamp,
            )
            product.update_work(
                current.id,
                {
                    "condition": WorkCondition.READY.value,
                    "production_plan_proposal": plan.model_dump(mode="json"),
                    "updated_at": timestamp,
                },
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    approve_work_draft = approve_work

    def _approve_long_lived_work(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
        rationale: str | None,
    ) -> WorkProjection:
        """Admit a Work authority envelope without admitting production."""

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            if work.mode is not WorkMode.LONG_LIVED_STEERING:
                raise ProductInvariantViolation("Work is not a long-lived Steering Work")
            if work.condition is WorkCondition.READY:
                return self._projection(product, work)
            if work.condition is not WorkCondition.AWAITING_APPROVAL:
                raise ProductInvariantViolation(
                    "Long-lived Work must await Human approval before Steering admission"
                )
            if not (work.desired_outcome or "").strip():
                raise ProductInvariantViolation(
                    "Long-lived Work requires a governed desired outcome"
                )
            scope = product.scope_for_work(work_id)
            if scope is None:
                raise ProductInvariantViolation("Work has no Engineering Scope")
            proposed = tuple(
                item
                for item in scope.bindings
                if item.condition is ResourceBindingCondition.PROPOSED
            )
            self._require_mvp_scope(proposed)
            resource = product.resource(proposed[0].resource_id)
            if resource is None:
                raise ProductInvariantViolation("Scope Resource is missing")
            artifact = self._artifact_target(work)
            change_proposal = work.code_change_proposal
            plan = work.production_plan

        baseline = self.runtime.current_baseline(repository_identity=resource.repository_identity, repository_ref=resource.authoritative_ref)
        if (
            baseline.repository_identity != resource.repository_identity
            or baseline.repository_ref != resource.authoritative_ref
        ):
            raise ProductInvariantViolation(
                "Engineering Resource does not match current governed Baseline"
            )
        if artifact is not None and (
            artifact.source_baseline_id != baseline.id
            or artifact.source_revision != baseline.repository_revision
        ):
            raise ProductInvariantViolation(
                "Artifact Target Proposal is stale against the current Source Baseline"
            )
        if change_proposal is not None and (
            change_proposal.engineering_resource_id != resource.id
            or change_proposal.repository_identity != resource.repository_identity
            or change_proposal.source_baseline_id != baseline.id
            or change_proposal.source_ref != baseline.repository_ref
            or change_proposal.source_revision != baseline.repository_revision
        ):
            raise ProductInvariantViolation(
                "Code Change Proposal is stale against the current Source Baseline"
            )
        if artifact is not None and change_proposal is not None:
            raise ProductInvariantViolation(
                "Long-lived Work cannot mix production target proposal forms"
            )
        if plan is not None:
            expected_targets = (
                ()
                if artifact is None
                else (
                    ProductionPlanArtifactTarget(
                        path=artifact.path,
                        operation=PlannedArtifactOperation(artifact.operation.value),
                    ),
                )
            )
            expected_kind = (
                ProductionTargetKind.CODE_WORK
                if change_proposal is not None
                else ProductionTargetKind.DOCUMENTATION_WORK
            )
            if (
                plan.desired_outcome != work.desired_outcome
                or plan.objective != work.production_objective
                or plan.target_kind is not expected_kind
                or plan.artifact_targets != expected_targets
                or plan.change_proposal != change_proposal
                or plan.change_contract is not None
                or plan.inherited_constraints != work.constraints
                or plan.engineering_resource_id != resource.id
                or plan.repository_identity != resource.repository_identity
                or plan.source_baseline_id != baseline.id
                or plan.source_revision != baseline.repository_revision
            ):
                raise ProductInvariantViolation(
                    "Production proposal exceeds the long-lived Work authority envelope"
                )

        timestamp = datetime.now(UTC)
        governance_id = uuid5(
            NAMESPACE_URL,
            f"spg:long-lived-work-admission:{work_id}:{scope.fingerprint}:{authority_identity}",
        )
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            current = self._required_work(product, work_id)
            if current.condition is WorkCondition.READY:
                unit_of_work.rollback()
                return self.get_work(work_id)
            if current.condition is not WorkCondition.AWAITING_APPROVAL:
                raise ProductInvariantViolation(
                    "Long-lived Work admission Reality changed before approval"
                )
            runtime.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": "ADMIT_LONG_LIVED_WORK",
                    "authority_identity": authority_identity,
                    "subject_type": "PRODUCT_WORK",
                    "subject_identity": str(work_id),
                    "scope": {
                        "work_mode": current.mode.value,
                        "engineering_scope_id": str(scope.id),
                        "scope_fingerprint": scope.fingerprint,
                        "resource_id": str(resource.id),
                        "repository_identity": resource.repository_identity,
                        "repository_ref": resource.authoritative_ref,
                        "source_baseline_id": str(baseline.id),
                        "source_revision": baseline.repository_revision,
                        "desired_outcome": current.desired_outcome,
                        "constraints": list(current.constraints),
                        "artifact_target": (
                            None
                            if artifact is None
                            else artifact.model_dump(mode="json")
                        ),
                        "source_change_proposal_fingerprint": (
                            None
                            if change_proposal is None
                            else change_proposal.proposal_fingerprint
                        ),
                    },
                    "rationale": rationale,
                    "created_at": timestamp,
                }
            )
            product.set_scope_condition(
                scope.id,
                EngineeringScopeCondition.ADMITTED,
                updated_at=timestamp,
            )
            product.update_work(
                work_id,
                {"condition": WorkCondition.READY.value, "updated_at": timestamp},
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    def reject_work_draft(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
    ) -> WorkProjection:
        return self._record_draft_decision(
            work_id,
            authority_identity=authority_identity,
            decision_type="REJECT_WORK_DRAFT",
            condition=WorkCondition.REJECTED,
        )

    def request_work_refinement(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
    ) -> WorkProjection:
        return self._record_draft_decision(
            work_id,
            authority_identity=authority_identity,
            decision_type="REQUEST_WORK_REFINEMENT",
            condition=WorkCondition.NEEDS_REFINEMENT,
        )

    reject_work = reject_work_draft
    request_refinement = request_work_refinement

    def get_work(self, work_id: UUID) -> WorkProjection:
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            work = self._required_work(store, work_id)
            return self._projection(store, work)

    def retry_failed_production(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
    ) -> WorkProjection:
        """Create a successor Attempt for a failed Provider execution."""

        if not authority_identity.strip():
            raise ProductInvariantViolation(
                "production retry requires a Human authority identity"
            )
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            binding = self._runtime_binding_for_current_context(product, work_id)
            if binding is None:
                raise ProductInvariantViolation(
                    "production retry requires a current Runtime binding"
                )
            facts = product.runtime_summary(binding)
            if facts.attempt_id is None or facts.dispatch_id is None:
                raise ProductInvariantViolation(
                    "production retry requires a completed failed dispatch"
                )
            dispatch = runtime.execution_dispatch(facts.dispatch_id)
            report = runtime.provider_execution_report(facts.dispatch_id)
            attempt = runtime.attempt(facts.attempt_id)
            if dispatch is None or report is None or attempt is None:
                raise ProductInvariantViolation(
                    "production retry lineage is incomplete"
                )
            if (
                report.outcome.value not in {"FAILURE", "UNKNOWN"}
                or facts.runtime_commit_id is not None
                or facts.candidate_id is not None
                or facts.authorization_id is not None
            ):
                raise ProductInvariantViolation(
                    "production retry requires a failed dispatch without an "
                    "authoritative Candidate or Runtime commit"
                )
            if attempt.generation > 3:
                raise ProductInvariantViolation(
                    "production retry recovery budget is exhausted"
                )

        self.runtime.retry_attempt(facts.attempt_id)
        return self.get_work(work.id)

    def orchestration_reality_fingerprint(self, work_id: UUID) -> str:
        """Fingerprint persisted facts used only to detect actual step progress."""

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            binding = self._runtime_binding_for_current_context(product, work_id)
            if binding is None:
                facts = RuntimeFactSummary()
            else:
                facts = product.runtime_summary(binding)
                preparation = (
                    None
                    if facts.attempt_id is None
                    else runtime.attempt_preparation(facts.attempt_id)
                )
                preparation_identity = (
                    None if preparation is None else str(preparation.attempt_id)
                )
            if binding is None:
                preparation_identity = None
        return self._fingerprint(
            {
                "work_condition": work.condition.value,
                "runtime_facts": facts.model_dump(mode="json"),
                "attempt_preparation_identity": preparation_identity,
            }
        )

    def list_works(self, goal_id: UUID | None = None) -> tuple[WorkProjection, ...]:
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            return tuple(
                self._projection(store, work)
                for work in store.list_works(goal_id=goal_id)
            )

    def discard_pre_work(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
    ) -> None:
        identity = authority_identity.strip()
        if not identity:
            raise ProductInvariantViolation("Human authority identity is required")
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            interactions = InteractionStore(unit_of_work.session)
            work = product.work(work_id, for_update=True)
            if work is None:
                raise ProductRecordNotFound(f"Work not found: {work_id}")
            if work.condition is not WorkCondition.PRE_WORK:
                raise ProductInvariantViolation(
                    "Only PRE_WORK may be discarded"
                )
            interaction = interactions.interaction_for_work(work_id)
            if interaction is None:
                raise ProductInvariantViolation(
                    "PRE_WORK has no durable Interaction context"
                )
            interactions.archive_interaction(
                interaction.id,
                expected_work_id=work_id,
                updated_by=identity,
                updated_at=timestamp,
            )
            product.update_work(
                work_id,
                {
                    "condition": WorkCondition.DISCARDED.value,
                    "updated_at": timestamp,
                },
            )
            unit_of_work.commit()

    def get_goal_projection(self, goal_id: UUID) -> GoalProjection:
        goal = self.get_goal(goal_id)
        works = self.list_works(goal_id=goal_id)
        counts: dict[WorkStatus, int] = {}
        for work in works:
            counts[work.status] = counts.get(work.status, 0) + 1
        return GoalProjection(
            goal=goal,
            work_count=len(works),
            works_by_status=counts,
            recent_works=works[:10],
            needs_attention_count=sum(
                item.status in {WorkStatus.NEEDS_ATTENTION, WorkStatus.AWAITING_APPROVAL}
                for item in works
            ),
        )

    def advance_work(self, work_id: UUID) -> WorkProjection:
        """Perform at most one currently legal governed production action."""

        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime_store = RuntimeStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            binding = self._runtime_binding_for_current_context(product, work_id)
            if binding is None:
                return self._projection(product, work)
            resource = product.resource(binding.resource_id)
            if resource is None:
                raise ProductInvariantViolation("Bound Engineering Resource is missing")
            summary = product.runtime_summary(binding)
            work_unit = runtime_store.work_unit(binding.work_unit_id)
            if work_unit is None:
                raise ProductInvariantViolation("Bound governed PWU is missing")

        if summary.runtime_commit_id is not None:
            if self.production_recorder is not None:
                self.production_recorder.record_authorized_work(work_id)
            return self.get_work(work_id)
        if summary.attempt_id is None:
            self.runtime.create_initial_attempt(binding.work_unit_id)
            return self.get_work(work_id)

        with self.database.unit_of_work() as unit_of_work:
            runtime_store = RuntimeStore(unit_of_work.session)
            package = runtime_store.latest_context_package(binding.work_unit_id)
            preparation = runtime_store.attempt_preparation(summary.attempt_id)
        if preparation is None:
            repository_path = Path(resource.location_ref).resolve()
            if package is None:
                package = self.preparation.assemble_context_package(
                    binding.work_unit_id,
                    repository_path,
                    ContextPackageRequest(
                        artifacts=tuple(
                            ContextArtifactSelection(
                                semantic_role=item.semantic_role,
                                repository_relative_path=item.repository_relative_path,
                            )
                            for item in resource.context_references
                        )
                    ),
                )
            self.preparation.prepare_attempt(
                summary.attempt_id,
                package.id,
                self.executor_binding,
                repository_path,
                self.workspace_root,
            )
            return self.get_work(work_id)

        if summary.dispatch_id is None:
            if self.executor is None:
                return self.get_work(work_id)
            self.execution.dispatch_and_observe(summary.attempt_id, self.executor)
            return self.get_work(work_id)

        if summary.observation_id is None:
            terminal_result = getattr(self.executor, "terminal_result", None)
            if callable(terminal_result) and summary.dispatch_id is not None:
                provider_result = terminal_result(summary.attempt_id)
                if provider_result is not None:
                    self.execution.complete_existing_dispatch(
                        summary.dispatch_id, provider_result
                    )
            return self.get_work(work_id)
        if summary.completion_id is None:
            if (
                work_unit.completion_contract.requires_observed_production_result
                and not summary.artifact_paths
            ):
                return self.get_work(work_id)
            self.completion.evaluate_observation(summary.observation_id)
            return self.get_work(work_id)
        if summary.completion_outcome != "PRODUCED":
            return self.get_work(work_id)

        if summary.proposed_snapshot_id is None:
            self.verification.create_proposed_snapshot(summary.completion_id)
            return self.get_work(work_id)

        required = work_unit.completion_contract.verification_obligations
        verified = set(summary.verification_obligations)
        missing = next((item for item in required if item not in verified), None)
        if missing is not None:
            if self.verifier is None:
                return self.get_work(work_id)
            self.verification.verify_obligation(
                summary.proposed_snapshot_id,
                missing,
                self.verifier,
            )
            return self.get_work(work_id)

        if summary.admissibility_id is None:
            self.verification.evaluate_admissibility(summary.proposed_snapshot_id)
            return self.get_work(work_id)
        if summary.admissibility_outcome != ProductionAdmissibilityOutcome.ADMISSIBLE.value:
            return self.get_work(work_id)

        if summary.candidate_id is None:
            with self.database.unit_of_work() as unit_of_work:
                current = RuntimeStore(unit_of_work.session).work_unit(
                    binding.work_unit_id
                )
            if current is None:
                raise ProductInvariantViolation("Governed PWU disappeared")
            self.governance.seal_candidate(
                CandidateSealRequest(
                    proposed_snapshot_id=summary.proposed_snapshot_id,
                    production_admissibility_id=summary.admissibility_id,
                    expected_work_unit_version=current.version,
                )
            )
            return self.get_work(work_id)

        if summary.authorization_id is None:
            return self.get_work(work_id)
        if summary.integration_effect_id is None:
            self.integration.integrate_repository_candidate(
                RepositoryIntegrationRequest(
                    candidate_id=summary.candidate_id,
                    candidate_fingerprint=summary.candidate_fingerprint or "",
                    human_authorization_id=summary.authorization_id,
                )
            )
            return self.get_work(work_id)
        if summary.integration_state != "CONVERGED":
            return self.get_work(work_id)

        self.runtime_commit.commit_runtime_candidate(
            RuntimeCommitRequest(
                candidate_id=summary.candidate_id,
                candidate_fingerprint=summary.candidate_fingerprint or "",
                human_authorization_id=summary.authorization_id,
                repository_integration_effect_id=summary.integration_effect_id,
            )
        )
        if self.production_recorder is not None:
            self.production_recorder.record_authorized_work(work_id)
        return self.get_work(work_id)

    def list_attention(
        self,
        *,
        work_id: UUID | None = None,
    ) -> tuple[AttentionItem, ...]:
        projections = (
            (self.get_work(work_id),)
            if work_id is not None
            else self.list_works()
        )
        items: list[AttentionItem] = []
        for projection in projections:
            if projection.status is WorkStatus.NEEDS_REFINEMENT:
                questions = (
                    ()
                    if projection.production_plan is None
                    else projection.production_plan.unresolved_questions
                )
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:work-refinement-attention:{projection.work_id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.WORK_REFINEMENT_REQUIRED,
                        decision="Refine this Work before production admission.",
                        reason=(
                            " ".join(questions)
                            or "The current Work cannot form a trustworthy single-PWU plan."
                        ),
                        available_actions=(),
                        recommended_action=None,
                        governed_subject_ref=f"work:{projection.work_id}",
                    )
                )
                continue
            if projection.status is WorkStatus.AWAITING_APPROVAL:
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:work-draft-attention:{projection.work_id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.WORK_DRAFT_APPROVAL,
                        decision="Admit this governed Work draft?",
                        reason="Draft generation does not create execution authority.",
                        available_actions=(
                            AttentionAction.APPROVE,
                            AttentionAction.REJECT,
                            AttentionAction.REQUEST_REFINEMENT,
                        ),
                        recommended_action=AttentionAction.APPROVE,
                        governed_subject_ref=f"work:{projection.work_id}",
                    )
                )
                continue
            with self.database.unit_of_work() as unit_of_work:
                interaction_store = InteractionStore(unit_of_work.session)
                product_store = ProductStore(unit_of_work.session)
                runtime_store = RuntimeStore(unit_of_work.session)
                focused_interaction = interaction_store.interaction_for_work(
                    projection.work_id
                )
                evolution_assessment = (
                    None
                    if focused_interaction is None
                    else interaction_store.latest_assessment(focused_interaction.id)
                )
                admitted_evolution = (
                    None
                    if evolution_assessment is None
                    else product_store.work_reality_revision_for_assessment(
                        evolution_assessment.id
                    )
                )
                evolution_decisions = (
                    []
                    if evolution_assessment is None
                    else runtime_store.governance_for_subject(
                        f"interaction-assessment:{evolution_assessment.id}"
                    )
                )
            if (
                focused_interaction is not None
                and evolution_assessment is not None
                and evolution_assessment.candidate_change is not None
                and admitted_evolution is None
                and not evolution_decisions
                and evolution_assessment.basis_work_revision_id
                == projection.current_work_reality_revision_id
            ):
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:work-revision-attention:{evolution_assessment.id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.WORK_REVISION_APPROVAL,
                        decision="Admit this interpreted change as the next Work Reality revision?",
                        reason=(
                            "Latest Human input is candidate meaning, not Work Truth. "
                            f"Impact: {evolution_assessment.impact_disposition.value}."
                        ),
                        available_actions=(
                            AttentionAction.APPROVE,
                            AttentionAction.REJECT,
                            AttentionAction.REQUEST_REFINEMENT,
                        ),
                        recommended_action=None,
                        governed_subject_ref=(
                            f"interaction-assessment:{evolution_assessment.id}"
                        ),
                        interaction_id=focused_interaction.id,
                        interaction_assessment_id=evolution_assessment.id,
                        expected_work_reality_revision_id=(
                            evolution_assessment.basis_work_revision_id
                        ),
                    )
                )
                continue
            with self.database.unit_of_work() as unit_of_work:
                steering = SteeringStore(unit_of_work.session)
                runtime = RuntimeStore(unit_of_work.session)
                plan = steering.plan_for_work(projection.work_id)
                revision = None if plan is None else steering.active_revision(plan.id)
                decision = (
                    None if revision is None else steering.latest_decision(revision.id)
                )
                semantic_result = (
                    None
                    if decision is None
                    else steering.latest_semantic_result_for_step(
                        decision.current_step_id
                    )
                )
                proposal_review_resolved = bool(
                    decision is not None
                    and decision.attention_reason
                    is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                    and semantic_result is not None
                    and any(
                        record.decision_type
                        in {
                            "APPROVE_GUIDED_PRODUCTION_PROPOSAL",
                            "REFINE_GUIDED_PRODUCTION_PROPOSAL",
                        }
                        and record.scope.get("semantic_result_id")
                        == str(semantic_result.id)
                        for record in runtime.governance_for_subject(
                            str(projection.work_id)
                        )
                    )
                )
            if (
                decision is not None
                and self._decision_matches_work_revision(decision, projection.current_work_reality_revision_id)
                and decision.steering_outcome is SteeringOutcome.HUMAN_ATTENTION
                and decision.attention_reason is not None
                and not proposal_review_resolved
            ):
                action_title, action_reason, action_recommendation, action_impact = (
                    _HUMAN_ACTION_COPY[decision.attention_reason]
                )
                conversation_prompt = (
                    semantic_result.unresolved_questions[0]
                    if decision.attention_reason
                    is not SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                    and semantic_result is not None
                    and semantic_result.unresolved_questions
                    else None
                )
                implementation_prerequisite_missing = False
                if (
                    decision.attention_reason
                    is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                    and semantic_result is not None
                    and semantic_result.proposed_production is not None
                    and semantic_result.proposed_production.target_kind
                    is ProductionTargetKind.CODE_WORK
                ):
                    from spg.application.guided_design import (
                        GuidedDesignApplicationService,
                    )

                    guided = GuidedDesignApplicationService(self.database)
                    implementation_prerequisite_missing = bool(
                        guided.get_optional(projection.work_id) is not None
                        and not guided.approved_design_artifact_references(
                            projection.work_id
                        )
                    )
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:steering-attention:{decision.id}",
                        ),
                        work_id=projection.work_id,
                        kind=(
                            AttentionKind.PRODUCTION_PROPOSAL_REVIEW
                            if decision.attention_reason
                            is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                            else AttentionKind.STEERING_DECISION_REQUIRED
                        ),
                        decision=(
                            "Answer the current Work question"
                            if conversation_prompt is not None
                            else action_title
                        ),
                        reason=conversation_prompt or action_reason,
                        available_actions=(
                            (
                                AttentionAction.REQUEST_REFINEMENT,
                            )
                            if implementation_prerequisite_missing
                            else (
                                AttentionAction.APPROVE,
                                AttentionAction.REQUEST_REFINEMENT,
                            )
                            if decision.attention_reason
                            is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                            else ()
                        ),
                        recommended_action=(
                            AttentionAction.REQUEST_REFINEMENT
                            if implementation_prerequisite_missing
                            else AttentionAction.APPROVE
                            if decision.attention_reason
                            is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
                            else None
                        ),
                        governed_subject_ref=f"steering-decision:{decision.id}",
                        steering_reason=decision.attention_reason,
                        recommendation=(
                            semantic_result.human_attention_recommendation
                            if conversation_prompt is not None
                            and semantic_result.human_attention_recommendation
                            else action_recommendation
                        ),
                        conversation_prompt=conversation_prompt,
                        alternatives=(),
                        trade_offs=(),
                        expected_impact=action_impact,
                        reality_refs=decision.reality_refs,
                        steering_plan_revision_id=(
                            decision.steering_plan_revision_id
                        ),
                        steering_step_id=decision.current_step_id,
                    )
                )
                continue
            with self.database.unit_of_work() as unit_of_work:
                store = ProductStore(unit_of_work.session)
                binding = self._runtime_binding_for_current_context(
                    store, projection.work_id
                )
                if (
                    binding is not None
                    and binding.work_reality_revision_id
                    != projection.current_work_reality_revision_id
                ):
                    binding = None
                summary = (
                    RuntimeFactSummary()
                    if binding is None
                    else store.runtime_summary(binding)
                )
            if summary.candidate_id is not None and summary.authorization_id is None:
                items.append(
                    AttentionItem(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"spg:candidate-attention:{summary.candidate_id}",
                        ),
                        work_id=projection.work_id,
                        kind=AttentionKind.CANDIDATE_AUTHORIZATION,
                        decision="Authorize exact sealed Candidate integration?",
                        reason="Repository integration requires exact Human Authority.",
                        available_actions=(AttentionAction.AUTHORIZE,),
                        recommended_action=None,
                        governed_subject_ref=f"baseline-candidate:{summary.candidate_id}",
                    )
                )
            # A technical blocker with no executable Human choice belongs to a
            # Watt recovery/operator path, not the Human Attention surface.
        return tuple(items)

    def resolve_attention(
        self,
        attention_id: UUID,
        request: AttentionResolutionRequest,
    ) -> WorkProjection:
        attention = next(
            (item for item in self.list_attention() if item.id == attention_id),
            None,
        )
        if attention is None:
            raise ProductRecordNotFound(f"Attention not found: {attention_id}")
        if request.action not in attention.available_actions:
            raise ProductInvariantViolation("Requested Attention action is not allowed")
        if attention.kind is AttentionKind.WORK_DRAFT_APPROVAL:
            if request.action is AttentionAction.APPROVE:
                return self.approve_work(
                    attention.work_id,
                    authority_identity=request.authority_identity,
                    rationale=request.rationale,
                )
            if request.action is AttentionAction.REJECT:
                return self.reject_work_draft(
                    attention.work_id,
                    authority_identity=request.authority_identity,
                )
            return self.request_work_refinement(
                attention.work_id,
                authority_identity=request.authority_identity,
            )

        if attention.kind is AttentionKind.WORK_REVISION_APPROVAL:
            if (
                attention.interaction_id is None
                or attention.interaction_assessment_id is None
                or attention.expected_work_reality_revision_id is None
            ):
                raise ProductInvariantViolation(
                    "Work revision Attention lost its exact governed basis"
                )
            with self.database.unit_of_work() as unit_of_work:
                assessment = InteractionStore(unit_of_work.session).assessment(
                    attention.interaction_assessment_id
                )
            if assessment is None:
                raise ProductInvariantViolation(
                    "Work revision Attention lost its assessment"
                )
            return self.decide_interaction_work_revision(
                attention.interaction_id,
                assessment_id=assessment.id,
                basis_fingerprint=assessment.basis_fingerprint,
                expected_previous_revision_id=(
                    attention.expected_work_reality_revision_id
                ),
                action=request.action,
                authority_identity=request.authority_identity,
                rationale=request.rationale,
            )

        if attention.kind is AttentionKind.PRODUCTION_PROPOSAL_REVIEW:
            if (
                attention.steering_step_id is None
                or attention.steering_plan_revision_id is None
            ):
                raise ProductInvariantViolation(
                    "Production proposal review lost its exact Steering basis"
                )
            timestamp = datetime.now(UTC)
            with self.database.unit_of_work() as unit_of_work:
                product = ProductStore(unit_of_work.session)
                steering = SteeringStore(unit_of_work.session)
                runtime = RuntimeStore(unit_of_work.session)
                work = self._required_work(product, attention.work_id)
                result = steering.latest_semantic_result_for_step(
                    attention.steering_step_id
                )
                if result is None or result.proposed_production is None:
                    raise ProductInvariantViolation(
                        "Production proposal review lost its governed semantic result"
                    )
                decision_type = (
                    "APPROVE_GUIDED_PRODUCTION_PROPOSAL"
                    if request.action is AttentionAction.APPROVE
                    else "REFINE_GUIDED_PRODUCTION_PROPOSAL"
                )
                governance_id = uuid5(
                    NAMESPACE_URL,
                    f"spg:guided-production-review:{result.id}:{decision_type}",
                )
                existing = next(
                    (
                        record
                        for record in runtime.governance_for_subject(str(work.id))
                        if record.id == governance_id
                    ),
                    None,
                )
                if existing is None:
                    runtime.insert_governance(
                        {
                            "id": governance_id,
                            "decision_type": decision_type,
                            "authority_identity": request.authority_identity,
                            "subject_type": "GUIDED_PRODUCTION_PROPOSAL",
                            "subject_identity": str(work.id),
                            "scope": {
                                "work_id": str(work.id),
                                "work_reality_revision_id": (
                                    None
                                    if work.current_work_reality_revision_id is None
                                    else str(work.current_work_reality_revision_id)
                                ),
                                "steering_plan_revision_id": str(
                                    attention.steering_plan_revision_id
                                ),
                                "steering_step_id": str(attention.steering_step_id),
                                "semantic_result_id": str(result.id),
                                "production_proposal": (
                                    result.proposed_production.model_dump(mode="json")
                                ),
                            },
                            "rationale": request.rationale,
                            "created_at": timestamp,
                        }
                    )
                unit_of_work.commit()
            if request.action is AttentionAction.REQUEST_REFINEMENT:
                from spg.application.guided_design import (
                    GuidedDesignApplicationService,
                )
                with self.database.unit_of_work() as uow:
                    current_step = SteeringStore(uow.session).step(attention.steering_step_id)
                if current_step is not None and current_step.design_issue_key is not None:
                    GuidedDesignApplicationService(self.database).reopen_issue(
                        attention.work_id,
                        current_step.design_issue_key,
                        rationale=(
                            request.rationale
                            or "Human requested refinement of the production proposal."
                        ),
                        reality_refs=(
                            RealityReference(
                                kind=RealityReferenceKind.GOVERNANCE_DECISION,
                                identity=governance_id,
                            ),
                        ),
                    )
                else:
                    from spg.application.steering import SteeringApplicationService
                    from spg.domain.steering import (
                        ReviseSteeringPlanRequest, SteeringStepSpec,
                        SteeringStepState, SteeringStepType,
                    )

                    current_plan = SteeringApplicationService(self.database).reconstruct(
                        attention.work_id
                    )
                    SteeringApplicationService(self.database).revise_plan(
                        ReviseSteeringPlanRequest(
                            steering_plan_id=current_plan.steering_plan_id,
                            superseded_revision_id=attention.steering_plan_revision_id,
                            rationale=(
                                request.rationale
                                or "Refine the bounded production proposal before admission."
                            ),
                            reality_refs=(
                                RealityReference(
                                    kind=RealityReferenceKind.GOVERNANCE_DECISION,
                                    identity=governance_id,
                                ),
                            ),
                            steps=(
                                SteeringStepSpec(
                                    type=SteeringStepType.DESIGN,
                                    objective="Refine the exact implementation scope",
                                    completion_condition="A corrected code proposal is reviewable",
                                    state=SteeringStepState.CURRENT,
                                ),
                                SteeringStepSpec(
                                    type=SteeringStepType.PRODUCE,
                                    objective="Implement the admitted code change",
                                    completion_condition="The code change reaches trusted Runtime Commit",
                                ),
                                SteeringStepSpec(
                                    type=SteeringStepType.VERIFY_ACCEPT,
                                    objective="Verify the implemented change",
                                    completion_condition="Governed evidence supports the Work outcome",
                                ),
                                SteeringStepSpec(
                                    type=SteeringStepType.COMPLETE,
                                    objective="Complete the Work outcome",
                                    completion_condition="The requested behavior is truthfully satisfied",
                                ),
                            ),
                        )
                    )
            return self.get_work(attention.work_id)

        if attention.kind is AttentionKind.CANDIDATE_AUTHORIZATION:
            with self.database.unit_of_work() as unit_of_work:
                product = ProductStore(unit_of_work.session)
                binding = self._runtime_binding_for_current_context(
                    product, attention.work_id
                )
                if binding is None:
                    raise ProductInvariantViolation("Attention has no Runtime lineage")
                summary = product.runtime_summary(binding)
            if summary.candidate_id is None:
                raise ProductInvariantViolation("Candidate Attention lost its subject")
            if self.candidate_authorization_guard is not None:
                self.candidate_authorization_guard(attention.work_id, summary.candidate_id)
            candidate = self.governance.candidate(summary.candidate_id)
            self.governance.authorize_candidate(
                HumanAuthorizationRequest(
                    authority_identity=request.authority_identity,
                    candidate_id=candidate.id,
                    candidate_fingerprint=candidate.fingerprint,
                    scope=CandidateAuthorizationScope(
                        repository_identity=candidate.repository_identity,
                        target_authoritative_ref=candidate.target_authoritative_ref,
                        expected_source_repository_revision=(
                            candidate.expected_source_repository_revision
                        ),
                        proposed_repository_revision=candidate.proposed_commit_identity,
                    ),
                    rationale=request.rationale,
                )
            )
            return self.get_work(attention.work_id)
        raise ProductInvariantViolation("Blocked Reality cannot be overridden")

    def get_work_result(self, work_id: UUID) -> WorkResultProjection:
        projection = self.get_work(work_id)
        actionable_attention = any(
            item.available_actions
            for item in self.list_attention(work_id=work_id)
        )
        with self.database.unit_of_work() as unit_of_work:
            store = ProductStore(unit_of_work.session)
            binding = store.runtime_binding(work_id)
            if (
                binding is not None
                and binding.work_reality_revision_id
                != projection.current_work_reality_revision_id
            ):
                binding = None
            summary = RuntimeFactSummary() if binding is None else store.runtime_summary(binding)
        verification = tuple(
            f"{obligation}: {result}"
            for obligation, result in zip(
                summary.verification_obligations,
                summary.verification_results,
                strict=False,
            )
        )
        repository_state = None
        if summary.runtime_commit_id is not None:
            repository_state = "TRUSTED_BASELINE_ADVANCED"
        elif summary.integration_state is not None:
            repository_state = f"REPOSITORY_INTEGRATION_{summary.integration_state}"
        elif summary.candidate_id is not None:
            repository_state = "SEALED_CANDIDATE"
        blocker = None
        if projection.status is not WorkStatus.COMPLETED:
            blocker = projection.what_happens_next
        return WorkResultProjection(
            work_id=work_id,
            status=projection.status,
            desired_outcome=projection.desired_outcome,
            produced_artifacts=summary.artifact_paths,
            verification_summary=verification,
            repository_state=repository_state,
            trusted_result=summary.runtime_commit_id is not None,
            remaining_blocker_or_risk=blocker,
            human_attention_required=(
                projection.human_attention_required or actionable_attention
            ),
        )

    @staticmethod
    def _decision_matches_work_revision(decision, revision_id: UUID | None) -> bool:
        """Historical semantic attention cannot block a newly admitted Work basis."""
        return revision_id is None or any(
            ref.kind is RealityReferenceKind.WORK_REALITY_REVISION
            and ref.identity == revision_id
            for ref in decision.reality_refs
        )

    def _projection(
        self,
        store: ProductStore,
        work: WorkRecord,
    ) -> WorkProjection:
        scope = store.scope_for_work(work.id)
        steering = SteeringStore(store.session)
        steering_plan = steering.plan_for_work(work.id)
        current_steering_step = None
        latest_steering_decision = None
        if steering_plan is not None:
            revision = steering.active_revision(steering_plan.id)
            if revision is not None:
                current_steering_step = next(
                    (
                        item
                        for item in steering.steps(revision.id)
                        if item.state.value == "CURRENT"
                    ),
                    None,
                )
                latest_steering_decision = steering.latest_decision(revision.id)
        current_cycle_binding = self._runtime_binding_for_current_context(
            store, work.id
        )
        latest_binding = store.runtime_binding(work.id)
        binding = current_cycle_binding
        if (
            current_steering_step is not None
            and current_steering_step.type.value == "COMPLETE"
        ):
            binding = latest_binding
        revision_reassessment_pending = bool(
            binding is not None
            and work.current_work_reality_revision_id is not None
            and binding.work_reality_revision_id
            != work.current_work_reality_revision_id
        )
        if revision_reassessment_pending:
            # The older cycle remains immutable history, but it must not keep
            # projecting its Candidate, verification, or Human action as if it
            # belonged to the newly admitted Work Reality revision.
            binding = None
        summary = RuntimeFactSummary() if binding is None else store.runtime_summary(binding)
        latest_summary = (
            RuntimeFactSummary()
            if latest_binding is None
            else store.runtime_summary(latest_binding)
        )
        steering_complete = bool(
            steering_plan is not None
            and latest_steering_decision is not None
            and latest_steering_decision.steering_outcome is SteeringOutcome.COMPLETE
            # A reviewed design artifact is a prerequisite for implementation,
            # not evidence that the Human's working-software outcome exists.
            and latest_summary.extra.get("task_contract_mode") != "DESIGN_ARTIFACT"
            and latest_summary.runtime_commit_id is not None
            and latest_summary.completion_outcome == "PRODUCED"
            and latest_summary.verification_results
            and all(item == "PASS" for item in latest_summary.verification_results)
            and latest_summary.integration_state == "CONVERGED"
            and latest_binding is not None
            and latest_binding.work_reality_revision_id
            == work.current_work_reality_revision_id
            and any(
                item.kind is RealityReferenceKind.RUNTIME_COMMIT
                and item.identity == latest_summary.runtime_commit_id
                for item in latest_steering_decision.reality_refs
            )
        )
        steering_attention = bool(
            latest_steering_decision is not None
            and self._decision_matches_work_revision(latest_steering_decision, work.current_work_reality_revision_id)
            and latest_steering_decision.steering_outcome
            is SteeringOutcome.HUMAN_ATTENTION
        )
        if (
            steering_attention
            and latest_steering_decision is not None
            and latest_steering_decision.attention_reason
            is SteeringAttentionReason.PRODUCTION_PROPOSAL_REVIEW_REQUIRED
        ):
            semantic_result = steering.latest_semantic_result_for_step(
                latest_steering_decision.current_step_id
            )
            if semantic_result is not None:
                runtime = RuntimeStore(store.session)
                steering_attention = not any(
                    record.decision_type
                    in {
                        "APPROVE_GUIDED_PRODUCTION_PROPOSAL",
                        "REFINE_GUIDED_PRODUCTION_PROPOSAL",
                    }
                    and record.scope.get("semantic_result_id")
                    == str(semantic_result.id)
                    for record in runtime.governance_for_subject(str(work.id))
                )
        status, step, event, next_action = self._projection_state(
            work,
            summary,
            steering_enabled=steering_plan is not None,
            steering_complete=steering_complete,
            steering_attention=steering_attention,
        )
        if revision_reassessment_pending and not steering_attention:
            status = WorkStatus.READY
            event = "WORK_REALITY_REVISION_ADMITTED"
            next_action = (
                "Reassess the governed Plan against the latest Work Reality revision"
            )
        if current_steering_step is not None:
            step = current_steering_step.type.value
        bindings = store.runtime_bindings(work.id)
        latest_trusted_commit_id = next(
            (
                facts.runtime_commit_id
                for facts in (
                    store.runtime_summary(item) for item in reversed(bindings)
                )
                if facts.runtime_commit_id is not None
            ),
            None,
        )
        result_summary = None
        if latest_trusted_commit_id is not None:
            result_summary = "Trusted Runtime Commit recorded"
        elif summary.artifact_paths:
            result_summary = (
                f"{len(summary.artifact_paths)} independently observed artifact change(s)"
            )
        return WorkProjection(
            work_id=work.id,
            goal_id=work.goal_id,
            mode=work.mode,
            raw_user_requirement=work.raw_user_requirement,
            title=work.refined_title,
            desired_outcome=work.desired_outcome,
            constraints=work.constraints,
            target_kind=(
                ProductionTargetKind.DOCUMENTATION_WORK
                if work.production_plan is None
                else work.production_plan.target_kind
            ),
            artifact_target=self._artifact_target(work),
            change_proposal=work.code_change_proposal,
            change_contract=(
                None
                if work.production_plan is None
                else work.production_plan.change_contract
            ),
            production_plan=work.production_plan,
            tags=work.tags,
            engineering_scope=scope,
            status=status,
            current_production_step=step,
            most_recent_meaningful_event=summary.latest_event or event,
            what_happens_next=next_action,
            human_attention_required=status
            in {
                WorkStatus.NEEDS_REFINEMENT,
                WorkStatus.AWAITING_APPROVAL,
                WorkStatus.NEEDS_ATTENTION,
            }
            or steering_attention,
            result_summary=result_summary,
            current_work_reality_revision_id=work.current_work_reality_revision_id,
            steering_enabled=steering_plan is not None,
            current_steering_step_id=(
                None if current_steering_step is None else current_steering_step.id
            ),
            current_steering_step_type=(
                None
                if current_steering_step is None
                else current_steering_step.type.value
            ),
            current_production_cycle_number=(
                None
                if current_cycle_binding is None or revision_reassessment_pending
                else current_cycle_binding.cycle_number
            ),
            current_production_run_id=(
                None
                if current_cycle_binding is None or revision_reassessment_pending
                else current_cycle_binding.production_run_id
            ),
            current_production_cycle_trusted=bool(
                current_cycle_binding is not None
                and not revision_reassessment_pending
                and summary.runtime_commit_id is not None
            ),
            latest_trusted_runtime_commit_id=latest_trusted_commit_id,
            work_complete=status is WorkStatus.COMPLETED,
        )

    def _projection_state(
        self,
        work: WorkRecord,
        facts: RuntimeFactSummary,
        *,
        steering_enabled: bool = False,
        steering_complete: bool = False,
        steering_attention: bool = False,
    ) -> tuple[WorkStatus, str, str, str]:
        if work.condition is WorkCondition.PRE_WORK:
            return (
                WorkStatus.PRE_WORK,
                "PRE_WORK",
                "CONVERSATION_DURABLE",
                "Continue the conversation or discard this unadmitted Work",
            )
        if work.condition is WorkCondition.DISCARDED:
            raise ProductRecordNotFound(f"Work not found: {work.id}")
        if work.condition is WorkCondition.DRAFT:
            return WorkStatus.DRAFT, "WORK_INTAKE", "WORK_SUBMITTED", "Refine Work draft"
        if work.condition is WorkCondition.NEEDS_REFINEMENT:
            if (
                work.production_plan is not None
                and work.production_plan.fit_classification
                is OnePwuFitClassification.MULTI_PWU_REQUIRED
            ):
                return (
                    WorkStatus.NEEDS_REFINEMENT,
                    "PRODUCTION_PLANNING",
                    "MULTI_PWU_REQUIRED",
                    "Narrow the Work to one governed PWU; multi-PWU production is deferred",
                )
            return (
                WorkStatus.NEEDS_REFINEMENT,
                "PRODUCTION_PLANNING",
                "PLAN_REFINEMENT_REQUIRED",
                "Narrow or clarify the Work",
            )
        if work.condition is WorkCondition.AWAITING_APPROVAL:
            return (
                WorkStatus.AWAITING_APPROVAL,
                "HUMAN_ADMISSION",
                "WORK_DRAFTED",
                "Human must approve, reject, or request refinement",
            )
        if work.condition is WorkCondition.REJECTED:
            return WorkStatus.BLOCKED, "WORK_REJECTED", "WORK_REJECTED", "No execution is authorized"
        if steering_complete:
            return WorkStatus.COMPLETED, "STEERING_COMPLETE", "STEERING_COMPLETE", "Work is complete"
        if steering_attention:
            return (
                WorkStatus.NEEDS_ATTENTION,
                "STEERING_ATTENTION",
                "STEERING_HUMAN_ATTENTION",
                "Human must resolve the material Steering decision",
            )
        if facts.runtime_commit_id is not None and steering_enabled:
            return (
                WorkStatus.RUNNING,
                "STEERING_REASSESSMENT",
                "PRODUCTION_CYCLE_TRUSTED",
                "Reassess governed Reality and admit the next Steering direction",
            )
        if facts.runtime_commit_id is not None:
            return WorkStatus.COMPLETED, "RUNTIME_COMMIT", "TRUSTED_BASELINE_ADVANCED", "Work is complete"
        if (
            work.mode is WorkMode.LONG_LIVED_STEERING
            and not steering_enabled
            and facts.attempt_id is None
        ):
            return (
                WorkStatus.READY,
                "STEERING_READY",
                "STEERING_BOOTSTRAP_PENDING",
                "Create the initial governed Steering Plan",
            )
        if steering_enabled and facts.attempt_id is None:
            return (
                WorkStatus.READY,
                "STEERING_ACTIVE",
                "STEERING_PLAN_ACTIVE",
                "Steering evaluates the current governed Plan Step",
            )
        if (
            facts.dispatch_id is not None
            and facts.provider_outcome == "UNKNOWN"
            and facts.observation_id is not None
            and not facts.artifact_paths
            and facts.completion_id is None
            and facts.completion_requires_production_result
        ):
            return (
                WorkStatus.BLOCKED,
                "EXECUTION_STOPPED",
                "PROVIDER_OUTCOME_UNKNOWN_PRODUCTION_NONE",
                "Execution stopped before Provider completion. Architecture/Operator review required.",
            )
        if (
            facts.dispatch_id is not None
            and facts.provider_outcome is not None
            and facts.observation_id is not None
            and not facts.artifact_paths
            and facts.completion_id is None
            and facts.completion_requires_production_result
        ):
            return (
                WorkStatus.BLOCKED,
                "EXECUTION_STOPPED",
                "REQUIRED_PRODUCTION_RESULT_ABSENT",
                "Execution completed without the required production result. "
                "Architecture/Operator review required.",
            )
        if facts.completion_outcome == "NOT_PRODUCED":
            return WorkStatus.BLOCKED, "COMPLETION", "OUTPUT_NOT_PRODUCED", "Review Completion failures"
        if (
            facts.admissibility_outcome is not None
            and facts.admissibility_outcome
            != ProductionAdmissibilityOutcome.ADMISSIBLE.value
        ):
            return WorkStatus.BLOCKED, "VERIFICATION", "NOT_ADMISSIBLE", "Review Verification evidence"
        if facts.candidate_id is not None and facts.authorization_id is None:
            return (
                WorkStatus.NEEDS_ATTENTION,
                "CANDIDATE_AUTHORITY",
                "CANDIDATE_SEALED",
                "Human must authorize the exact Candidate",
            )
        if facts.attempt_id is not None and facts.dispatch_id is None and self.executor is None:
            return (
                WorkStatus.NEEDS_ATTENTION,
                "EXECUTOR_BINDING",
                "ATTEMPT_READY",
                "Configure an Executor capability",
            )
        if (
            facts.proposed_snapshot_id is not None
            and not facts.verification_obligations
            and self.verifier is None
        ):
            return (
                WorkStatus.NEEDS_ATTENTION,
                "VERIFICATION_PROVIDER",
                "SNAPSHOT_PROPOSED",
                "Configure a Verification capability",
            )
        if facts.attempt_id is None:
            return WorkStatus.READY, "PWU_READY", "WORK_ADMITTED", "Create initial Attempt"
        return WorkStatus.RUNNING, self._runtime_step(facts), facts.latest_event or "RUNTIME_ACTIVE", self._next_runtime_action(facts)

    @staticmethod
    def _runtime_step(facts: RuntimeFactSummary) -> str:
        if facts.integration_effect_id is not None:
            return "REPOSITORY_INTEGRATION"
        if facts.authorization_id is not None:
            return "AUTHORIZED_CANDIDATE"
        if facts.candidate_id is not None:
            return "CANDIDATE_GOVERNANCE"
        if facts.admissibility_id is not None:
            return "PRODUCTION_ADMISSIBILITY"
        if facts.proposed_snapshot_id is not None:
            return "VERIFICATION"
        if facts.completion_id is not None:
            return "COMPLETION"
        if facts.observation_id is not None:
            return "PRODUCTION_OBSERVATION"
        if facts.dispatch_id is not None:
            return "EXECUTION"
        return "ATTEMPT_PREPARATION"

    @staticmethod
    def _next_runtime_action(facts: RuntimeFactSummary) -> str:
        if facts.integration_effect_id is not None:
            return "Commit converged repository Reality to Runtime"
        if facts.authorization_id is not None:
            return "Integrate authorized Candidate"
        if facts.admissibility_id is not None:
            return "Seal eligible Candidate"
        if facts.proposed_snapshot_id is not None:
            return "Complete Verification and admissibility"
        if facts.completion_id is not None:
            return "Create proposed repository snapshot"
        if facts.observation_id is not None:
            return "Evaluate Completion"
        if facts.dispatch_id is not None:
            return "Observe production Reality"
        return "Prepare or dispatch current Attempt"

    def _record_draft_decision(
        self,
        work_id: UUID,
        *,
        authority_identity: str,
        decision_type: str,
        condition: WorkCondition,
    ) -> WorkProjection:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            work = self._required_work(product, work_id)
            if product.runtime_binding(work_id) is not None:
                raise ProductInvariantViolation(
                    "Admitted Work cannot be rewritten as a draft decision"
                )
            if work.condition not in {
                WorkCondition.DRAFT,
                WorkCondition.NEEDS_REFINEMENT,
                WorkCondition.AWAITING_APPROVAL,
            }:
                raise ProductInvariantViolation("Work is not in draft governance")
            governance_id = uuid5(
                NAMESPACE_URL,
                f"spg:{decision_type}:{work.id}:{authority_identity}",
            )
            runtime.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": decision_type,
                    "authority_identity": authority_identity,
                    "subject_type": "PRODUCT_WORK",
                    "subject_identity": str(work.id),
                    "scope": {},
                    "rationale": None,
                    "created_at": timestamp,
                }
            )
            product.update_work(
                work.id,
                {"condition": condition.value, "updated_at": timestamp},
            )
            unit_of_work.commit()
        return self.get_work(work_id)

    @staticmethod
    def _required_work(store: ProductStore, work_id: UUID) -> WorkRecord:
        work = store.work(work_id)
        if work is None:
            raise ProductRecordNotFound(f"Work not found: {work_id}")
        return work

    @staticmethod
    def _runtime_binding_for_current_context(
        store: ProductStore,
        work_id: UUID,
    ):
        steering = SteeringStore(store.session)
        plan = steering.plan_for_work(work_id)
        if plan is None:
            return store.runtime_binding(work_id)
        revision = steering.active_revision(plan.id)
        if revision is None:
            return None
        current = next(
            (
                step
                for step in steering.steps(revision.id)
                if step.state.value == "CURRENT"
            ),
            None,
        )
        if current is None or current.type.value != "PRODUCE":
            return None
        return store.runtime_binding_for_step(current.id)

    @staticmethod
    def _require_mvp_scope(bindings) -> None:
        if len(bindings) != 1:
            raise ProductInvariantViolation(
                "MVP execution requires exactly one active Engineering Resource binding"
            )

    @staticmethod
    def _default_title(raw: str) -> str:
        first = next((line.strip() for line in raw.splitlines() if line.strip()), "")
        return first[:120] or "Untitled Work"

    @classmethod
    def _is_code_work(
        cls,
        raw: str,
        request: WorkRefinementRequest,
    ) -> bool:
        if any(
            value is not None
            for value in (
                request.code_exact_targets,
                request.code_allowed_areas,
                request.code_forbidden_areas,
                request.code_verification_obligations,
            )
        ):
            return True
        paths = cls._explicit_repository_paths(raw)
        if any(
            path.startswith(("src/", "tests/")) or path.endswith(".py")
            for path in paths
        ) or cls._explicit_repository_areas(raw):
            return True
        normalized = " ".join(raw.casefold().split())
        markers = (
            "source code",
            "python code",
            "code change",
            "modify code",
            "update code",
            "frontend",
            "javascript",
            "fix the bug",
            "unit test",
            "代码",
            "前端",
            "源文件",
            "修复 bug",
            "单元测试",
        )
        return any(marker in normalized for marker in markers)

    def _repository_change_proposal(
        self,
        *,
        work_id: UUID,
        raw: str,
        request: WorkRefinementRequest,
        existing: RepositoryChangeProposal | None,
        resource: EngineeringResourceRecord,
        baseline_id: UUID,
        source_ref: str,
        source_revision: str,
        desired_outcome: str,
        constraints: tuple[str, ...],
    ) -> RepositoryChangeProposal:
        exact_paths = (
            request.code_exact_targets
            if request.code_exact_targets is not None
            else self._explicit_repository_paths(raw)
            or (
                tuple(target.path for target in existing.required_targets)
                if existing is not None
                else ()
            )
        )
        allowed_areas = (
            request.code_allowed_areas
            if request.code_allowed_areas is not None
            else existing.allowed_areas
            if existing is not None
            else self._explicit_repository_areas(raw)
        )
        forbidden_areas = (
            request.code_forbidden_areas
            if request.code_forbidden_areas is not None
            else existing.forbidden_areas
            if existing is not None
            else ()
        )
        existing_targets = (
            tuple(target.path for target in existing.required_targets)
            if existing is not None
            else ()
        )
        scope_unchanged = (
            existing is not None
            and tuple(exact_paths) == existing_targets
            and tuple(allowed_areas) == existing.allowed_areas
        )
        requested_verification = (
            request.code_verification_obligations
            if request.code_verification_obligations is not None
            else existing.verification_obligations
            if scope_unchanged
            else ()
        )
        try:
            return self.change_proposals.propose(
                RepositoryChangeProposalRequest(
                    work_id=work_id,
                    refined_code_intent=desired_outcome,
                    constraints=constraints,
                    engineering_resource_id=resource.id,
                    repository_identity=resource.repository_identity,
                    repository_location=resource.location_ref,
                    source_baseline_id=baseline_id,
                    source_ref=source_ref,
                    source_revision=source_revision,
                    explicit_targets=tuple(exact_paths),
                    explicit_allowed_areas=tuple(allowed_areas),
                    explicit_forbidden_areas=tuple(forbidden_areas),
                    requested_verification=requested_verification,
                )
            )
        except ValueError as error:
            raise ProductInvariantViolation(f"Invalid Code Change Proposal: {error}") from error

    @staticmethod
    def _admit_change_contract(
        proposal: RepositoryChangeProposal,
        *,
        desired_outcome: str,
        constraints: tuple[str, ...],
    ) -> CodeChangeContract:
        if proposal.unresolved_scope_questions:
            raise ProductInvariantViolation(
                "Change Proposal still requires refinement before Human admission"
            )
        targets = tuple(
            CodeChangeTarget(path=target.path, operation=target.operation)
            for target in proposal.required_targets
        )
        shape = (
            ChangeTargetShape.EXACT_AND_BOUNDED
            if targets and proposal.allowed_areas
            else ChangeTargetShape.EXACT_TARGET_SET
            if targets
            else ChangeTargetShape.BOUNDED_REPOSITORY_AREAS
        )
        return CodeChangeContract(
            target_shape=shape,
            engineering_resource_id=proposal.engineering_resource_id,
            repository_identity=proposal.repository_identity,
            source_baseline_id=proposal.source_baseline_id,
            source_revision=proposal.source_revision,
            desired_outcome=desired_outcome,
            constraints=constraints,
            exact_targets=targets,
            allowed_areas=proposal.allowed_areas,
            forbidden_areas=proposal.forbidden_areas,
            verification_obligations=proposal.verification_obligations,
            source_proposal_id=proposal.proposal_id,
            source_proposal_fingerprint=proposal.proposal_fingerprint,
        )

    @staticmethod
    def _explicit_repository_areas(raw: str) -> tuple[str, ...]:
        matches = re.findall(
            r"(?<![\w./*-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/\*\*)(?![\w/*-])",
            raw,
        )
        return tuple(dict.fromkeys(matches))

    @staticmethod
    def _explicit_repository_paths(raw: str) -> tuple[str, ...]:
        nested = re.findall(
            r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+)(?![\w./*-])",
            raw,
        )
        roots = re.findall(
            r"(?<![\w./-])([A-Za-z0-9_-]+\.(?:py|toml|json|ya?ml))(?![\w./-])",
            raw,
            flags=re.IGNORECASE,
        )
        return tuple(
            dict.fromkeys(
                path.rstrip(".,:;。；")
                for path in (*nested, *roots)
                if "*" not in path
                and not (
                    path.startswith("docs/") and path.casefold().endswith(".md")
                )
            )
        )

    @classmethod
    def _default_code_verification_obligations(
        cls,
        exact_paths: tuple[str, ...],
        allowed_areas: tuple[str, ...],
    ) -> tuple[CodeVerificationObligation, ...]:
        obligations: list[CodeVerificationObligation] = [
            CodeVerificationObligation(kind=CodeVerificationKind.PATH_SCOPE),
            CodeVerificationObligation(kind=CodeVerificationKind.GIT_DIFF_CHECK),
        ]
        if any(path.endswith(".py") for path in exact_paths) or any(
            area.startswith(("src/", "tests/")) for area in allowed_areas
        ):
            obligations.append(
                CodeVerificationObligation(kind=CodeVerificationKind.PYTHON_COMPILE)
            )
        for path in exact_paths:
            if path.startswith("tests/") and path.endswith(".py"):
                obligations.append(
                    CodeVerificationObligation(
                        kind=CodeVerificationKind.PYTEST_TARGET,
                        target=path,
                    )
                )
            if path.startswith("tests/") and Path(path).suffix.casefold() in {
                ".js",
                ".cjs",
                ".mjs",
            }:
                obligations.append(
                    CodeVerificationObligation(
                        kind=CodeVerificationKind.NODE_TEST_TARGET,
                        target=path,
                    )
                )
            module = cls._python_module_for_path(path)
            if module is not None:
                obligations.append(
                    CodeVerificationObligation(
                        kind=CodeVerificationKind.IMPORT_CHECK,
                        target=module,
                    )
                )
        for area in allowed_areas:
            prefix = area[:-3].rstrip("/")
            if prefix.startswith("tests/"):
                obligations.append(
                    CodeVerificationObligation(
                        kind=CodeVerificationKind.PYTEST_TARGET,
                        target=prefix,
                    )
                )
        return tuple({item.identity: item for item in obligations}.values())

    @staticmethod
    def _python_module_for_path(path: str) -> str | None:
        if not path.startswith("src/") or not path.endswith(".py"):
            return None
        stem = path[4:-3].replace("/", ".")
        if stem.endswith(".__init__"):
            stem = stem[: -len(".__init__")]
        return stem or None

    @staticmethod
    def _code_verification_summary(contract: CodeChangeContract | None) -> str:
        if contract is None:
            return "Define a bounded Code Change Contract before Verification"
        return "Run admitted typed checks: " + ", ".join(
            contract.verification_identities
        )

    @staticmethod
    def _proposal_verification_summary(
        proposal: RepositoryChangeProposal | None,
    ) -> str:
        if proposal is None:
            return "Define a bounded Code Change Proposal before Verification"
        return "Proposed typed checks: " + ", ".join(
            item.identity for item in proposal.verification_obligations
        )

    @staticmethod
    def _code_change_objective(contract: CodeChangeContract) -> str:
        exact = "\n".join(
            f"- {target.operation.value} {target.path}"
            for target in contract.exact_targets
        )
        areas = "\n".join(f"- {area}" for area in contract.allowed_areas)
        constraints = "\n".join(f"- {item}" for item in contract.constraints)
        return (
            f"Produce the admitted code change.\n"
            f"Desired outcome: {contract.desired_outcome}\n"
            f"Admitted constraints:\n{constraints or '- None.'}\n"
            f"Exact targets:\n{exact or '- None.'}\n"
            f"Bounded areas:\n{areas or '- None.'}"
        )

    @staticmethod
    def _is_too_broad(raw: str) -> bool:
        normalized = " ".join(raw.lower().split())
        broad_markers = (
            "entire platform",
            "complete platform",
            "all systems",
            "everything",
            "multiple repositories",
            "rewrite the whole",
        )
        return len(normalized) > 600 or any(item in normalized for item in broad_markers)

    @staticmethod
    def _artifact_target(work: WorkRecord) -> ArtifactTargetProposal | None:
        values = (
            work.expected_artifact_path,
            work.artifact_operation,
            work.artifact_placement_rationale,
            work.artifact_target_confidence,
            work.artifact_source_baseline_id,
            work.artifact_source_revision,
        )
        if any(item is None for item in values):
            return None
        return ArtifactTargetProposal(
            path=work.expected_artifact_path or "",
            operation=work.artifact_operation or ArtifactTargetOperation.CREATE,
            placement_rationale=work.artifact_placement_rationale or "",
            confidence=(
                work.artifact_target_confidence or ArtifactTargetConfidence.LOW
            ),
            source_baseline_id=work.artifact_source_baseline_id,
            source_revision=work.artifact_source_revision or "",
        )

    @classmethod
    def _required_artifact_target(cls, work: WorkRecord) -> ArtifactTargetProposal:
        target = cls._artifact_target(work)
        if target is None:
            raise ProductInvariantViolation(
                "Work requires an exact Human-visible Artifact Target before approval"
            )
        return target

    @staticmethod
    def _required_production_plan(work: WorkRecord) -> ProductionPlanProposal:
        if work.production_plan is None:
            raise ProductInvariantViolation(
                "Work requires a Human-visible Production Plan before approval"
            )
        return work.production_plan

    @classmethod
    def _artifact_target_proposal(
        cls,
        *,
        raw: str,
        explicit_path: str | None,
        resource: EngineeringResourceRecord,
        baseline_id: UUID,
        source_revision: str,
    ) -> ArtifactTargetProposal | None:
        repository = Path(resource.location_ref).resolve()
        paths = cls._baseline_paths(repository, source_revision)
        path: str | None = None
        rationale: str | None = None
        confidence = ArtifactTargetConfidence.LOW
        if explicit_path is not None:
            path = cls._validate_artifact_path(explicit_path)
            rationale = "Human-selected repository-relative documentation target."
            confidence = ArtifactTargetConfidence.HIGH
        else:
            match = re.search(
                r"(?<![\w.-])((?:docs/)[A-Za-z0-9_./-]+\.md)(?![\w.-])",
                raw,
                flags=re.IGNORECASE,
            )
            if match:
                path = cls._validate_artifact_path(match.group(1))
                rationale = "The requirement names this exact documentation path."
                confidence = ArtifactTargetConfidence.HIGH
            else:
                normalized = " ".join(raw.casefold().split())
                if "production orchestration lite" in normalized:
                    path = "docs/architecture/production-orchestration-lite.md"
                    rationale = (
                        "Architecture terminology and the baseline documentation tree "
                        "place this product/architecture document under docs/architecture/."
                    )
                    confidence = ArtifactTargetConfidence.HIGH
                else:
                    folder = cls._documentation_folder(normalized, paths)
                    slug = cls._document_slug(raw)
                    if folder is not None and slug:
                        path = f"{folder}/{slug}.md"
                        rationale = (
                            f"The exact Source Baseline contains {folder}/ and the "
                            "requirement category maps to that documentation area."
                        )
                        confidence = ArtifactTargetConfidence.MEDIUM
        if path is None:
            return None
        operation = (
            ArtifactTargetOperation.UPDATE
            if path in paths
            else ArtifactTargetOperation.CREATE
        )
        return ArtifactTargetProposal(
            path=path,
            operation=operation,
            placement_rationale=rationale or "Repository-aware documentation placement.",
            confidence=confidence,
            source_baseline_id=baseline_id,
            source_revision=source_revision,
        )

    @staticmethod
    def _baseline_paths(repository: Path, source_revision: str) -> frozenset[str]:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "ls-tree",
                "-r",
                "--name-only",
                source_revision,
                "--",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ProductInvariantViolation(
                "Exact Source Baseline repository structure is unavailable"
            )
        return frozenset(result.stdout.splitlines())

    @staticmethod
    def _documentation_folder(normalized: str, paths: frozenset[str]) -> str | None:
        directories = {
            str(PurePosixPath(path).parent)
            for path in paths
            if path.startswith("docs/")
        }
        categories = (
            ("docs/roadmap", ("roadmap", "migration plan", "delivery plan")),
            ("docs/evidence", ("evidence", "finding", "benchmark", "test report")),
            (
                "docs/architecture",
                ("architecture", "principle", "production orchestration", "product"),
            ),
        )
        for folder, markers in categories:
            if folder in directories and any(marker in normalized for marker in markers):
                return folder
        if "docs" in directories and any(
            marker in normalized
            for marker in ("document", "documentation", "markdown", "work result", "product result")
        ):
            return "docs"
        return None

    @staticmethod
    def _document_slug(raw: str) -> str | None:
        first = next((line.strip() for line in raw.splitlines() if line.strip()), "")
        words = re.findall(r"[a-z0-9]+", first.casefold())
        ignored = {
            "a", "an", "the", "create", "add", "write", "produce", "update",
            "document", "documentation", "markdown", "governed", "admitted",
        }
        selected = [word for word in words if word not in ignored][:8]
        return "-".join(selected) or None

    @staticmethod
    def _validate_artifact_path(raw_path: str) -> str:
        value = raw_path.strip()
        if "\\" in value:
            raise ProductInvariantViolation("Artifact Target must use POSIX separators")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {"", "."}:
            raise ProductInvariantViolation(
                "Artifact Target must be a safe repository-relative path"
            )
        if any(part.startswith(".") for part in path.parts):
            raise ProductInvariantViolation(
                "Artifact Target cannot address hidden or Git-internal paths"
            )
        if not value.startswith("docs/") or path.suffix.casefold() != ".md":
            raise ProductInvariantViolation(
                "MVP documentation Artifact Target must be a Markdown path under docs/"
            )
        return str(path)

    @staticmethod
    def _extract_constraints(raw: str) -> tuple[str, ...]:
        normalized = " ".join(raw.casefold().split())
        constraints: list[str] = []
        if "do not expand" in normalized and any(
            marker in normalized for marker in ("invent", "introduce", "new capabilities")
        ):
            constraints.append(
                "Do not expand or invent capabilities beyond the already accepted design."
            )
        marker = re.compile(
            r"\b(do not|must not|only|must|keep|without|do not expand|do not introduce)\b",
            flags=re.IGNORECASE,
        )
        chinese_markers = (
            "不要",
            "不得",
            "不应",
            "禁止",
            "必须",
            "只能",
            "仅限",
        )
        fragments = tuple(
            " ".join(fragment.split()).strip(" -:")
            for fragment in re.split(r"[\n.;。；]+", raw)
        )
        has_explicit_chinese_instruction = any(
            any(chinese_marker in fragment for chinese_marker in chinese_markers)
            for fragment in fragments
        )
        for candidate in fragments:
            chinese_instruction = any(
                chinese_marker in candidate for chinese_marker in chinese_markers
            )
            bounded_reuse = (
                "尽量复用" in candidate and has_explicit_chinese_instruction
            )
            if candidate and (
                marker.search(candidate) or chinese_instruction or bounded_reuse
            ):
                constraints.append(candidate)
        return tuple(dict.fromkeys(constraints))

    @staticmethod
    def _merge_constraints(*groups: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item.strip()
                for group in groups
                for item in group
                if item.strip()
            )
        )

    @staticmethod
    def _artifact_objective(contract: ArtifactContract) -> str:
        constraint_text = "\n".join(f"- {item}" for item in contract.constraints)
        return (
            f"{contract.operation.value} the exact artifact {contract.artifact_path}.\n"
            f"Intended outcome: {contract.expected_outcome}\n"
            f"Constraints:\n{constraint_text or '- None beyond the admitted contract.'}"
        )

    @staticmethod
    def _fingerprint(value: object) -> str:
        canonical = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        return sha256(canonical).hexdigest()
