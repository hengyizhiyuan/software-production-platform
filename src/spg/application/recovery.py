"""S5-A read-mostly recovery assessment and classification."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.domain.execution import ProviderReportedOutcome
from spg.domain.integration import RepositoryEffectState
from spg.domain.recovery import (
    AttemptRecoveryAssessmentRequest,
    RecoveryAssessmentRecord,
    RecoveryAssessmentRequest,
    RecoveryBarrierActive,
    RecoveryClassification,
    RecoveryGuidance,
    RecoverySubjectType,
    RepositoryRecoveryAssessmentRequest,
)
from spg.domain.runtime import (
    RepositoryRealityError,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
)
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


RECOVERY_ACTOR = "spg-runtime:recovery-assessment"


@dataclass(frozen=True, slots=True)
class _AssessmentDraft:
    subject_type: RecoverySubjectType
    subject_identity: str
    governed_basis: dict[str, object]
    observed_facts: dict[str, object]
    differences: tuple[str, ...]
    classification: RecoveryClassification
    guidance: RecoveryGuidance
    subject_is_current: bool
    safely_recoverable: bool
    requires_human_attention: bool
    recovery_barrier: bool


class RecoveryAssessmentService:
    """Classify known facts and persist evidence without executing recovery."""

    def __init__(
        self,
        database: Database,
        git: GitRepositoryIntegrationAdapter | None = None,
    ) -> None:
        self.database = database
        self.git = git or GitRepositoryIntegrationAdapter()

    def assess_recovery(
        self,
        request: RecoveryAssessmentRequest,
    ) -> RecoveryAssessmentRecord:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            if isinstance(request, AttemptRecoveryAssessmentRequest):
                draft = self._assess_attempt(store, request)
            elif isinstance(request, RepositoryRecoveryAssessmentRequest):
                draft = self._assess_repository_integration(store, request)
            else:  # pragma: no cover - closed typed API guard
                raise TypeError("unsupported Recovery Assessment request")

            basis_fingerprint = _fingerprint(
                {
                    "subject_type": draft.subject_type.value,
                    "subject_identity": draft.subject_identity,
                    "governed_basis": draft.governed_basis,
                    "observed_facts": draft.observed_facts,
                    "differences": draft.differences,
                    "classification": draft.classification.value,
                    "guidance": draft.guidance.value,
                    "subject_is_current": draft.subject_is_current,
                    "safely_recoverable": draft.safely_recoverable,
                    "requires_human_attention": draft.requires_human_attention,
                    "recovery_barrier": draft.recovery_barrier,
                }
            )
            existing = store.recovery_assessment_by_basis(basis_fingerprint)
            if existing is not None:
                return existing

            assessment_id = uuid5(
                NAMESPACE_URL,
                f"spg:recovery-assessment:{basis_fingerprint}",
            )
            store.insert_recovery_assessment(
                {
                    "id": assessment_id,
                    "subject_type": draft.subject_type.value,
                    "subject_identity": draft.subject_identity,
                    "governed_basis": draft.governed_basis,
                    "observed_facts": draft.observed_facts,
                    "differences": list(draft.differences),
                    "classification": draft.classification.value,
                    "guidance": draft.guidance.value,
                    "subject_is_current": int(draft.subject_is_current),
                    "safely_recoverable": int(draft.safely_recoverable),
                    "requires_human_attention": int(
                        draft.requires_human_attention
                    ),
                    "recovery_barrier": int(draft.recovery_barrier),
                    "basis_fingerprint": basis_fingerprint,
                    "assessed_at": timestamp,
                }
            )
            store.insert_transition(
                {
                    "id": uuid4(),
                    "entity_type": "RECOVERY_ASSESSMENT",
                    "entity_identity": str(assessment_id),
                    "from_condition": None,
                    "to_condition": draft.classification.value,
                    "reason": "RECOVERY_REALITY_CLASSIFIED",
                    "actor_identity": RECOVERY_ACTOR,
                    "correlation_identity": draft.subject_identity,
                    "created_at": timestamp,
                }
            )
            assessment = store.recovery_assessment(assessment_id)
            if assessment is None:
                raise RuntimeInvariantViolation(
                    "Recovery Assessment was not constructed"
                )
            unit_of_work.commit()
            return assessment

    def assessment(self, assessment_id: UUID) -> RecoveryAssessmentRecord:
        with self.database.unit_of_work() as unit_of_work:
            assessment = RuntimeStore(unit_of_work.session).recovery_assessment(
                assessment_id
            )
            if assessment is None:
                raise RuntimeRecordNotFound(
                    f"Recovery Assessment not found: {assessment_id}"
                )
            return assessment

    def assert_forward_progress_allowed(self, assessment_id: UUID) -> None:
        """Minimum Recovery Barrier seam; it performs no recovery action."""

        assessment = self.assessment(assessment_id)
        if assessment.recovery_barrier:
            raise RecoveryBarrierActive(
                "unresolved Recovery Assessment blocks silent forward progress: "
                f"{assessment.classification.value}"
            )

    @staticmethod
    def _assess_attempt(
        store: RuntimeStore,
        request: AttemptRecoveryAssessmentRequest,
    ) -> _AssessmentDraft:
        attempt = store.attempt(request.attempt_id)
        if attempt is None:
            raise RuntimeRecordNotFound(f"Attempt not found: {request.attempt_id}")
        if (
            attempt.work_unit_id != request.expected_work_unit_id
            or attempt.generation != request.expected_generation
        ):
            raise RuntimeInvariantViolation(
                "Recovery Assessment request does not bind the exact Attempt lineage"
            )
        work_unit = store.work_unit(attempt.work_unit_id)
        pointer = store.current_pointer(source_baseline_id=attempt.source_baseline_id)
        if work_unit is None or pointer is None:
            raise RuntimeInvariantViolation(
                "Attempt Recovery Assessment lineage is incomplete"
            )
        run = store.run(work_unit.production_run_id)
        plan = store.plan_revision(attempt.plan_revision_id)
        if run is None or plan is None:
            raise RuntimeInvariantViolation(
                "Attempt Recovery Assessment Run/Plan lineage is incomplete"
            )
        preparation = store.attempt_preparation(attempt.id)
        dispatch = store.execution_dispatch_for_attempt(attempt.id)
        report = (
            store.provider_execution_report(dispatch.id)
            if dispatch is not None
            else None
        )
        observation = (
            store.repository_observation(dispatch.id)
            if dispatch is not None
            else None
        )
        work_products = (
            store.work_product_references(observation.id)
            if observation is not None
            else ()
        )
        workspace_path = (
            dispatch.workspace.workspace_path
            if dispatch is not None
            else preparation.workspace.workspace_path
            if preparation is not None
            else None
        )
        current = (
            pointer.snapshot_id == attempt.source_baseline_id
            and run.current_plan_revision_id == attempt.plan_revision_id
            and work_unit.plan_revision_id == attempt.plan_revision_id
            and work_unit.source_baseline_id == attempt.source_baseline_id
            and work_unit.current_execution_generation == attempt.generation
        )
        governed_basis: dict[str, object] = {
            "production_run_id": str(run.id),
            "plan_revision_id": str(attempt.plan_revision_id),
            "source_baseline_id": str(attempt.source_baseline_id),
            "current_baseline_id": str(pointer.snapshot_id),
            "work_unit_id": str(work_unit.id),
            "work_unit_condition": work_unit.condition.value,
            "attempt_id": str(attempt.id),
            "attempt_generation": attempt.generation,
            "current_attempt_generation": work_unit.current_execution_generation,
            "dispatch_id": str(dispatch.id) if dispatch is not None else None,
            "workspace_identity": (
                dispatch.workspace.workspace_identity
                if dispatch is not None
                else preparation.workspace.workspace_identity
                if preparation is not None
                else None
            ),
        }
        observed_facts: dict[str, object] = {
            "dispatch_exists": dispatch is not None,
            "provider_report_id": (
                str(report.id) if report is not None else None
            ),
            "provider_outcome": report.outcome.value if report is not None else None,
            "repository_observation_id": (
                str(observation.id) if observation is not None else None
            ),
            "repository_observation_fingerprint": (
                observation.observation_fingerprint
                if observation is not None
                else None
            ),
            "observed_change_count": (
                len(observation.changes) if observation is not None else None
            ),
            "work_product_reference_ids": [
                str(item.id) for item in work_products
            ],
            "workspace_exists": (
                Path(workspace_path).exists() if workspace_path is not None else None
            ),
        }

        if not current:
            return _AssessmentDraft(
                subject_type=RecoverySubjectType.ATTEMPT,
                subject_identity=str(attempt.id),
                governed_basis=governed_basis,
                observed_facts=observed_facts,
                differences=("ATTEMPT_AUTHORITY_IS_STALE",),
                classification=RecoveryClassification.STALE,
                guidance=RecoveryGuidance.REPLAN_SUPERSEDE,
                subject_is_current=False,
                safely_recoverable=False,
                requires_human_attention=True,
                recovery_barrier=True,
            )
        if dispatch is None:
            classification = RecoveryClassification.BLOCKED
            guidance = RecoveryGuidance.RESUME_EXISTING_ATTEMPT
            differences = ("ATTEMPT_NOT_DISPATCHED",)
        elif report is None and observation is None:
            classification = RecoveryClassification.UNKNOWN
            guidance = RecoveryGuidance.REOBSERVE
            differences = ("DISPATCH_OUTCOME_AND_REALITY_UNKNOWN",)
        elif report is None:
            classification = RecoveryClassification.UNKNOWN
            guidance = RecoveryGuidance.REOBSERVE
            differences = ("PROVIDER_REPORT_MISSING",)
        elif report.outcome is ProviderReportedOutcome.UNKNOWN:
            classification = RecoveryClassification.UNKNOWN
            guidance = RecoveryGuidance.REOBSERVE
            differences = ("PROVIDER_OUTCOME_UNKNOWN",)
        elif observation is None:
            classification = RecoveryClassification.UNKNOWN
            guidance = RecoveryGuidance.REOBSERVE
            differences = ("INDEPENDENT_REPOSITORY_OBSERVATION_MISSING",)
        elif report.outcome is ProviderReportedOutcome.SUCCESS and not observation.changes:
            classification = RecoveryClassification.BLOCKED
            guidance = RecoveryGuidance.REOBSERVE
            differences = ("PROVIDER_SUCCESS_WITHOUT_OBSERVED_CHANGE",)
        elif report.outcome is ProviderReportedOutcome.FAILURE and observation.changes:
            classification = RecoveryClassification.RECOVERABLE
            guidance = RecoveryGuidance.REOBSERVE
            differences = ("PROVIDER_FAILURE_WITH_OBSERVED_WORK",)
        elif report.outcome is ProviderReportedOutcome.FAILURE:
            classification = RecoveryClassification.RECOVERABLE
            guidance = RecoveryGuidance.RETRY_WITH_NEW_ATTEMPT
            differences = ("PROVIDER_FAILURE_WITHOUT_OBSERVED_WORK",)
        else:
            classification = RecoveryClassification.COHERENT
            guidance = RecoveryGuidance.NO_ACTION
            differences = ()

        barrier = classification is not RecoveryClassification.COHERENT
        return _AssessmentDraft(
            subject_type=RecoverySubjectType.ATTEMPT,
            subject_identity=str(attempt.id),
            governed_basis=governed_basis,
            observed_facts=observed_facts,
            differences=differences,
            classification=classification,
            guidance=guidance,
            subject_is_current=True,
            safely_recoverable=classification
            in {RecoveryClassification.COHERENT, RecoveryClassification.RECOVERABLE},
            requires_human_attention=classification
            in {
                RecoveryClassification.UNKNOWN,
                RecoveryClassification.DIVERGED,
                RecoveryClassification.STALE,
                RecoveryClassification.BLOCKED,
            },
            recovery_barrier=barrier,
        )

    def _assess_repository_integration(
        self,
        store: RuntimeStore,
        request: RepositoryRecoveryAssessmentRequest,
    ) -> _AssessmentDraft:
        effect = store.repository_integration_effect(
            request.repository_integration_effect_id
        )
        if effect is None:
            raise RuntimeRecordNotFound(
                "Repository Integration Effect not found: "
                f"{request.repository_integration_effect_id}"
            )
        if effect.operation_fingerprint != request.expected_operation_fingerprint:
            raise RuntimeInvariantViolation(
                "Recovery Assessment request does not bind the exact integration operation"
            )
        candidate = store.baseline_candidate(effect.candidate_id)
        pointer = store.current_pointer(repository_identity=effect.repository_identity, repository_ref=effect.target_authoritative_ref)
        if candidate is None or pointer is None:
            raise RuntimeInvariantViolation(
                "Repository Recovery Assessment lineage is incomplete"
            )
        proposed = store.proposed_snapshot(candidate.proposed_snapshot_id)
        if proposed is None:
            raise RuntimeInvariantViolation(
                "Repository Recovery Assessment proposed snapshot is missing"
            )
        observation = store.repository_observation_by_id(
            proposed.repository_observation_id
        )
        dispatch = (
            store.execution_dispatch(observation.dispatch_id)
            if observation is not None
            else None
        )
        if dispatch is None:
            raise RuntimeInvariantViolation(
                "Repository Recovery Assessment path lineage is incomplete"
            )
        runtime_commit = store.runtime_commit_for_candidate(candidate.id)

        observed_ref: str | None = None
        observed_tree: str | None = None
        observation_error: str | None = None
        try:
            observed_ref = self.git.read_ref(
                dispatch.workspace.repository_path,
                effect.target_authoritative_ref,
            )
            if (
                observed_ref == effect.proposed_repository_revision
                and self.git.commit_exists(
                    dispatch.workspace.repository_path,
                    effect.proposed_repository_revision,
                )
            ):
                observed_tree = self.git.read_commit_tree(
                    dispatch.workspace.repository_path,
                    effect.proposed_repository_revision,
                )
        except RepositoryRealityError as error:
            observation_error = str(error)

        governed_basis: dict[str, object] = {
            "production_run_id": str(candidate.production_run_id),
            "plan_revision_id": str(candidate.plan_revision_id),
            "source_baseline_id": str(candidate.source_baseline_id),
            "current_baseline_id": str(pointer.snapshot_id),
            "candidate_id": str(candidate.id),
            "candidate_fingerprint": candidate.fingerprint,
            "integration_effect_id": str(effect.id),
            "integration_operation_fingerprint": effect.operation_fingerprint,
            "integration_effect_state": effect.state.value,
            "repository_identity": effect.repository_identity,
            "target_authoritative_ref": effect.target_authoritative_ref,
            "expected_source_repository_revision": (
                effect.expected_source_repository_revision
            ),
            "proposed_repository_revision": effect.proposed_repository_revision,
            "proposed_tree_identity": effect.proposed_tree_identity,
            "runtime_commit_id": (
                str(runtime_commit.id) if runtime_commit is not None else None
            ),
            "runtime_commit_baseline_id": (
                str(runtime_commit.new_baseline_id)
                if runtime_commit is not None
                else None
            ),
        }
        observed_facts: dict[str, object] = {
            "observed_repository_revision": observed_ref,
            "observed_tree_identity": observed_tree,
            "repository_observation_error": observation_error,
            "effect_recorded_observation": effect.observed_repository_revision,
            "runtime_commit_exists": runtime_commit is not None,
        }
        current = pointer.snapshot_id in {
            candidate.source_baseline_id,
            runtime_commit.new_baseline_id if runtime_commit is not None else None,
        }

        if observation_error is not None or observed_ref is None:
            classification = RecoveryClassification.UNKNOWN
            guidance = RecoveryGuidance.REOBSERVE
            differences = ("AUTHORITATIVE_REF_OBSERVATION_UNKNOWN",)
        elif effect.state is RepositoryEffectState.PREPARED:
            if observed_ref == effect.expected_source_repository_revision:
                classification = RecoveryClassification.RECOVERABLE
                guidance = RecoveryGuidance.REOBSERVE
                differences = ("PREPARED_REF_AT_EXPECTED_SOURCE",)
            elif (
                observed_ref == effect.proposed_repository_revision
                and observed_tree == effect.proposed_tree_identity
            ):
                classification = RecoveryClassification.RECOVERABLE
                guidance = RecoveryGuidance.RECORD_EXTERNAL_CONVERGENCE
                differences = ("EXTERNAL_CONVERGENCE_LOCAL_FACT_MISSING",)
            else:
                classification = RecoveryClassification.DIVERGED
                guidance = RecoveryGuidance.ESCALATE_DIVERGENCE
                differences = ("PREPARED_REF_DIVERGED_FROM_EXPECTED_AND_PROPOSED",)
        elif observed_ref != effect.proposed_repository_revision:
            classification = RecoveryClassification.DIVERGED
            guidance = RecoveryGuidance.ESCALATE_DIVERGENCE
            differences = ("CONVERGED_EFFECT_REF_NO_LONGER_PROPOSED",)
        elif observed_tree != effect.proposed_tree_identity:
            classification = RecoveryClassification.DIVERGED
            guidance = RecoveryGuidance.ESCALATE_DIVERGENCE
            differences = ("PROPOSED_COMMIT_TREE_DIVERGED",)
        elif runtime_commit is None and pointer.snapshot_id == candidate.source_baseline_id:
            classification = RecoveryClassification.RECOVERABLE
            guidance = RecoveryGuidance.RETRY_RUNTIME_COMMIT
            differences = ("REPOSITORY_CONVERGED_RUNTIME_COMMIT_MISSING",)
        elif runtime_commit is None:
            classification = RecoveryClassification.STALE
            guidance = RecoveryGuidance.REPLAN_SUPERSEDE
            differences = ("SOURCE_BASELINE_SUPERSEDED_BEFORE_RUNTIME_COMMIT",)
        elif pointer.snapshot_id == runtime_commit.new_baseline_id:
            classification = RecoveryClassification.COHERENT
            guidance = RecoveryGuidance.NO_ACTION
            differences = ()
        else:
            classification = RecoveryClassification.DIVERGED
            guidance = RecoveryGuidance.ESCALATE_DIVERGENCE
            differences = ("RUNTIME_COMMIT_POINTER_REALITY_DIVERGED",)

        barrier = classification is not RecoveryClassification.COHERENT
        return _AssessmentDraft(
            subject_type=RecoverySubjectType.REPOSITORY_INTEGRATION,
            subject_identity=str(effect.id),
            governed_basis=governed_basis,
            observed_facts=observed_facts,
            differences=differences,
            classification=classification,
            guidance=guidance,
            subject_is_current=current,
            safely_recoverable=classification
            in {RecoveryClassification.COHERENT, RecoveryClassification.RECOVERABLE},
            requires_human_attention=classification
            in {
                RecoveryClassification.UNKNOWN,
                RecoveryClassification.DIVERGED,
                RecoveryClassification.STALE,
                RecoveryClassification.BLOCKED,
            },
            recovery_barrier=barrier,
        )


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()
