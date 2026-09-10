"""S4-B local Runtime Commit orchestration."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.domain.completion import CompletionEvaluationOutcome
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
)
from spg.domain.runtime import (
    BaselinePointerRecord,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
    SnapshotCondition,
    SnapshotRecord,
    WorkUnitCondition,
)
from spg.domain.runtime_commit import (
    RuntimeCommitRecord,
    RuntimeCommitRequest,
    RuntimeCommitResult,
)
from spg.domain.verification import (
    ProductionAdmissibilityOutcome,
    VerificationResultValue,
)
from spg.infrastructure.git_integration import GitRepositoryIntegrationAdapter
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


RUNTIME_COMMIT_ACTOR = "spg-runtime:runtime-commit"


@dataclass(frozen=True, slots=True)
class _CommitBasis:
    candidate: BaselineCandidateRecord
    authorization: HumanAuthorizationRecord
    effect: RepositoryIntegrationEffectRecord
    pointer: BaselinePointerRecord
    source_baseline: SnapshotRecord
    repository_path: Path
    commit_fingerprint: str


class RuntimeCommitService:
    """Admit already-converged repository Reality as a new Trusted Baseline."""

    def __init__(
        self,
        database: Database,
        git: GitRepositoryIntegrationAdapter | None = None,
    ) -> None:
        self.database = database
        self.git = git or GitRepositoryIntegrationAdapter()

    def commit_runtime_candidate(
        self,
        request: RuntimeCommitRequest,
    ) -> RuntimeCommitResult:
        """Revalidate and atomically create Snapshot, advance pointer, and audit."""

        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            basis = self._require_exact_basis(store, request)

            observed_revision = self.git.read_ref(
                basis.repository_path,
                basis.candidate.target_authoritative_ref,
            )
            if observed_revision != basis.candidate.proposed_commit_identity:
                raise RuntimeInvariantViolation(
                    "authoritative repository ref is not the exact proposed revision"
                )
            if not self.git.commit_exists(
                basis.repository_path,
                basis.candidate.proposed_commit_identity,
            ):
                raise RuntimeInvariantViolation(
                    "sealed Candidate proposed commit does not exist"
                )
            observed_tree = self.git.read_commit_tree(
                basis.repository_path,
                basis.candidate.proposed_commit_identity,
            )
            if observed_tree != basis.candidate.proposed_tree_identity:
                raise RuntimeInvariantViolation(
                    "sealed Candidate proposed commit tree does not match"
                )

            existing = store.runtime_commit_by_fingerprint(
                basis.commit_fingerprint
            )
            if existing is not None:
                return self._existing_result(
                    store,
                    existing,
                    basis.pointer,
                    observed_revision,
                )
            if store.runtime_commit_for_candidate(basis.candidate.id) is not None:
                raise RuntimeInvariantViolation(
                    "Candidate already belongs to a different Runtime Commit basis"
                )
            if basis.pointer.snapshot_id != basis.candidate.source_baseline_id:
                raise RuntimeInvariantViolation(
                    "Current Trusted Baseline is not the exact Candidate Source Baseline"
                )

            new_baseline_id = uuid5(
                NAMESPACE_URL,
                f"spg:trusted-baseline:{basis.commit_fingerprint}",
            )
            runtime_commit_id = uuid5(
                NAMESPACE_URL,
                f"spg:runtime-commit:{basis.commit_fingerprint}",
            )
            candidate = basis.candidate
            store.insert_snapshot(
                {
                    "id": new_baseline_id,
                    "condition": SnapshotCondition.TRUSTED.value,
                    "repository_identity": candidate.repository_identity,
                    "repository_ref": candidate.target_authoritative_ref,
                    "repository_revision": candidate.proposed_commit_identity,
                    "source_baseline_id": candidate.source_baseline_id,
                    "created_at": timestamp,
                }
            )
            store.insert_runtime_commit(
                {
                    "id": runtime_commit_id,
                    "candidate_id": candidate.id,
                    "candidate_fingerprint": candidate.fingerprint,
                    "human_authorization_id": basis.authorization.id,
                    "repository_integration_effect_id": basis.effect.id,
                    "source_baseline_id": candidate.source_baseline_id,
                    "new_baseline_id": new_baseline_id,
                    "production_run_id": candidate.production_run_id,
                    "plan_revision_id": candidate.plan_revision_id,
                    "repository_identity": candidate.repository_identity,
                    "target_authoritative_ref": candidate.target_authoritative_ref,
                    "expected_source_repository_revision": (
                        candidate.expected_source_repository_revision
                    ),
                    "repository_revision": candidate.proposed_commit_identity,
                    "repository_tree_identity": candidate.proposed_tree_identity,
                    "satisfied_work_unit_ids": [
                        str(item) for item in candidate.satisfied_work_unit_ids
                    ],
                    "completion_evaluation_ids": [
                        str(item) for item in candidate.completion_evaluation_ids
                    ],
                    "verification_record_ids": [
                        str(item) for item in candidate.verification_record_ids
                    ],
                    "production_admissibility_id": (
                        candidate.production_admissibility_id
                    ),
                    "production_admissibility_basis_fingerprint": (
                        candidate.production_admissibility_basis_fingerprint
                    ),
                    "commit_fingerprint": basis.commit_fingerprint,
                    "committed_at": timestamp,
                }
            )
            store.update_baseline_pointer(
                basis.pointer.version,
                new_baseline_id,
                expected_snapshot_id=candidate.source_baseline_id,
            )
            self._append_history(
                store,
                entity_type="RUNTIME_COMMIT",
                entity_identity=runtime_commit_id,
                from_condition=None,
                to_condition="COMMITTED",
                reason="EXACT_GOVERNED_REALITY_COMMITTED",
                correlation=candidate.id,
                timestamp=timestamp,
            )
            self._append_history(
                store,
                entity_type="CURRENT_TRUSTED_BASELINE_POINTER",
                entity_identity=UUID(int=0),
                from_condition=str(candidate.source_baseline_id),
                to_condition=str(new_baseline_id),
                reason="RUNTIME_COMMIT_BASELINE_ADVANCED",
                correlation=runtime_commit_id,
                timestamp=timestamp,
            )

            runtime_commit = store.runtime_commit(runtime_commit_id)
            trusted_baseline = store.snapshot(new_baseline_id)
            pointer = store.current_pointer(source_baseline_id=candidate.source_baseline_id)
            if runtime_commit is None or trusted_baseline is None or pointer is None:
                raise RuntimeInvariantViolation(
                    "Runtime Commit transaction did not construct complete state"
                )
            result = RuntimeCommitResult(
                runtime_commit=runtime_commit,
                trusted_baseline=trusted_baseline,
                current_pointer=pointer,
                observed_repository_revision=observed_revision,
                idempotent_recognition=False,
            )
            unit_of_work.commit()
            return result

    def runtime_commit(self, commit_id: UUID) -> RuntimeCommitRecord:
        with self.database.unit_of_work() as unit_of_work:
            record = RuntimeStore(unit_of_work.session).runtime_commit(commit_id)
            if record is None:
                raise RuntimeRecordNotFound(f"Runtime Commit not found: {commit_id}")
            return record

    def _require_exact_basis(
        self,
        store: RuntimeStore,
        request: RuntimeCommitRequest,
    ) -> _CommitBasis:
        candidate = store.baseline_candidate(request.candidate_id)
        authorization = store.human_authorization(request.human_authorization_id)
        effect = store.repository_integration_effect(
            request.repository_integration_effect_id,
            for_update=True,
        )
        if candidate is None:
            raise RuntimeRecordNotFound(
                f"Baseline Candidate not found: {request.candidate_id}"
            )
        if authorization is None:
            raise RuntimeRecordNotFound(
                f"Human Authorization not found: {request.human_authorization_id}"
            )
        if effect is None:
            raise RuntimeRecordNotFound(
                "Repository Integration Effect not found: "
                f"{request.repository_integration_effect_id}"
            )
        if candidate.condition is not CandidateCondition.SEALED:
            raise RuntimeInvariantViolation("Runtime Commit requires a SEALED Candidate")
        if candidate.fingerprint != request.candidate_fingerprint:
            raise RuntimeInvariantViolation(
                "Runtime Commit Candidate fingerprint does not match"
            )
        self._require_exact_authorization(candidate, authorization)
        self._require_converged_effect(candidate, authorization, effect)

        pointer = store.current_pointer(source_baseline_id=candidate.source_baseline_id, for_update=True)
        source_baseline = store.snapshot(candidate.source_baseline_id)
        run = store.run(candidate.production_run_id, for_update=True)
        plan = store.plan_revision(candidate.plan_revision_id)
        proposed = store.proposed_snapshot(candidate.proposed_snapshot_id)
        admissibility = store.production_admissibility(
            candidate.production_admissibility_id
        )
        if any(
            item is None
            for item in (pointer, source_baseline, run, plan, proposed, admissibility)
        ):
            raise RuntimeInvariantViolation("Runtime Commit production lineage is incomplete")
        if (
            source_baseline.condition is not SnapshotCondition.TRUSTED
            or source_baseline.id != candidate.source_baseline_id
            or source_baseline.repository_identity != candidate.repository_identity
            or source_baseline.repository_ref != candidate.target_authoritative_ref
            or source_baseline.repository_revision
            != candidate.expected_source_repository_revision
            or run.source_baseline_id != candidate.source_baseline_id
            or run.current_plan_revision_id != candidate.plan_revision_id
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
            or proposed.completion_evaluation_id
            not in candidate.completion_evaluation_ids
            or admissibility.id != candidate.production_admissibility_id
            or admissibility.basis_fingerprint
            != candidate.production_admissibility_basis_fingerprint
            or admissibility.outcome
            is not ProductionAdmissibilityOutcome.ADMISSIBLE
            or admissibility.production_run_id != candidate.production_run_id
            or admissibility.plan_revision_id != candidate.plan_revision_id
            or admissibility.source_baseline_id != candidate.source_baseline_id
            or admissibility.proposed_snapshot_id != candidate.proposed_snapshot_id
            or admissibility.completion_evaluation_id
            not in candidate.completion_evaluation_ids
            or set(admissibility.verification_record_ids)
            != set(candidate.verification_record_ids)
        ):
            raise RuntimeInvariantViolation(
                "Runtime Commit Candidate production basis is stale or inconsistent"
            )

        self._require_satisfied_work_units(store, candidate)
        self._require_completion_and_work_products(store, candidate, proposed)
        self._require_verification(store, candidate)

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
            or observation.source_baseline_id != candidate.source_baseline_id
            or dispatch.source_baseline_id != candidate.source_baseline_id
            or dispatch.workspace.repository_identity != candidate.repository_identity
        ):
            raise RuntimeInvariantViolation(
                "Runtime Commit repository path lineage is incomplete"
            )

        commit_fingerprint = _fingerprint(
            {
                "candidate_id": str(candidate.id),
                "candidate_fingerprint": candidate.fingerprint,
                "human_authorization_id": str(authorization.id),
                "repository_integration_effect_id": str(effect.id),
                "integration_operation_fingerprint": effect.operation_fingerprint,
                "source_baseline_id": str(candidate.source_baseline_id),
                "production_run_id": str(candidate.production_run_id),
                "plan_revision_id": str(candidate.plan_revision_id),
                "repository_identity": candidate.repository_identity,
                "target_authoritative_ref": candidate.target_authoritative_ref,
                "expected_source_repository_revision": (
                    candidate.expected_source_repository_revision
                ),
                "repository_revision": candidate.proposed_commit_identity,
                "repository_tree_identity": candidate.proposed_tree_identity,
                "satisfied_work_unit_ids": sorted(
                    str(item) for item in candidate.satisfied_work_unit_ids
                ),
                "completion_evaluation_ids": sorted(
                    str(item) for item in candidate.completion_evaluation_ids
                ),
                "verification_record_ids": sorted(
                    str(item) for item in candidate.verification_record_ids
                ),
                "production_admissibility_id": str(
                    candidate.production_admissibility_id
                ),
                "production_admissibility_basis_fingerprint": (
                    candidate.production_admissibility_basis_fingerprint
                ),
            }
        )
        return _CommitBasis(
            candidate=candidate,
            authorization=authorization,
            effect=effect,
            pointer=pointer,
            source_baseline=source_baseline,
            repository_path=dispatch.workspace.repository_path,
            commit_fingerprint=commit_fingerprint,
        )

    @staticmethod
    def _require_exact_authorization(
        candidate: BaselineCandidateRecord,
        authorization: HumanAuthorizationRecord,
    ) -> None:
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
                "Human Authorization does not match the exact Runtime Commit Candidate"
            )

    @staticmethod
    def _require_converged_effect(
        candidate: BaselineCandidateRecord,
        authorization: HumanAuthorizationRecord,
        effect: RepositoryIntegrationEffectRecord,
    ) -> None:
        if (
            effect.effect_type is not RepositoryEffectType.REPOSITORY_REF_ADVANCE
            or effect.state is not RepositoryEffectState.CONVERGED
            or effect.candidate_id != candidate.id
            or effect.candidate_fingerprint != candidate.fingerprint
            or effect.human_authorization_id != authorization.id
            or effect.repository_identity != candidate.repository_identity
            or effect.target_authoritative_ref != candidate.target_authoritative_ref
            or effect.expected_source_repository_revision
            != candidate.expected_source_repository_revision
            or effect.proposed_repository_revision
            != candidate.proposed_commit_identity
            or effect.proposed_tree_identity != candidate.proposed_tree_identity
            or effect.observed_repository_revision
            != candidate.proposed_commit_identity
            or effect.converged_at is None
        ):
            raise RuntimeInvariantViolation(
                "Runtime Commit requires the exact CONVERGED Repository Integration"
            )

    @staticmethod
    def _require_satisfied_work_units(
        store: RuntimeStore,
        candidate: BaselineCandidateRecord,
    ) -> None:
        if not candidate.satisfied_work_unit_ids:
            raise RuntimeInvariantViolation("Runtime Commit requires SATISFIED PWUs")
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
                    "Runtime Commit requires exact current SATISFIED PWU lineage"
                )

    @staticmethod
    def _require_completion_and_work_products(
        store: RuntimeStore,
        candidate: BaselineCandidateRecord,
        proposed,
    ) -> None:
        if not candidate.completion_evaluation_ids:
            raise RuntimeInvariantViolation(
                "Runtime Commit requires exact Completion Evaluation basis"
            )
        completion_work_products: set[UUID] = set()
        for evaluation_id in candidate.completion_evaluation_ids:
            evaluation = store.completion_evaluation(evaluation_id)
            if (
                evaluation is None
                or evaluation.outcome is not CompletionEvaluationOutcome.PRODUCED
                or evaluation.production_run_id != candidate.production_run_id
                or evaluation.work_unit_id not in candidate.satisfied_work_unit_ids
                or evaluation.plan_revision_id != candidate.plan_revision_id
                or evaluation.source_baseline_id != candidate.source_baseline_id
                or evaluation.repository_observation_id
                != proposed.repository_observation_id
            ):
                raise RuntimeInvariantViolation(
                    "Runtime Commit Completion Evaluation basis is stale or wrong"
                )
            completion_work_products.update(
                item.reference_id for item in evaluation.work_product_lineage
            )
        work_products = store.work_product_references(
            proposed.repository_observation_id
        )
        if (
            {item.id for item in work_products}
            != set(candidate.work_product_reference_ids)
            or completion_work_products != set(candidate.work_product_reference_ids)
            or any(
                item.production_run_id != candidate.production_run_id
                or item.work_unit_id not in candidate.satisfied_work_unit_ids
                or item.plan_revision_id != candidate.plan_revision_id
                or item.source_baseline_id != candidate.source_baseline_id
                for item in work_products
            )
        ):
            raise RuntimeInvariantViolation(
                "Runtime Commit Work Product lineage is stale or incomplete"
            )

    @staticmethod
    def _require_verification(
        store: RuntimeStore,
        candidate: BaselineCandidateRecord,
    ) -> None:
        if not candidate.verification_record_ids:
            raise RuntimeInvariantViolation(
                "Runtime Commit requires exact Verification PASS records"
            )
        for verification_id in candidate.verification_record_ids:
            verification = store.verification_record(verification_id)
            if (
                verification is None
                or verification.result is not VerificationResultValue.PASS
                or verification.production_run_id != candidate.production_run_id
                or verification.work_unit_id
                not in candidate.satisfied_work_unit_ids
                or verification.plan_revision_id != candidate.plan_revision_id
                or verification.source_baseline_id != candidate.source_baseline_id
                or verification.completion_evaluation_id
                not in candidate.completion_evaluation_ids
                or verification.proposed_snapshot_id
                != candidate.proposed_snapshot_id
                or verification.proposed_commit_identity
                != candidate.proposed_commit_identity
                or verification.tree_identity != candidate.proposed_tree_identity
            ):
                raise RuntimeInvariantViolation(
                    "Runtime Commit Verification basis is stale or wrong"
                )

    @staticmethod
    def _existing_result(
        store: RuntimeStore,
        existing: RuntimeCommitRecord,
        pointer: BaselinePointerRecord,
        observed_revision: str,
    ) -> RuntimeCommitResult:
        baseline = store.snapshot(existing.new_baseline_id)
        if baseline is None:
            raise RuntimeInvariantViolation(
                "existing Runtime Commit has no immutable Trusted Baseline"
            )
        return RuntimeCommitResult(
            runtime_commit=existing,
            trusted_baseline=baseline,
            current_pointer=pointer,
            observed_repository_revision=observed_revision,
            idempotent_recognition=True,
        )

    @staticmethod
    def _append_history(
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
                "actor_identity": RUNTIME_COMMIT_ACTOR,
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
