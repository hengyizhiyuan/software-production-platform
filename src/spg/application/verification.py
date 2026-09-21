"""S3-B exact snapshot, Verification, admissibility, and Satisfaction orchestration."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.preparation import completion_contract_fingerprint
from spg.domain.completion import CompletionEvaluationOutcome, CompletionEvaluationRecord
from spg.domain.execution import ExecutionDispatchRecord, RepositoryObservationRecord
from spg.domain.runtime import (
    ExecutionAttemptRecord,
    PlanRevisionRecord,
    ProductionRunRecord,
    RuntimeInvariantViolation,
    RuntimeRecordNotFound,
    SnapshotRecord,
    WorkUnitCondition,
    WorkUnitRecord,
)
from spg.domain.verification import (
    ProductionAdmissibilityObligation,
    ProductionAdmissibilityOutcome,
    ProposedRepositorySnapshotRecord,
    SatisfactionResult,
    VerificationApplicabilityAssessment,
    VerificationCapabilityRequest,
    VerificationProviderBinding,
    VerificationRecord,
    VerificationResultValue,
)
from spg.domain.verifier import VerificationCapabilityContract
from spg.infrastructure.git_observation import GitWorkspaceObserver
from spg.infrastructure.git_snapshot import GitProposedSnapshotBuilder
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


VERIFICATION_ACTOR = "spg-runtime:verification"


@dataclass(frozen=True, slots=True)
class _VerificationBasis:
    run: ProductionRunRecord
    plan: PlanRevisionRecord
    work_unit: WorkUnitRecord
    attempt: ExecutionAttemptRecord
    source_baseline: SnapshotRecord
    dispatch: ExecutionDispatchRecord
    observation: RepositoryObservationRecord
    completion: CompletionEvaluationRecord


@dataclass(frozen=True, slots=True)
class _SnapshotBasis:
    basis: _VerificationBasis
    proposed_snapshot: ProposedRepositorySnapshotRecord


class VerificationService:
    """Coordinate provider-neutral assurance and own production admissibility."""

    def __init__(
        self,
        database: Database,
        observer: GitWorkspaceObserver | None = None,
        snapshots: GitProposedSnapshotBuilder | None = None,
    ) -> None:
        self.database = database
        self.observer = observer or GitWorkspaceObserver()
        self.snapshots = snapshots or GitProposedSnapshotBuilder()

    def create_proposed_snapshot(
        self,
        completion_evaluation_id: UUID,
    ) -> ProposedRepositorySnapshotRecord:
        """Freeze exact Produced Reality without advancing an authoritative ref."""

        basis = self._load_verification_basis(completion_evaluation_id)
        self._require_produced_current_basis(basis)
        self._revalidate_observation(basis)
        basis_fingerprint = _fingerprint(
            {
                "completion_evaluation_id": str(basis.completion.id),
                "completion_basis_fingerprint": basis.completion.basis_fingerprint,
                "repository_observation_id": str(basis.observation.id),
                "repository_observation_fingerprint": basis.observation.observation_fingerprint,
                "work_unit_id": str(basis.work_unit.id),
                "plan_revision_id": str(basis.plan.id),
                "source_baseline_id": str(basis.source_baseline.id),
                "attempt_id": str(basis.attempt.id),
                "generation": basis.attempt.generation,
            }
        )
        with self.database.unit_of_work() as unit_of_work:
            existing = RuntimeStore(unit_of_work.session).proposed_snapshot_by_basis(
                basis_fingerprint
            )
            if existing is not None:
                self._validate_snapshot_object(existing, basis.dispatch)
                return existing

        git_snapshot = self.snapshots.create(
            basis.dispatch.workspace,
            repository_ref=basis.source_baseline.repository_ref,
            expected_authoritative_ref_revision=basis.observation.authoritative_ref_revision,
            expected_changes=basis.observation.changes,
            created_at=basis.completion.created_at,
        )
        snapshot_id = uuid5(NAMESPACE_URL, f"spg:proposed-snapshot:{basis_fingerprint}")
        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            current = self._required_verification_basis(store, completion_evaluation_id)
            self._require_same_verification_basis(basis, current)
            self._require_produced_current_basis(current)
            existing = store.proposed_snapshot_by_basis(basis_fingerprint)
            if existing is not None:
                return existing
            store.insert_proposed_snapshot(
                {
                    "id": snapshot_id,
                    "production_run_id": current.run.id,
                    "work_unit_id": current.work_unit.id,
                    "plan_revision_id": current.plan.id,
                    "source_baseline_id": current.source_baseline.id,
                    "attempt_id": current.attempt.id,
                    "generation": current.attempt.generation,
                    "completion_evaluation_id": current.completion.id,
                    "repository_observation_id": current.observation.id,
                    "repository_identity": current.observation.repository_identity,
                    "repository_ref": current.source_baseline.repository_ref,
                    "authoritative_ref_revision": git_snapshot.authoritative_ref_revision,
                    "proposed_commit_identity": git_snapshot.proposed_commit_identity,
                    "tree_identity": git_snapshot.tree_identity,
                    "basis_fingerprint": basis_fingerprint,
                    "created_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="PROPOSED_REPOSITORY_SNAPSHOT",
                entity_id=snapshot_id,
                to_condition="FROZEN",
                reason="EXACT_PRODUCED_REALITY_FROZEN",
                correlation=current.completion.id,
                timestamp=timestamp,
            )
            record = store.proposed_snapshot(snapshot_id)
            if record is None:
                raise RuntimeInvariantViolation("Proposed Repository Snapshot was not constructed")
            unit_of_work.commit()
            return record

    def verify_obligation(
        self,
        proposed_snapshot_id: UUID,
        obligation: str,
        provider: VerificationCapabilityContract,
    ) -> VerificationRecord:
        """Execute one obligation through a replaceable exact-subject capability."""

        snapshot_basis = self._load_snapshot_basis(proposed_snapshot_id)
        self._require_produced_current_basis(snapshot_basis.basis, allow_satisfied=True)
        self._validate_snapshot_object(
            snapshot_basis.proposed_snapshot,
            snapshot_basis.basis.dispatch,
        )
        if obligation not in snapshot_basis.basis.work_unit.completion_contract.verification_obligations:
            raise RuntimeInvariantViolation(
                "verification obligation is not required by the PWU Completion Contract"
            )
        obligation_fingerprint = _fingerprint(obligation)
        binding = provider.binding
        basis_fingerprint = self._verification_basis_fingerprint(
            snapshot_basis,
            obligation_fingerprint,
            binding,
        )
        verification_id = uuid5(
            NAMESPACE_URL,
            f"spg:verification-record:{basis_fingerprint}",
        )
        with self.database.unit_of_work() as unit_of_work:
            existing = RuntimeStore(unit_of_work.session).verification_record_by_basis(
                basis_fingerprint
            )
            if existing is not None:
                return existing

        request = VerificationCapabilityRequest(
            verification_identity=verification_id,
            obligation=obligation,
            semantic_fact_obligations=(
                snapshot_basis.basis.work_unit.completion_contract.semantic_fact_obligations
            ),
            task_contract_id=(
                None
                if snapshot_basis.basis.work_unit.completion_contract.task_contract is None
                else snapshot_basis.basis.work_unit.completion_contract.task_contract.task_contract_id
            ),
            snapshot_id=snapshot_basis.proposed_snapshot.id,
            proposed_commit_identity=snapshot_basis.proposed_snapshot.proposed_commit_identity,
            tree_identity=snapshot_basis.proposed_snapshot.tree_identity,
            completion_evaluation_id=snapshot_basis.basis.completion.id,
            plan_revision_id=snapshot_basis.basis.plan.id,
            source_baseline_id=snapshot_basis.basis.source_baseline.id,
        )
        before_ref = self.snapshots.current_ref_revision(
            snapshot_basis.basis.dispatch.workspace.repository_path,
            snapshot_basis.proposed_snapshot.repository_ref,
        )
        result = provider.verify(request)
        after_ref = self.snapshots.current_ref_revision(
            snapshot_basis.basis.dispatch.workspace.repository_path,
            snapshot_basis.proposed_snapshot.repository_ref,
        )
        if (
            before_ref != after_ref
            or after_ref != snapshot_basis.proposed_snapshot.authoritative_ref_revision
        ):
            raise RuntimeInvariantViolation(
                "Verification capability moved the authoritative repository ref"
            )
        if (
            result.evidence.obligation != obligation
            or result.evidence.subject_commit_identity
            != snapshot_basis.proposed_snapshot.proposed_commit_identity
            or result.evidence.subject_tree_identity
            != snapshot_basis.proposed_snapshot.tree_identity
        ):
            raise RuntimeInvariantViolation(
                "Verification evidence does not bind the exact requested subject"
            )

        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            current = self._required_snapshot_basis(store, proposed_snapshot_id)
            self._require_same_snapshot_basis(snapshot_basis, current)
            self._require_produced_current_basis(current.basis, allow_satisfied=True)
            existing = store.verification_record_by_basis(basis_fingerprint)
            if existing is not None:
                return existing
            store.insert_verification_record(
                {
                    "id": verification_id,
                    "production_run_id": current.basis.run.id,
                    "work_unit_id": current.basis.work_unit.id,
                    "plan_revision_id": current.basis.plan.id,
                    "source_baseline_id": current.basis.source_baseline.id,
                    "completion_evaluation_id": current.basis.completion.id,
                    "proposed_snapshot_id": current.proposed_snapshot.id,
                    "proposed_commit_identity": current.proposed_snapshot.proposed_commit_identity,
                    "tree_identity": current.proposed_snapshot.tree_identity,
                    "obligation": obligation,
                    "obligation_fingerprint": obligation_fingerprint,
                    "provider_binding": binding.model_dump(mode="json"),
                    "result": result.result.value,
                    "evidence": result.evidence.model_dump(mode="json"),
                    "basis_fingerprint": basis_fingerprint,
                    "created_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="VERIFICATION_RECORD",
                entity_id=verification_id,
                to_condition=result.result.value,
                reason="EXACT_SUBJECT_VERIFICATION_RECORDED",
                correlation=current.proposed_snapshot.id,
                timestamp=timestamp,
            )
            record = store.verification_record(verification_id)
            if record is None:
                raise RuntimeInvariantViolation("Verification Record was not constructed")
            unit_of_work.commit()
            return record

    def assess_applicability(
        self,
        verification_record_id: UUID,
        proposed_snapshot_id: UUID,
    ) -> VerificationApplicabilityAssessment:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            record = store.verification_record(verification_record_id)
            snapshot_basis = self._required_snapshot_basis(store, proposed_snapshot_id)
            if record is None:
                raise RuntimeRecordNotFound(
                    f"Verification Record not found: {verification_record_id}"
                )
        reasons = self._applicability_reasons(record, snapshot_basis)
        return VerificationApplicabilityAssessment(
            verification_record_id=record.id,
            proposed_snapshot_id=proposed_snapshot_id,
            applicable=not reasons,
            reasons=reasons,
        )

    def evaluate_admissibility(
        self,
        proposed_snapshot_id: UUID,
        *,
        expected_work_unit_version: int | None = None,
    ) -> SatisfactionResult:
        """Append SPG admissibility and atomically satisfy only on complete PASS."""

        timestamp = datetime.now(UTC)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            snapshot_basis = self._required_snapshot_basis(store, proposed_snapshot_id)
            locked_work_unit = store.work_unit(
                snapshot_basis.basis.work_unit.id,
                for_update=True,
            )
            if locked_work_unit is None:
                raise RuntimeInvariantViolation("Satisfaction PWU disappeared")
            snapshot_basis = _SnapshotBasis(
                basis=_VerificationBasis(
                    run=snapshot_basis.basis.run,
                    plan=snapshot_basis.basis.plan,
                    work_unit=locked_work_unit,
                    attempt=snapshot_basis.basis.attempt,
                    source_baseline=snapshot_basis.basis.source_baseline,
                    dispatch=snapshot_basis.basis.dispatch,
                    observation=snapshot_basis.basis.observation,
                    completion=snapshot_basis.basis.completion,
                ),
                proposed_snapshot=snapshot_basis.proposed_snapshot,
            )
            self._require_produced_current_basis(snapshot_basis.basis, allow_satisfied=True)
            records = store.verification_records_for_snapshot(proposed_snapshot_id)
            required = tuple(
                dict.fromkeys(
                    snapshot_basis.basis.work_unit.completion_contract.verification_obligations
                )
            )
            obligation_results = tuple(
                self._admissibility_for_obligation(obligation, records, snapshot_basis)
                for obligation in required
            )
            outcome = (
                ProductionAdmissibilityOutcome.ADMISSIBLE
                if all(item.admissible for item in obligation_results)
                else ProductionAdmissibilityOutcome.NOT_ADMISSIBLE
            )
            required_fingerprint = _fingerprint(required)
            record_ids = tuple(record.id for record in records)
            basis_fingerprint = _fingerprint(
                {
                    "proposed_snapshot_id": str(proposed_snapshot_id),
                    "completion_evaluation_id": str(snapshot_basis.basis.completion.id),
                    "plan_revision_id": str(snapshot_basis.basis.plan.id),
                    "source_baseline_id": str(snapshot_basis.basis.source_baseline.id),
                    "required_obligations_fingerprint": required_fingerprint,
                    "verification_records": [
                        {
                            "id": str(record.id),
                            "basis_fingerprint": record.basis_fingerprint,
                            "result": record.result.value,
                        }
                        for record in records
                    ],
                }
            )
            existing = store.production_admissibility_by_basis(basis_fingerprint)
            if existing is not None:
                return SatisfactionResult(
                    admissibility=existing,
                    work_unit=locked_work_unit,
                )

            admissibility_id = uuid5(
                NAMESPACE_URL,
                f"spg:production-admissibility:{basis_fingerprint}",
            )
            store.insert_production_admissibility(
                {
                    "id": admissibility_id,
                    "production_run_id": snapshot_basis.basis.run.id,
                    "work_unit_id": locked_work_unit.id,
                    "plan_revision_id": snapshot_basis.basis.plan.id,
                    "source_baseline_id": snapshot_basis.basis.source_baseline.id,
                    "completion_evaluation_id": snapshot_basis.basis.completion.id,
                    "proposed_snapshot_id": proposed_snapshot_id,
                    "required_obligations_fingerprint": required_fingerprint,
                    "verification_record_ids": [str(value) for value in record_ids],
                    "obligation_results": [
                        item.model_dump(mode="json") for item in obligation_results
                    ],
                    "basis_fingerprint": basis_fingerprint,
                    "outcome": outcome.value,
                    "created_at": timestamp,
                }
            )
            self._append_history(
                store,
                entity_type="PRODUCTION_ADMISSIBILITY",
                entity_id=admissibility_id,
                to_condition=outcome.value,
                reason="VERIFICATION_EVIDENCE_ADMISSIBILITY_EVALUATED",
                correlation=proposed_snapshot_id,
                timestamp=timestamp,
            )
            if outcome is ProductionAdmissibilityOutcome.ADMISSIBLE:
                if locked_work_unit.condition is WorkUnitCondition.SATISFIED:
                    raise RuntimeInvariantViolation(
                        "SATISFIED PWU has no matching idempotent admissibility fact"
                    )
                expected_version = (
                    locked_work_unit.version
                    if expected_work_unit_version is None
                    else expected_work_unit_version
                )
                store.mark_work_unit_satisfied(locked_work_unit.id, expected_version)
                self._append_history(
                    store,
                    entity_type="PRODUCTION_WORK_UNIT",
                    entity_id=locked_work_unit.id,
                    from_condition=WorkUnitCondition.PRODUCED.value,
                    to_condition=WorkUnitCondition.SATISFIED.value,
                    reason="REQUIRED_VERIFICATION_EVIDENCE_ADMITTED",
                    correlation=admissibility_id,
                    timestamp=timestamp,
                )
            admissibility = store.production_admissibility_by_basis(basis_fingerprint)
            work_unit = store.work_unit(locked_work_unit.id)
            if admissibility is None or work_unit is None:
                raise RuntimeInvariantViolation(
                    "Satisfaction transaction did not construct its result"
                )
            unit_of_work.commit()
            return SatisfactionResult(admissibility=admissibility, work_unit=work_unit)

    def _load_verification_basis(self, completion_evaluation_id: UUID) -> _VerificationBasis:
        with self.database.unit_of_work() as unit_of_work:
            return self._required_verification_basis(
                RuntimeStore(unit_of_work.session),
                completion_evaluation_id,
            )

    def _load_snapshot_basis(self, proposed_snapshot_id: UUID) -> _SnapshotBasis:
        with self.database.unit_of_work() as unit_of_work:
            return self._required_snapshot_basis(
                RuntimeStore(unit_of_work.session),
                proposed_snapshot_id,
            )

    @staticmethod
    def _required_verification_basis(
        store: RuntimeStore,
        completion_evaluation_id: UUID,
    ) -> _VerificationBasis:
        completion = store.completion_evaluation(completion_evaluation_id)
        if completion is None:
            raise RuntimeRecordNotFound(
                f"Completion Evaluation not found: {completion_evaluation_id}"
            )
        work_unit = store.work_unit(completion.work_unit_id)
        attempt = store.attempt(completion.attempt_id)
        observation = store.repository_observation_by_id(
            completion.repository_observation_id
        )
        if any(item is None for item in (work_unit, attempt, observation)):
            raise RuntimeInvariantViolation("S3-B Completion lineage is incomplete")
        run = store.run(completion.production_run_id)
        plan = store.plan_revision(completion.plan_revision_id)
        source_baseline = store.snapshot(completion.source_baseline_id)
        dispatch = store.execution_dispatch(observation.dispatch_id)
        if any(item is None for item in (run, plan, source_baseline, dispatch)):
            raise RuntimeInvariantViolation("S3-B production lineage is incomplete")
        if (
            completion.outcome is not CompletionEvaluationOutcome.PRODUCED
            or completion.work_unit_id != work_unit.id
            or completion.plan_revision_id != plan.id
            or completion.source_baseline_id != source_baseline.id
            or completion.attempt_id != attempt.id
            or completion.generation != attempt.generation
            or completion.repository_observation_id != observation.id
            or completion.repository_observation_fingerprint
            != observation.observation_fingerprint
            or completion.completion_contract_fingerprint
            != completion_contract_fingerprint(work_unit.completion_contract)
            or attempt.work_unit_id != work_unit.id
            or attempt.plan_revision_id != plan.id
            or attempt.source_baseline_id != source_baseline.id
            or observation.attempt_id != attempt.id
            or observation.generation != attempt.generation
            or observation.source_baseline_id != source_baseline.id
            or dispatch.attempt_id != attempt.id
            or dispatch.generation != attempt.generation
            or dispatch.source_baseline_id != source_baseline.id
            or run.id != work_unit.production_run_id
            or run.current_plan_revision_id != plan.id
            or run.source_baseline_id != source_baseline.id
            or plan.production_run_id != run.id
            or plan.source_baseline_id != source_baseline.id
        ):
            raise RuntimeInvariantViolation("S3-B basis is not an exact Produced lineage")
        return _VerificationBasis(
            run=run,
            plan=plan,
            work_unit=work_unit,
            attempt=attempt,
            source_baseline=source_baseline,
            dispatch=dispatch,
            observation=observation,
            completion=completion,
        )

    @classmethod
    def _required_snapshot_basis(
        cls,
        store: RuntimeStore,
        proposed_snapshot_id: UUID,
    ) -> _SnapshotBasis:
        proposed = store.proposed_snapshot(proposed_snapshot_id)
        if proposed is None:
            raise RuntimeRecordNotFound(
                f"Proposed Repository Snapshot not found: {proposed_snapshot_id}"
            )
        basis = cls._required_verification_basis(
            store,
            proposed.completion_evaluation_id,
        )
        if (
            proposed.production_run_id != basis.run.id
            or proposed.work_unit_id != basis.work_unit.id
            or proposed.plan_revision_id != basis.plan.id
            or proposed.source_baseline_id != basis.source_baseline.id
            or proposed.attempt_id != basis.attempt.id
            or proposed.generation != basis.attempt.generation
            or proposed.repository_observation_id != basis.observation.id
            or proposed.repository_identity != basis.observation.repository_identity
            or proposed.repository_ref != basis.source_baseline.repository_ref
            or proposed.authoritative_ref_revision
            != basis.observation.authoritative_ref_revision
        ):
            raise RuntimeInvariantViolation("Proposed Snapshot exact lineage is inconsistent")
        return _SnapshotBasis(basis=basis, proposed_snapshot=proposed)

    @staticmethod
    def _require_produced_current_basis(
        basis: _VerificationBasis,
        *,
        allow_satisfied: bool = False,
    ) -> None:
        allowed = {WorkUnitCondition.PRODUCED}
        if allow_satisfied:
            allowed.add(WorkUnitCondition.SATISFIED)
        if basis.work_unit.condition not in allowed:
            raise RuntimeInvariantViolation("only a PRODUCED PWU may enter S3-B")
        if basis.attempt.generation != basis.work_unit.current_execution_generation:
            raise RuntimeInvariantViolation(
                "stale production lineage has no current Satisfaction authority"
            )

    def _revalidate_observation(self, basis: _VerificationBasis) -> None:
        reality = self.observer.observe(
            basis.dispatch.workspace,
            repository_ref=basis.source_baseline.repository_ref,
            expected_authoritative_ref_revision=basis.observation.authoritative_ref_revision,
        )
        if (
            reality.observation_fingerprint != basis.observation.observation_fingerprint
            or reality.changes != basis.observation.changes
        ):
            raise RuntimeInvariantViolation(
                "Attempt workspace changed after Completion Evaluation Observation"
            )

    def _validate_snapshot_object(
        self,
        proposed: ProposedRepositorySnapshotRecord,
        dispatch: ExecutionDispatchRecord,
    ) -> None:
        self.snapshots.validate(
            dispatch.workspace.repository_path,
            repository_ref=proposed.repository_ref,
            expected_authoritative_ref_revision=proposed.authoritative_ref_revision,
            proposed_commit_identity=proposed.proposed_commit_identity,
            tree_identity=proposed.tree_identity,
        )

    @staticmethod
    def _require_same_verification_basis(
        expected: _VerificationBasis,
        current: _VerificationBasis,
    ) -> None:
        if expected != current:
            raise RuntimeInvariantViolation("S3-B basis changed before persistence")

    @staticmethod
    def _require_same_snapshot_basis(
        expected: _SnapshotBasis,
        current: _SnapshotBasis,
    ) -> None:
        if expected != current:
            raise RuntimeInvariantViolation("Verification subject changed before persistence")

    @staticmethod
    def _verification_basis_fingerprint(
        snapshot_basis: _SnapshotBasis,
        obligation_fingerprint: str,
        binding: VerificationProviderBinding,
    ) -> str:
        return _fingerprint(
            {
                "proposed_snapshot_id": str(snapshot_basis.proposed_snapshot.id),
                "proposed_commit_identity": snapshot_basis.proposed_snapshot.proposed_commit_identity,
                "tree_identity": snapshot_basis.proposed_snapshot.tree_identity,
                "completion_evaluation_id": str(snapshot_basis.basis.completion.id),
                "plan_revision_id": str(snapshot_basis.basis.plan.id),
                "source_baseline_id": str(snapshot_basis.basis.source_baseline.id),
                "obligation_fingerprint": obligation_fingerprint,
                "provider": binding.model_dump(mode="json"),
            }
        )

    @staticmethod
    def _applicability_reasons(
        record: VerificationRecord,
        snapshot_basis: _SnapshotBasis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        proposed = snapshot_basis.proposed_snapshot
        basis = snapshot_basis.basis
        comparisons = (
            (record.proposed_snapshot_id, proposed.id, "snapshot identity changed"),
            (record.proposed_commit_identity, proposed.proposed_commit_identity, "snapshot commit changed"),
            (record.tree_identity, proposed.tree_identity, "snapshot tree changed"),
            (record.completion_evaluation_id, basis.completion.id, "Completion Evaluation changed"),
            (record.plan_revision_id, basis.plan.id, "Plan Revision changed"),
            (record.source_baseline_id, basis.source_baseline.id, "Source Baseline changed"),
            (record.work_unit_id, basis.work_unit.id, "PWU changed"),
        )
        for actual, expected, reason in comparisons:
            if actual != expected:
                reasons.append(reason)
        if record.obligation not in basis.work_unit.completion_contract.verification_obligations:
            reasons.append("verification obligation is not required by current Completion Contract")
        return tuple(reasons)

    @classmethod
    def _admissibility_for_obligation(
        cls,
        obligation: str,
        records: tuple[VerificationRecord, ...],
        snapshot_basis: _SnapshotBasis,
    ) -> ProductionAdmissibilityObligation:
        matching = tuple(record for record in records if record.obligation == obligation)
        applicable = tuple(
            record
            for record in matching
            if not cls._applicability_reasons(record, snapshot_basis)
        )
        passing = tuple(
            record
            for record in applicable
            if record.result is VerificationResultValue.PASS
        )
        if passing:
            selected = passing[-1]
            return ProductionAdmissibilityObligation(
                obligation=obligation,
                verification_record_id=selected.id,
                result=selected.result,
                applicable=True,
                admissible=True,
                reason="exact applicable Verification PASS admitted",
            )
        if applicable:
            selected = applicable[-1]
            return ProductionAdmissibilityObligation(
                obligation=obligation,
                verification_record_id=selected.id,
                result=selected.result,
                applicable=True,
                admissible=False,
                reason=f"applicable Verification result {selected.result.value} blocks admission",
            )
        if matching:
            selected = matching[-1]
            return ProductionAdmissibilityObligation(
                obligation=obligation,
                verification_record_id=selected.id,
                result=selected.result,
                applicable=False,
                admissible=False,
                reason="Verification evidence is stale or bound to the wrong subject",
            )
        return ProductionAdmissibilityObligation(
            obligation=obligation,
            verification_record_id=None,
            result=None,
            applicable=False,
            admissible=False,
            reason="required Verification evidence is missing",
        )

    @staticmethod
    def _append_history(
        store: RuntimeStore,
        *,
        entity_type: str,
        entity_id: UUID,
        to_condition: str,
        reason: str,
        correlation: UUID,
        timestamp: datetime,
        from_condition: str | None = None,
    ) -> None:
        store.insert_transition(
            {
                "id": uuid4(),
                "entity_type": entity_type,
                "entity_identity": str(entity_id),
                "from_condition": from_condition,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": VERIFICATION_ACTOR,
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
