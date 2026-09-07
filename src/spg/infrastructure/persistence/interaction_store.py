"""Persistence adapter for append-only Work Interaction truth."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from spg.domain.interaction import (
    Interaction,
    InteractionActor,
    InteractionAssessment,
    InteractionCondition,
    InteractionInvariantViolation,
    InteractionRecord,
    InterpretationMeaning,
    WorkEvolutionCandidateChange,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkAdmissionReadiness,
)
from spg.infrastructure.persistence.product_schema import (
    interaction_assessments,
    interaction_records,
    product_interactions,
)


class InteractionStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_interaction(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(product_interactions).values(**values))

    def interaction(self, interaction_id: UUID, *, for_update: bool = False) -> Interaction | None:
        statement = select(product_interactions).where(
            product_interactions.c.id == interaction_id
        )
        if for_update:
            statement = statement.with_for_update()
        row = self.session.execute(statement).mappings().first()
        return None if row is None else self._interaction(row)

    def list_interactions(self) -> tuple[Interaction, ...]:
        rows = self.session.execute(
            select(product_interactions).order_by(
                product_interactions.c.updated_at.desc(),
                product_interactions.c.id,
            )
        ).mappings()
        return tuple(self._interaction(row) for row in rows)

    def interaction_for_work(self, work_id: UUID) -> Interaction | None:
        row = self.session.execute(
            select(product_interactions)
            .where(product_interactions.c.current_work_id == work_id)
            .order_by(product_interactions.c.updated_at.desc())
            .limit(1)
        ).mappings().first()
        return None if row is None else self._interaction(row)

    def next_sequence(self, interaction_id: UUID) -> int:
        value = self.session.execute(
            select(func.max(interaction_records.c.sequence)).where(
                interaction_records.c.interaction_id == interaction_id
            )
        ).scalar_one()
        return int(value or 0) + 1

    def insert_record(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(interaction_records).values(**values))

    def touch_interaction(self, interaction_id: UUID, *, updated_by: str, updated_at) -> None:
        self.session.execute(
            update(product_interactions)
            .where(product_interactions.c.id == interaction_id)
            .values(updated_by=updated_by, updated_at=updated_at)
        )

    def set_current_work(
        self,
        interaction_id: UUID,
        *,
        work_id: UUID,
        updated_by: str,
        updated_at,
    ) -> None:
        result = self.session.execute(
            update(product_interactions)
            .where(
                (product_interactions.c.id == interaction_id)
                & (
                    product_interactions.c.current_work_id.is_(None)
                    | (product_interactions.c.current_work_id == work_id)
                )
            )
            .values(
                current_work_id=work_id,
                updated_by=updated_by,
                updated_at=updated_at,
            )
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(
                "Interaction focus changed before governed Work admission"
            )

    def records(self, interaction_id: UUID) -> tuple[InteractionRecord, ...]:
        rows = self.session.execute(
            select(interaction_records)
            .where(interaction_records.c.interaction_id == interaction_id)
            .order_by(interaction_records.c.sequence, interaction_records.c.id)
        ).mappings()
        return tuple(self._record(row) for row in rows)

    def insert_assessment(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(interaction_assessments).values(**values))

    def assessment_for_basis(
        self, interaction_id: UUID, basis_fingerprint: str
    ) -> InteractionAssessment | None:
        row = self.session.execute(
            select(interaction_assessments).where(
                (interaction_assessments.c.interaction_id == interaction_id)
                & (interaction_assessments.c.basis_fingerprint == basis_fingerprint)
            )
        ).mappings().first()
        return None if row is None else self._assessment(row)

    def latest_assessment(self, interaction_id: UUID) -> InteractionAssessment | None:
        row = self.session.execute(
            select(interaction_assessments)
            .where(interaction_assessments.c.interaction_id == interaction_id)
            .order_by(
                interaction_assessments.c.basis_last_sequence.desc(),
                interaction_assessments.c.created_at.desc(),
                interaction_assessments.c.id,
            )
            .limit(1)
        ).mappings().first()
        return None if row is None else self._assessment(row)

    def assessment(self, assessment_id: UUID) -> InteractionAssessment | None:
        row = self.session.execute(
            select(interaction_assessments).where(
                interaction_assessments.c.id == assessment_id
            )
        ).mappings().first()
        return None if row is None else self._assessment(row)

    def assessments(self, interaction_id: UUID) -> tuple[InteractionAssessment, ...]:
        rows = self.session.execute(
            select(interaction_assessments)
            .where(interaction_assessments.c.interaction_id == interaction_id)
            .order_by(
                interaction_assessments.c.basis_last_sequence,
                interaction_assessments.c.created_at,
                interaction_assessments.c.id,
            )
        ).mappings()
        return tuple(self._assessment(row) for row in rows)

    @staticmethod
    def _interaction(row: Mapping[str, Any]) -> Interaction:
        return Interaction(
            id=row["id"],
            condition=InteractionCondition(row["condition"]),
            current_work_id=row["current_work_id"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _record(row: Mapping[str, Any]) -> InteractionRecord:
        return InteractionRecord(
            id=row["id"],
            interaction_id=row["interaction_id"],
            sequence=row["sequence"],
            actor=InteractionActor(row["actor"]),
            source=row["source"],
            content=row["content"],
            content_fingerprint=row["content_fingerprint"],
            work_focus_id=row["work_focus_id"],
            supporting_references=tuple(row["supporting_references"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _assessment(row: Mapping[str, Any]) -> InteractionAssessment:
        return InteractionAssessment(
            id=row["id"],
            interaction_id=row["interaction_id"],
            basis_fingerprint=row["basis_fingerprint"],
            basis_last_sequence=row["basis_last_sequence"],
            interpreted_motive=row["interpreted_motive"],
            desired_outcome=row["desired_outcome"],
            candidate_context=tuple(row["candidate_context"]),
            candidate_constraints=tuple(row["candidate_constraints"]),
            current_requests=tuple(row["current_requests"]),
            unresolved_material_questions=tuple(row["unresolved_material_questions"]),
            meanings=tuple(
                InterpretationMeaning.model_validate(item) for item in row["meanings"]
            ),
            focus_classification=(
                None
                if row["focus_classification"] is None
                else WorkFocusClassification(row["focus_classification"])
            ),
            impact_disposition=(
                None
                if row["impact_disposition"] is None
                else WorkImpactDisposition(row["impact_disposition"])
            ),
            candidate_change=(
                None
                if row["candidate_change"] is None
                else WorkEvolutionCandidateChange.model_validate(
                    row["candidate_change"]
                )
            ),
            basis_work_revision_id=row["basis_work_revision_id"],
            basis_steering_plan_revision_id=row[
                "basis_steering_plan_revision_id"
            ],
            basis_steering_step_id=row["basis_steering_step_id"],
            basis_active_runtime_binding_id=row[
                "basis_active_runtime_binding_id"
            ],
            supporting_references=tuple(row["supporting_references"]),
            natural_response=row["natural_response"],
            readiness=WorkAdmissionReadiness.model_validate(row["readiness"]),
            provider_identity=row["provider_identity"],
            model_identity=row["model_identity"],
            schema_version=row["schema_version"],
            created_at=row["created_at"],
        )
