"""R4-B verified maintenance Baseline and production-lineage recovery."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.domain.execution import ProviderReportedOutcome
from spg.domain.maintenance_recovery import (
    MaintenanceAdmissionOutcome,
    MaintenanceEvidenceResult,
    MaintenanceRecoveryAdmissionRecord,
    MaintenanceRepositoryReality,
    VerifiedMaintenanceRecoveryRequest,
    VerifiedMaintenanceRecoveryResult,
    recovery_operation_fingerprint,
)
from spg.domain.recovery import (
    RecoveryClassification,
    RecoveryGuidance,
    RecoverySubjectType,
)
from spg.domain.runtime import (
    InitialRuntimeSpine,
    PlanCondition,
    RunCondition,
    RuntimeInvariantViolation,
    RuntimeNotBootstrapped,
    RuntimeRecordNotFound,
    SnapshotCondition,
    WorkUnitCondition,
)
from spg.infrastructure.git_maintenance import GitMaintenanceObserver
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.runtime_store import RuntimeStore


MAINTENANCE_RECOVERY_ACTOR = "spg-maintenance-recovery"
MAINTENANCE_RECOVERY_AUTHORITY = "VERIFIED_MAINTENANCE_RECOVERY"
FailureInjector = Callable[[str], None]


class VerifiedMaintenanceRecoveryService:
    """One atomic local authority handoff after exact read-only Git qualification."""

    def __init__(
        self,
        database: Database,
        *,
        git: GitMaintenanceObserver | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        self.database = database
        self.git = git or GitMaintenanceObserver()
        self.failure_injector = failure_injector or (lambda _: None)

    def recover_lineage_after_verified_maintenance(
        self,
        request: VerifiedMaintenanceRecoveryRequest,
    ) -> VerifiedMaintenanceRecoveryResult:
        """Admit exact maintenance Reality; never execute production or mutate Git."""

        operation_fingerprint = recovery_operation_fingerprint(request)
        existing = self._existing_result(operation_fingerprint)
        if existing is not None:
            return existing

        self._qualify_evidence_and_authority(request)
        timestamp = datetime.now(UTC)
        identities = self._identities(operation_fingerprint)
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            existing_admission = store.maintenance_recovery_admission_by_fingerprint(
                operation_fingerprint
            )
            if existing_admission is not None:
                return self._result(store, existing_admission, idempotent=True)

            pointer = store.current_pointer(source_baseline_id=request.expected_old_trusted_baseline_id, for_update=True)
            if pointer is None:
                raise RuntimeNotBootstrapped("no Current Trusted Baseline exists")
            if (
                pointer.snapshot_id != request.expected_old_trusted_baseline_id
                or pointer.version != request.expected_current_pointer_version
            ):
                concurrent = store.maintenance_recovery_admission_by_fingerprint(
                    operation_fingerprint
                )
                if concurrent is not None:
                    return self._result(store, concurrent, idempotent=True)
                raise RuntimeInvariantViolation(
                    "Current Trusted Baseline pointer identity/version is stale"
                )

            old_baseline = store.snapshot(pointer.snapshot_id)
            if old_baseline is None:
                raise RuntimeInvariantViolation("Current Baseline Snapshot is missing")
            self._qualify_baseline(request, old_baseline)

            exact_reality = self._observe_git(
                request,
                old_revision=old_baseline.repository_revision,
            )
            self._qualify_changed_paths(request, exact_reality)

            old_run = store.run(request.old_run_id, for_update=True)
            old_plan = store.plan_revision(
                request.old_plan_revision_id,
                for_update=True,
            )
            old_work_unit = store.work_unit(
                request.old_work_unit_id,
                for_update=True,
            )
            old_attempt = store.attempt(request.old_attempt_id)
            if any(item is None for item in (old_run, old_plan, old_work_unit, old_attempt)):
                raise RuntimeRecordNotFound("old production lineage is incomplete")
            self._qualify_old_lineage(
                request,
                old_run,
                old_plan,
                old_work_unit,
                old_attempt,
            )

            assessment = store.recovery_assessment(request.recovery_assessment_id)
            if assessment is None:
                raise RuntimeRecordNotFound("Recovery Assessment not found")
            self._qualify_assessment(request, assessment)
            self._qualify_execution_reality(store, request, old_attempt, assessment)

            store.insert_snapshot(
                {
                    "id": identities["baseline"],
                    "condition": SnapshotCondition.TRUSTED.value,
                    "repository_identity": request.repository_identity,
                    "repository_ref": request.authoritative_ref,
                    "repository_revision": request.target_maintenance_commit,
                    "source_baseline_id": old_baseline.id,
                    "created_at": timestamp,
                }
            )
            self._checkpoint("new_baseline")

            store.update_baseline_pointer(
                request.expected_current_pointer_version,
                identities["baseline"],
                expected_snapshot_id=request.expected_old_trusted_baseline_id,
            )
            self._checkpoint("baseline_pointer")

            store.supersede_run(old_run.id, request.expected_old_run_version)
            self._append_transition(
                store,
                identity=identities["old_run_transition"],
                entity_type="PRODUCTION_RUN",
                entity_id=old_run.id,
                from_condition=RunCondition.OPEN.value,
                to_condition=RunCondition.SUPERSEDED.value,
                reason="VERIFIED_MAINTENANCE_LINEAGE_SUPERSEDED",
                correlation=identities["admission"],
                timestamp=timestamp,
            )
            self._checkpoint("old_run_superseded")

            store.supersede_plan_revision(
                old_plan.id,
                request.expected_old_plan_version,
            )
            self._append_transition(
                store,
                identity=identities["old_plan_transition"],
                entity_type="PLAN_REVISION",
                entity_id=old_plan.id,
                from_condition=PlanCondition.ACTIVE.value,
                to_condition=PlanCondition.SUPERSEDED.value,
                reason="VERIFIED_MAINTENANCE_LINEAGE_SUPERSEDED",
                correlation=identities["admission"],
                timestamp=timestamp,
            )
            self._checkpoint("old_plan_superseded")

            store.supersede_work_unit(
                old_work_unit.id,
                request.expected_old_work_unit_version,
            )
            self._append_transition(
                store,
                identity=identities["old_work_unit_transition"],
                entity_type="PRODUCTION_WORK_UNIT",
                entity_id=old_work_unit.id,
                from_condition=WorkUnitCondition.PROPOSED.value,
                to_condition=WorkUnitCondition.SUPERSEDED.value,
                reason="VERIFIED_MAINTENANCE_LINEAGE_SUPERSEDED",
                correlation=identities["admission"],
                timestamp=timestamp,
            )
            self._checkpoint("old_work_unit_superseded")

            new = request.new_lineage
            store.insert_run(
                {
                    "id": identities["run"],
                    "intent_ref": new.intent_ref,
                    "goal": new.goal,
                    "production_horizon": new.production_horizon.value,
                    "source_baseline_id": identities["baseline"],
                    "current_plan_revision_id": None,
                    "condition": RunCondition.OPEN.value,
                    "version": 0,
                    "created_at": timestamp,
                }
            )
            self._checkpoint("new_run")
            store.insert_plan_revision(
                {
                    "id": identities["plan"],
                    "production_run_id": identities["run"],
                    "revision_number": 1,
                    "source_baseline_id": identities["baseline"],
                    "condition": PlanCondition.ACTIVE.value,
                    "version": 0,
                    "created_at": timestamp,
                }
            )
            store.bind_run_to_plan(identities["run"], 0, identities["plan"])
            self._checkpoint("new_plan")
            store.insert_work_unit(
                {
                    "id": identities["work_unit"],
                    "production_run_id": identities["run"],
                    "plan_revision_id": identities["plan"],
                    "source_baseline_id": identities["baseline"],
                    "objective": new.work_unit_objective,
                    "completion_contract": new.completion_contract.model_dump(mode="json"),
                    "condition": WorkUnitCondition.PROPOSED.value,
                    "version": 0,
                    "current_execution_generation": 0,
                    "created_at": timestamp,
                }
            )
            self._append_new_lineage_transitions(store, identities, timestamp)
            self._checkpoint("new_work_unit")

            store.insert_governance(
                {
                    "id": identities["governance"],
                    "decision_type": "AUTHORIZE_VERIFIED_MAINTENANCE_RECOVERY",
                    "authority_identity": request.authority.authority_identity,
                    "subject_type": "MAINTENANCE_RECOVERY_ADMISSION",
                    "subject_identity": str(identities["admission"]),
                    "scope": {
                        "operation_fingerprint": operation_fingerprint,
                        "old_trusted_baseline_id": str(old_baseline.id),
                        "new_trusted_baseline_id": str(identities["baseline"]),
                        "target_commit": request.target_maintenance_commit,
                        "target_tree": request.target_maintenance_tree,
                        "maintenance_evidence_fingerprint": (
                            request.verification_evidence.evidence_fingerprint
                        ),
                        "maintenance_authority_fingerprint": (
                            request.authority.authority_fingerprint
                        ),
                        "recovery_assessment_id": str(assessment.id),
                        "old_run_id": str(old_run.id),
                        "new_run_id": str(identities["run"]),
                    },
                    "rationale": request.maintenance_purpose,
                    "created_at": timestamp,
                }
            )
            self._checkpoint("governance")

            store.insert_maintenance_recovery_admission(
                {
                    "id": identities["admission"],
                    "operation_fingerprint": operation_fingerprint,
                    "old_trusted_baseline_id": old_baseline.id,
                    "new_trusted_baseline_id": identities["baseline"],
                    "expected_pointer_version": request.expected_current_pointer_version,
                    "repository_identity": request.repository_identity,
                    "authoritative_ref": request.authoritative_ref,
                    "target_commit": request.target_maintenance_commit,
                    "target_tree": request.target_maintenance_tree,
                    "maintenance_purpose": request.maintenance_purpose,
                    "approved_changed_paths": list(request.approved_changed_paths),
                    "verification_evidence": request.verification_evidence.model_dump(
                        mode="json"
                    ),
                    "maintenance_evidence_fingerprint": (
                        request.verification_evidence.evidence_fingerprint
                    ),
                    "authority": request.authority.model_dump(mode="json"),
                    "maintenance_authority_fingerprint": (
                        request.authority.authority_fingerprint
                    ),
                    "governance_record_id": identities["governance"],
                    "recovery_assessment_id": assessment.id,
                    "recovery_assessment_fingerprint": assessment.basis_fingerprint,
                    "old_run_id": old_run.id,
                    "old_plan_revision_id": old_plan.id,
                    "old_work_unit_id": old_work_unit.id,
                    "old_attempt_id": old_attempt.id,
                    "new_run_id": identities["run"],
                    "new_plan_revision_id": identities["plan"],
                    "new_work_unit_id": identities["work_unit"],
                    "governance_contract_snapshot_identity": (
                        request.governance_contract_snapshot_identity
                    ),
                    "governance_contract_snapshot_fingerprint": (
                        request.governance_contract_snapshot_fingerprint
                    ),
                    "external_intent_ref": new.intent_ref,
                    "outcome": MaintenanceAdmissionOutcome.APPLIED.value,
                    "admitted_at": timestamp,
                }
            )
            self._append_transition(
                store,
                identity=identities["admission_transition"],
                entity_type="MAINTENANCE_RECOVERY_ADMISSION",
                entity_id=identities["admission"],
                from_condition=None,
                to_condition=MaintenanceAdmissionOutcome.APPLIED.value,
                reason="VERIFIED_MAINTENANCE_RECOVERY_APPLIED",
                correlation=assessment.id,
                timestamp=timestamp,
            )
            self._checkpoint("recovery_admission")

            final_reality = self._observe_git(
                request,
                old_revision=old_baseline.repository_revision,
            )
            if final_reality != exact_reality:
                raise RuntimeInvariantViolation(
                    "maintenance repository Reality moved before local commit"
                )
            self._checkpoint("before_commit")

            admission = store.maintenance_recovery_admission(
                identities["admission"]
            )
            if admission is None:
                raise RuntimeInvariantViolation(
                    "maintenance recovery admission was not constructed"
                )
            result = self._result(store, admission, idempotent=False)
            unit_of_work.commit()
            return result

    def assert_recovered_lineage_progress_allowed(self, run_id: UUID) -> None:
        """Distinguish a new admitted lineage from its superseded historical barrier."""

        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            run = store.run(run_id)
            if run is None:
                raise RuntimeRecordNotFound(f"Run not found: {run_id}")
            admission = store.maintenance_recovery_for_new_run(run_id)
            if admission is None or run.condition is not RunCondition.OPEN:
                raise RuntimeInvariantViolation(
                    "Run is not the current lineage of a verified maintenance recovery"
                )

    def admission(self, admission_id: UUID) -> MaintenanceRecoveryAdmissionRecord:
        with self.database.unit_of_work() as unit_of_work:
            record = RuntimeStore(unit_of_work.session).maintenance_recovery_admission(
                admission_id
            )
            if record is None:
                raise RuntimeRecordNotFound(
                    f"Maintenance Recovery Admission not found: {admission_id}"
                )
            return record

    def _existing_result(
        self,
        operation_fingerprint: str,
    ) -> VerifiedMaintenanceRecoveryResult | None:
        with self.database.unit_of_work() as unit_of_work:
            store = RuntimeStore(unit_of_work.session)
            existing = store.maintenance_recovery_admission_by_fingerprint(
                operation_fingerprint
            )
            if existing is None:
                return None
            return self._result(store, existing, idempotent=True)

    @staticmethod
    def _qualify_evidence_and_authority(
        request: VerifiedMaintenanceRecoveryRequest,
    ) -> None:
        evidence = request.verification_evidence
        if any(
            suite.terminal_result is not MaintenanceEvidenceResult.PASS
            or suite.failed != 0
            for suite in evidence.suites
        ):
            raise RuntimeInvariantViolation(
                "maintenance verification evidence contains a failed suite"
            )
        if any(
            check.terminal_result is not MaintenanceEvidenceResult.PASS
            for check in evidence.checks
        ):
            raise RuntimeInvariantViolation(
                "maintenance verification evidence contains a failed check"
            )
        suite_identities = {(item.suite_identity, item.command_identity) for item in evidence.suites}
        if len(suite_identities) != len(evidence.suites):
            raise RuntimeInvariantViolation("maintenance suite evidence is duplicated")
        check_identities = {item.check_identity for item in evidence.checks}
        if len(check_identities) != len(evidence.checks):
            raise RuntimeInvariantViolation("maintenance check evidence is duplicated")
        if MAINTENANCE_RECOVERY_AUTHORITY not in request.authority.authorization_scope:
            raise RuntimeInvariantViolation(
                "Human / Architecture Authority lacks maintenance recovery scope"
            )

    def _observe_git(
        self,
        request: VerifiedMaintenanceRecoveryRequest,
        *,
        old_revision: str,
    ) -> MaintenanceRepositoryReality:
        return self.git.observe(
            request.repository_path,
            repository_identity=request.repository_identity,
            authoritative_ref=request.authoritative_ref,
            old_revision=old_revision,
            target_commit=request.target_maintenance_commit,
            target_tree=request.target_maintenance_tree,
        )

    @staticmethod
    def _qualify_baseline(request, old_baseline) -> None:
        if old_baseline.condition is not SnapshotCondition.TRUSTED:
            raise RuntimeInvariantViolation("old Baseline is not TRUSTED")
        if old_baseline.id != request.expected_old_trusted_baseline_id:
            raise RuntimeInvariantViolation("old Baseline identity mismatch")
        if old_baseline.repository_identity != request.repository_identity:
            raise RuntimeInvariantViolation("old Baseline repository identity mismatch")

    @staticmethod
    def _qualify_changed_paths(
        request: VerifiedMaintenanceRecoveryRequest,
        reality: MaintenanceRepositoryReality,
    ) -> None:
        if reality.changed_paths != request.approved_changed_paths:
            raise RuntimeInvariantViolation(
                "actual changed paths do not equal approved maintenance scope"
            )

    @staticmethod
    def _qualify_old_lineage(request, run, plan, work_unit, attempt) -> None:
        if (
            run.id != request.old_run_id
            or run.version != request.expected_old_run_version
            or run.condition is not RunCondition.OPEN
            or run.current_plan_revision_id != plan.id
            or run.source_baseline_id != request.expected_old_trusted_baseline_id
        ):
            raise RuntimeInvariantViolation("old Run is not exact current authority")
        if (
            plan.id != request.old_plan_revision_id
            or plan.version != request.expected_old_plan_version
            or plan.condition is not PlanCondition.ACTIVE
            or plan.production_run_id != run.id
            or plan.source_baseline_id != run.source_baseline_id
        ):
            raise RuntimeInvariantViolation("old Plan is not exact current authority")
        if (
            work_unit.id != request.old_work_unit_id
            or work_unit.version != request.expected_old_work_unit_version
            or work_unit.condition is not WorkUnitCondition.PROPOSED
            or work_unit.production_run_id != run.id
            or work_unit.plan_revision_id != plan.id
            or work_unit.source_baseline_id != run.source_baseline_id
        ):
            raise RuntimeInvariantViolation("old PWU is outside narrow recovery eligibility")
        if (
            attempt.id != request.old_attempt_id
            or attempt.work_unit_id != work_unit.id
            or attempt.plan_revision_id != plan.id
            or attempt.source_baseline_id != run.source_baseline_id
            or attempt.generation != work_unit.current_execution_generation
        ):
            raise RuntimeInvariantViolation("old Attempt is not exact current generation")

    @staticmethod
    def _qualify_assessment(request, assessment) -> None:
        if (
            assessment.id != request.recovery_assessment_id
            or assessment.basis_fingerprint
            != request.expected_recovery_assessment_fingerprint
            or assessment.subject_type is not RecoverySubjectType.ATTEMPT
            or assessment.subject_identity != str(request.old_attempt_id)
            or not assessment.subject_is_current
            or not assessment.recovery_barrier
            or assessment.classification
            not in {RecoveryClassification.UNKNOWN, RecoveryClassification.BLOCKED}
            or assessment.guidance is not RecoveryGuidance.REOBSERVE
        ):
            raise RuntimeInvariantViolation(
                "Recovery Assessment is not the exact admitted blocked basis"
            )

    @staticmethod
    def _qualify_execution_reality(store, request, attempt, assessment) -> None:
        dispatch = store.execution_dispatch_for_attempt(attempt.id)
        if dispatch is None:
            raise RuntimeInvariantViolation("old Attempt has no exact Dispatch")
        report = store.provider_execution_report(dispatch.id)
        observation = store.repository_observation(dispatch.id)
        if report is None or observation is None:
            raise RuntimeInvariantViolation(
                "old Attempt requires exact Provider Report and Observation"
            )
        if report.outcome not in {
            ProviderReportedOutcome.UNKNOWN,
            ProviderReportedOutcome.FAILURE,
        }:
            raise RuntimeInvariantViolation(
                "successful Provider work is outside narrow maintenance recovery"
            )
        if observation.changes:
            raise RuntimeInvariantViolation(
                "material observed production work blocks narrow supersession"
            )
        counts = store.maintenance_recovery_disqualifying_counts(
            run_id=request.old_run_id,
            work_unit_id=request.old_work_unit_id,
            attempt_id=request.old_attempt_id,
            recovery_assessment_id=assessment.id,
        )
        if counts.pop("attempts") != 1 or any(counts.values()):
            raise RuntimeInvariantViolation(
                f"old lineage has disqualifying production facts: {counts}"
            )

    def _result(self, store, admission, *, idempotent: bool):
        old_baseline = store.snapshot(admission.old_trusted_baseline_id)
        new_baseline = store.snapshot(admission.new_trusted_baseline_id)
        pointer = store.current_pointer(source_baseline_id=admission.old_trusted_baseline_id)
        old_run = store.run(admission.old_run_id)
        old_plan = store.plan_revision(admission.old_plan_revision_id)
        old_work_unit = store.work_unit(admission.old_work_unit_id)
        new_run = store.run(admission.new_run_id)
        new_plan = store.plan_revision(admission.new_plan_revision_id)
        new_work_unit = store.work_unit(admission.new_work_unit_id)
        if any(
            item is None
            for item in (
                old_baseline,
                new_baseline,
                pointer,
                old_run,
                old_plan,
                old_work_unit,
                new_run,
                new_plan,
                new_work_unit,
            )
        ):
            raise RuntimeInvariantViolation(
                "maintenance recovery result lineage is incomplete"
            )
        return VerifiedMaintenanceRecoveryResult(
            admission=admission,
            old_baseline=old_baseline,
            new_baseline=new_baseline,
            pointer=pointer,
            old_run=old_run,
            old_plan_revision=old_plan,
            old_work_unit=old_work_unit,
            new_lineage=InitialRuntimeSpine(
                run=new_run,
                plan_revision=new_plan,
                work_unit=new_work_unit,
            ),
            idempotent_recognition=idempotent,
        )

    @staticmethod
    def _identities(operation_fingerprint: str) -> dict[str, UUID]:
        labels = (
            "admission",
            "baseline",
            "governance",
            "run",
            "plan",
            "work_unit",
            "old_run_transition",
            "old_plan_transition",
            "old_work_unit_transition",
            "new_run_transition",
            "new_plan_transition",
            "new_work_unit_transition",
            "admission_transition",
        )
        return {
            label: uuid5(
                NAMESPACE_URL,
                f"spg:verified-maintenance-recovery:{operation_fingerprint}:{label}",
            )
            for label in labels
        }

    @staticmethod
    def _append_transition(
        store,
        *,
        identity,
        entity_type,
        entity_id,
        from_condition,
        to_condition,
        reason,
        correlation,
        timestamp,
    ) -> None:
        store.insert_transition(
            {
                "id": identity,
                "entity_type": entity_type,
                "entity_identity": str(entity_id),
                "from_condition": from_condition,
                "to_condition": to_condition,
                "reason": reason,
                "actor_identity": MAINTENANCE_RECOVERY_ACTOR,
                "correlation_identity": str(correlation),
                "created_at": timestamp,
            }
        )

    def _append_new_lineage_transitions(self, store, identities, timestamp) -> None:
        for key, entity_type, condition, reason in (
            ("run", "PRODUCTION_RUN", RunCondition.OPEN.value, "RECOVERED_RUN_CREATED"),
            ("plan", "PLAN_REVISION", PlanCondition.ACTIVE.value, "RECOVERED_PLAN_ACTIVATED"),
            (
                "work_unit",
                "PRODUCTION_WORK_UNIT",
                WorkUnitCondition.PROPOSED.value,
                "RECOVERED_WORK_UNIT_PROPOSED",
            ),
        ):
            self._append_transition(
                store,
                identity=identities[f"new_{key}_transition"],
                entity_type=entity_type,
                entity_id=identities[key],
                from_condition=None,
                to_condition=condition,
                reason=reason,
                correlation=identities["admission"],
                timestamp=timestamp,
            )

    def _checkpoint(self, boundary: str) -> None:
        self.failure_injector(boundary)
