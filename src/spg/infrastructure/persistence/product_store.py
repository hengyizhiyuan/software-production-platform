"""Persistence adapter for product-owned Goal, Work, and Engineering Scope facts."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from spg.domain.product import (
    ArtifactTargetConfidence,
    ArtifactTargetOperation,
    EngineeringContextReference,
    EngineeringResourceKind,
    EngineeringResourceRecord,
    EngineeringScopeCondition,
    EngineeringScopeRecord,
    GoalCondition,
    GoalRecord,
    ProductionCycleBindingCondition,
    ResourceBindingCondition,
    ResourceBindingRecord,
    RuntimeFactSummary,
    WorkCondition,
    WorkMode,
    WorkRecord,
    WorkRuntimeBindingRecord,
)
from spg.domain.runtime import CompletionContract
from spg.domain.planning import ProductionPlanProposal
from spg.domain.refinement import RepositoryChangeProposal
from spg.infrastructure.persistence.product_schema import (
    engineering_resource_bindings,
    engineering_resources,
    engineering_scopes,
    product_goals,
    product_works,
    work_runtime_bindings,
)
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    completion_evaluations,
    execution_attempts,
    execution_dispatches,
    human_authorizations,
    production_admissibility_records,
    production_work_units,
    provider_execution_reports,
    proposed_repository_snapshots,
    repository_integration_effects,
    repository_observations,
    runtime_commits,
    transition_history,
    verification_records,
    work_product_references,
)


class ProductStore:
    """Own product facts and read Runtime facts without changing their authority."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_goal(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(product_goals).values(**values))

    def goal(self, goal_id: UUID) -> GoalRecord | None:
        row = self._one(product_goals, product_goals.c.id == goal_id)
        return None if row is None else self._goal(row)

    def list_goals(self) -> tuple[GoalRecord, ...]:
        rows = self.session.execute(
            select(product_goals).order_by(product_goals.c.created_at, product_goals.c.id)
        ).mappings()
        return tuple(self._goal(row) for row in rows)

    def insert_resource(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(engineering_resources).values(**values))

    def resource(self, resource_id: UUID) -> EngineeringResourceRecord | None:
        row = self._one(engineering_resources, engineering_resources.c.id == resource_id)
        return None if row is None else self._resource(row)

    def default_resource(self) -> EngineeringResourceRecord | None:
        row = self._one(engineering_resources, engineering_resources.c.is_default.is_(True))
        return None if row is None else self._resource(row)

    def insert_work(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(product_works).values(**values))

    def update_work(self, work_id: UUID, values: Mapping[str, Any]) -> None:
        result = self.session.execute(
            update(product_works).where(product_works.c.id == work_id).values(**values)
        )
        if result.rowcount != 1:
            raise LookupError(f"Work not found: {work_id}")

    def work(self, work_id: UUID) -> WorkRecord | None:
        row = self._one(product_works, product_works.c.id == work_id)
        return None if row is None else self._work(row)

    def list_works(self, goal_id: UUID | None = None) -> tuple[WorkRecord, ...]:
        statement = select(product_works)
        if goal_id is not None:
            statement = statement.where(product_works.c.goal_id == goal_id)
        rows = self.session.execute(
            statement.order_by(product_works.c.created_at.desc(), product_works.c.id)
        ).mappings()
        return tuple(self._work(row) for row in rows)

    def replace_scope(
        self,
        *,
        scope_values: Mapping[str, Any],
        binding_values: tuple[Mapping[str, Any], ...],
    ) -> None:
        existing = self.session.execute(
            select(engineering_scopes.c.id).where(
                engineering_scopes.c.work_id == scope_values["work_id"]
            )
        ).scalar_one_or_none()
        if existing is not None:
            self.session.execute(
                delete(engineering_resource_bindings).where(
                    engineering_resource_bindings.c.engineering_scope_id == existing
                )
            )
            self.session.execute(
                delete(engineering_scopes).where(engineering_scopes.c.id == existing)
            )
        self.session.execute(insert(engineering_scopes).values(**scope_values))
        for values in binding_values:
            self.session.execute(insert(engineering_resource_bindings).values(**values))

    def set_scope_condition(
        self,
        scope_id: UUID,
        condition: EngineeringScopeCondition,
        *,
        updated_at,
    ) -> None:
        self.session.execute(
            update(engineering_scopes)
            .where(engineering_scopes.c.id == scope_id)
            .values(condition=condition.value, updated_at=updated_at)
        )
        self.session.execute(
            update(engineering_resource_bindings)
            .where(engineering_resource_bindings.c.engineering_scope_id == scope_id)
            .values(condition=ResourceBindingCondition.ACTIVE.value)
        )

    def scope_for_work(self, work_id: UUID) -> EngineeringScopeRecord | None:
        current_scope_id = self.session.execute(
            select(product_works.c.current_engineering_scope_id).where(
                product_works.c.id == work_id
            )
        ).scalar_one_or_none()
        statement = select(engineering_scopes).where(
            engineering_scopes.c.work_id == work_id
        )
        if current_scope_id is not None:
            statement = statement.where(engineering_scopes.c.id == current_scope_id)
        row = self.session.execute(
            statement.order_by(
                engineering_scopes.c.created_at.desc(),
                engineering_scopes.c.id.desc(),
            ).limit(1)
        ).mappings().first()
        if row is None:
            return None
        bindings = self.session.execute(
            select(engineering_resource_bindings)
            .where(engineering_resource_bindings.c.engineering_scope_id == row["id"])
            .order_by(engineering_resource_bindings.c.created_at, engineering_resource_bindings.c.id)
        ).mappings()
        return EngineeringScopeRecord(
            id=row["id"],
            work_id=row["work_id"],
            summary=row["summary"],
            fingerprint=row["fingerprint"],
            condition=EngineeringScopeCondition(row["condition"]),
            bindings=tuple(self._binding(item) for item in bindings),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def insert_runtime_binding(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(work_runtime_bindings).values(**values))

    def runtime_binding(self, work_id: UUID) -> WorkRuntimeBindingRecord | None:
        row = self.session.execute(
            select(work_runtime_bindings)
            .where(work_runtime_bindings.c.work_id == work_id)
            .order_by(
                work_runtime_bindings.c.cycle_number.desc(),
                work_runtime_bindings.c.created_at.desc(),
            )
            .limit(1)
        ).mappings().first()
        if row is None:
            return None
        return self._runtime_binding(row)

    def runtime_bindings(self, work_id: UUID) -> tuple[WorkRuntimeBindingRecord, ...]:
        rows = self.session.execute(
            select(work_runtime_bindings)
            .where(work_runtime_bindings.c.work_id == work_id)
            .order_by(
                work_runtime_bindings.c.cycle_number,
                work_runtime_bindings.c.created_at,
            )
        ).mappings()
        return tuple(self._runtime_binding(row) for row in rows)

    def runtime_binding_for_step(
        self,
        steering_step_id: UUID,
    ) -> WorkRuntimeBindingRecord | None:
        row = self._one(
            work_runtime_bindings,
            work_runtime_bindings.c.steering_step_id == steering_step_id,
        )
        return None if row is None else self._runtime_binding(row)

    def runtime_binding_for_work_unit(
        self,
        work_unit_id: UUID,
    ) -> WorkRuntimeBindingRecord | None:
        row = self._one(
            work_runtime_bindings,
            work_runtime_bindings.c.work_unit_id == work_unit_id,
        )
        return None if row is None else self._runtime_binding(row)

    def associate_runtime_binding(
        self,
        binding_id: UUID,
        *,
        steering_step_id: UUID,
        steering_decision_id: UUID | None,
    ) -> None:
        result = self.session.execute(
            update(work_runtime_bindings)
            .where(
                (work_runtime_bindings.c.id == binding_id)
                & work_runtime_bindings.c.steering_step_id.is_(None)
            )
            .values(
                steering_step_id=steering_step_id,
                steering_decision_id=steering_decision_id,
            )
        )
        if result.rowcount != 1:
            raise LookupError(f"Unassociated production cycle not found: {binding_id}")

    def set_runtime_binding_condition(
        self,
        binding_id: UUID,
        condition: ProductionCycleBindingCondition,
    ) -> None:
        result = self.session.execute(
            update(work_runtime_bindings)
            .where(work_runtime_bindings.c.id == binding_id)
            .values(condition=condition.value)
        )
        if result.rowcount != 1:
            raise LookupError(f"Production cycle not found: {binding_id}")

    @staticmethod
    def _runtime_binding(row: Mapping[str, Any]) -> WorkRuntimeBindingRecord:
        return WorkRuntimeBindingRecord(
            id=row["id"],
            work_id=row["work_id"],
            cycle_number=row["cycle_number"],
            steering_step_id=row["steering_step_id"],
            steering_decision_id=row["steering_decision_id"],
            condition=ProductionCycleBindingCondition(row["condition"]),
            work_reality_revision_id=row["work_reality_revision_id"],
            engineering_scope_id=row["engineering_scope_id"],
            resource_id=row["resource_id"],
            production_run_id=row["production_run_id"],
            plan_revision_id=row["plan_revision_id"],
            work_unit_id=row["work_unit_id"],
            governance_record_id=row["governance_record_id"],
            admitted_by=row["admitted_by"],
            created_at=row["created_at"],
        )

    def runtime_summary(self, binding: WorkRuntimeBindingRecord) -> RuntimeFactSummary:
        raw_completion_contract = self.session.execute(
            select(production_work_units.c.completion_contract).where(
                production_work_units.c.id == binding.work_unit_id
            )
        ).scalar_one_or_none()
        completion_contract = (
            None
            if raw_completion_contract is None
            else CompletionContract.model_validate(raw_completion_contract)
        )
        attempt = self.session.execute(
            select(execution_attempts)
            .where(execution_attempts.c.work_unit_id == binding.work_unit_id)
            .order_by(execution_attempts.c.generation.desc())
            .limit(1)
        ).mappings().first()
        dispatch = None
        report = None
        observation = None
        if attempt is not None:
            dispatch = self.session.execute(
                select(execution_dispatches).where(
                    execution_dispatches.c.attempt_id == attempt["id"]
                )
            ).mappings().first()
        if dispatch is not None:
            report = self.session.execute(
                select(provider_execution_reports).where(
                    provider_execution_reports.c.dispatch_id == dispatch["id"]
                )
            ).mappings().first()
            observation = self.session.execute(
                select(repository_observations).where(
                    repository_observations.c.dispatch_id == dispatch["id"]
                )
            ).mappings().first()

        completion = self.session.execute(
            select(completion_evaluations)
            .where(completion_evaluations.c.work_unit_id == binding.work_unit_id)
            .order_by(completion_evaluations.c.created_at.desc())
            .limit(1)
        ).mappings().first()
        proposed = None
        if completion is not None:
            proposed = self.session.execute(
                select(proposed_repository_snapshots).where(
                    proposed_repository_snapshots.c.completion_evaluation_id
                    == completion["id"]
                )
            ).mappings().first()

        verification_rows: tuple[Mapping[str, Any], ...] = ()
        admissibility = None
        if proposed is not None:
            verification_rows = tuple(
                self.session.execute(
                    select(verification_records)
                    .where(
                        verification_records.c.proposed_snapshot_id == proposed["id"]
                    )
                    .order_by(verification_records.c.created_at, verification_records.c.id)
                ).mappings()
            )
            admissibility = self.session.execute(
                select(production_admissibility_records).where(
                    production_admissibility_records.c.proposed_snapshot_id
                    == proposed["id"]
                )
            ).mappings().first()

        candidate = self.session.execute(
            select(baseline_candidates)
            .where(baseline_candidates.c.production_run_id == binding.production_run_id)
            .order_by(baseline_candidates.c.sealed_at.desc())
            .limit(1)
        ).mappings().first()
        authorization = None
        effect = None
        runtime_commit = None
        if candidate is not None:
            authorization = self.session.execute(
                select(human_authorizations)
                .where(human_authorizations.c.candidate_id == candidate["id"])
                .order_by(human_authorizations.c.authorized_at.desc())
                .limit(1)
            ).mappings().first()
            effect = self.session.execute(
                select(repository_integration_effects)
                .where(repository_integration_effects.c.candidate_id == candidate["id"])
                .order_by(repository_integration_effects.c.prepared_at.desc())
                .limit(1)
            ).mappings().first()
            runtime_commit = self.session.execute(
                select(runtime_commits)
                .where(runtime_commits.c.candidate_id == candidate["id"])
                .order_by(runtime_commits.c.committed_at.desc())
                .limit(1)
            ).mappings().first()

        artifacts = tuple(
            row["artifact_path"]
            for row in self.session.execute(
                select(work_product_references.c.artifact_path)
                .where(work_product_references.c.work_unit_id == binding.work_unit_id)
                .order_by(work_product_references.c.artifact_path)
            ).mappings()
        )
        event = self.session.execute(
            select(transition_history.c.reason)
            .where(
                transition_history.c.correlation_identity.in_(
                    (
                        str(binding.production_run_id),
                        str(binding.work_unit_id),
                        str(attempt["id"]) if attempt is not None else "",
                    )
                )
            )
            .order_by(transition_history.c.created_at.desc(), transition_history.c.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        return RuntimeFactSummary(
            attempt_id=None if attempt is None else attempt["id"],
            dispatch_id=None if dispatch is None else dispatch["id"],
            provider_outcome=None if report is None else report["outcome"],
            observation_id=None if observation is None else observation["id"],
            completion_id=None if completion is None else completion["id"],
            completion_outcome=None if completion is None else completion["outcome"],
            proposed_snapshot_id=None if proposed is None else proposed["id"],
            verification_obligations=tuple(
                item["obligation"] for item in verification_rows
            ),
            verification_results=tuple(item["result"] for item in verification_rows),
            admissibility_id=None if admissibility is None else admissibility["id"],
            admissibility_outcome=(
                None if admissibility is None else admissibility["outcome"]
            ),
            candidate_id=None if candidate is None else candidate["id"],
            candidate_fingerprint=(
                None if candidate is None else candidate["fingerprint"]
            ),
            authorization_id=None if authorization is None else authorization["id"],
            integration_effect_id=None if effect is None else effect["id"],
            integration_state=None if effect is None else effect["state"],
            runtime_commit_id=None if runtime_commit is None else runtime_commit["id"],
            artifact_paths=artifacts,
            completion_requires_production_result=(
                False
                if completion_contract is None
                else completion_contract.requires_observed_production_result
            ),
            latest_event=event,
            extra={
                "proposed_commit_identity": (
                    None if proposed is None else proposed["proposed_commit_identity"]
                )
            },
        )

    @staticmethod
    def _goal(row: Mapping[str, Any]) -> GoalRecord:
        return GoalRecord(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            condition=GoalCondition(row["condition"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _resource(row: Mapping[str, Any]) -> EngineeringResourceRecord:
        return EngineeringResourceRecord(
            id=row["id"],
            kind=EngineeringResourceKind(row["kind"]),
            repository_identity=row["repository_identity"],
            location_ref=row["location_ref"],
            authoritative_ref=row["authoritative_ref"],
            context_references=tuple(
                EngineeringContextReference.model_validate(item)
                for item in row["context_references"]
            ),
            is_default=row["is_default"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _work(self, row: Mapping[str, Any]) -> WorkRecord:
        scope = row["current_engineering_scope_id"]
        if scope is None:
            scope = self.session.execute(
                select(engineering_scopes.c.id)
                .where(engineering_scopes.c.work_id == row["id"])
                .order_by(
                    engineering_scopes.c.created_at.desc(),
                    engineering_scopes.c.id.desc(),
                )
                .limit(1)
            ).scalar_one_or_none()
        return WorkRecord(
            id=row["id"],
            goal_id=row["goal_id"],
            mode=WorkMode(row["work_mode"]),
            raw_user_requirement=row["raw_user_requirement"],
            refined_title=row["refined_title"],
            desired_outcome=row["desired_outcome"],
            constraints=tuple(row["constraints"]),
            tags=tuple(row["tags"]),
            condition=WorkCondition(row["condition"]),
            engineering_scope_id=scope,
            scope_summary=row["scope_summary"],
            production_objective=row["production_objective"],
            expected_artifact_path=row["expected_artifact_path"],
            artifact_operation=(
                None
                if row["artifact_operation"] is None
                else ArtifactTargetOperation(row["artifact_operation"])
            ),
            artifact_placement_rationale=row["artifact_placement_rationale"],
            artifact_target_confidence=(
                None
                if row["artifact_target_confidence"] is None
                else ArtifactTargetConfidence(row["artifact_target_confidence"])
            ),
            artifact_source_baseline_id=row["artifact_source_baseline_id"],
            artifact_source_revision=row["artifact_source_revision"],
            verification_expectation=row["verification_expectation"],
            code_change_proposal=(
                None
                if row["code_change_proposal"] is None
                else RepositoryChangeProposal.model_validate(
                    row["code_change_proposal"]
                )
            ),
            production_plan=(
                None
                if row["production_plan_proposal"] is None
                else ProductionPlanProposal.model_validate(
                    row["production_plan_proposal"]
                )
            ),
            current_work_reality_revision_id=row[
                "current_work_reality_revision_id"
            ],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _binding(row: Mapping[str, Any]) -> ResourceBindingRecord:
        return ResourceBindingRecord(
            id=row["id"],
            engineering_scope_id=row["engineering_scope_id"],
            resource_id=row["resource_id"],
            condition=ResourceBindingCondition(row["condition"]),
            created_at=row["created_at"],
        )

    def _one(self, table, condition) -> Mapping[str, Any] | None:
        return self.session.execute(select(table).where(condition)).mappings().first()
