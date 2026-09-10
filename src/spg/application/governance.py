"""S3-C Candidate sealing and exact Human Authorization orchestration."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.preparation import completion_contract_fingerprint
from spg.domain.completion import CompletionEvaluationOutcome, CompletionEvaluationRecord
from spg.domain.execution import (
    ExecutionDispatchRecord,
    RepositoryObservationRecord,
    WorkProductReferenceRecord,
)
from spg.domain.governance import (
    BaselineCandidateRecord,
    CandidateAuthorizationScope,
    CandidateCondition,
    CandidateSealRequest,
    HumanAuthorizationRecord,
    HumanAuthorizationRequest,
)
from spg.domain.runtime import (
    BaselinePointerRecord,
    PlanRevisionRecord,
    ProductionRunRecord,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
    SnapshotRecord,
    WorkUnitCondition,
    WorkUnitRecord,
)
from spg.domain.verification import (
    ProductionAdmissibilityOutcome,
    ProductionAdmissibilityRecord,
    ProposedRepositorySnapshotRecord,
    VerificationRecord,
    VerificationResultValue,
)
from spg.infrastructure.git_snapshot import GitProposedSnapshotBuilder
from spg.infrastructure.persistence import Database, OptimisticConcurrencyConflict
from spg.infrastructure.persistence.runtime_store import RuntimeStore


CANDIDATE_ACTOR = "spg-runtime:candidate-governance"


@dataclass(frozen=True, slots=True)
class _CandidateBasis:
    run: ProductionRunRecord
    plan: PlanRevisionRecord
    work_unit: WorkUnitRecord
    source_baseline: SnapshotRecord
    pointer: BaselinePointerRecord
    completion: CompletionEvaluationRecord
    proposed_snapshot: ProposedRepositorySnapshotRecord
    observation: RepositoryObservationRecord
    dispatch: ExecutionDispatchRecord
    work_products: tuple[WorkProductReferenceRecord, ...]
    verifications: tuple[VerificationRecord, ...]
    admissibility: ProductionAdmissibilityRecord
    fingerprint: str


class CandidateGovernanceService:
    """Own exact Candidate eligibility, sealing, and Human permission binding."""

    def __init__(
        self,
        database: Database,
        snapshots: GitProposedSnapshotBuilder | None = None,
    ) -> None:
        self.database = database
        self.snapshots = snapshots or GitProposedSnapshotBuilder()

    def seal_candidate(self, request: CandidateSealRequest) -> BaselineCandidateRecord:
        """Atomically seal one exact eligible basis without repository integration."""

        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            basis = self._required_basis(store, request)
            existing = store.baseline_candidate_by_fingerprint(basis.fingerprint)
            if existing is not None:
                return existing

            self._require_current_eligible_basis(basis, request)
            self.snapshots.validate(
                basis.dispatch.workspace.repository_path,
                repository_ref=basis.proposed_snapshot.repository_ref,
                expected_authoritative_ref_revision=(
                    basis.proposed_snapshot.authoritative_ref_revision
                ),
                proposed_commit_identity=(
                    basis.proposed_snapshot.proposed_commit_identity
                ),
                tree_identity=basis.proposed_snapshot.tree_identity,
            )

            candidate_id = uuid5(
                NAMESPACE_URL,
                f"spg:baseline-candidate:{basis.fingerprint}",
            )
            store.insert_baseline_candidate(
                {
                    "id": candidate_id,
                    "condition": CandidateCondition.SEALED.value,
                    "production_run_id": basis.run.id,
                    "plan_revision_id": basis.plan.id,
                    "source_baseline_id": basis.source_baseline.id,
                    "repository_identity": basis.proposed_snapshot.repository_identity,
                    "target_authoritative_ref": basis.proposed_snapshot.repository_ref,
                    "expected_source_repository_revision": (
                        basis.proposed_snapshot.authoritative_ref_revision
                    ),
                    "proposed_snapshot_id": basis.proposed_snapshot.id,
                    "proposed_commit_identity": (
                        basis.proposed_snapshot.proposed_commit_identity
                    ),
                    "proposed_tree_identity": basis.proposed_snapshot.tree_identity,
                    "satisfied_work_unit_ids": [str(basis.work_unit.id)],
                    "completion_evaluation_ids": [str(basis.completion.id)],
                    "work_product_reference_ids": [
                        str(item.id) for item in basis.work_products
                    ],
                    "verification_record_ids": [
                        str(item.id) for item in basis.verifications
                    ],
                    "production_admissibility_id": basis.admissibility.id,
                    "production_admissibility_basis_fingerprint": (
                        basis.admissibility.basis_fingerprint
                    ),
                    "fingerprint": basis.fingerprint,
                    "sealed_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="BASELINE_CANDIDATE",
                entity_id=candidate_id,
                to_condition=CandidateCondition.SEALED.value,
                reason="EXACT_SATISFIED_PRODUCTION_BASIS_SEALED",
                actor=CANDIDATE_ACTOR,
                correlation=basis.admissibility.id,
                timestamp=timestamp,
            )
            candidate = store.baseline_candidate(candidate_id)
            if candidate is None:
                raise RuntimeInvariantViolation("Baseline Candidate was not constructed")
            unit_of_work.commit()
            return candidate

    def authorize_candidate(
        self,
        request: HumanAuthorizationRequest,
    ) -> HumanAuthorizationRecord:
        """Record permission for one explicit Candidate; never resolve a latest value."""

        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            candidate = store.baseline_candidate(request.candidate_id)
            if candidate is None:
                raise RuntimeRecordNotFound(
                    f"Baseline Candidate not found: {request.candidate_id}"
                )
            if candidate.condition is not CandidateCondition.SEALED:
                raise RuntimeInvariantViolation("Human Authorization requires a SEALED Candidate")
            if request.candidate_fingerprint != candidate.fingerprint:
                raise RuntimeInvariantViolation(
                    "Human Authorization Candidate fingerprint does not match"
                )
            expected_scope = CandidateAuthorizationScope(
                repository_identity=candidate.repository_identity,
                target_authoritative_ref=candidate.target_authoritative_ref,
                expected_source_repository_revision=(
                    candidate.expected_source_repository_revision
                ),
                proposed_repository_revision=candidate.proposed_commit_identity,
            )
            if request.scope != expected_scope:
                raise RuntimeInvariantViolation(
                    "Human Authorization scope must match the exact sealed Candidate"
                )

            basis_fingerprint = _fingerprint(
                {
                    "authority_identity": request.authority_identity,
                    "candidate_id": str(candidate.id),
                    "candidate_fingerprint": candidate.fingerprint,
                    "scope": request.scope.model_dump(mode="json"),
                }
            )
            existing = store.human_authorization_by_basis(basis_fingerprint)
            if existing is not None:
                return existing

            authorization_id = uuid5(
                NAMESPACE_URL,
                f"spg:human-authorization:{basis_fingerprint}",
            )
            governance_id = uuid5(
                NAMESPACE_URL,
                f"spg:human-authorization-governance:{basis_fingerprint}",
            )
            exact_scope = request.scope.model_dump(mode="json")
            store.insert_governance(
                {
                    "id": governance_id,
                    "decision_type": "AUTHORIZE_EXACT_BASELINE_CANDIDATE",
                    "authority_identity": request.authority_identity,
                    "subject_type": "BASELINE_CANDIDATE",
                    "subject_identity": str(candidate.id),
                    "scope": {
                        **exact_scope,
                        "candidate_fingerprint": candidate.fingerprint,
                    },
                    "rationale": request.rationale,
                    "created_at": timestamp,
                }
            )
            store.insert_human_authorization(
                {
                    "id": authorization_id,
                    "authority_identity": request.authority_identity,
                    "candidate_id": candidate.id,
                    "candidate_fingerprint": candidate.fingerprint,
                    "authorization_scope": exact_scope,
                    "source_baseline_id": candidate.source_baseline_id,
                    "repository_identity": candidate.repository_identity,
                    "target_authoritative_ref": candidate.target_authoritative_ref,
                    "expected_source_repository_revision": (
                        candidate.expected_source_repository_revision
                    ),
                    "proposed_repository_revision": (
                        candidate.proposed_commit_identity
                    ),
                    "rationale": request.rationale,
                    "governance_record_id": governance_id,
                    "basis_fingerprint": basis_fingerprint,
                    "authorized_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="HUMAN_AUTHORIZATION",
                entity_id=authorization_id,
                to_condition="AUTHORIZED",
                reason="EXACT_CANDIDATE_PERMISSION_RECORDED",
                actor=request.authority_identity,
                correlation=candidate.id,
                timestamp=timestamp,
            )
            authorization = store.human_authorization(authorization_id)
            governance = store.governance_for_subject(str(candidate.id))
            if authorization is None or not any(
                item.id == governance_id for item in governance
            ):
                raise RuntimeInvariantViolation("Human Authorization was not constructed")
            unit_of_work.commit()
            return authorization

    def candidate(self, candidate_id: UUID) -> BaselineCandidateRecord:
        with self.database.unit_of_work() as unit_of_work:
            candidate = RuntimeStore(unit_of_work.session).baseline_candidate(candidate_id)
            if candidate is None:
                raise RuntimeRecordNotFound(f"Baseline Candidate not found: {candidate_id}")
            return candidate

    @classmethod
    def _required_basis(
        cls,
        store: RuntimeStore,
        request: CandidateSealRequest,
    ) -> _CandidateBasis:
        proposed = store.proposed_snapshot(request.proposed_snapshot_id)
        admissibility = store.production_admissibility(
            request.production_admissibility_id
        )
        if proposed is None:
            raise RuntimeRecordNotFound(
                f"Proposed Repository Snapshot not found: {request.proposed_snapshot_id}"
            )
        if admissibility is None:
            raise RuntimeRecordNotFound(
                f"Production Admissibility not found: {request.production_admissibility_id}"
            )
        completion = store.completion_evaluation(proposed.completion_evaluation_id)
        pointer = store.current_pointer(source_baseline_id=proposed.source_baseline_id, for_update=True)
        work_unit = store.work_unit(proposed.work_unit_id, for_update=True)
        run = store.run(proposed.production_run_id, for_update=True)
        plan = store.plan_revision(proposed.plan_revision_id)
        source_baseline = store.snapshot(proposed.source_baseline_id)
        observation = store.repository_observation_by_id(
            proposed.repository_observation_id
        )
        if any(
            item is None
            for item in (
                completion,
                work_unit,
                run,
                plan,
                source_baseline,
                pointer,
                observation,
            )
        ):
            raise RuntimeInvariantViolation("Candidate production lineage is incomplete")
        dispatch = store.execution_dispatch(observation.dispatch_id)
        if dispatch is None:
            raise RuntimeInvariantViolation("Candidate dispatch lineage is incomplete")
        work_products = store.work_product_references(observation.id)

        selected_ids = tuple(
            item.verification_record_id
            for item in admissibility.obligation_results
            if item.verification_record_id is not None
        )
        verifications: list[VerificationRecord] = []
        for record_id in selected_ids:
            record = store.verification_record(record_id)
            if record is None:
                raise RuntimeInvariantViolation(
                    "Candidate Verification lineage is incomplete"
                )
            verifications.append(record)

        fingerprint = cls._candidate_fingerprint(
            run=run,
            plan=plan,
            source_baseline=source_baseline,
            work_unit=work_unit,
            completion=completion,
            proposed=proposed,
            work_products=work_products,
            verifications=tuple(verifications),
            admissibility=admissibility,
        )
        return _CandidateBasis(
            run=run,
            plan=plan,
            work_unit=work_unit,
            source_baseline=source_baseline,
            pointer=pointer,
            completion=completion,
            proposed_snapshot=proposed,
            observation=observation,
            dispatch=dispatch,
            work_products=work_products,
            verifications=tuple(verifications),
            admissibility=admissibility,
            fingerprint=fingerprint,
        )

    @classmethod
    def _require_current_eligible_basis(
        cls,
        basis: _CandidateBasis,
        request: CandidateSealRequest,
    ) -> None:
        if basis.work_unit.version != request.expected_work_unit_version:
            raise OptimisticConcurrencyConflict(
                "stale version for production_work_units: "
                f"expected {request.expected_work_unit_version}"
            )
        if basis.work_unit.condition is not WorkUnitCondition.SATISFIED:
            raise RuntimeInvariantViolation("Candidate sealing requires a SATISFIED PWU")
        if basis.completion.outcome is not CompletionEvaluationOutcome.PRODUCED:
            raise RuntimeInvariantViolation(
                "Candidate sealing requires an exact PRODUCED Completion Evaluation"
            )
        if basis.admissibility.outcome is not ProductionAdmissibilityOutcome.ADMISSIBLE:
            raise RuntimeInvariantViolation(
                "Candidate sealing requires exact ADMISSIBLE production evidence"
            )
        if basis.pointer.snapshot_id != basis.source_baseline.id:
            raise RuntimeInvariantViolation(
                "Candidate Source Baseline is not the Current Trusted Baseline"
            )
        if (
            basis.run.current_plan_revision_id != basis.plan.id
            or basis.run.source_baseline_id != basis.source_baseline.id
            or basis.plan.production_run_id != basis.run.id
            or basis.plan.source_baseline_id != basis.source_baseline.id
            or basis.work_unit.production_run_id != basis.run.id
            or basis.work_unit.plan_revision_id != basis.plan.id
            or basis.work_unit.source_baseline_id != basis.source_baseline.id
            or basis.work_unit.current_execution_generation != basis.completion.generation
        ):
            raise RuntimeInvariantViolation("Candidate production lineage is stale")
        proposed = basis.proposed_snapshot
        completion = basis.completion
        observation = basis.observation
        admissibility = basis.admissibility
        if (
            proposed.production_run_id != basis.run.id
            or proposed.work_unit_id != basis.work_unit.id
            or proposed.plan_revision_id != basis.plan.id
            or proposed.source_baseline_id != basis.source_baseline.id
            or proposed.completion_evaluation_id != completion.id
            or proposed.repository_observation_id != observation.id
            or proposed.generation != completion.generation
            or completion.production_run_id != basis.run.id
            or completion.work_unit_id != basis.work_unit.id
            or completion.plan_revision_id != basis.plan.id
            or completion.source_baseline_id != basis.source_baseline.id
            or completion.repository_observation_id != observation.id
            or completion.repository_observation_fingerprint
            != observation.observation_fingerprint
            or completion.completion_contract_fingerprint
            != completion_contract_fingerprint(basis.work_unit.completion_contract)
            or observation.repository_identity != proposed.repository_identity
            or observation.authoritative_ref_revision
            != proposed.authoritative_ref_revision
            or basis.source_baseline.repository_identity != proposed.repository_identity
            or basis.source_baseline.repository_ref != proposed.repository_ref
            or basis.source_baseline.repository_revision
            != proposed.authoritative_ref_revision
        ):
            raise RuntimeInvariantViolation("Candidate exact production basis is inconsistent")
        if (
            admissibility.production_run_id != basis.run.id
            or admissibility.work_unit_id != basis.work_unit.id
            or admissibility.plan_revision_id != basis.plan.id
            or admissibility.source_baseline_id != basis.source_baseline.id
            or admissibility.completion_evaluation_id != completion.id
            or admissibility.proposed_snapshot_id != proposed.id
        ):
            raise RuntimeInvariantViolation(
                "Candidate Production Admissibility is bound to the wrong subject"
            )

        expected_products = tuple(item.reference_id for item in completion.work_product_lineage)
        actual_products = tuple(item.id for item in basis.work_products)
        if expected_products != actual_products:
            raise RuntimeInvariantViolation("Candidate Work Product lineage is stale or wrong")

        required = tuple(
            dict.fromkeys(basis.work_unit.completion_contract.verification_obligations)
        )
        if admissibility.required_obligations_fingerprint != _fingerprint(required):
            raise RuntimeInvariantViolation(
                "Candidate Verification obligations are stale or wrong"
            )
        if len(admissibility.obligation_results) != len(required):
            raise RuntimeInvariantViolation("Candidate Verification evidence is incomplete")
        records_by_id = {record.id: record for record in basis.verifications}
        for obligation, result in zip(required, admissibility.obligation_results, strict=True):
            record = (
                records_by_id.get(result.verification_record_id)
                if result.verification_record_id is not None
                else None
            )
            if (
                result.obligation != obligation
                or not result.applicable
                or not result.admissible
                or result.result is not VerificationResultValue.PASS
                or record is None
                or record.result is not VerificationResultValue.PASS
                or record.obligation != obligation
                or record.proposed_snapshot_id != proposed.id
                or record.proposed_commit_identity != proposed.proposed_commit_identity
                or record.tree_identity != proposed.tree_identity
                or record.completion_evaluation_id != completion.id
                or record.plan_revision_id != basis.plan.id
                or record.source_baseline_id != basis.source_baseline.id
                or record.work_unit_id != basis.work_unit.id
            ):
                raise RuntimeInvariantViolation(
                    "Candidate requires exact applicable Verification PASS evidence"
                )

    @staticmethod
    def _candidate_fingerprint(
        *,
        run: ProductionRunRecord,
        plan: PlanRevisionRecord,
        source_baseline: SnapshotRecord,
        work_unit: WorkUnitRecord,
        completion: CompletionEvaluationRecord,
        proposed: ProposedRepositorySnapshotRecord,
        work_products: tuple[WorkProductReferenceRecord, ...],
        verifications: tuple[VerificationRecord, ...],
        admissibility: ProductionAdmissibilityRecord,
    ) -> str:
        return _fingerprint(
            {
                "contract": "S3-C/FVS-1/v1",
                "production_run_id": str(run.id),
                "plan_revision_id": str(plan.id),
                "source_baseline": {
                    "id": str(source_baseline.id),
                    "repository_identity": source_baseline.repository_identity,
                    "repository_ref": source_baseline.repository_ref,
                    "repository_revision": source_baseline.repository_revision,
                },
                "repository": {
                    "identity": proposed.repository_identity,
                    "target_authoritative_ref": proposed.repository_ref,
                    "expected_source_repository_revision": (
                        proposed.authoritative_ref_revision
                    ),
                },
                "proposed_snapshot": {
                    "id": str(proposed.id),
                    "basis_fingerprint": proposed.basis_fingerprint,
                    "commit": proposed.proposed_commit_identity,
                    "tree": proposed.tree_identity,
                },
                "satisfied_work_unit_ids": [str(work_unit.id)],
                "completion_evaluations": [
                    {
                        "id": str(completion.id),
                        "basis_fingerprint": completion.basis_fingerprint,
                        "completion_contract_fingerprint": (
                            completion.completion_contract_fingerprint
                        ),
                        "work_product_set_fingerprint": (
                            completion.work_product_set_fingerprint
                        ),
                    }
                ],
                "work_product_reference_ids": [
                    str(item.id) for item in work_products
                ],
                "verification_records": [
                    {
                        "id": str(item.id),
                        "basis_fingerprint": item.basis_fingerprint,
                        "result": item.result.value,
                    }
                    for item in verifications
                ],
                "production_admissibility": {
                    "id": str(admissibility.id),
                    "basis_fingerprint": admissibility.basis_fingerprint,
                    "required_obligations_fingerprint": (
                        admissibility.required_obligations_fingerprint
                    ),
                    "outcome": admissibility.outcome.value,
                },
            }
        )

    @staticmethod
    def _append_history(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_id: UUID,
        to_condition: str,
        reason: str,
        actor: str,
        correlation: UUID,
        timestamp: datetime,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": entity_type,
                "entity_identity": str(entity_id),
                "from_condition": None,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": actor,
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
