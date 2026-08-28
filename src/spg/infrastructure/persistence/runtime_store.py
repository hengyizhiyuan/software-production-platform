"""One bounded SQLAlchemy adapter for admitted Runtime state persistence."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from spg.domain.completion import (
    CompletionEvaluationOutcome,
    CompletionEvaluationRecord,
    CompletionObligationResult,
    CompletionWorkProductLineage,
)
from spg.domain.verification import (
    ProductionAdmissibilityObligation,
    ProductionAdmissibilityOutcome,
    ProductionAdmissibilityRecord,
    ProposedRepositorySnapshotRecord,
    VerificationEvidence,
    VerificationProviderBinding,
    VerificationRecord,
    VerificationResultValue,
)
from spg.domain.runtime import (
    AttemptCondition,
    BaselinePointerRecord,
    CompletionContract,
    ExecutionAttemptRecord,
    GovernanceRecord,
    PlanCondition,
    PlanRevisionRecord,
    ProductionHorizon,
    ProductionRunRecord,
    RunCondition,
    SnapshotCondition,
    SnapshotRecord,
    TransitionRecord,
    WorkUnitCondition,
    WorkUnitRecord,
)
from spg.domain.preparation import (
    AttemptPreparationRecord,
    ContextPackageManifest,
    ContextPackageRecord,
    ExecutorBinding,
    WorkspaceBinding,
)
from spg.domain.execution import (
    ArtifactChangeType,
    ExecutionDispatchRecord,
    ObservedArtifactChange,
    ProviderExecutionReportRecord,
    ProviderReportedOutcome,
    RepositoryObservationRecord,
    WorkProductReferenceRecord,
)
from spg.infrastructure.persistence.concurrency import update_versioned_row
from spg.infrastructure.persistence.runtime_schema import (
    attempt_preparations,
    completion_evaluations,
    context_packages,
    current_trusted_baseline_pointer,
    execution_attempts,
    governance_records,
    plan_revisions,
    production_runs,
    production_snapshots,
    production_work_units,
    transition_history,
    execution_dispatches,
    provider_execution_reports,
    repository_observations,
    work_product_references,
    proposed_repository_snapshots,
    verification_records,
    production_admissibility_records,
)


class RuntimeStore:
    """Persist and load the bounded Runtime spine without owning transitions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_snapshot(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(production_snapshots).values(**values))

    def insert_baseline_pointer(self, values: Mapping[str, Any]) -> None:
        self.session.execute(
            insert(current_trusted_baseline_pointer).values(**values)
        )

    def insert_governance(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(governance_records).values(**values))

    def insert_run(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(production_runs).values(**values))

    def insert_plan_revision(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(plan_revisions).values(**values))

    def insert_work_unit(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(production_work_units).values(**values))

    def insert_attempt(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(execution_attempts).values(**values))

    def insert_transition(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(transition_history).values(**values))

    def insert_context_package(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(context_packages).values(**values))

    def insert_attempt_preparation(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(attempt_preparations).values(**values))

    def insert_execution_dispatch(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(execution_dispatches).values(**values))

    def insert_provider_execution_report(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(provider_execution_reports).values(**values))

    def insert_repository_observation(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(repository_observations).values(**values))

    def insert_work_product_reference(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(work_product_references).values(**values))

    def insert_completion_evaluation(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(completion_evaluations).values(**values))

    def insert_proposed_snapshot(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(proposed_repository_snapshots).values(**values))

    def insert_verification_record(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(verification_records).values(**values))

    def insert_production_admissibility(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(production_admissibility_records).values(**values))

    def bind_run_to_plan(self, run_id: UUID, expected_version: int, plan_id: UUID) -> int:
        return update_versioned_row(
            self.session,
            production_runs,
            identity={"id": run_id},
            expected_version=expected_version,
            values={"current_plan_revision_id": plan_id},
        )

    def advance_work_unit_generation(
        self,
        work_unit_id: UUID,
        expected_version: int,
        generation: int,
    ) -> int:
        return update_versioned_row(
            self.session,
            production_work_units,
            identity={"id": work_unit_id},
            expected_version=expected_version,
            values={"current_execution_generation": generation},
        )

    def mark_work_unit_produced(
        self,
        work_unit_id: UUID,
        expected_version: int,
    ) -> int:
        return update_versioned_row(
            self.session,
            production_work_units,
            identity={
                "id": work_unit_id,
                "condition": WorkUnitCondition.PROPOSED.value,
            },
            expected_version=expected_version,
            values={"condition": WorkUnitCondition.PRODUCED.value},
        )

    def mark_work_unit_satisfied(
        self,
        work_unit_id: UUID,
        expected_version: int,
    ) -> int:
        return update_versioned_row(
            self.session,
            production_work_units,
            identity={
                "id": work_unit_id,
                "condition": WorkUnitCondition.PRODUCED.value,
            },
            expected_version=expected_version,
            values={"condition": WorkUnitCondition.SATISFIED.value},
        )

    def update_baseline_pointer(
        self,
        expected_version: int,
        snapshot_id: UUID,
    ) -> int:
        """Provide the version-aware pointer primitive without advancing a baseline."""

        return update_versioned_row(
            self.session,
            current_trusted_baseline_pointer,
            identity={"singleton_id": 1},
            expected_version=expected_version,
            values={"snapshot_id": snapshot_id, "updated_at": func.now()},
        )

    def current_pointer(self) -> BaselinePointerRecord | None:
        row = self.session.execute(
            select(current_trusted_baseline_pointer).where(
                current_trusted_baseline_pointer.c.singleton_id == 1
            )
        ).mappings().one_or_none()
        if row is None:
            return None
        values = dict(row)
        values.pop("singleton_id")
        return BaselinePointerRecord.model_validate(values)

    def snapshot(self, snapshot_id: UUID) -> SnapshotRecord | None:
        row = self._one(production_snapshots, production_snapshots.c.id == snapshot_id)
        if row is None:
            return None
        values = dict(row)
        values["condition"] = SnapshotCondition(values["condition"])
        return SnapshotRecord.model_validate(values)

    def governance_for_subject(self, subject_identity: str) -> list[GovernanceRecord]:
        rows = self.session.execute(
            select(governance_records)
            .where(governance_records.c.subject_identity == subject_identity)
            .order_by(governance_records.c.created_at, governance_records.c.id)
        ).mappings()
        return [GovernanceRecord.model_validate(dict(row)) for row in rows]

    def run(self, run_id: UUID) -> ProductionRunRecord | None:
        row = self._one(production_runs, production_runs.c.id == run_id)
        if row is None or row["current_plan_revision_id"] is None:
            return None
        values = dict(row)
        values["production_horizon"] = ProductionHorizon(
            values["production_horizon"]
        )
        values["condition"] = RunCondition(values["condition"])
        return ProductionRunRecord.model_validate(values)

    def plan_revision(self, plan_id: UUID) -> PlanRevisionRecord | None:
        row = self._one(plan_revisions, plan_revisions.c.id == plan_id)
        if row is None:
            return None
        values = dict(row)
        values["condition"] = PlanCondition(values["condition"])
        return PlanRevisionRecord.model_validate(values)

    def work_unit(
        self,
        work_unit_id: UUID,
        *,
        for_update: bool = False,
    ) -> WorkUnitRecord | None:
        statement = select(production_work_units).where(
            production_work_units.c.id == work_unit_id
        )
        if for_update:
            statement = statement.with_for_update()
        row = self.session.execute(statement).mappings().one_or_none()
        if row is None:
            return None
        return self._work_unit_record(row)

    def work_unit_for_run(self, run_id: UUID) -> WorkUnitRecord | None:
        row = self.session.execute(
            select(production_work_units)
            .where(production_work_units.c.production_run_id == run_id)
            .order_by(production_work_units.c.created_at)
            .limit(1)
        ).mappings().one_or_none()
        if row is None:
            return None
        return self._work_unit_record(row)

    def attempt(self, attempt_id: UUID) -> ExecutionAttemptRecord | None:
        row = self._one(execution_attempts, execution_attempts.c.id == attempt_id)
        if row is None:
            return None
        values = dict(row)
        values["condition"] = AttemptCondition(values["condition"])
        return ExecutionAttemptRecord.model_validate(values)

    def transitions(self) -> list[TransitionRecord]:
        rows = self.session.execute(
            select(transition_history).order_by(
                transition_history.c.created_at,
                transition_history.c.id,
            )
        ).mappings()
        return [TransitionRecord.model_validate(dict(row)) for row in rows]

    def context_package(self, package_id: UUID) -> ContextPackageRecord | None:
        row = self._one(context_packages, context_packages.c.id == package_id)
        if row is None:
            return None
        return self._context_package_record(row)

    def latest_context_package(self, work_unit_id: UUID) -> ContextPackageRecord | None:
        row = self.session.execute(
            select(context_packages)
            .where(context_packages.c.work_unit_id == work_unit_id)
            .order_by(context_packages.c.version.desc())
            .limit(1)
        ).mappings().one_or_none()
        if row is None:
            return None
        return self._context_package_record(row)

    def attempt_preparation(
        self,
        attempt_id: UUID,
    ) -> AttemptPreparationRecord | None:
        row = self._one(
            attempt_preparations,
            attempt_preparations.c.attempt_id == attempt_id,
        )
        if row is None:
            return None
        values = dict(row)
        executor_binding = ExecutorBinding.model_validate(values.pop("executor_binding"))
        workspace = WorkspaceBinding(
            workspace_identity=values.pop("workspace_identity"),
            workspace_path=values.pop("workspace_path"),
            repository_identity=values.pop("repository_identity"),
            repository_path=values.pop("repository_path"),
            source_revision=values.pop("source_revision"),
        )
        return AttemptPreparationRecord.model_validate(
            {
                **values,
                "executor_binding": executor_binding,
                "workspace": workspace,
            }
        )

    def execution_dispatch(self, dispatch_id: UUID) -> ExecutionDispatchRecord | None:
        row = self._one(execution_dispatches, execution_dispatches.c.id == dispatch_id)
        if row is None:
            return None
        return self._execution_dispatch_record(row)

    def execution_dispatch_for_attempt(
        self,
        attempt_id: UUID,
    ) -> ExecutionDispatchRecord | None:
        row = self._one(
            execution_dispatches,
            execution_dispatches.c.attempt_id == attempt_id,
        )
        if row is None:
            return None
        return self._execution_dispatch_record(row)

    def provider_execution_report(
        self,
        dispatch_id: UUID,
    ) -> ProviderExecutionReportRecord | None:
        row = self._one(
            provider_execution_reports,
            provider_execution_reports.c.dispatch_id == dispatch_id,
        )
        if row is None:
            return None
        values = dict(row)
        values["executor_binding"] = ExecutorBinding.model_validate(
            values["executor_binding"]
        )
        values["outcome"] = ProviderReportedOutcome(values["outcome"])
        return ProviderExecutionReportRecord.model_validate(values)

    def repository_observation(
        self,
        dispatch_id: UUID,
    ) -> RepositoryObservationRecord | None:
        row = self._one(
            repository_observations,
            repository_observations.c.dispatch_id == dispatch_id,
        )
        if row is None:
            return None
        return self._repository_observation_record(row)

    def repository_observation_by_id(
        self,
        observation_id: UUID,
    ) -> RepositoryObservationRecord | None:
        row = self._one(
            repository_observations,
            repository_observations.c.id == observation_id,
        )
        if row is None:
            return None
        return self._repository_observation_record(row)

    def work_product_references(
        self,
        observation_id: UUID,
    ) -> tuple[WorkProductReferenceRecord, ...]:
        rows = self.session.execute(
            select(work_product_references)
            .where(
                work_product_references.c.repository_observation_id == observation_id
            )
            .order_by(work_product_references.c.artifact_path)
        ).mappings()
        records: list[WorkProductReferenceRecord] = []
        for row in rows:
            values = dict(row)
            values["change_type"] = ArtifactChangeType(values["change_type"])
            records.append(WorkProductReferenceRecord.model_validate(values))
        return tuple(records)

    def completion_evaluation_by_basis(
        self,
        basis_fingerprint: str,
    ) -> CompletionEvaluationRecord | None:
        row = self._one(
            completion_evaluations,
            completion_evaluations.c.basis_fingerprint == basis_fingerprint,
        )
        if row is None:
            return None
        return self._completion_evaluation_record(row)

    def completion_evaluation(
        self,
        evaluation_id: UUID,
    ) -> CompletionEvaluationRecord | None:
        row = self._one(
            completion_evaluations,
            completion_evaluations.c.id == evaluation_id,
        )
        if row is None:
            return None
        return self._completion_evaluation_record(row)

    def completion_evaluations_for_work_unit(
        self,
        work_unit_id: UUID,
    ) -> tuple[CompletionEvaluationRecord, ...]:
        rows = self.session.execute(
            select(completion_evaluations)
            .where(completion_evaluations.c.work_unit_id == work_unit_id)
            .order_by(completion_evaluations.c.created_at, completion_evaluations.c.id)
        ).mappings()
        return tuple(self._completion_evaluation_record(row) for row in rows)

    def proposed_snapshot_by_basis(
        self,
        basis_fingerprint: str,
    ) -> ProposedRepositorySnapshotRecord | None:
        row = self._one(
            proposed_repository_snapshots,
            proposed_repository_snapshots.c.basis_fingerprint == basis_fingerprint,
        )
        if row is None:
            return None
        return ProposedRepositorySnapshotRecord.model_validate(dict(row))

    def proposed_snapshot(
        self,
        snapshot_id: UUID,
    ) -> ProposedRepositorySnapshotRecord | None:
        row = self._one(
            proposed_repository_snapshots,
            proposed_repository_snapshots.c.id == snapshot_id,
        )
        if row is None:
            return None
        return ProposedRepositorySnapshotRecord.model_validate(dict(row))

    def verification_record_by_basis(
        self,
        basis_fingerprint: str,
    ) -> VerificationRecord | None:
        row = self._one(
            verification_records,
            verification_records.c.basis_fingerprint == basis_fingerprint,
        )
        if row is None:
            return None
        return self._verification_record(row)

    def verification_record(self, record_id: UUID) -> VerificationRecord | None:
        row = self._one(verification_records, verification_records.c.id == record_id)
        if row is None:
            return None
        return self._verification_record(row)

    def verification_records_for_snapshot(
        self,
        snapshot_id: UUID,
    ) -> tuple[VerificationRecord, ...]:
        rows = self.session.execute(
            select(verification_records)
            .where(verification_records.c.proposed_snapshot_id == snapshot_id)
            .order_by(verification_records.c.created_at, verification_records.c.id)
        ).mappings()
        return tuple(self._verification_record(row) for row in rows)

    def production_admissibility_by_basis(
        self,
        basis_fingerprint: str,
    ) -> ProductionAdmissibilityRecord | None:
        row = self._one(
            production_admissibility_records,
            production_admissibility_records.c.basis_fingerprint == basis_fingerprint,
        )
        if row is None:
            return None
        return self._production_admissibility_record(row)

    def production_admissibility_for_snapshot(
        self,
        snapshot_id: UUID,
    ) -> tuple[ProductionAdmissibilityRecord, ...]:
        rows = self.session.execute(
            select(production_admissibility_records)
            .where(production_admissibility_records.c.proposed_snapshot_id == snapshot_id)
            .order_by(
                production_admissibility_records.c.created_at,
                production_admissibility_records.c.id,
            )
        ).mappings()
        return tuple(self._production_admissibility_record(row) for row in rows)

    @staticmethod
    def _work_unit_record(row: Mapping[str, Any]) -> WorkUnitRecord:
        values = dict(row)
        values["completion_contract"] = CompletionContract.model_validate(
            values["completion_contract"]
        )
        values["condition"] = WorkUnitCondition(values["condition"])
        return WorkUnitRecord.model_validate(values)

    @staticmethod
    def _context_package_record(row: Mapping[str, Any]) -> ContextPackageRecord:
        values = dict(row)
        values["manifest"] = ContextPackageManifest.model_validate(values["manifest"])
        return ContextPackageRecord.model_validate(values)

    @staticmethod
    def _execution_dispatch_record(row: Mapping[str, Any]) -> ExecutionDispatchRecord:
        values = dict(row)
        values["executor_binding"] = ExecutorBinding.model_validate(
            values.pop("executor_binding")
        )
        values["workspace"] = WorkspaceBinding(
            workspace_identity=values.pop("workspace_identity"),
            workspace_path=values.pop("workspace_path"),
            repository_identity=values.pop("repository_identity"),
            repository_path=values.pop("repository_path"),
            source_revision=values.pop("source_revision"),
        )
        return ExecutionDispatchRecord.model_validate(values)

    @staticmethod
    def _repository_observation_record(
        row: Mapping[str, Any],
    ) -> RepositoryObservationRecord:
        values = dict(row)
        values["changes"] = tuple(
            ObservedArtifactChange.model_validate(item)
            for item in values.pop("change_manifest")
        )
        return RepositoryObservationRecord.model_validate(values)

    @staticmethod
    def _completion_evaluation_record(
        row: Mapping[str, Any],
    ) -> CompletionEvaluationRecord:
        values = dict(row)
        values["outcome"] = CompletionEvaluationOutcome(values["outcome"])
        values["work_product_lineage"] = tuple(
            CompletionWorkProductLineage.model_validate(item)
            for item in values["work_product_lineage"]
        )
        values["obligation_results"] = tuple(
            CompletionObligationResult.model_validate(item)
            for item in values["obligation_results"]
        )
        return CompletionEvaluationRecord.model_validate(values)

    @staticmethod
    def _verification_record(row: Mapping[str, Any]) -> VerificationRecord:
        values = dict(row)
        values["provider"] = VerificationProviderBinding.model_validate(
            values.pop("provider_binding")
        )
        values["result"] = VerificationResultValue(values["result"])
        values["evidence"] = VerificationEvidence.model_validate(values["evidence"])
        return VerificationRecord.model_validate(values)

    @staticmethod
    def _production_admissibility_record(
        row: Mapping[str, Any],
    ) -> ProductionAdmissibilityRecord:
        values = dict(row)
        values["outcome"] = ProductionAdmissibilityOutcome(values["outcome"])
        values["verification_record_ids"] = tuple(
            UUID(value) for value in values["verification_record_ids"]
        )
        values["obligation_results"] = tuple(
            ProductionAdmissibilityObligation.model_validate(item)
            for item in values["obligation_results"]
        )
        return ProductionAdmissibilityRecord.model_validate(values)

    def _one(self, table, condition) -> Mapping[str, Any] | None:
        return self.session.execute(select(table).where(condition)).mappings().one_or_none()
