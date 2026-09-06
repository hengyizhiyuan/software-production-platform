"""DCP-2 read-only projection of normalized production measurements."""

from datetime import datetime
from hashlib import sha256
import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from spg.domain.change import ChangeOperation, ProductionTargetKind
from spg.domain.governance import BaselineCandidateRecord
from spg.domain.integration import RepositoryIntegrationEffectRecord
from spg.domain.measurement import (
    MeasurementAvailability,
    MeasurementDerivation,
    MeasurementSourceReference,
    ProductionMeasurementKind,
    ProductionMeasurementSampleV0,
    ProductionMeasurementScope,
    ProductionMeasurementV0,
    ProductionPhase,
    TaskShapeSnapshotV0,
    TaskShapeSourceReference,
)
from spg.domain.product import WorkMode, WorkRuntimeBindingRecord
from spg.domain.runtime import WorkUnitRecord
from spg.domain.steering import SteeringOutcome
from spg.domain.verification import VerificationRecord
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore


class MeasurementSubjectNotFound(LookupError):
    """The requested production subject has no admitted persisted identity."""


class MeasurementLineageError(RuntimeError):
    """Persisted identities cannot support one truthful measurement projection."""


class ProductionMeasurementService:
    """Query existing authoritative facts without changing production decisions."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def task_shape_snapshot(self, work_unit_id: UUID) -> TaskShapeSnapshotV0:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            binding, work_unit = self._required_pwu_lineage(
                product,
                runtime,
                work_unit_id,
            )
            plan_revision = runtime.plan_revision(work_unit.plan_revision_id)
            baseline = runtime.snapshot(work_unit.source_baseline_id)
            if plan_revision is None or baseline is None:
                raise MeasurementLineageError(
                    "Task shape requires persisted Plan Revision and Source Baseline"
                )
            if (
                plan_revision.id != binding.plan_revision_id
                or plan_revision.source_baseline_id != work_unit.source_baseline_id
            ):
                raise MeasurementLineageError(
                    "Task shape Plan/PWU/Baseline lineage does not match"
                )
            return self._task_shape(binding, work_unit, baseline.repository_identity)

    def machine_execution_measurement(
        self,
        attempt_id: UUID,
    ) -> ProductionMeasurementV0:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            attempt = runtime.attempt(attempt_id)
            if attempt is None:
                raise MeasurementSubjectNotFound(f"Attempt not found: {attempt_id}")
            binding, _ = self._required_pwu_lineage(
                product,
                runtime,
                attempt.work_unit_id,
            )
            dispatch = runtime.execution_dispatch_for_attempt(attempt.id)
            report = (
                None
                if dispatch is None
                else runtime.provider_execution_report(dispatch.id)
            )
            if report is None:
                return self._unavailable(
                    kind=ProductionMeasurementKind.MACHINE_EXECUTION,
                    scope=ProductionMeasurementScope.AGGREGATE_PROVIDER_EXECUTION,
                    phase=ProductionPhase.EXECUTION,
                    subject_type="EXECUTION_ATTEMPT",
                    subject_id=attempt.id,
                    work_id=binding.work_id,
                    work_unit_id=attempt.work_unit_id,
                    attempt_id=attempt.id,
                    reason=(
                        "No aggregate Provider Report with authoritative "
                        "started_at/finished_at exists for this Attempt"
                    ),
                    source_facts=(
                        MeasurementSourceReference(
                            fact_type="EXECUTION_ATTEMPT",
                            fact_id=attempt.id,
                            field_name="created_at_not_execution_start",
                            observed_at=attempt.created_at,
                        ),
                    ),
                )
            return self._interval(
                kind=ProductionMeasurementKind.MACHINE_EXECUTION,
                scope=ProductionMeasurementScope.AGGREGATE_PROVIDER_EXECUTION,
                phase=ProductionPhase.EXECUTION,
                subject_type="PROVIDER_EXECUTION_REPORT",
                subject_id=report.id,
                work_id=binding.work_id,
                work_unit_id=attempt.work_unit_id,
                attempt_id=attempt.id,
                started_at=report.started_at,
                finished_at=report.finished_at,
                source_facts=(
                    MeasurementSourceReference(
                        fact_type="PROVIDER_EXECUTION_REPORT",
                        fact_id=report.id,
                        field_name="started_at",
                        observed_at=report.started_at,
                    ),
                    MeasurementSourceReference(
                        fact_type="PROVIDER_EXECUTION_REPORT",
                        fact_id=report.id,
                        field_name="finished_at",
                        observed_at=report.finished_at,
                    ),
                ),
                internal_turn_count=self._positive_int(
                    report.metadata.get("internal_turn_count")
                ),
                self_refine_occurred=self._optional_bool(
                    report.metadata.get("self_refine_occurred")
                ),
            )

    def human_wait_measurement(
        self,
        candidate_id: UUID,
    ) -> ProductionMeasurementV0:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            candidate = runtime.baseline_candidate(candidate_id)
            if candidate is None:
                raise MeasurementSubjectNotFound(
                    f"Candidate not found: {candidate_id}"
                )
            binding, work_unit_id = self._candidate_lineage(product, candidate)
            authorizations = runtime.human_authorizations_for_candidate(candidate.id)
            if not authorizations:
                return self._unavailable(
                    kind=ProductionMeasurementKind.HUMAN_WAIT,
                    scope=ProductionMeasurementScope.CANDIDATE_AUTHORIZATION_WAIT,
                    phase=ProductionPhase.HUMAN_WAIT,
                    subject_type="BASELINE_CANDIDATE",
                    subject_id=candidate.id,
                    work_id=binding.work_id,
                    work_unit_id=work_unit_id,
                    reason="The sealed Candidate has no Human Authorization timestamp",
                    source_facts=(
                        MeasurementSourceReference(
                            fact_type="BASELINE_CANDIDATE",
                            fact_id=candidate.id,
                            field_name="sealed_at",
                            observed_at=candidate.sealed_at,
                        ),
                    ),
                )
            if len(authorizations) != 1:
                raise MeasurementLineageError(
                    "Human wait v0 requires exactly one Authorization per Candidate"
                )
            authorization = authorizations[0]
            return self._interval(
                kind=ProductionMeasurementKind.HUMAN_WAIT,
                scope=ProductionMeasurementScope.CANDIDATE_AUTHORIZATION_WAIT,
                phase=ProductionPhase.HUMAN_WAIT,
                subject_type="BASELINE_CANDIDATE",
                subject_id=candidate.id,
                work_id=binding.work_id,
                work_unit_id=work_unit_id,
                attempt_id=None,
                started_at=candidate.sealed_at,
                finished_at=authorization.authorized_at,
                source_facts=(
                    MeasurementSourceReference(
                        fact_type="BASELINE_CANDIDATE",
                        fact_id=candidate.id,
                        field_name="sealed_at",
                        observed_at=candidate.sealed_at,
                    ),
                    MeasurementSourceReference(
                        fact_type="HUMAN_AUTHORIZATION",
                        fact_id=authorization.id,
                        field_name="authorized_at",
                        observed_at=authorization.authorized_at,
                    ),
                ),
            )

    def integration_measurement(
        self,
        candidate_id: UUID,
    ) -> ProductionMeasurementV0:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            candidate = runtime.baseline_candidate(candidate_id)
            if candidate is None:
                raise MeasurementSubjectNotFound(
                    f"Candidate not found: {candidate_id}"
                )
            binding, work_unit_id = self._candidate_lineage(product, candidate)
            effects = runtime.repository_integration_effects_for_candidate(candidate.id)
            if len(effects) > 1:
                raise MeasurementLineageError(
                    "Integration measurement v0 requires one Effect per Candidate"
                )
            effect = None if not effects else effects[0]
            if effect is None or effect.converged_at is None:
                source_facts = () if effect is None else (
                    MeasurementSourceReference(
                        fact_type="REPOSITORY_INTEGRATION_EFFECT",
                        fact_id=effect.id,
                        field_name="prepared_at",
                        observed_at=effect.prepared_at,
                    ),
                )
                return self._unavailable(
                    kind=ProductionMeasurementKind.INTEGRATION,
                    scope=ProductionMeasurementScope.INTEGRATION_CONVERGENCE,
                    phase=ProductionPhase.INTEGRATION,
                    subject_type=(
                        "BASELINE_CANDIDATE"
                        if effect is None
                        else "REPOSITORY_INTEGRATION_EFFECT"
                    ),
                    subject_id=candidate.id if effect is None else effect.id,
                    work_id=binding.work_id,
                    work_unit_id=work_unit_id,
                    reason=(
                        "No Integration Effect exists for this Candidate"
                        if effect is None
                        else "Integration Effect has not recorded convergence"
                    ),
                    source_facts=source_facts,
                )
            return self._integration_interval(
                binding,
                work_unit_id,
                effect,
            )

    def verification_measurements(
        self,
        work_unit_id: UUID,
    ) -> tuple[ProductionMeasurementV0, ...]:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            binding, _ = self._required_pwu_lineage(
                product,
                runtime,
                work_unit_id,
            )
            records = runtime.verification_records_for_work_unit(work_unit_id)
            total = self._unavailable(
                kind=ProductionMeasurementKind.VERIFICATION,
                scope=ProductionMeasurementScope.PWU_VERIFICATION_TOTAL,
                phase=ProductionPhase.VERIFICATION,
                subject_type="PRODUCTION_WORK_UNIT",
                subject_id=work_unit_id,
                work_id=binding.work_id,
                work_unit_id=work_unit_id,
                reason=(
                    "Verification v0 has no authoritative aggregate "
                    "start/end boundary"
                ),
                source_facts=tuple(
                    MeasurementSourceReference(
                        fact_type="VERIFICATION_RECORD",
                        fact_id=record.id,
                        field_name="created_at_not_verification_start",
                        observed_at=record.created_at,
                    )
                    for record in records
                ),
            )
            individual = tuple(
                measurement
                for record in records
                if (measurement := self._verification_observed_duration(binding, record))
                is not None
            )
            return (total, *individual)

    def total_cycle_measurement(self, work_id: UUID) -> ProductionMeasurementV0:
        with self.database.unit_of_work() as unit_of_work:
            product = ProductStore(unit_of_work.session)
            runtime = RuntimeStore(unit_of_work.session)
            steering = SteeringStore(unit_of_work.session)
            work = product.work(work_id)
            if work is None:
                raise MeasurementSubjectNotFound(f"Work not found: {work_id}")
            admissions = tuple(
                record
                for record in runtime.governance_for_subject(str(work_id))
                if record.decision_type == "ADMIT_LONG_LIVED_WORK"
            )
            if work.mode is not WorkMode.LONG_LIVED_STEERING:
                return self._unavailable(
                    kind=ProductionMeasurementKind.TOTAL_STEERING_CYCLE,
                    scope=ProductionMeasurementScope.LONG_LIVED_WORK_CYCLE,
                    phase=ProductionPhase.TRUSTED_COMPLETION,
                    subject_type="PRODUCT_WORK",
                    subject_id=work.id,
                    work_id=work.id,
                    reason="Total-cycle v0 is scoped to LONG_LIVED_STEERING Work",
                )
            if len(admissions) != 1:
                return self._unavailable(
                    kind=ProductionMeasurementKind.TOTAL_STEERING_CYCLE,
                    scope=ProductionMeasurementScope.LONG_LIVED_WORK_CYCLE,
                    phase=ProductionPhase.TRUSTED_COMPLETION,
                    subject_type="PRODUCT_WORK",
                    subject_id=work.id,
                    work_id=work.id,
                    reason=(
                        "Long-lived total cycle requires exactly one persisted "
                        "Work admission fact"
                    ),
                )
            plan = steering.plan_for_work(work.id)
            decision = (
                None
                if plan is None
                else steering.latest_decision_for_plan(plan.id)
            )
            admission = admissions[0]
            if decision is None or decision.steering_outcome is not SteeringOutcome.COMPLETE:
                return self._unavailable(
                    kind=ProductionMeasurementKind.TOTAL_STEERING_CYCLE,
                    scope=ProductionMeasurementScope.LONG_LIVED_WORK_CYCLE,
                    phase=ProductionPhase.TRUSTED_COMPLETION,
                    subject_type="PRODUCT_WORK",
                    subject_id=work.id,
                    work_id=work.id,
                    reason="Long-lived Work has no terminal COMPLETE Steering Decision",
                    source_facts=(
                        MeasurementSourceReference(
                            fact_type="GOVERNANCE_RECORD",
                            fact_id=admission.id,
                            field_name="created_at_as_work_admission",
                            observed_at=admission.created_at,
                        ),
                    ),
                )
            return self._interval(
                kind=ProductionMeasurementKind.TOTAL_STEERING_CYCLE,
                scope=ProductionMeasurementScope.LONG_LIVED_WORK_CYCLE,
                phase=ProductionPhase.TRUSTED_COMPLETION,
                subject_type="PRODUCT_WORK",
                subject_id=work.id,
                work_id=work.id,
                work_unit_id=None,
                attempt_id=None,
                started_at=admission.created_at,
                finished_at=decision.created_at,
                source_facts=(
                    MeasurementSourceReference(
                        fact_type="GOVERNANCE_RECORD",
                        fact_id=admission.id,
                        field_name="created_at_as_work_admission",
                        observed_at=admission.created_at,
                    ),
                    MeasurementSourceReference(
                        fact_type="STEERING_DECISION",
                        fact_id=decision.id,
                        field_name="created_at_as_complete",
                        observed_at=decision.created_at,
                    ),
                ),
            )

    def sample_for_work_unit(
        self,
        work_unit_id: UUID,
    ) -> ProductionMeasurementSampleV0:
        shape = self.task_shape_snapshot(work_unit_id)
        with self.database.unit_of_work() as unit_of_work:
            runtime = RuntimeStore(unit_of_work.session)
            attempts = runtime.attempts_for_work_unit(work_unit_id)
            candidates = runtime.baseline_candidates_for_work_unit(work_unit_id)
        measurements: list[ProductionMeasurementV0] = [
            self.machine_execution_measurement(attempt.id) for attempt in attempts
        ]
        measurements.extend(self.verification_measurements(work_unit_id))
        for candidate in candidates:
            measurements.append(self.human_wait_measurement(candidate.id))
            measurements.append(self.integration_measurement(candidate.id))
        measurements.append(self.total_cycle_measurement(shape.work_id))
        return ProductionMeasurementSampleV0(
            task_shape=shape,
            measurements=tuple(measurements),
        )

    @staticmethod
    def _required_pwu_lineage(
        product: ProductStore,
        runtime: RuntimeStore,
        work_unit_id: UUID,
    ) -> tuple[WorkRuntimeBindingRecord, WorkUnitRecord]:
        binding = product.runtime_binding_for_work_unit(work_unit_id)
        work_unit = runtime.work_unit(work_unit_id)
        if binding is None or work_unit is None:
            raise MeasurementSubjectNotFound(
                f"Admitted Work/PWU lineage not found: {work_unit_id}"
            )
        if (
            binding.work_unit_id != work_unit.id
            or binding.production_run_id != work_unit.production_run_id
            or binding.plan_revision_id != work_unit.plan_revision_id
        ):
            raise MeasurementLineageError("Work/PWU Runtime binding does not match")
        return binding, work_unit

    @staticmethod
    def _candidate_lineage(
        product: ProductStore,
        candidate: BaselineCandidateRecord,
    ) -> tuple[WorkRuntimeBindingRecord, UUID]:
        if len(candidate.satisfied_work_unit_ids) != 1:
            raise MeasurementLineageError(
                "DCP-2 v0 Candidate measurement requires one satisfied PWU"
            )
        work_unit_id = candidate.satisfied_work_unit_ids[0]
        binding = product.runtime_binding_for_work_unit(work_unit_id)
        if binding is None or binding.production_run_id != candidate.production_run_id:
            raise MeasurementLineageError("Candidate Work/PWU lineage does not match")
        return binding, work_unit_id

    @classmethod
    def _task_shape(
        cls,
        binding: WorkRuntimeBindingRecord,
        work_unit: WorkUnitRecord,
        baseline_repository_identity: str,
    ) -> TaskShapeSnapshotV0:
        contract = work_unit.completion_contract
        plan = contract.production_plan
        change = contract.change_contract or (
            None if plan is None else plan.change_contract
        )
        artifact_targets = () if plan is None else plan.artifact_targets
        if not artifact_targets and contract.artifact_contract is not None:
            artifact_targets = (contract.artifact_contract,)
        exact_targets = () if change is None else change.exact_targets
        operations = tuple(
            getattr(target.operation, "value", str(target.operation))
            for target in (*artifact_targets, *exact_targets)
        )
        target_kind = (
            plan.target_kind
            if plan is not None
            else ProductionTargetKind.CODE_WORK
            if change is not None
            else ProductionTargetKind.DOCUMENTATION_WORK
            if artifact_targets
            else None
        )
        repository_identity = (
            change.repository_identity
            if change is not None
            else contract.artifact_contract.repository_identity
            if contract.artifact_contract is not None
            else plan.repository_identity
            if plan is not None
            else baseline_repository_identity
        )
        unavailable = (
            "context_reference_count",
            "executor_capability_identity",
            "executor_profile_identity",
        )
        source_facts = (
            TaskShapeSourceReference(
                fact_type="WORK_RUNTIME_BINDING",
                fact_id=binding.id,
                field_name="work/resource/plan/PWU lineage",
            ),
            TaskShapeSourceReference(
                fact_type="PLAN_REVISION",
                fact_id=work_unit.plan_revision_id,
                field_name="planning identity",
            ),
            TaskShapeSourceReference(
                fact_type="PRODUCTION_WORK_UNIT",
                fact_id=work_unit.id,
                field_name="objective/completion_contract/created_at",
            ),
            TaskShapeSourceReference(
                fact_type="PRODUCTION_SNAPSHOT",
                fact_id=work_unit.source_baseline_id,
                field_name="repository identity and source basis",
            ),
        )
        payload = {
            "semantic_version": "DCP2_TASK_SHAPE_V0",
            "captured_at": work_unit.created_at.isoformat(),
            "work_id": str(binding.work_id),
            "production_plan_revision_id": str(work_unit.plan_revision_id),
            "production_plan_proposal_id": (
                None if plan is None else str(plan.proposal_id)
            ),
            "work_unit_id": str(work_unit.id),
            "resource_id": str(binding.resource_id),
            "source_baseline_id": str(work_unit.source_baseline_id),
            "repository_identity": repository_identity,
            "target_kind": None if target_kind is None else target_kind.value,
            "target_path_count": len(artifact_targets) + len(exact_targets),
            "create_count": operations.count(ChangeOperation.CREATE.value),
            "update_count": operations.count(ChangeOperation.UPDATE.value),
            "allowed_scope_count": 0 if change is None else len(change.allowed_areas),
            "forbidden_scope_count": (
                len(contract.forbidden_changes)
                if change is None
                else len(change.forbidden_areas)
            ),
            "required_output_count": len(contract.required_outputs),
            "required_change_count": len(contract.required_changes),
            "verification_obligation_count": len(contract.verification_obligations),
            "ordered_planning_step_count": 0 if plan is None else len(plan.ordered_steps),
            "context_reference_count": None,
            "executor_capability_identity": None,
            "executor_profile_identity": None,
            "unavailable_facts": unavailable,
            "source_facts": [item.model_dump(mode="json") for item in source_facts],
        }
        fingerprint = cls._fingerprint(payload)
        return TaskShapeSnapshotV0(
            snapshot_id=uuid5(
                NAMESPACE_URL,
                f"spg:dcp2:task-shape:{work_unit.id}:{fingerprint}",
            ),
            basis_fingerprint=fingerprint,
            source_facts=source_facts,
            **{key: value for key, value in payload.items() if key not in {"source_facts"}},
        )

    @classmethod
    def _verification_observed_duration(
        cls,
        binding: WorkRuntimeBindingRecord,
        record: VerificationRecord,
    ) -> ProductionMeasurementV0 | None:
        duration_ms = record.evidence.metadata.get("duration_ms")
        if not isinstance(duration_ms, int) or isinstance(duration_ms, bool) or duration_ms < 0:
            return None
        source_facts = (
            MeasurementSourceReference(
                fact_type="VERIFICATION_RECORD",
                fact_id=record.id,
                field_name="evidence.metadata.duration_ms",
                observed_at=record.created_at,
            ),
        )
        return cls._available_duration(
            kind=ProductionMeasurementKind.VERIFICATION,
            scope=ProductionMeasurementScope.VERIFICATION_OBLIGATION,
            phase=ProductionPhase.VERIFICATION,
            subject_type="VERIFICATION_RECORD",
            subject_id=record.id,
            work_id=binding.work_id,
            work_unit_id=record.work_unit_id,
            attempt_id=None,
            duration_microseconds=duration_ms * 1_000,
            source_facts=source_facts,
        )

    @classmethod
    def _integration_interval(
        cls,
        binding: WorkRuntimeBindingRecord,
        work_unit_id: UUID,
        effect: RepositoryIntegrationEffectRecord,
    ) -> ProductionMeasurementV0:
        assert effect.converged_at is not None
        return cls._interval(
            kind=ProductionMeasurementKind.INTEGRATION,
            scope=ProductionMeasurementScope.INTEGRATION_CONVERGENCE,
            phase=ProductionPhase.INTEGRATION,
            subject_type="REPOSITORY_INTEGRATION_EFFECT",
            subject_id=effect.id,
            work_id=binding.work_id,
            work_unit_id=work_unit_id,
            attempt_id=None,
            started_at=effect.prepared_at,
            finished_at=effect.converged_at,
            source_facts=(
                MeasurementSourceReference(
                    fact_type="REPOSITORY_INTEGRATION_EFFECT",
                    fact_id=effect.id,
                    field_name="prepared_at",
                    observed_at=effect.prepared_at,
                ),
                MeasurementSourceReference(
                    fact_type="REPOSITORY_INTEGRATION_EFFECT",
                    fact_id=effect.id,
                    field_name="converged_at",
                    observed_at=effect.converged_at,
                ),
            ),
        )

    @classmethod
    def _interval(
        cls,
        *,
        kind: ProductionMeasurementKind,
        scope: ProductionMeasurementScope,
        phase: ProductionPhase,
        subject_type: str,
        subject_id: UUID,
        work_id: UUID,
        work_unit_id: UUID | None,
        attempt_id: UUID | None,
        started_at: datetime,
        finished_at: datetime,
        source_facts: tuple[MeasurementSourceReference, ...],
        internal_turn_count: int | None = None,
        self_refine_occurred: bool | None = None,
    ) -> ProductionMeasurementV0:
        delta = finished_at - started_at
        duration_microseconds = (
            delta.days * 86_400_000_000
            + delta.seconds * 1_000_000
            + delta.microseconds
        )
        if duration_microseconds < 0:
            raise MeasurementLineageError("Measurement end precedes its start")
        return cls._available_duration(
            kind=kind,
            scope=scope,
            phase=phase,
            subject_type=subject_type,
            subject_id=subject_id,
            work_id=work_id,
            work_unit_id=work_unit_id,
            attempt_id=attempt_id,
            duration_microseconds=duration_microseconds,
            source_facts=source_facts,
            observed_start_at=started_at,
            observed_end_at=finished_at,
            derivation=MeasurementDerivation.DERIVED_INTERVAL,
            internal_turn_count=internal_turn_count,
            self_refine_occurred=self_refine_occurred,
        )

    @classmethod
    def _available_duration(
        cls,
        *,
        kind: ProductionMeasurementKind,
        scope: ProductionMeasurementScope,
        phase: ProductionPhase,
        subject_type: str,
        subject_id: UUID,
        work_id: UUID,
        work_unit_id: UUID | None,
        attempt_id: UUID | None,
        duration_microseconds: int,
        source_facts: tuple[MeasurementSourceReference, ...],
        observed_start_at: datetime | None = None,
        observed_end_at: datetime | None = None,
        derivation: MeasurementDerivation = MeasurementDerivation.OBSERVED_DURATION,
        internal_turn_count: int | None = None,
        self_refine_occurred: bool | None = None,
    ) -> ProductionMeasurementV0:
        payload = {
            "semantic_version": "DCP2_PRODUCTION_MEASUREMENT_V0",
            "kind": kind.value,
            "scope": scope.value,
            "phase": phase.value,
            "availability": MeasurementAvailability.AVAILABLE.value,
            "derivation": derivation.value,
            "subject_type": subject_type,
            "subject_id": str(subject_id),
            "work_id": str(work_id),
            "work_unit_id": None if work_unit_id is None else str(work_unit_id),
            "attempt_id": None if attempt_id is None else str(attempt_id),
            "observed_start_at": (
                None if observed_start_at is None else observed_start_at.isoformat()
            ),
            "observed_end_at": (
                None if observed_end_at is None else observed_end_at.isoformat()
            ),
            "duration_microseconds": duration_microseconds,
            "source_facts": [item.model_dump(mode="json") for item in source_facts],
            "internal_turn_count": internal_turn_count,
            "self_refine_occurred": self_refine_occurred,
        }
        fingerprint = cls._fingerprint(payload)
        return ProductionMeasurementV0(
            measurement_id=uuid5(
                NAMESPACE_URL,
                f"spg:dcp2:measurement:{fingerprint}",
            ),
            basis_fingerprint=fingerprint,
            source_facts=source_facts,
            **{key: value for key, value in payload.items() if key != "source_facts"},
        )

    @classmethod
    def _unavailable(
        cls,
        *,
        kind: ProductionMeasurementKind,
        scope: ProductionMeasurementScope,
        phase: ProductionPhase,
        subject_type: str,
        subject_id: UUID,
        work_id: UUID,
        reason: str,
        work_unit_id: UUID | None = None,
        attempt_id: UUID | None = None,
        source_facts: tuple[MeasurementSourceReference, ...] = (),
    ) -> ProductionMeasurementV0:
        payload = {
            "semantic_version": "DCP2_PRODUCTION_MEASUREMENT_V0",
            "kind": kind.value,
            "scope": scope.value,
            "phase": phase.value,
            "availability": MeasurementAvailability.UNAVAILABLE.value,
            "derivation": MeasurementDerivation.UNAVAILABLE.value,
            "subject_type": subject_type,
            "subject_id": str(subject_id),
            "work_id": str(work_id),
            "work_unit_id": None if work_unit_id is None else str(work_unit_id),
            "attempt_id": None if attempt_id is None else str(attempt_id),
            "source_facts": [item.model_dump(mode="json") for item in source_facts],
            "unavailable_reason": reason,
        }
        fingerprint = cls._fingerprint(payload)
        return ProductionMeasurementV0(
            measurement_id=uuid5(
                NAMESPACE_URL,
                f"spg:dcp2:measurement:{fingerprint}",
            ),
            basis_fingerprint=fingerprint,
            source_facts=source_facts,
            **{key: value for key, value in payload.items() if key != "source_facts"},
        )

    @staticmethod
    def _positive_int(value: object) -> int | None:
        return (
            value
            if isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 1
            else None
        )

    @staticmethod
    def _optional_bool(value: object) -> bool | None:
        return value if isinstance(value, bool) else None

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        return sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
