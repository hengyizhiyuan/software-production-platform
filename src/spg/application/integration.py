"""S4-A authorized local repository-ref integration orchestration."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.domain.governance import (
    BaselineCandidateRecord,
    CandidateAuthorizationAction,
    CandidateCondition,
    HumanAuthorizationRecord,
)
from spg.domain.integration import (
    RepositoryEffectState,
    RepositoryEffectType,
    RepositoryIntegrationEffectRecord,
    RepositoryIntegrationRequest,
    RepositoryIntegrationResult,
)
from spg.domain.runtime import (
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
    WorkUnitCondition,
)
from spg.domain.verification import (
    ProductionAdmissibilityOutcome,
    VerificationResultValue,
)
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database, OptimisticConcurrencyConflict
from spg.infrastructure.persistence.runtime_store import RuntimeStore


INTEGRATION_ACTOR = "spg-runtime:repository-integration"


@dataclass(frozen=True, slots=True)
class _PreparedOperation:
    effect: RepositoryIntegrationEffectRecord
    repository_path: Path


class RepositoryIntegrationService:
    """Perform one authorized ref CAS without claiming Runtime Commit."""

    def __init__(
        self,
        database: Database,
        git: GitRepositoryIntegrationAdapter | None = None,
    ) -> None:
        self.database = database
        self.git = git or GitRepositoryIntegrationAdapter()

    def integrate_repository_candidate(
        self,
        request: RepositoryIntegrationRequest,
    ) -> RepositoryIntegrationResult:
        """Persist PREPARED, commit, then CAS and independently observe Git."""

        prepared = self._prepare_operation(request)
        effect = prepared.effect
        observed_before = self.git.read_ref(
            prepared.repository_path,
            effect.target_authoritative_ref,
        )

        if effect.state is RepositoryEffectState.CONVERGED:
            return RepositoryIntegrationResult(
                effect=effect,
                observed_repository_revision=observed_before,
                cas_attempted=False,
                converged=observed_before == effect.proposed_repository_revision,
            )

        if observed_before == effect.proposed_repository_revision:
            # A prior process may have completed Git CAS but not the local state write.
            # S4-A preserves this PREPARED truth for later S5 reconciliation.
            observed = self._record_nonconverged_observation(
                effect,
                observed_before,
            )
            return RepositoryIntegrationResult(
                effect=observed,
                observed_repository_revision=observed_before,
                cas_attempted=False,
                converged=False,
            )

        if observed_before != effect.expected_source_repository_revision:
            observed = self._record_nonconverged_observation(
                effect,
                observed_before,
            )
            return RepositoryIntegrationResult(
                effect=observed,
                observed_repository_revision=observed_before,
                cas_attempted=False,
                converged=False,
            )

        self.git.compare_and_swap_ref(
            prepared.repository_path,
            effect.target_authoritative_ref,
            effect.expected_source_repository_revision,
            effect.proposed_repository_revision,
        )
        independently_observed = self.git.read_ref(
            prepared.repository_path,
            effect.target_authoritative_ref,
        )
        if independently_observed == effect.proposed_repository_revision:
            converged = self._mark_converged(effect, independently_observed)
            return RepositoryIntegrationResult(
                effect=converged,
                observed_repository_revision=independently_observed,
                cas_attempted=True,
                converged=True,
            )

        observed = self._record_nonconverged_observation(
            effect,
            independently_observed,
        )
        return RepositoryIntegrationResult(
            effect=observed,
            observed_repository_revision=independently_observed,
            cas_attempted=True,
            converged=False,
        )

    def effect(self, effect_id: UUID) -> RepositoryIntegrationEffectRecord:
        with self.database.unit_of_work() as unit_of_work:
            effect = RuntimeStore(unit_of_work.session).repository_integration_effect(
                effect_id
            )
            if effect is None:
                raise RuntimeRecordNotFound(
                    f"Repository Integration Effect not found: {effect_id}"
                )
            return effect

    def _prepare_operation(
        self,
        request: RepositoryIntegrationRequest,
    ) -> _PreparedOperation:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            candidate = store.baseline_candidate(request.candidate_id)
            authorization = store.human_authorization(
                request.human_authorization_id
            )
            if candidate is None:
                raise RuntimeRecordNotFound(
                    f"Baseline Candidate not found: {request.candidate_id}"
                )
            if authorization is None:
                raise RuntimeRecordNotFound(
                    "Human Authorization not found: "
                    f"{request.human_authorization_id}"
                )
            repository_path = self._require_current_authorized_basis(
                store,
                request,
                candidate,
                authorization,
            )
            if not self.git.commit_exists(
                repository_path,
                candidate.proposed_commit_identity,
            ):
                raise RuntimeInvariantViolation(
                    "sealed Candidate proposed commit does not exist"
                )
            if (
                self.git.read_commit_tree(
                    repository_path,
                    candidate.proposed_commit_identity,
                )
                != candidate.proposed_tree_identity
            ):
                raise RuntimeInvariantViolation(
                    "sealed Candidate proposed commit tree does not match"
                )

            operation_fingerprint = _fingerprint(
                {
                    "effect_type": RepositoryEffectType.REPOSITORY_REF_ADVANCE.value,
                    "candidate_id": str(candidate.id),
                    "candidate_fingerprint": candidate.fingerprint,
                    "human_authorization_id": str(authorization.id),
                    "repository_identity": candidate.repository_identity,
                    "target_authoritative_ref": candidate.target_authoritative_ref,
                    "expected_source_repository_revision": (
                        candidate.expected_source_repository_revision
                    ),
                    "proposed_repository_revision": (
                        candidate.proposed_commit_identity
                    ),
                }
            )
            existing = store.repository_integration_effect_by_operation(
                operation_fingerprint
            )
            if existing is not None:
                return _PreparedOperation(
                    effect=existing,
                    repository_path=repository_path,
                )

            effect_id = uuid5(
                NAMESPACE_URL,
                f"spg:repository-integration:{operation_fingerprint}",
            )
            store.insert_repository_integration_effect(
                {
                    "id": effect_id,
                    "version": 0,
                    "effect_type": (
                        RepositoryEffectType.REPOSITORY_REF_ADVANCE.value
                    ),
                    "state": RepositoryEffectState.PREPARED.value,
                    "candidate_id": candidate.id,
                    "candidate_fingerprint": candidate.fingerprint,
                    "human_authorization_id": authorization.id,
                    "repository_identity": candidate.repository_identity,
                    "target_authoritative_ref": candidate.target_authoritative_ref,
                    "expected_source_repository_revision": (
                        candidate.expected_source_repository_revision
                    ),
                    "proposed_repository_revision": (
                        candidate.proposed_commit_identity
                    ),
                    "proposed_tree_identity": candidate.proposed_tree_identity,
                    "operation_fingerprint": operation_fingerprint,
                    "prepared_at": timestamp,
                    "observed_repository_revision": None,
                    "observed_at": None,
                    "converged_at": None,
                }
            )
            self._append_history(
                store,
                effect_id=effect_id,
                from_condition=None,
                to_condition=RepositoryEffectState.PREPARED.value,
                reason="AUTHORIZED_REPOSITORY_REF_ADVANCE_PREPARED",
                correlation=authorization.id,
                timestamp=timestamp,
            )
            effect = store.repository_integration_effect(effect_id)
            if effect is None:
                raise RuntimeInvariantViolation(
                    "Repository Integration Effect was not constructed"
                )
            unit_of_work.commit()
            return _PreparedOperation(effect=effect, repository_path=repository_path)

    @staticmethod
    def _require_current_authorized_basis(
        store: RuntimeStore,
        request: RepositoryIntegrationRequest,
        candidate: BaselineCandidateRecord,
        authorization: HumanAuthorizationRecord,
    ) -> Path:
        if candidate.condition is not CandidateCondition.SEALED:
            raise RuntimeInvariantViolation(
                "Repository Integration requires a SEALED Candidate"
            )
        if candidate.fingerprint != request.candidate_fingerprint:
            raise RuntimeInvariantViolation(
                "Repository Integration Candidate fingerprint does not match"
            )
        scope = authorization.scope
        if (
            authorization.candidate_id != candidate.id
            or authorization.candidate_fingerprint != candidate.fingerprint
            or authorization.source_baseline_id != candidate.source_baseline_id
            or authorization.repository_identity != candidate.repository_identity
            or authorization.target_authoritative_ref
            != candidate.target_authoritative_ref
            or authorization.expected_source_repository_revision
            != candidate.expected_source_repository_revision
            or authorization.proposed_repository_revision
            != candidate.proposed_commit_identity
            or scope.action
            is not CandidateAuthorizationAction.REPOSITORY_INTEGRATION
            or scope.repository_identity != candidate.repository_identity
            or scope.target_authoritative_ref != candidate.target_authoritative_ref
            or scope.expected_source_repository_revision
            != candidate.expected_source_repository_revision
            or scope.proposed_repository_revision
            != candidate.proposed_commit_identity
        ):
            raise RuntimeInvariantViolation(
                "Human Authorization does not cover the exact repository integration"
            )

        pointer = store.current_pointer(for_update=True)
        source_baseline = store.snapshot(candidate.source_baseline_id)
        run = store.run(candidate.production_run_id, for_update=True)
        plan = store.plan_revision(candidate.plan_revision_id)
        proposed = store.proposed_snapshot(candidate.proposed_snapshot_id)
        admissibility = store.production_admissibility(
            candidate.production_admissibility_id
        )
        if any(
            item is None
            for item in (
                pointer,
                source_baseline,
                run,
                plan,
                proposed,
                admissibility,
            )
        ):
            raise RuntimeInvariantViolation(
                "Repository Integration production lineage is incomplete"
            )
        if (
            pointer.snapshot_id != candidate.source_baseline_id
            or source_baseline.repository_identity != candidate.repository_identity
            or source_baseline.repository_ref != candidate.target_authoritative_ref
            or source_baseline.repository_revision
            != candidate.expected_source_repository_revision
            or run.current_plan_revision_id != candidate.plan_revision_id
            or run.source_baseline_id != candidate.source_baseline_id
            or plan.production_run_id != candidate.production_run_id
            or plan.source_baseline_id != candidate.source_baseline_id
            or proposed.production_run_id != candidate.production_run_id
            or proposed.plan_revision_id != candidate.plan_revision_id
            or proposed.source_baseline_id != candidate.source_baseline_id
            or proposed.repository_identity != candidate.repository_identity
            or proposed.repository_ref != candidate.target_authoritative_ref
            or proposed.authoritative_ref_revision
            != candidate.expected_source_repository_revision
            or proposed.proposed_commit_identity
            != candidate.proposed_commit_identity
            or proposed.tree_identity != candidate.proposed_tree_identity
            or admissibility.id != candidate.production_admissibility_id
            or admissibility.basis_fingerprint
            != candidate.production_admissibility_basis_fingerprint
            or admissibility.outcome
            is not ProductionAdmissibilityOutcome.ADMISSIBLE
        ):
            raise RuntimeInvariantViolation(
                "Repository Integration Candidate basis is stale or inconsistent"
            )

        for work_unit_id in candidate.satisfied_work_unit_ids:
            work_unit = store.work_unit(work_unit_id, for_update=True)
            if (
                work_unit is None
                or work_unit.condition is not WorkUnitCondition.SATISFIED
                or work_unit.production_run_id != candidate.production_run_id
                or work_unit.plan_revision_id != candidate.plan_revision_id
                or work_unit.source_baseline_id != candidate.source_baseline_id
            ):
                raise RuntimeInvariantViolation(
                    "Repository Integration requires current SATISFIED PWU lineage"
                )

        for verification_id in candidate.verification_record_ids:
            verification = store.verification_record(verification_id)
            if (
                verification is None
                or verification.result is not VerificationResultValue.PASS
                or verification.proposed_snapshot_id != candidate.proposed_snapshot_id
                or verification.proposed_commit_identity
                != candidate.proposed_commit_identity
                or verification.tree_identity != candidate.proposed_tree_identity
                or verification.plan_revision_id != candidate.plan_revision_id
                or verification.source_baseline_id != candidate.source_baseline_id
            ):
                raise RuntimeInvariantViolation(
                    "Repository Integration Verification basis is stale or wrong"
                )

        observation = store.repository_observation_by_id(
            proposed.repository_observation_id
        )
        dispatch = (
            store.execution_dispatch(observation.dispatch_id)
            if observation is not None
            else None
        )
        if (
            observation is None
            or dispatch is None
            or observation.repository_identity != candidate.repository_identity
            or dispatch.workspace.repository_identity != candidate.repository_identity
        ):
            raise RuntimeInvariantViolation(
                "Repository Integration repository path lineage is incomplete"
            )
        return dispatch.workspace.repository_path

    def _record_nonconverged_observation(
        self,
        expected: RepositoryIntegrationEffectRecord,
        observed_revision: str,
    ) -> RepositoryIntegrationEffectRecord:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            current = store.repository_integration_effect(
                expected.id,
                for_update=True,
            )
            if current is None:
                raise RuntimeInvariantViolation(
                    "Repository Integration Effect disappeared"
                )
            if current.state is RepositoryEffectState.CONVERGED:
                return current
            if current.version != expected.version:
                raise OptimisticConcurrencyConflict(
                    "Repository Integration Effect changed during observation"
                )
            store.record_repository_effect_observation(
                current.id,
                current.version,
                observed_revision,
                timestamp,
            )
            observed = store.repository_integration_effect(current.id)
            if observed is None:
                raise RuntimeInvariantViolation(
                    "Repository Integration observation was not persisted"
                )
            unit_of_work.commit()
            return observed

    def _mark_converged(
        self,
        expected: RepositoryIntegrationEffectRecord,
        observed_revision: str,
    ) -> RepositoryIntegrationEffectRecord:
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            current = store.repository_integration_effect(
                expected.id,
                for_update=True,
            )
            if current is None:
                raise RuntimeInvariantViolation(
                    "Repository Integration Effect disappeared"
                )
            if current.state is RepositoryEffectState.CONVERGED:
                return current
            if current.version != expected.version:
                raise OptimisticConcurrencyConflict(
                    "Repository Integration Effect changed before convergence"
                )
            if observed_revision != current.proposed_repository_revision:
                raise RuntimeInvariantViolation(
                    "only exact independently observed revision may converge"
                )
            store.mark_repository_effect_converged(
                current.id,
                current.version,
                observed_revision,
                timestamp,
            )
            self._append_history(
                store,
                effect_id=current.id,
                from_condition=RepositoryEffectState.PREPARED.value,
                to_condition=RepositoryEffectState.CONVERGED.value,
                reason="INDEPENDENT_REPOSITORY_REF_OBSERVATION_CONVERGED",
                correlation=current.human_authorization_id,
                timestamp=timestamp,
            )
            converged = store.repository_integration_effect(current.id)
            if converged is None:
                raise RuntimeInvariantViolation(
                    "Repository Integration convergence was not persisted"
                )
            unit_of_work.commit()
            return converged

    @staticmethod
    def _append_history(
        store: RuntimeStore,
        *,
        effect_id: UUID,
        from_condition: str | None,
        to_condition: str,
        reason: str,
        correlation: UUID,
        timestamp: datetime,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": "REPOSITORY_INTEGRATION_EFFECT",
                "entity_identity": str(effect_id),
                "from_condition": from_condition,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": INTEGRATION_ACTOR,
                "correlation_identity": str(correlation),
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
