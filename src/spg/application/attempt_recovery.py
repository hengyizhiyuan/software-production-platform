"""S5-C exact Attempt/workspace salvage and retry preparation."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.completion import CompletionService
from spg.application.execution import ExecutionService
from spg.application.preparation import PreparationService
from spg.application.recovery import RecoveryAssessmentService
from spg.application.runtime import RuntimeService
from spg.domain.completion import CompletionEvaluationOutcome
from spg.domain.recovery import (
    AttemptRecoveryAssessmentRequest,
    AttemptRecoveryResult,
    AttemptRetryRecoveryRequest,
    RecoveryActionOutcome,
    RecoveryActionRecord,
    RecoveryActionRequest,
    RecoveryActionType,
    RecoveryAssessmentRecord,
    RecoveryAssessmentStale,
    RecoveryClassification,
    RecoveryGuidance,
    RecoverySubjectType,
)
from spg.domain.runtime import (
    AttemptRequest,
    RepositoryRealityError,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
    WorkUnitCondition,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


ATTEMPT_RECOVERY_ACTOR = "spg-runtime:attempt-recovery"


class AttemptRecoveryService:
    """Inspect existing work first; create a clean retry only when still required."""

    def __init__(
        self,
        database: Database,
        *,
        preparation: PreparationService | None = None,
        execution: ExecutionService | None = None,
        completion: CompletionService | None = None,
    ) -> None:
        self.database = database
        self.preparation = preparation or PreparationService(database)
        self.execution = execution or ExecutionService(
            database,
            preparation=self.preparation,
        )
        self.completion = completion or CompletionService(
            database,
            observer=self.execution.observer,
        )
        self.assessments = RecoveryAssessmentService(database)
        self.runtime = RuntimeService(database)

    def recover_attempt_work(
        self,
        request: RecoveryActionRequest,
    ) -> AttemptRecoveryResult:
        assessment = self._exact_attempt_assessment(request)
        existing = self._existing_action_result(
            assessment,
            RecoveryActionType.REOBSERVE_ATTEMPT_WORK,
        )
        if existing is not None:
            return existing

        current = self._fresh_assessment(assessment)
        if current.id != assessment.id:
            raise RecoveryAssessmentStale(
                "Attempt authority or workspace existence changed after assessment"
            )
        if assessment.guidance is RecoveryGuidance.RESUME_EXISTING_ATTEMPT:
            return self._record_attempt_result(
                assessment=assessment,
                action_type=RecoveryActionType.REOBSERVE_ATTEMPT_WORK,
                outcome=RecoveryActionOutcome.UNSUPPORTED_DEFERRED,
                observation=None,
                completion_evaluation=None,
                retry_attempt=None,
                retry_preparation=None,
                retry_required=False,
                workspace_prepared=False,
            )

        original, dispatch, preparation = self._attempt_facts(assessment)
        if dispatch is None:
            raise RuntimeInvariantViolation(
                "Attempt reobservation requires an existing dispatch; provider Resume is deferred"
            )
        if preparation is None:
            raise RuntimeInvariantViolation(
                "Attempt reobservation requires exact preparation lineage"
            )
        workspace_exists = preparation.workspace.workspace_path.exists()
        if not workspace_exists:
            return self._record_attempt_result(
                assessment=assessment,
                action_type=RecoveryActionType.REOBSERVE_ATTEMPT_WORK,
                outcome=RecoveryActionOutcome.INCOMPLETE,
                observation=None,
                completion_evaluation=None,
                retry_attempt=None,
                retry_preparation=None,
                retry_required=(
                    assessment.guidance is RecoveryGuidance.RETRY_WITH_NEW_ATTEMPT
                ),
                workspace_prepared=False,
            )

        try:
            observation, _ = self.execution.observe_dispatch(dispatch.id)
            completion_result = self.completion.evaluate_observation(observation.id)
        except (RepositoryRealityError, RuntimeInvariantViolation) as error:
            raise RecoveryAssessmentStale(
                "Attempt workspace Reality changed or no longer matches its exact basis"
            ) from error

        salvaged = (
            completion_result.evaluation.outcome
            is CompletionEvaluationOutcome.PRODUCED
        )
        return self._record_attempt_result(
            assessment=assessment,
            action_type=RecoveryActionType.REOBSERVE_ATTEMPT_WORK,
            outcome=(
                RecoveryActionOutcome.SALVAGED
                if salvaged
                else RecoveryActionOutcome.INCOMPLETE
            ),
            observation=observation,
            completion_evaluation=completion_result.evaluation,
            retry_attempt=None,
            retry_preparation=None,
            retry_required=(
                not salvaged
                and assessment.guidance is RecoveryGuidance.RETRY_WITH_NEW_ATTEMPT
            ),
            workspace_prepared=True,
        )

    def retry_attempt_from_recovery(
        self,
        request: AttemptRetryRecoveryRequest,
    ) -> AttemptRecoveryResult:
        assessment = self._exact_attempt_assessment(request)
        self._require_retry_guidance(assessment)
        existing = self._existing_action_result(
            assessment,
            RecoveryActionType.RETRY_WITH_NEW_ATTEMPT,
        )
        if existing is not None:
            return self._ensure_retry_prepared(existing, request)

        salvage = self.recover_attempt_work(
            RecoveryActionRequest(
                recovery_assessment_id=assessment.id,
                expected_assessment_fingerprint=assessment.basis_fingerprint,
            )
        )
        if salvage.action.outcome is RecoveryActionOutcome.SALVAGED:
            return salvage
        if not salvage.retry_required:
            raise RuntimeInvariantViolation(
                "current Attempt Reality does not authorize a new Retry Attempt"
            )

        current = self._fresh_assessment(assessment)
        if current.id != assessment.id:
            # A reobservation can add normal evidence. It is actionable only if the
            # resulting exact assessment independently retains retry guidance.
            if not (
                current.classification is RecoveryClassification.RECOVERABLE
                and current.guidance is RecoveryGuidance.RETRY_WITH_NEW_ATTEMPT
                and current.subject_identity == assessment.subject_identity
            ):
                raise RecoveryAssessmentStale(
                    "Attempt Reality changed and no longer supports retry"
                )
            raise RecoveryAssessmentStale(
                "reobservation created a new exact basis; retry requires that assessment"
            )

        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            original = store.attempt(UUID(assessment.subject_identity))
            if original is None:
                raise RuntimeRecordNotFound(
                    f"Attempt not found: {assessment.subject_identity}"
                )
            work_unit = store.work_unit(original.work_unit_id, for_update=True)
            pointer = store.current_pointer(for_update=True)
            if work_unit is None or pointer is None:
                raise RuntimeInvariantViolation(
                    "Retry Attempt current PWU/Baseline lineage is incomplete"
                )
            run = store.run(work_unit.production_run_id, for_update=True)
            plan = store.plan_revision(work_unit.plan_revision_id)
            package = store.context_package(request.context_package_id)
            if any(item is None for item in (run, plan, package)):
                raise RuntimeInvariantViolation(
                    "Retry Attempt Plan/Context lineage is incomplete"
                )
            if (
                original.generation != work_unit.current_execution_generation
                or original.generation != assessment.governed_basis.get(
                    "attempt_generation"
                )
                or original.work_unit_id
                != UUID(str(assessment.governed_basis.get("work_unit_id")))
                or original.plan_revision_id != work_unit.plan_revision_id
                or original.source_baseline_id != work_unit.source_baseline_id
                or pointer.snapshot_id != work_unit.source_baseline_id
                or run.current_plan_revision_id != work_unit.plan_revision_id
                or run.source_baseline_id != work_unit.source_baseline_id
                or plan.production_run_id != run.id
                or plan.source_baseline_id != work_unit.source_baseline_id
                or package.production_run_id != run.id
                or package.work_unit_id != work_unit.id
                or package.plan_revision_id != plan.id
                or package.source_baseline_id != work_unit.source_baseline_id
                or work_unit.condition is not WorkUnitCondition.PROPOSED
            ):
                raise RecoveryAssessmentStale(
                    "Retry Attempt Plan/Baseline/PWU/generation authority is stale"
                )
            retry = self.runtime._insert_attempt(
                unit_of_work,
                store,
                work_unit,
                AttemptRequest(
                    context_ref=str(package.id),
                    provider_ref=request.executor_binding.binding_ref,
                    workspace_ref=None,
                ),
                retry_of=original.id,
                reason="RECOVERY_RETRY_ATTEMPT_CREATED",
                commit=False,
            )
            workspace_identity = f"attempt-worktree:{retry.id}"
            action = self._insert_attempt_action(
                store,
                assessment=assessment,
                action_type=RecoveryActionType.RETRY_WITH_NEW_ATTEMPT,
                outcome=RecoveryActionOutcome.RETRY_CREATED,
                original_attempt=original,
                retry_attempt=retry,
                workspace_identity=workspace_identity,
                observation_id=salvage.action.repository_observation_id,
                completion_id=salvage.action.completion_evaluation_id,
                timestamp=timestamp,
            )
            self._append_transition(
                store,
                action=action,
                reason="GOVERNED_RETRY_ATTEMPT_CREATED",
                timestamp=timestamp,
            )
            unit_of_work.commit()

        base_result = AttemptRecoveryResult(
            action=action,
            original_attempt=original,
            retry_attempt=retry,
            observation=salvage.observation,
            completion_evaluation=salvage.completion_evaluation,
            retry_preparation=None,
            retry_required=True,
            workspace_prepared=False,
            idempotent_recognition=False,
        )
        return self._ensure_retry_prepared(base_result, request)

    def _ensure_retry_prepared(
        self,
        result: AttemptRecoveryResult,
        request: AttemptRetryRecoveryRequest,
    ) -> AttemptRecoveryResult:
        retry = result.retry_attempt
        if retry is None:
            return result
        preparation = self.preparation.prepare_attempt(
            retry.id,
            request.context_package_id,
            request.executor_binding,
            request.repository_path,
            request.workspace_root,
        )
        return result.model_copy(
            update={
                "retry_preparation": preparation,
                "workspace_prepared": True,
            }
        )

    def _exact_attempt_assessment(
        self,
        request: RecoveryActionRequest,
    ) -> RecoveryAssessmentRecord:
        assessment = self.assessments.assessment(request.recovery_assessment_id)
        if assessment.basis_fingerprint != request.expected_assessment_fingerprint:
            raise RuntimeInvariantViolation(
                "Recovery Assessment fingerprint does not match"
            )
        if assessment.subject_type is not RecoverySubjectType.ATTEMPT:
            raise RuntimeInvariantViolation(
                "S5-C requires an exact ATTEMPT Recovery Assessment"
            )
        return assessment

    @staticmethod
    def _require_retry_guidance(assessment: RecoveryAssessmentRecord) -> None:
        if not (
            assessment.classification is RecoveryClassification.RECOVERABLE
            and assessment.guidance is RecoveryGuidance.RETRY_WITH_NEW_ATTEMPT
            and assessment.safely_recoverable
        ):
            raise RuntimeInvariantViolation(
                "selected Recovery Assessment does not authorize a new Retry Attempt"
            )

    def _fresh_assessment(
        self,
        assessment: RecoveryAssessmentRecord,
    ) -> RecoveryAssessmentRecord:
        governed = assessment.governed_basis
        return self.assessments.assess_recovery(
            AttemptRecoveryAssessmentRequest(
                attempt_id=UUID(assessment.subject_identity),
                expected_work_unit_id=UUID(str(governed["work_unit_id"])),
                expected_generation=int(governed["attempt_generation"]),
            )
        )

    def _attempt_facts(self, assessment: RecoveryAssessmentRecord):
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            attempt = store.attempt(UUID(assessment.subject_identity))
            if attempt is None:
                raise RuntimeRecordNotFound(
                    f"Attempt not found: {assessment.subject_identity}"
                )
            return (
                attempt,
                store.execution_dispatch_for_attempt(attempt.id),
                store.attempt_preparation(attempt.id),
            )

    def _record_attempt_result(
        self,
        *,
        assessment: RecoveryAssessmentRecord,
        action_type: RecoveryActionType,
        outcome: RecoveryActionOutcome,
        observation,
        completion_evaluation,
        retry_attempt,
        retry_preparation,
        retry_required: bool,
        workspace_prepared: bool,
    ) -> AttemptRecoveryResult:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            original = store.attempt(UUID(assessment.subject_identity))
            if original is None:
                raise RuntimeRecordNotFound(
                    f"Attempt not found: {assessment.subject_identity}"
                )
            preparation = store.attempt_preparation(original.id)
            action = self._insert_attempt_action(
                store,
                assessment=assessment,
                action_type=action_type,
                outcome=outcome,
                original_attempt=original,
                retry_attempt=retry_attempt,
                workspace_identity=(
                    preparation.workspace.workspace_identity
                    if preparation is not None
                    else None
                ),
                observation_id=observation.id if observation is not None else None,
                completion_id=(
                    completion_evaluation.id
                    if completion_evaluation is not None
                    else None
                ),
                timestamp=timestamp,
            )
            self._append_transition(
                store,
                action=action,
                reason="ATTEMPT_RECOVERY_REALITY_RECORDED",
                timestamp=timestamp,
            )
            unit_of_work.commit()
        return AttemptRecoveryResult(
            action=action,
            original_attempt=original,
            retry_attempt=retry_attempt,
            observation=observation,
            completion_evaluation=completion_evaluation,
            retry_preparation=retry_preparation,
            retry_required=retry_required,
            workspace_prepared=workspace_prepared,
            idempotent_recognition=False,
        )

    def _insert_attempt_action(
        self,
        store: RuntimeStore,
        *,
        assessment: RecoveryAssessmentRecord,
        action_type: RecoveryActionType,
        outcome: RecoveryActionOutcome,
        original_attempt,
        retry_attempt,
        workspace_identity: str | None,
        observation_id: UUID | None,
        completion_id: UUID | None,
        timestamp: datetime,
    ) -> RecoveryActionRecord:
        basis = {
            "recovery_assessment_id": str(assessment.id),
            "assessment_basis_fingerprint": assessment.basis_fingerprint,
            "action_type": action_type.value,
            "old_attempt_id": str(original_attempt.id),
            "new_attempt_id": str(retry_attempt.id) if retry_attempt else None,
            "old_generation": original_attempt.generation,
            "new_generation": retry_attempt.generation if retry_attempt else None,
            "workspace_identity": workspace_identity,
            "repository_observation_id": (
                str(observation_id) if observation_id else None
            ),
            "completion_evaluation_id": str(completion_id) if completion_id else None,
            "outcome": outcome.value,
        }
        action_fingerprint = _fingerprint(basis)
        action_id = uuid5(
            NAMESPACE_URL,
            f"spg:recovery-action:{action_fingerprint}",
        )
        store.insert_recovery_action(
            {
                "id": action_id,
                "recovery_assessment_id": assessment.id,
                "assessment_basis_fingerprint": assessment.basis_fingerprint,
                "action_type": action_type.value,
                "subject_type": RecoverySubjectType.ATTEMPT.value,
                "subject_identity": assessment.subject_identity,
                "integration_effect_id": None,
                "candidate_id": None,
                "runtime_commit_id": None,
                "old_attempt_id": original_attempt.id,
                "new_attempt_id": retry_attempt.id if retry_attempt else None,
                "old_generation": original_attempt.generation,
                "new_generation": retry_attempt.generation if retry_attempt else None,
                "workspace_identity": workspace_identity,
                "repository_observation_id": observation_id,
                "completion_evaluation_id": completion_id,
                "action_basis_fingerprint": action_fingerprint,
                "outcome": outcome.value,
                "observed_repository_revision": None,
                "observed_tree_identity": None,
                "resolved_at": timestamp,
            }
        )
        action = store.recovery_action(action_id)
        if action is None:
            raise RuntimeInvariantViolation("Attempt Recovery Action was not constructed")
        return action

    def _existing_action_result(
        self,
        assessment: RecoveryAssessmentRecord,
        action_type: RecoveryActionType,
    ) -> AttemptRecoveryResult | None:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            action = store.recovery_action_for_assessment(assessment.id, action_type)
            if action is None:
                return None
            original = store.attempt(action.old_attempt_id)
            retry = (
                store.attempt(action.new_attempt_id)
                if action.new_attempt_id is not None
                else None
            )
            observation = (
                store.repository_observation_by_id(action.repository_observation_id)
                if action.repository_observation_id is not None
                else None
            )
            completion = (
                store.completion_evaluation(action.completion_evaluation_id)
                if action.completion_evaluation_id is not None
                else None
            )
            preparation = store.attempt_preparation(retry.id) if retry is not None else None
            if original is None:
                raise RuntimeInvariantViolation(
                    "Attempt Recovery Action original Attempt is missing"
                )
            return AttemptRecoveryResult(
                action=action,
                original_attempt=original,
                retry_attempt=retry,
                observation=observation,
                completion_evaluation=completion,
                retry_preparation=None,
                retry_required=(
                    action.outcome
                    in {RecoveryActionOutcome.INCOMPLETE, RecoveryActionOutcome.RETRY_CREATED}
                ),
                workspace_prepared=preparation is not None,
                idempotent_recognition=True,
            )

    @staticmethod
    def _append_transition(
        store: RuntimeStore,
        *,
        action: RecoveryActionRecord,
        reason: str,
        timestamp: datetime,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": "RECOVERY_ACTION",
                "entity_identity": str(action.id),
                "from_condition": None,
                "to_condition": action.outcome.value,
                "reason": reason,
                "actor_identity": ATTEMPT_RECOVERY_ACTOR,
                "correlation_identity": str(action.recovery_assessment_id),
                "created_at": timestamp,
            }
        )


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()
