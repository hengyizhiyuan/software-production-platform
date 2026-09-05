"""Persistence adapter for long-lived Steering Plan truth."""

from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from spg.domain.steering import (
    RealityReference,
    RealityReferenceKind,
    ResolvedRealityReference,
    SteeringAttentionReason,
    SteeringAuthorityAssessment,
    SteeringDecisionRecord,
    SteeringHistoryEventRecord,
    SteeringHistoryEventType,
    SteeringOutcome,
    SteeringPlanRecord,
    SteeringPlanRevisionCondition,
    SteeringPlanRevisionRecord,
    SteeringStepRecord,
    SteeringStepState,
    SteeringStepType,
)
from spg.infrastructure.persistence.product_schema import product_works
from spg.infrastructure.persistence.runtime_schema import (
    baseline_candidates,
    completion_evaluations,
    governance_records,
    human_authorizations,
    production_snapshots,
    recovery_assessments,
    repository_integration_effects,
    repository_observations,
    runtime_commits,
    verification_records,
)
from spg.infrastructure.persistence.steering_schema import (
    steering_decisions,
    steering_history_events,
    steering_plan_revisions,
    steering_plans,
    steering_steps,
)


_REALITY_TABLES = {
    RealityReferenceKind.WORK: product_works,
    RealityReferenceKind.GOVERNANCE_DECISION: governance_records,
    RealityReferenceKind.TRUSTED_BASELINE: production_snapshots,
    RealityReferenceKind.REPOSITORY_OBSERVATION: repository_observations,
    RealityReferenceKind.VERIFICATION: verification_records,
    RealityReferenceKind.COMPLETION: completion_evaluations,
    RealityReferenceKind.CANDIDATE: baseline_candidates,
    RealityReferenceKind.AUTHORIZATION: human_authorizations,
    RealityReferenceKind.INTEGRATION_EFFECT: repository_integration_effects,
    RealityReferenceKind.RUNTIME_COMMIT: runtime_commits,
    RealityReferenceKind.RECOVERY_ASSESSMENT: recovery_assessments,
}


