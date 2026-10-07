"""Persistence adapter for product-owned Goal, Work, and Engineering Scope facts."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from spg.infrastructure.persistence.projection_reads import rows_for, first_for
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
from spg.domain.engineering_semantics import EngineeringSemanticFact
from spg.domain.interaction import WorkRealityRevision
from spg.domain.planning import ProductionPlanProposal
from spg.domain.refinement import RepositoryChangeProposal
from spg.infrastructure.persistence.product_schema import (
    engineering_resource_bindings,
    engineering_resources,
    engineering_scopes,
    product_goals,
    product_works,
    work_reality_revisions,
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


def projection_read(fn):
    """Memoize repeated canonical reads only inside an explicit read projection.

    Never enabled in command stores; lifetime is one read-only UoW. No TTL or
    cross-request owner truth cache is introduced.
    """
    from functools import wraps
    @wraps(fn)
    def call(self, *args, **kwargs):
        if not self._projection_reads:
            return fn(self, *args, **kwargs)
        key = (fn.__name__, repr(args), repr(sorted(kwargs.items())))
        if key not in self._read_results:
            self._read_results[key] = fn(self, *args, **kwargs)
        return self._read_results[key]
    return call


class ProductStore:
    """Own product facts and read Runtime facts without changing their authority."""

    def __init__(self, session: Session, *, projection_reads=False) -> None:
        self.session = session
        self._projection_reads = projection_reads
        self._read_results = {}
        self._summary_data = getattr(session, 'info', {}).get("watt_projection_rows")

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

    def insert_pre_work(self, work_id: UUID, timestamp: datetime,
                        *, product_id: UUID | None = None) -> None:
        """Form a provisional Work without admitting production authority."""
        self.insert_work({
            "id": work_id,
            "product_id": product_id,
            "goal_id": None,
            "work_mode": WorkMode.LONG_LIVED_STEERING.value,
            "raw_user_requirement": "",
            "refined_title": "New Work",
            "desired_outcome": None,
            "constraints": [],
            "tags": [],
            "condition": WorkCondition.PRE_WORK.value,
            "scope_summary": None,
            "production_objective": None,
            "expected_artifact_path": None,
            "artifact_operation": None,
            "artifact_placement_rationale": None,
            "artifact_target_confidence": None,
            "artifact_source_baseline_id": None,
            "artifact_source_revision": None,
            "verification_expectation": None,
            "code_change_proposal": None,
            "production_plan_proposal": None,
            "current_work_reality_revision_id": None,
            "current_engineering_scope_id": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        })

    def update_work(self, work_id: UUID, values: Mapping[str, Any]) -> None:
        result = self.session.execute(
            update(product_works).where(product_works.c.id == work_id).values(**values)
        )
        if result.rowcount != 1:
            raise LookupError(f"Work not found: {work_id}")

    def work(self, work_id: UUID, *, for_update: bool = False) -> WorkRecord | None:
        statement = select(product_works).where(product_works.c.id == work_id)
        if for_update:
            statement = statement.with_for_update()
        row = None if for_update else first_for(self.session, product_works, {'id':work_id})
        if row is None: row = self.session.execute(statement).mappings().first()
        return None if not row else self._work(row)

    def list_works(self, goal_id: UUID | None = None) -> tuple[WorkRecord, ...]:
        statement = select(product_works).where(
            product_works.c.condition != WorkCondition.DISCARDED.value
        )
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
                update(product_works)
                .where(product_works.c.id == scope_values["work_id"])
                .values(current_engineering_scope_id=None)
            )
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
        self.session.execute(
            update(product_works)
            .where(product_works.c.id == scope_values["work_id"])
            .values(current_engineering_scope_id=scope_values["id"])
        )

    def insert_scope(
        self,
        *,
        scope_values: Mapping[str, Any],
        binding_values: tuple[Mapping[str, Any], ...],
    ) -> None:
        self.session.execute(insert(engineering_scopes).values(**scope_values))
        for values in binding_values:
            self.session.execute(insert(engineering_resource_bindings).values(**values))

    def insert_work_reality_revision(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(work_reality_revisions).values(**values))

    def work_reality_revision(
        self, revision_id: UUID
    ) -> WorkRealityRevision | None:
        row = first_for(self.session, work_reality_revisions, {'id':revision_id})
        if row is None: row = self._one(work_reality_revisions, work_reality_revisions.c.id == revision_id)
        return None if not row else self._work_reality_revision(row)

    def work_reality_revision_for_assessment(
        self, assessment_id: UUID
    ) -> WorkRealityRevision | None:
        row = first_for(self.session, work_reality_revisions, {'source_assessment_id':assessment_id})
        if row is None: row = self._one(work_reality_revisions, work_reality_revisions.c.source_assessment_id == assessment_id)
        return None if not row else self._work_reality_revision(row)

    def work_reality_revisions(
        self, work_id: UUID
    ) -> tuple[WorkRealityRevision, ...]:
        rows = self.session.execute(
            select(work_reality_revisions)
            .where(work_reality_revisions.c.work_id == work_id)
            .order_by(work_reality_revisions.c.revision_number)
        ).mappings()
        return tuple(self._work_reality_revision(row) for row in rows)

    def current_work_reality_revision(
        self, work_id: UUID
    ) -> WorkRealityRevision | None:
        row = first_for(self.session, product_works, {'id':work_id})
        revision_id = row.get('current_work_reality_revision_id') if row is not None else self.session.execute(select(product_works.c.current_work_reality_revision_id).where(product_works.c.id == work_id)).scalar_one_or_none()
        return None if revision_id is None else self.work_reality_revision(revision_id)

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

    @projection_read
    def scope_for_work(self, work_id: UUID) -> EngineeringScopeRecord | None:
        prefetched = first_for(self.session, product_works, {'id': work_id})
        current_scope_id = (prefetched.get('current_engineering_scope_id') if prefetched is not None else self.session.execute(
            select(product_works.c.current_engineering_scope_id).where(
                product_works.c.id == work_id
            )
        ).scalar_one_or_none())
        statement = select(engineering_scopes).where(
            engineering_scopes.c.work_id == work_id
        )
        if current_scope_id is not None:
            statement = statement.where(engineering_scopes.c.id == current_scope_id)
        filters = {'work_id': work_id}
        if current_scope_id is not None: filters['id'] = current_scope_id
        row = first_for(self.session, engineering_scopes, filters, order=('created_at','id'), descending=True)
        if row is None:
            row = self.session.execute(statement.order_by(engineering_scopes.c.created_at.desc(), engineering_scopes.c.id.desc()).limit(1)).mappings().first()
        if not row:
            return None
        bindings = rows_for(self.session, engineering_resource_bindings, {'engineering_scope_id':row['id']}, order=('created_at','id'))
        if bindings is None:
            bindings = self.session.execute(select(engineering_resource_bindings).where(engineering_resource_bindings.c.engineering_scope_id == row["id"]).order_by(engineering_resource_bindings.c.created_at, engineering_resource_bindings.c.id)).mappings()
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

    def scope(self, scope_id: UUID) -> EngineeringScopeRecord | None:
        row = self.session.execute(
            select(engineering_scopes).where(engineering_scopes.c.id == scope_id)
        ).mappings().first()
        if row is None:
            return None
        bindings = self.session.execute(
            select(engineering_resource_bindings)
            .where(engineering_resource_bindings.c.engineering_scope_id == scope_id)
            .order_by(
                engineering_resource_bindings.c.created_at,
                engineering_resource_bindings.c.id,
            )
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

    def resource_for_work(self, work_id: UUID):
        scope = self.scope_for_work(work_id)
        if scope is None or not scope.bindings:
            return None
        revision = self.current_work_reality_revision(work_id)
        selected = None if revision is None else revision.engineering_resource_id
        if selected is None and len(scope.bindings) == 1:
            selected = scope.bindings[0].resource_id
        if selected is None or selected not in {item.resource_id for item in scope.bindings}:
            return None
        return self.resource(selected)

    def insert_runtime_binding(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(work_runtime_bindings).values(**values))

    def rebind_runtime_plan(self, binding_id: UUID, plan_id: UUID, root_pwu_id: UUID) -> None:
        result = self.session.execute(
            update(work_runtime_bindings)
            .where(work_runtime_bindings.c.id == binding_id)
            .values(plan_revision_id=plan_id, work_unit_id=root_pwu_id)
        )
        if result.rowcount != 1:
            raise LookupError(f"Production cycle binding not found: {binding_id}")

    @projection_read
    def runtime_binding(self, work_id: UUID) -> WorkRuntimeBindingRecord | None:
        row = first_for(self.session, work_runtime_bindings, {'work_id': work_id}, order=('cycle_number','created_at'), descending=True)
        if row is None:
            row = self.session.execute(select(work_runtime_bindings).where(work_runtime_bindings.c.work_id == work_id).order_by(work_runtime_bindings.c.cycle_number.desc(),work_runtime_bindings.c.created_at.desc()).limit(1)).mappings().first()
        return None if not row else self._runtime_binding(row)

    @projection_read
    def runtime_bindings(self, work_id: UUID) -> tuple[WorkRuntimeBindingRecord, ...]:
        rows = rows_for(self.session, work_runtime_bindings, {'work_id':work_id}, order=('cycle_number','created_at'))
        if rows is None:
            rows = self.session.execute(select(work_runtime_bindings).where(work_runtime_bindings.c.work_id == work_id).order_by(work_runtime_bindings.c.cycle_number,work_runtime_bindings.c.created_at)).mappings()
        return tuple(self._runtime_binding(row) for row in rows)

    def runtime_binding_for_step(
        self,
        steering_step_id: UUID,
    ) -> WorkRuntimeBindingRecord | None:
        row = first_for(self.session, work_runtime_bindings, {'steering_step_id':steering_step_id})
        if row is None:
            row = self._one(work_runtime_bindings, work_runtime_bindings.c.steering_step_id == steering_step_id)
        return None if not row else self._runtime_binding(row)

    def runtime_binding_for_work_unit(
        self,
        work_unit_id: UUID,
    ) -> WorkRuntimeBindingRecord | None:
        row = self._one(
            work_runtime_bindings,
            work_runtime_bindings.c.work_unit_id == work_unit_id,
        )
        if row is None:
            # Multi-PWU cycles bind one Work to the Run, not one binding row per
            # executable sibling. Resolve sibling lineage through that Run.
            run_id = self.session.execute(select(production_work_units.c.production_run_id).where(
                production_work_units.c.id == work_unit_id,
            )).scalar_one_or_none()
            if run_id is not None:
                row = self._one(work_runtime_bindings,
                    work_runtime_bindings.c.production_run_id == run_id)
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

    def prepare_projection_summaries(self, work_ids):
        """Batch the exact runtime lineage needed by these read-only Works.

        The same RuntimeFactSummary mapping is used in command and projection
        paths. No Product condition substitutes for runtime/verification truth.
        """
        if not self._projection_reads:
            raise ValueError("runtime prefetch requires a read-only projection store")
        data = {}
        def load(table, column, values):
            data[table.name] = ([] if not values else list(self.session.execute(
                select(table).where(column.in_(values))).mappings()))
            return data[table.name]
        bindings = load(work_runtime_bindings, work_runtime_bindings.c.work_id, work_ids)
        run_ids = {r['production_run_id'] for r in bindings}
        units = load(production_work_units, production_work_units.c.production_run_id, run_ids)
        attempts = load(execution_attempts, execution_attempts.c.work_unit_id, {r['id'] for r in units})
        attempt_ids = {r['id'] for r in attempts}
        dispatches = load(execution_dispatches, execution_dispatches.c.attempt_id, attempt_ids)
        dispatch_ids = {r['id'] for r in dispatches}
        load(provider_execution_reports, provider_execution_reports.c.dispatch_id, dispatch_ids)
        load(repository_observations, repository_observations.c.dispatch_id, dispatch_ids)
        completions = load(completion_evaluations, completion_evaluations.c.attempt_id, attempt_ids)
        proposed = load(proposed_repository_snapshots, proposed_repository_snapshots.c.completion_evaluation_id,
            {r['id'] for r in completions})
        proposed_ids = {r['id'] for r in proposed}
        load(verification_records, verification_records.c.proposed_snapshot_id, proposed_ids)
        load(production_admissibility_records, production_admissibility_records.c.proposed_snapshot_id, proposed_ids)
        candidates = load(baseline_candidates, baseline_candidates.c.production_run_id, run_ids)
        candidate_ids = {r['id'] for r in candidates}
        load(human_authorizations, human_authorizations.c.candidate_id, candidate_ids)
        load(repository_integration_effects, repository_integration_effects.c.candidate_id, candidate_ids)
        load(runtime_commits, runtime_commits.c.candidate_id, candidate_ids)
        load(work_product_references, work_product_references.c.attempt_id, attempt_ids)
        load(transition_history, transition_history.c.correlation_identity,
            {str(x) for x in run_ids | attempt_ids | {r['id'] for r in units}} | {''})
        from spg.infrastructure.persistence.runtime_schema import production_runs, plan_revisions, production_snapshots
        from spg.infrastructure.persistence.steering_schema import steering_plans, steering_plan_revisions, steering_steps, steering_decisions, semantic_step_results
        from spg.infrastructure.persistence.native_execution_schema import executor_queue
        load(product_works, product_works.c.id, work_ids)
        scopes = load(engineering_scopes, engineering_scopes.c.work_id, work_ids)
        load(engineering_resource_bindings, engineering_resource_bindings.c.engineering_scope_id, {r['id'] for r in scopes})
        runs = load(production_runs, production_runs.c.id, run_ids)
        load(plan_revisions, plan_revisions.c.id, {r['plan_revision_id'] for r in bindings} | {r['current_plan_revision_id'] for r in runs if r['current_plan_revision_id']})
        snapshot_ids = {r['source_baseline_id'] for r in units if r['source_baseline_id']} | {r['verified_output_baseline_id'] for r in units if r['verified_output_baseline_id']}
        snapshot_ids |= {r['source_baseline_id'] for r in runs} | {r['integrated_baseline_id'] for r in runs if r['integrated_baseline_id']}
        load(production_snapshots, production_snapshots.c.id, snapshot_ids)
        load(executor_queue, executor_queue.c.attempt_id, attempt_ids)
        plans = load(steering_plans, steering_plans.c.work_id, work_ids)
        revisions = load(steering_plan_revisions, steering_plan_revisions.c.steering_plan_id, {r['id'] for r in plans})
        steps = load(steering_steps, steering_steps.c.steering_plan_revision_id, {r['id'] for r in revisions})
        load(steering_decisions, steering_decisions.c.steering_plan_revision_id, {r['id'] for r in revisions})
        load(semantic_step_results, semantic_step_results.c.step_id, {r['id'] for r in steps})
        from spg.infrastructure.persistence.product_schema import product_interactions, interaction_assessments
        from spg.infrastructure.persistence.runtime_schema import governance_records
        interactions = load(product_interactions, product_interactions.c.current_work_id, work_ids)
        assessments = load(interaction_assessments, interaction_assessments.c.interaction_id, {r['id'] for r in interactions})
        load(work_reality_revisions, work_reality_revisions.c.work_id, work_ids)
        load(governance_records, governance_records.c.subject_identity, {str(w) for w in work_ids} |
            {'interaction-assessment:'+str(a['id']) for a in assessments})
        self._summary_data = data
        self.session.info['watt_projection_rows'] = data

    def _summary_rows(self, table, column, values, *, order=(), descending=False):
        if self._summary_data is None:
            query = select(table).where(column.in_(values))
            if order:
                query = query.order_by(*[getattr(table.c, key).desc() if descending else getattr(table.c, key) for key in order])
            return list(self.session.execute(query).mappings())
        rows = [r for r in self._summary_data[table.name] if r[column.name] in values]
        return sorted(rows, key=lambda r: tuple((r[k] is None, r[k] if r[k] is not None else 0) for k in order), reverse=descending) if order else rows

    def _summary_first(self, table, column, value, *, order=(), descending=False):
        rows = self._summary_rows(table, column, (value,), order=order, descending=descending)
        return rows[0] if rows else None

    @projection_read
    def runtime_summary(self, binding: WorkRuntimeBindingRecord) -> RuntimeFactSummary:
        unit = self._summary_first(production_work_units, production_work_units.c.id, binding.work_unit_id)
        raw_completion_contract = None if unit is None else unit['completion_contract']
        completion_contract = None if raw_completion_contract is None else CompletionContract.model_validate(raw_completion_contract)
        attempt = self._summary_first(execution_attempts, execution_attempts.c.work_unit_id, binding.work_unit_id,
            order=('generation',), descending=True)
        dispatch = None if attempt is None else self._summary_first(execution_dispatches, execution_dispatches.c.attempt_id, attempt['id'])
        report = None if dispatch is None else self._summary_first(provider_execution_reports, provider_execution_reports.c.dispatch_id, dispatch['id'])
        observation = None if dispatch is None else self._summary_first(repository_observations, repository_observations.c.dispatch_id, dispatch['id'])
        completion = None if attempt is None else self._summary_first(completion_evaluations, completion_evaluations.c.attempt_id, attempt['id'], order=('created_at',), descending=True)
        proposed = None if completion is None else self._summary_first(proposed_repository_snapshots, proposed_repository_snapshots.c.completion_evaluation_id, completion['id'])
        verification_rows = () if proposed is None else self._summary_rows(verification_records, verification_records.c.proposed_snapshot_id, (proposed['id'],), order=('created_at','id'))
        admissibility = None if proposed is None else self._summary_first(production_admissibility_records, production_admissibility_records.c.proposed_snapshot_id, proposed['id'])
        candidate = self._summary_first(baseline_candidates, baseline_candidates.c.production_run_id, binding.production_run_id, order=('sealed_at',), descending=True)
        authorization = None if candidate is None else self._summary_first(human_authorizations, human_authorizations.c.candidate_id, candidate['id'], order=('authorized_at',), descending=True)
        effect = None if candidate is None else self._summary_first(repository_integration_effects, repository_integration_effects.c.candidate_id, candidate['id'], order=('prepared_at',), descending=True)
        runtime_commit = None if candidate is None else self._summary_first(runtime_commits, runtime_commits.c.candidate_id, candidate['id'], order=('committed_at',), descending=True)
        artifacts = () if attempt is None else tuple(r['artifact_path'] for r in self._summary_rows(work_product_references, work_product_references.c.attempt_id, (attempt['id'],), order=('artifact_path',)))
        events = self._summary_rows(transition_history, transition_history.c.correlation_identity,
            (str(binding.production_run_id),str(binding.work_unit_id),str(attempt['id']) if attempt else ''), order=('created_at','id'), descending=True)
        event = None if not events else events[0]['reason']
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
                ),
                "task_contract_mode": (
                    None
                    if completion_contract is None
                    or completion_contract.task_contract is None
                    else completion_contract.task_contract.task_mode.value
                ),
                "artifact_contract_path": (
                    None
                    if completion_contract is None
                    or completion_contract.artifact_contract is None
                    else completion_contract.artifact_contract.artifact_path
                ),
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

    @staticmethod
    def _work_reality_revision(row: Mapping[str, Any]) -> WorkRealityRevision:
        return WorkRealityRevision(
            id=row["id"],
            work_id=row["work_id"],
            revision_number=row["revision_number"],
            previous_revision_id=row["previous_revision_id"],
            basis_fingerprint=row["basis_fingerprint"],
            revision_fingerprint=row["revision_fingerprint"],
            source_interaction_id=row["source_interaction_id"],
            source_assessment_id=row["source_assessment_id"],
            source_kind=row.get("source_kind", "INTERACTION_ASSESSMENT"),
            source_record_ids=tuple(UUID(item) for item in row["source_record_ids"]),
            motive=row["motive"],
            desired_outcome=row["desired_outcome"],
            context_facts=tuple(row["context_facts"]),
            constraints=tuple(row["constraints"]),
            requests=tuple(row["requests"]),
            engineering_semantic_facts=tuple(
                EngineeringSemanticFact.model_validate(item)
                for item in row["engineering_semantic_facts"]
            ),
            engineering_scope_id=row["engineering_scope_id"],
            engineering_resource_id=row["engineering_resource_id"],
            scope_basis_fingerprint=row["scope_basis_fingerprint"],
            repository_identity=row["repository_identity"],
            repository_ref=row["repository_ref"],
            source_baseline_id=row["source_baseline_id"],
            source_revision=row["source_revision"],
            governance_record_id=row["governance_record_id"],
            supporting_references=tuple(row["supporting_references"]),
            change_set=tuple(row["change_set"]),
            rationale=row["rationale"],
            admitted_by=row["admitted_by"],
            schema_version=row["schema_version"],
            created_at=row["created_at"],
        )

    def _one(self, table, condition) -> Mapping[str, Any] | None:
        return self.session.execute(select(table).where(condition)).mappings().first()
