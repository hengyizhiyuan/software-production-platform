"""S5-B exact repository/runtime reconciliation without Git mutation."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.integration import RepositoryIntegrationService
from spg.application.recovery import RecoveryAssessmentService
from spg.application.runtime_commit import RuntimeCommitService
from spg.domain.integration import (
    RepositoryEffectState,
    RepositoryIntegrationRequest,
)
from spg.domain.recovery import (
    RecoveryActionOutcome,
    RecoveryActionRecord,
    RecoveryActionRequest,
    RecoveryActionType,
    RecoveryAssessmentRecord,
    RecoveryAssessmentStale,
    RecoveryClassification,
    RecoveryGuidance,
    RecoveryReconciliationResult,
    RecoverySubjectType,
    RepositoryRecoveryAssessmentRequest,
)
from spg.domain.runtime import RuntimeInvariantViolation, RuntimeRecordNotFound
from spg.domain.runtime_commit import RuntimeCommitRequest
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


RECONCILIATION_ACTOR = "spg-runtime:reconciliation"


class RecoveryReconciliationService:
    """Repair only independently proven local repository/runtime knowledge."""

    def __init__(
        self,
        database: Database,
        git: GitRepositoryIntegrationAdapter | None = None,
    ) -> None:
        self.database = database
        self.git = git or GitRepositoryIntegrationAdapter()
        self.assessments = RecoveryAssessmentService(database, git=self.git)
        self.runtime_commits = RuntimeCommitService(database, git=self.git)

    def record_external_convergence(
        self,
        request: RecoveryActionRequest,
    ) -> RecoveryReconciliationResult:
        assessment = self._exact_assessment(request)
        self._require_assessment_action(
            assessment,
            RecoveryClassification.RECOVERABLE,
            RecoveryGuidance.RECORD_EXTERNAL_CONVERGENCE,
        )
        existing = self._existing_result(
            assessment,
            RecoveryActionType.RECORD_EXTERNAL_CONVERGENCE,
        )
        if existing is not None:
            return existing

        current = self._fresh_repository_assessment(assessment)
        if current.id != assessment.id:
            raise RecoveryAssessmentStale(
                "repository Reality changed after the selected Recovery Assessment"
            )

        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            effect = store.repository_integration_effect(
                UUID(assessment.subject_identity),
                for_update=True,
            )
            if effect is None:
                raise RuntimeRecordNotFound(
                    f"Repository Integration Effect not found: {assessment.subject_identity}"
                )
            if effect.state is not RepositoryEffectState.PREPARED:
                raise RecoveryAssessmentStale(
                    "selected assessment no longer describes a PREPARED effect"
                )
            candidate = store.baseline_candidate(effect.candidate_id)
            authorization = store.human_authorization(effect.human_authorization_id)
            if candidate is None or authorization is None:
                raise RuntimeInvariantViolation(
                    "reconciliation Candidate/Authorization lineage is incomplete"
                )
            repository_path = RepositoryIntegrationService._require_current_authorized_basis(
                store,
                RepositoryIntegrationRequest(
                    candidate_id=candidate.id,
                    candidate_fingerprint=candidate.fingerprint,
                    human_authorization_id=authorization.id,
                ),
                candidate,
                authorization,
            )
            observed_revision, observed_tree = self._observe_exact_candidate(
                repository_path,
                effect.target_authoritative_ref,
                effect.proposed_repository_revision,
                effect.proposed_tree_identity,
            )
            action_fingerprint = _fingerprint(
                {
                    "recovery_assessment_id": str(assessment.id),
                    "assessment_basis_fingerprint": assessment.basis_fingerprint,
                    "action_type": (
                        RecoveryActionType.RECORD_EXTERNAL_CONVERGENCE.value
                    ),
                    "integration_effect_id": str(effect.id),
                    "integration_operation_fingerprint": effect.operation_fingerprint,
                    "candidate_id": str(candidate.id),
                    "candidate_fingerprint": candidate.fingerprint,
                    "observed_repository_revision": observed_revision,
                    "observed_tree_identity": observed_tree,
                }
            )
            action_id = uuid5(
                NAMESPACE_URL,
                f"spg:recovery-action:{action_fingerprint}",
            )
            store.mark_repository_effect_converged(
                effect.id,
                effect.version,
                observed_revision,
                timestamp,
            )
            self._insert_action(
                store,
                action_id=action_id,
                assessment=assessment,
                action_type=RecoveryActionType.RECORD_EXTERNAL_CONVERGENCE,
                effect_id=effect.id,
                candidate_id=candidate.id,
                runtime_commit_id=None,
                action_fingerprint=action_fingerprint,
                outcome=RecoveryActionOutcome.APPLIED,
                observed_revision=observed_revision,
                observed_tree=observed_tree,
                timestamp=timestamp,
            )
            self._append_transition(
                store,
                entity_type="REPOSITORY_INTEGRATION_EFFECT",
                entity_identity=effect.id,
                from_condition=RepositoryEffectState.PREPARED.value,
                to_condition=RepositoryEffectState.CONVERGED.value,
                reason="RECOVERY_INDEPENDENT_REALITY_CONFIRMED",
                correlation=action_id,
                timestamp=timestamp,
            )
            self._append_transition(
                store,
                entity_type="RECOVERY_ACTION",
                entity_identity=action_id,
                from_condition=None,
                to_condition=RecoveryActionOutcome.APPLIED.value,
                reason="EXTERNAL_CONVERGENCE_RECORDED_LOCALLY",
                correlation=assessment.id,
                timestamp=timestamp,
            )
            action = store.recovery_action(action_id)
            converged = store.repository_integration_effect(effect.id)
            if action is None or converged is None:
                raise RuntimeInvariantViolation(
                    "external convergence reconciliation was not constructed"
                )
            unit_of_work.commit()
            return RecoveryReconciliationResult(
                action=action,
                effect=converged,
                runtime_commit=None,
                idempotent_recognition=False,
            )

    def retry_runtime_commit_from_recovery(
        self,
        request: RecoveryActionRequest,
    ) -> RecoveryReconciliationResult:
        assessment = self._exact_assessment(request)
        if assessment.guidance not in {
            RecoveryGuidance.RETRY_RUNTIME_COMMIT,
            RecoveryGuidance.NO_ACTION,
        }:
            raise RuntimeInvariantViolation(
                "selected Recovery Assessment does not authorize Runtime Commit reconciliation"
            )
        existing_action = self._existing_result(
            assessment,
            RecoveryActionType.RETRY_RUNTIME_COMMIT,
        )
        if existing_action is not None:
            return existing_action

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            effect = store.repository_integration_effect(
                UUID(assessment.subject_identity)
            )
            if effect is None:
                raise RuntimeRecordNotFound(
                    f"Repository Integration Effect not found: {assessment.subject_identity}"
                )
            candidate = store.baseline_candidate(effect.candidate_id)
            if candidate is None:
                raise RuntimeInvariantViolation(
                    "Runtime Commit reconciliation Candidate is missing"
                )
            normal_request = RuntimeCommitRequest(
                candidate_id=candidate.id,
                candidate_fingerprint=candidate.fingerprint,
                human_authorization_id=effect.human_authorization_id,
                repository_integration_effect_id=effect.id,
            )
            commit_before = store.runtime_commit_for_candidate(candidate.id)

        current = self._fresh_repository_assessment(assessment)
        if commit_before is None and current.id != assessment.id:
            raise RecoveryAssessmentStale(
                "repository/runtime Reality changed after the selected Recovery Assessment"
            )
        if commit_before is not None and not (
            current.classification is RecoveryClassification.COHERENT
            and current.guidance is RecoveryGuidance.NO_ACTION
        ):
            raise RecoveryAssessmentStale(
                "existing Runtime Commit is not coherent with current repository Reality"
            )

        commit_result = self.runtime_commits.commit_runtime_candidate(normal_request)
        observed_tree = self.git.read_commit_tree(
            self._repository_path(candidate.id),
            candidate.proposed_commit_identity,
        )
        outcome = (
            RecoveryActionOutcome.NO_ACTION
            if commit_result.idempotent_recognition
            else RecoveryActionOutcome.APPLIED
        )
        action = self._record_runtime_commit_action(
            assessment=assessment,
            effect_id=effect.id,
            candidate_id=candidate.id,
            runtime_commit_id=commit_result.runtime_commit.id,
            runtime_commit_fingerprint=commit_result.runtime_commit.commit_fingerprint,
            observed_revision=commit_result.observed_repository_revision,
            observed_tree=observed_tree,
            outcome=outcome,
        )
        return RecoveryReconciliationResult(
            action=action,
            effect=self._effect(effect.id),
            runtime_commit=commit_result.runtime_commit,
            idempotent_recognition=commit_result.idempotent_recognition,
        )

    def action(self, action_id: UUID) -> RecoveryActionRecord:
        with self.database.unit_of_work() as unit_of_work:
            action = RuntimeStore(unit_of_work.session).recovery_action(action_id)
            if action is None:
                raise RuntimeRecordNotFound(f"Recovery Action not found: {action_id}")
            return action

    def _exact_assessment(
        self,
        request: RecoveryActionRequest,
    ) -> RecoveryAssessmentRecord:
        assessment = self.assessments.assessment(request.recovery_assessment_id)
        if assessment.basis_fingerprint != request.expected_assessment_fingerprint:
            raise RuntimeInvariantViolation(
                "Recovery Assessment fingerprint does not match"
            )
        if assessment.subject_type is not RecoverySubjectType.REPOSITORY_INTEGRATION:
            raise RuntimeInvariantViolation(
                "S5-B supports only Repository Integration recovery subjects"
            )
        return assessment

    @staticmethod
    def _require_assessment_action(
        assessment: RecoveryAssessmentRecord,
        classification: RecoveryClassification,
        guidance: RecoveryGuidance,
    ) -> None:
        if (
            assessment.classification is not classification
            or assessment.guidance is not guidance
            or not assessment.safely_recoverable
        ):
            raise RuntimeInvariantViolation(
                "selected Recovery Assessment does not match the requested action"
            )

    def _fresh_repository_assessment(
        self,
        assessment: RecoveryAssessmentRecord,
    ) -> RecoveryAssessmentRecord:
        operation_fingerprint = assessment.governed_basis.get(
            "integration_operation_fingerprint"
        )
        if not isinstance(operation_fingerprint, str):
            raise RuntimeInvariantViolation(
                "Recovery Assessment lacks exact integration operation lineage"
            )
        return self.assessments.assess_recovery(
            RepositoryRecoveryAssessmentRequest(
                repository_integration_effect_id=UUID(assessment.subject_identity),
                expected_operation_fingerprint=operation_fingerprint,
            )
        )

    def _existing_result(
        self,
        assessment: RecoveryAssessmentRecord,
        action_type: RecoveryActionType,
    ) -> RecoveryReconciliationResult | None:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            action = store.recovery_action_for_assessment(assessment.id, action_type)
            if action is None:
                return None
            effect = store.repository_integration_effect(action.integration_effect_id)
            runtime_commit = (
                store.runtime_commit(action.runtime_commit_id)
                if action.runtime_commit_id is not None
                else None
            )
            if effect is None:
                raise RuntimeInvariantViolation(
                    "Recovery Action target Effect is missing"
                )
            return RecoveryReconciliationResult(
                action=action,
                effect=effect,
                runtime_commit=runtime_commit,
                idempotent_recognition=True,
            )

    def _observe_exact_candidate(
        self,
        repository_path,
        repository_ref: str,
        proposed_revision: str,
        proposed_tree: str,
    ) -> tuple[str, str]:
        observed_revision = self.git.read_ref(repository_path, repository_ref)
        if observed_revision != proposed_revision:
            raise RecoveryAssessmentStale(
                "authoritative repository ref no longer equals the proposed revision"
            )
        if not self.git.commit_exists(repository_path, proposed_revision):
            raise RecoveryAssessmentStale("proposed repository commit no longer exists")
        observed_tree = self.git.read_commit_tree(repository_path, proposed_revision)
        if observed_tree != proposed_tree:
            raise RecoveryAssessmentStale(
                "proposed repository commit tree no longer matches the Candidate"
            )
        return observed_revision, observed_tree

    def _repository_path(self, candidate_id: UUID):
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            candidate = store.baseline_candidate(candidate_id)
            if candidate is None:
                raise RuntimeRecordNotFound(f"Baseline Candidate not found: {candidate_id}")
            proposed = store.proposed_snapshot(candidate.proposed_snapshot_id)
            observation = (
                store.repository_observation_by_id(proposed.repository_observation_id)
                if proposed is not None
                else None
            )
            dispatch = (
                store.execution_dispatch(observation.dispatch_id)
                if observation is not None
                else None
            )
            if dispatch is None:
                raise RuntimeInvariantViolation(
                    "reconciliation repository path lineage is incomplete"
                )
            return dispatch.workspace.repository_path

    def _record_runtime_commit_action(
        self,
        *,
        assessment: RecoveryAssessmentRecord,
        effect_id: UUID,
        candidate_id: UUID,
        runtime_commit_id: UUID,
        runtime_commit_fingerprint: str,
        observed_revision: str,
        observed_tree: str,
        outcome: RecoveryActionOutcome,
    ) -> RecoveryActionRecord:
        timestamp = datetime.now(UTC)
        action_fingerprint = _fingerprint(
            {
                "recovery_assessment_id": str(assessment.id),
                "assessment_basis_fingerprint": assessment.basis_fingerprint,
                "action_type": RecoveryActionType.RETRY_RUNTIME_COMMIT.value,
                "integration_effect_id": str(effect_id),
                "candidate_id": str(candidate_id),
                "runtime_commit_id": str(runtime_commit_id),
                "runtime_commit_fingerprint": runtime_commit_fingerprint,
                "observed_repository_revision": observed_revision,
                "observed_tree_identity": observed_tree,
            }
        )
        action_id = uuid5(
            NAMESPACE_URL,
            f"spg:recovery-action:{action_fingerprint}",
        )
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            existing = store.recovery_action_for_assessment(
                assessment.id,
                RecoveryActionType.RETRY_RUNTIME_COMMIT,
            )
            if existing is not None:
                return existing
            self._insert_action(
                store,
                action_id=action_id,
                assessment=assessment,
                action_type=RecoveryActionType.RETRY_RUNTIME_COMMIT,
                effect_id=effect_id,
                candidate_id=candidate_id,
                runtime_commit_id=runtime_commit_id,
                action_fingerprint=action_fingerprint,
                outcome=outcome,
                observed_revision=observed_revision,
                observed_tree=observed_tree,
                timestamp=timestamp,
            )
            self._append_transition(
                store,
                entity_type="RECOVERY_ACTION",
                entity_identity=action_id,
                from_condition=None,
                to_condition=outcome.value,
                reason="RUNTIME_COMMIT_RECONCILED",
                correlation=assessment.id,
                timestamp=timestamp,
            )
            action = store.recovery_action(action_id)
            if action is None:
                raise RuntimeInvariantViolation(
                    "Runtime Commit Recovery Action was not constructed"
                )
            unit_of_work.commit()
            return action

    @staticmethod
    def _insert_action(
        store: RuntimeStore,
        *,
        action_id: UUID,
        assessment: RecoveryAssessmentRecord,
        action_type: RecoveryActionType,
        effect_id: UUID,
        candidate_id: UUID,
        runtime_commit_id: UUID | None,
        action_fingerprint: str,
        outcome: RecoveryActionOutcome,
        observed_revision: str,
        observed_tree: str,
        timestamp: datetime,
    ) -> None:
        store.insert_recovery_action(
            {
                "id": action_id,
                "recovery_assessment_id": assessment.id,
                "assessment_basis_fingerprint": assessment.basis_fingerprint,
                "action_type": action_type.value,
                "subject_type": assessment.subject_type.value,
                "subject_identity": assessment.subject_identity,
                "integration_effect_id": effect_id,
                "candidate_id": candidate_id,
                "runtime_commit_id": runtime_commit_id,
                "action_basis_fingerprint": action_fingerprint,
                "outcome": outcome.value,
                "observed_repository_revision": observed_revision,
                "observed_tree_identity": observed_tree,
                "resolved_at": timestamp,
            }
        )

    @staticmethod
    def _append_transition(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_identity: UUID,
        from_condition: str | None,
        to_condition: str,
        reason: str,
        correlation: UUID,
        timestamp: datetime,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": entity_type,
                "entity_identity": str(entity_identity),
                "from_condition": from_condition,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": RECONCILIATION_ACTOR,
                "correlation_identity": str(correlation),
                "created_at": timestamp,
            }
        )

    def _effect(self, effect_id: UUID):
        with self.database.unit_of_work() as unit_of_work:
            effect = RuntimeStore(unit_of_work.session).repository_integration_effect(
                effect_id
            )
            if effect is None:
                raise RuntimeRecordNotFound(
                    f"Repository Integration Effect not found: {effect_id}"
                )
            return effect


def _fingerprint(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return sha256(canonical).hexdigest()