class SteeringStore:
    """Read and append Steering facts without taking ownership of referenced Reality."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_plan(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(steering_plans).values(**values))

    def insert_revision(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(steering_plan_revisions).values(**values))

    def insert_step(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(steering_steps).values(**values))

    def insert_decision(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(steering_decisions).values(**values))

    def insert_history(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(steering_history_events).values(**values))

    def plan(self, plan_id: UUID) -> SteeringPlanRecord | None:
        row = self._one(steering_plans, steering_plans.c.id == plan_id)
        return None if row is None else self._plan(row)

    def plan_for_work(self, work_id: UUID) -> SteeringPlanRecord | None:
        row = self._one(steering_plans, steering_plans.c.work_id == work_id)
        return None if row is None else self._plan(row)

    def revision(self, revision_id: UUID) -> SteeringPlanRevisionRecord | None:
        row = self._one(
            steering_plan_revisions,
            steering_plan_revisions.c.id == revision_id,
        )
        return None if row is None else self._revision(row)

    def active_revision(self, plan_id: UUID) -> SteeringPlanRevisionRecord | None:
        row = self._one(
            steering_plan_revisions,
            (steering_plan_revisions.c.steering_plan_id == plan_id)
            & (
                steering_plan_revisions.c.condition
                == SteeringPlanRevisionCondition.ACTIVE.value
            ),
        )
        return None if row is None else self._revision(row)

    def revisions(self, plan_id: UUID) -> tuple[SteeringPlanRevisionRecord, ...]:
        rows = self.session.execute(
            select(steering_plan_revisions)
            .where(steering_plan_revisions.c.steering_plan_id == plan_id)
            .order_by(steering_plan_revisions.c.revision_number)
        ).mappings()
        return tuple(self._revision(row) for row in rows)

    def step(self, step_id: UUID) -> SteeringStepRecord | None:
        row = self._one(steering_steps, steering_steps.c.id == step_id)
        return None if row is None else self._step(row)

    def steps(self, revision_id: UUID) -> tuple[SteeringStepRecord, ...]:
        rows = self.session.execute(
            select(steering_steps)
            .where(steering_steps.c.steering_plan_revision_id == revision_id)
            .order_by(steering_steps.c.position, steering_steps.c.created_at, steering_steps.c.id)
        ).mappings()
        return tuple(self._step(row) for row in rows)

    def decision(self, decision_id: UUID) -> SteeringDecisionRecord | None:
        row = self._one(steering_decisions, steering_decisions.c.id == decision_id)
        return None if row is None else self._decision(row)

    def latest_decision(self, revision_id: UUID) -> SteeringDecisionRecord | None:
        row = self.session.execute(
            select(steering_decisions)
            .where(
                steering_decisions.c.steering_plan_revision_id == revision_id
            )
            .order_by(steering_decisions.c.created_at.desc(), steering_decisions.c.id.desc())
            .limit(1)
        ).mappings().first()
        return None if row is None else self._decision(row)

    def latest_decision_for_plan(self, plan_id: UUID) -> SteeringDecisionRecord | None:
        row = self.session.execute(
            select(steering_decisions)
            .join(
                steering_plan_revisions,
                steering_plan_revisions.c.id
                == steering_decisions.c.steering_plan_revision_id,
            )
            .where(steering_plan_revisions.c.steering_plan_id == plan_id)
            .order_by(steering_decisions.c.created_at.desc(), steering_decisions.c.id.desc())
            .limit(1)
        ).mappings().first()
        return None if row is None else self._decision(row)

    def history(self, plan_id: UUID) -> tuple[SteeringHistoryEventRecord, ...]:
        rows = self.session.execute(
            select(steering_history_events)
            .where(steering_history_events.c.steering_plan_id == plan_id)
            .order_by(steering_history_events.c.created_at, steering_history_events.c.id)
        ).mappings()
        return tuple(self._history(row) for row in rows)

    def set_step_state(self, step_id: UUID, state: SteeringStepState) -> None:
        result = self.session.execute(
            update(steering_steps)
            .where(steering_steps.c.id == step_id)
            .values(state=state.value)
        )
        if result.rowcount != 1:
            raise LookupError(f"Steering Step not found: {step_id}")

    def shift_active_steps_after(
        self,
        revision_id: UUID,
        position: int,
        delta: int,
    ) -> None:
        rows = self.session.execute(
            select(steering_steps.c.id, steering_steps.c.position)
            .where(
                (steering_steps.c.steering_plan_revision_id == revision_id)
                & (steering_steps.c.position > position)
                & (steering_steps.c.state != SteeringStepState.SUPERSEDED.value)
            )
            .order_by(steering_steps.c.position.desc())
        ).all()
        for step_id, current_position in rows:
            self.session.execute(
                update(steering_steps)
                .where(steering_steps.c.id == step_id)
                .values(position=current_position + delta)
            )

    def supersede_revision(self, revision_id: UUID) -> None:
        result = self.session.execute(
            update(steering_plan_revisions)
            .where(
                (steering_plan_revisions.c.id == revision_id)
                & (
                    steering_plan_revisions.c.condition
                    == SteeringPlanRevisionCondition.ACTIVE.value
                )
            )
            .values(condition=SteeringPlanRevisionCondition.SUPERSEDED.value)
        )
        if result.rowcount != 1:
            raise LookupError(f"Active Steering Plan Revision not found: {revision_id}")

    def reality_reference_exists(self, reference: RealityReference) -> bool:
        table = _REALITY_TABLES[reference.kind]
        return (
            self.session.execute(
                select(table.c.id).where(table.c.id == reference.identity)
            ).scalar_one_or_none()
            is not None
        )

    def resolve_reality_reference(
        self,
        reference: RealityReference,
    ) -> ResolvedRealityReference | None:
        """Resolve an external fact without copying its payload into Steering truth."""

        table = _REALITY_TABLES[reference.kind]
        row = self.session.execute(
            select(table).where(table.c.id == reference.identity)
        ).mappings().one_or_none()
        if row is None:
            return None
        canonical = json.dumps(
            self._canonical_value(dict(row)),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return ResolvedRealityReference(
            reference=reference,
            material_fingerprint=sha256(canonical.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _references(raw: list[dict[str, Any]]) -> tuple[RealityReference, ...]:
        return tuple(RealityReference.model_validate(item) for item in raw)

    @staticmethod
    def _plan(row: Mapping[str, Any]) -> SteeringPlanRecord:
        return SteeringPlanRecord(
            id=row["id"], work_id=row["work_id"], created_at=row["created_at"]
        )

    @classmethod
    def _revision(cls, row: Mapping[str, Any]) -> SteeringPlanRevisionRecord:
        return SteeringPlanRevisionRecord(
            id=row["id"],
            steering_plan_id=row["steering_plan_id"],
            work_id=row["work_id"],
            revision_number=row["revision_number"],
            condition=SteeringPlanRevisionCondition(row["condition"]),
            supersedes_revision_id=row["supersedes_revision_id"],
            rationale=row["rationale"],
            reality_refs=cls._references(row["reality_refs"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _step(row: Mapping[str, Any]) -> SteeringStepRecord:
        return SteeringStepRecord(
            id=row["id"],
            steering_plan_revision_id=row["steering_plan_revision_id"],
            type=SteeringStepType(row["type"]),
            objective=row["objective"],
            completion_condition=row["completion_condition"],
            position=row["position"],
            state=SteeringStepState(row["state"]),
            elaborates_step_id=row["elaborates_step_id"],
            created_at=row["created_at"],
        )

    @classmethod
    def _decision(cls, row: Mapping[str, Any]) -> SteeringDecisionRecord:
        return SteeringDecisionRecord(
            id=row["id"],
            steering_plan_revision_id=row["steering_plan_revision_id"],
            current_step_id=row["current_step_id"],
            next_step_type=SteeringStepType(row["next_step_type"]),
            objective=row["objective"],
            reason=row["reason"],
            reality_refs=cls._references(row["reality_refs"]),
            human_required=row["human_required"],
            completion_condition=row["completion_condition"],
            steering_outcome=SteeringOutcome(row["steering_outcome"]),
            basis_fingerprint=row["basis_fingerprint"],
            reasoning_provider_identity=row["reasoning_provider_identity"],
            attention_reason=(
                None
                if row["attention_reason"] is None
                else SteeringAttentionReason(row["attention_reason"])
            ),
            recommendation=row["recommendation"],
            alternatives=tuple(row["alternatives"]),
            trade_offs=tuple(row["trade_offs"]),
            expected_impact=row["expected_impact"],
            authority_assessment=(
                None
                if row["authority_assessment"] is None
                else SteeringAuthorityAssessment(row["authority_assessment"])
            ),
            proposed_engineering_scope_fingerprint=row[
                "proposed_engineering_scope_fingerprint"
            ],
            created_at=row["created_at"],
        )

    @classmethod
    def _history(cls, row: Mapping[str, Any]) -> SteeringHistoryEventRecord:
        return SteeringHistoryEventRecord(
            id=row["id"],
            steering_plan_id=row["steering_plan_id"],
            steering_plan_revision_id=row["steering_plan_revision_id"],
            event_type=SteeringHistoryEventType(row["event_type"]),
            from_revision_id=row["from_revision_id"],
            to_revision_id=row["to_revision_id"],
            from_step_id=row["from_step_id"],
            to_step_id=row["to_step_id"],
            steering_decision_id=row["steering_decision_id"],
            related_step_ids=tuple(UUID(item) for item in row["related_step_ids"]),
            rationale=row["rationale"],
            reality_refs=cls._references(row["reality_refs"]),
            created_at=row["created_at"],
        )

    def _one(self, table, condition) -> Mapping[str, Any] | None:
        return self.session.execute(select(table).where(condition)).mappings().first()

    @classmethod
    def _canonical_value(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): cls._canonical_value(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, (list, tuple)):
            return [cls._canonical_value(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, bytes):
            return value.hex()
        return value
