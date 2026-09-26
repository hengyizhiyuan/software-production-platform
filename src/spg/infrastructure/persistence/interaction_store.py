"""Persistence adapter for append-only Work Interaction truth."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from spg.domain.design_intent import DesignIntentFrame
from spg.domain.response_contract import ResponseContract
from spg.domain.interaction import (
    ConversationMessage,
    Interaction,
    InteractionActor,
    InteractionAssessment,
    InteractionCondition,
    InteractionInvariantViolation,
    InteractionRecord,
    InteractionTurn,
    InteractionTurnStatus,
    InterpretationMeaning,
    WorkEvolutionCandidateChange,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkAdmissionReadiness,
    WorkTransitionChoice,
    WorkTransitionRecord,
)
from spg.domain.engineering_semantics import (
    EngineeringSemanticFact,
    NeutralSemanticExtractionCandidate,
)
from spg.domain.wic_intelligence import ProgressiveSemanticStructure
from spg.domain.wic_response import (
    ResponseReconciliation,
    WicResponseEvent,
    WicResponseEventType,
    WicRuntimeMode,
)
from spg.infrastructure.persistence.product_schema import (
    interaction_assessments,
    interaction_messages,
    interaction_response_events,
    interaction_records,
    interaction_turns,
    interaction_work_transitions,
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
            select(product_interactions).where(
                product_interactions.c.condition == InteractionCondition.OPEN.value
            ).order_by(
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

    def record(self, record_id: UUID) -> InteractionRecord | None:
        row = self.session.execute(
            select(interaction_records).where(interaction_records.c.id == record_id)
        ).mappings().one_or_none()
        return None if row is None else self._record(row)

    def insert_turn(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(interaction_turns).values(**values))

    def turn(self, turn_id: UUID, *, for_update: bool = False) -> InteractionTurn | None:
        statement = select(interaction_turns).where(interaction_turns.c.id == turn_id)
        if for_update:
            statement = statement.with_for_update()
        row = self.session.execute(statement).mappings().one_or_none()
        return None if row is None else self._turn(row)

    def turns(self, interaction_id: UUID) -> tuple[InteractionTurn, ...]:
        rows = self.session.execute(
            select(interaction_turns)
            .where(interaction_turns.c.interaction_id == interaction_id)
            .order_by(interaction_turns.c.created_at, interaction_turns.c.id)
        ).mappings()
        return tuple(self._turn(row) for row in rows)

    def unfinished_turn(self, interaction_id: UUID) -> InteractionTurn | None:
        row = self.session.execute(
            select(interaction_turns)
            .where(
                (interaction_turns.c.interaction_id == interaction_id)
                & interaction_turns.c.status.in_(
                    (
                        InteractionTurnStatus.RECEIVED.value,
                        InteractionTurnStatus.PROCESSING.value,
                    )
                )
            )
            .order_by(interaction_turns.c.created_at)
            .limit(1)
        ).mappings().one_or_none()
        return None if row is None else self._turn(row)

    def pending_turns(self) -> tuple[InteractionTurn, ...]:
        rows = self.session.execute(
            select(interaction_turns)
            .where(
                interaction_turns.c.status.in_(
                    (
                        InteractionTurnStatus.RECEIVED.value,
                        InteractionTurnStatus.PROCESSING.value,
                    )
                )
            )
            .order_by(interaction_turns.c.created_at, interaction_turns.c.id)
        ).mappings()
        return tuple(self._turn(row) for row in rows)

    def update_turn(
        self,
        turn_id: UUID,
        *,
        status: InteractionTurnStatus,
        updated_at,
        assessment_id: UUID | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        refinement_observation: dict[str, Any] | None = None,
        started_at=None,
        completed_at=None,
    ) -> None:
        values: dict[str, Any] = {
            "status": status.value,
            "updated_at": updated_at,
            "assessment_id": assessment_id,
            "failure_code": failure_code,
            "failure_message": failure_message,
        }
        if refinement_observation is not None:
            values["refinement_observation"] = refinement_observation
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        result = self.session.execute(
            update(interaction_turns)
            .where(interaction_turns.c.id == turn_id)
            .values(**values)
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(f"Interaction Turn not found: {turn_id}")

    def reset_turn_for_retry(self, turn_id: UUID, *, updated_at) -> None:
        """Reset current Turn state while response events retain prior-attempt evidence."""

        result = self.session.execute(
            update(interaction_turns)
            .where(interaction_turns.c.id == turn_id)
            .values(
                status=InteractionTurnStatus.RECEIVED.value,
                assessment_id=None,
                failure_code=None,
                failure_message=None,
                started_at=None,
                completed_at=None,
                updated_at=updated_at,
            )
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(f"Interaction Turn not found: {turn_id}")

    def next_message_sequence(self, interaction_id: UUID) -> int:
        value = self.session.execute(
            select(func.max(interaction_messages.c.sequence)).where(
                interaction_messages.c.interaction_id == interaction_id
            )
        ).scalar_one()
        return int(value or 0) + 1

    def insert_message(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(interaction_messages).values(**values))

    def next_response_event_sequence(self, turn_id: UUID) -> int:
        value = self.session.execute(
            select(func.max(interaction_response_events.c.sequence)).where(
                interaction_response_events.c.turn_id == turn_id
            )
        ).scalar_one()
        return int(value or 0) + 1

    def insert_response_event(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(interaction_response_events).values(**values))

    def response_events(
        self, turn_id: UUID, *, after_sequence: int = 0
    ) -> tuple[WicResponseEvent, ...]:
        rows = self.session.execute(
            select(interaction_response_events)
            .where(
                (interaction_response_events.c.turn_id == turn_id)
                & (interaction_response_events.c.sequence > after_sequence)
            )
            .order_by(interaction_response_events.c.sequence)
        ).mappings()
        return tuple(self._response_event(row) for row in rows)

    def latest_response_contract(
        self, interaction_id: UUID, *, basis_fingerprint: str | None = None,
        completed_only: bool = False,
    ) -> ResponseContract | None:
        """Read advisory turn evidence; never project it into engineering truth."""
        statement = select(interaction_response_events.c.event_metadata).where(
            interaction_response_events.c.interaction_id == interaction_id,
            interaction_response_events.c.event_type == "RESPONSE_CONTRACT_READY",
        )
        if basis_fingerprint is not None:
            statement = statement.where(
                interaction_response_events.c.basis_fingerprint == basis_fingerprint
            )
        if completed_only:
            statement = statement.join(
                interaction_turns,
                interaction_turns.c.id == interaction_response_events.c.turn_id,
            ).where(interaction_turns.c.status == InteractionTurnStatus.COMPLETED.value)
        value = self.session.execute(statement.order_by(
            interaction_response_events.c.created_at.desc(),
            interaction_response_events.c.sequence.desc(),
        ).limit(1)).scalar_one_or_none()
        return None if value is None else ResponseContract.model_validate(value["response_contract"])

    def update_turn_messages_status(
        self,
        turn_id: UUID,
        *,
        status: InteractionTurnStatus,
        updated_at,
    ) -> None:
        self.session.execute(
            update(interaction_messages)
            .where(interaction_messages.c.turn_id == turn_id)
            .values(processing_status=status.value, updated_at=updated_at)
        )

    def messages(
        self, interaction_id: UUID, *, limit: int | None = None
    ) -> tuple[ConversationMessage, ...]:
        statement = select(interaction_messages).where(
            interaction_messages.c.interaction_id == interaction_id
        )
        if limit is None:
            statement = statement.order_by(
                interaction_messages.c.sequence, interaction_messages.c.id
            )
        else:
            if limit < 1:
                raise ValueError("Message limit must be positive")
            statement = statement.order_by(
                interaction_messages.c.sequence.desc(), interaction_messages.c.id.desc()
            ).limit(limit)
        rows = self.session.execute(statement).mappings()
        messages = tuple(self._message(row) for row in rows)
        return messages if limit is None else tuple(reversed(messages))

    def message_for_turn(
        self, turn_id: UUID, actor: InteractionActor
    ) -> ConversationMessage | None:
        row = self.session.execute(
            select(interaction_messages).where(
                (interaction_messages.c.turn_id == turn_id)
                & (interaction_messages.c.actor == actor.value)
            )
        ).mappings().one_or_none()
        return None if row is None else self._message(row)

    def select_design_schema(
        self,
        interaction_id: UUID,
        *,
        identity: str,
        version: str,
        rationale: str,
        updated_at,
    ) -> None:
        self.session.execute(
            update(product_interactions)
            .where(product_interactions.c.id == interaction_id)
            .values(
                selected_design_schema_identity=identity,
                selected_design_schema_version=version,
                design_schema_selection_rationale=rationale,
                updated_at=updated_at,
            )
        )

    def clear_design_schema(self, interaction_id: UUID, *, updated_at) -> None:
        self.session.execute(
            update(product_interactions)
            .where(product_interactions.c.id == interaction_id)
            .values(
                selected_design_schema_identity=None,
                selected_design_schema_version=None,
                design_schema_selection_rationale=None,
                updated_at=updated_at,
            )
        )

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

    def clear_current_work(
        self,
        interaction_id: UUID,
        *,
        expected_work_id: UUID,
        updated_by: str,
        updated_at,
    ) -> None:
        result = self.session.execute(
            update(product_interactions)
            .where(
                (product_interactions.c.id == interaction_id)
                & (product_interactions.c.current_work_id == expected_work_id)
            )
            .values(
                current_work_id=None,
                updated_by=updated_by,
                updated_at=updated_at,
            )
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(
                "Interaction Work focus changed before transition admission"
            )

    def replace_current_work(
        self,
        interaction_id: UUID,
        *,
        expected_work_id: UUID,
        new_work_id: UUID,
        updated_by: str,
        updated_at,
    ) -> None:
        result = self.session.execute(
            update(product_interactions)
            .where(
                (product_interactions.c.id == interaction_id)
                & (product_interactions.c.current_work_id == expected_work_id)
            )
            .values(
                current_work_id=new_work_id,
                updated_by=updated_by,
                updated_at=updated_at,
            )
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(
                "Interaction Work focus changed before PRE_WORK creation"
            )

    def archive_interaction(
        self,
        interaction_id: UUID,
        *,
        expected_work_id: UUID,
        updated_by: str,
        updated_at,
    ) -> None:
        result = self.session.execute(
            update(product_interactions)
            .where(
                (product_interactions.c.id == interaction_id)
                & (product_interactions.c.current_work_id == expected_work_id)
                & (product_interactions.c.condition == InteractionCondition.OPEN.value)
            )
            .values(
                condition=InteractionCondition.ARCHIVED.value,
                updated_by=updated_by,
                updated_at=updated_at,
            )
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(
                "Interaction is no longer an open PRE_WORK context"
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

    def insert_work_transition(self, values: Mapping[str, Any]) -> None:
        self.session.execute(insert(interaction_work_transitions).values(**values))

    def work_transition(
        self, transition_id: UUID, *, for_update: bool = False
    ) -> WorkTransitionRecord | None:
        statement = select(interaction_work_transitions).where(
            interaction_work_transitions.c.id == transition_id
        )
        if for_update:
            statement = statement.with_for_update()
        row = self.session.execute(statement).mappings().first()
        return None if row is None else self._work_transition(row)

    def transition_for_assessment(
        self, assessment_id: UUID
    ) -> WorkTransitionRecord | None:
        row = self.session.execute(
            select(interaction_work_transitions).where(
                interaction_work_transitions.c.source_assessment_id == assessment_id
            )
        ).mappings().first()
        return None if row is None else self._work_transition(row)

    def transitions(self, interaction_id: UUID) -> tuple[WorkTransitionRecord, ...]:
        rows = self.session.execute(
            select(interaction_work_transitions)
            .where(interaction_work_transitions.c.interaction_id == interaction_id)
            .order_by(
                interaction_work_transitions.c.created_at,
                interaction_work_transitions.c.id,
            )
        ).mappings()
        return tuple(self._work_transition(row) for row in rows)

    def latest_transition(
        self, interaction_id: UUID
    ) -> WorkTransitionRecord | None:
        row = self.session.execute(
            select(interaction_work_transitions)
            .where(interaction_work_transitions.c.interaction_id == interaction_id)
            .order_by(
                interaction_work_transitions.c.created_at.desc(),
                interaction_work_transitions.c.id.desc(),
            )
            .limit(1)
        ).mappings().first()
        return None if row is None else self._work_transition(row)

    def decide_transition(
        self,
        transition_id: UUID,
        *,
        choice: WorkTransitionChoice,
        decided_by: str,
        decision_rationale: str,
        decided_at,
    ) -> None:
        result = self.session.execute(
            update(interaction_work_transitions)
            .where(
                (interaction_work_transitions.c.id == transition_id)
                & (
                    interaction_work_transitions.c.choice
                    == WorkTransitionChoice.PENDING_HUMAN.value
                )
            )
            .values(
                choice=choice.value,
                decided_by=decided_by,
                decision_rationale=decision_rationale,
                decided_at=decided_at,
            )
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(
                "Work transition changed before Human decision admission"
            )

    def bind_transition_target(
        self, transition_id: UUID, *, target_work_id: UUID
    ) -> None:
        result = self.session.execute(
            update(interaction_work_transitions)
            .where(
                (interaction_work_transitions.c.id == transition_id)
                & (
                    interaction_work_transitions.c.choice
                    == WorkTransitionChoice.START_NEW_WORK.value
                )
                & interaction_work_transitions.c.target_work_id.is_(None)
            )
            .values(target_work_id=target_work_id)
        )
        if result.rowcount != 1:
            raise InteractionInvariantViolation(
                "New Work transition target changed before Work admission"
            )

    @staticmethod
    def _interaction(row: Mapping[str, Any]) -> Interaction:
        return Interaction(
            id=row["id"],
            condition=InteractionCondition(row["condition"]),
            current_work_id=row["current_work_id"],
            selected_design_schema_identity=row["selected_design_schema_identity"],
            selected_design_schema_version=row["selected_design_schema_version"],
            design_schema_selection_rationale=row["design_schema_selection_rationale"],
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
            design_intent_frame=(
                None
                if row["design_intent_frame"] is None
                else DesignIntentFrame.model_validate(row["design_intent_frame"])
            ),
            candidate_context=tuple(row["candidate_context"]),
            candidate_constraints=tuple(row["candidate_constraints"]),
            current_requests=tuple(row["current_requests"]),
            unresolved_material_questions=tuple(row["unresolved_material_questions"]),
            neutral_semantic_extractions=tuple(
                NeutralSemanticExtractionCandidate.model_validate(item)
                for item in row["neutral_semantic_extractions"]
            ),
            engineering_semantic_facts=tuple(
                EngineeringSemanticFact.model_validate(item)
                for item in row["engineering_semantic_facts"]
            ),
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
            refinement_observation=row["refinement_observation"],
            natural_response=row["natural_response"],
            readiness=WorkAdmissionReadiness.model_validate(row["readiness"]),
            progressive_semantics=(
                None
                if row["progressive_semantics"] is None
                else ProgressiveSemanticStructure.model_validate(row["progressive_semantics"])
            ),
            provider_identity=row["provider_identity"],
            model_identity=row["model_identity"],
            schema_version=row["schema_version"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _turn(row: Mapping[str, Any]) -> InteractionTurn:
        return InteractionTurn(
            id=row["id"],
            interaction_id=row["interaction_id"],
            request_record_id=row["request_record_id"],
            assessment_id=row["assessment_id"],
            wic_mode=WicRuntimeMode(row["wic_mode"]),
            status=InteractionTurnStatus(row["status"]),
            failure_code=row["failure_code"],
            failure_message=row["failure_message"],
            refinement_observation=row["refinement_observation"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _message(row: Mapping[str, Any]) -> ConversationMessage:
        return ConversationMessage(
            id=row["id"],
            interaction_id=row["interaction_id"],
            turn_id=row["turn_id"],
            sequence=row["sequence"],
            actor=InteractionActor(row["actor"]),
            content=row["content"],
            processing_status=InteractionTurnStatus(row["processing_status"]),
            interaction_record_id=row["interaction_record_id"],
            interpretation_assessment_id=row["interpretation_assessment_id"],
            design_result_references=tuple(row["design_result_references"]),
            governance_event_references=tuple(row["governance_event_references"]),
            supporting_references=tuple(row["supporting_references"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _response_event(row: Mapping[str, Any]) -> WicResponseEvent:
        return WicResponseEvent(
            id=row["id"],
            interaction_id=row["interaction_id"],
            turn_id=row["turn_id"],
            response_id=row["response_id"],
            sequence=row["sequence"],
            event_type=WicResponseEventType(row["event_type"]),
            content=row["content"],
            basis_fingerprint=row["basis_fingerprint"],
            reconciliation=(
                None
                if row["reconciliation"] is None
                else ResponseReconciliation(row["reconciliation"])
            ),
            metadata=dict(row["event_metadata"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _work_transition(row: Mapping[str, Any]) -> WorkTransitionRecord:
        return WorkTransitionRecord(
            id=row["id"],
            interaction_id=row["interaction_id"],
            source_record_id=row["source_record_id"],
            source_assessment_id=row["source_assessment_id"],
            originating_work_id=row["originating_work_id"],
            target_work_id=row["target_work_id"],
            reason=row["reason"],
            focus_classification=WorkFocusClassification(
                row["focus_classification"]
            ),
            impact_disposition=WorkImpactDisposition(row["impact_disposition"]),
            choice=WorkTransitionChoice(row["choice"]),
            decided_by=row["decided_by"],
            decision_rationale=row["decision_rationale"],
            decided_at=row["decided_at"],
            created_at=row["created_at"],
        )
