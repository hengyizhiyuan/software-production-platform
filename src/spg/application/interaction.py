"""Pre-Work Interaction application service and governed assessment admission."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
import hashlib
import json
from threading import RLock
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from spg.application.guided_design import (
    design_schema_by_identity,
    match_design_schema_text,
)

from spg.domain.interaction import (
    ActiveWorkInterpretationContext,
    Interaction,
    InteractionActor,
    InteractionAssessment,
    InteractionAssessmentCandidate,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionRecord,
    InteractionRecordNotFound,
    InteractionTurn,
    InteractionTurnStatus,
    InterpretationMeaningKind,
    SharedUnderstanding,
    WorkEvolutionCandidateChange,
    WorkFocusClassification,
    WorkImpactDisposition,
    WorkRevisionAdmissionStatus,
    WorkSatisfactionState,
    WorkTransitionChoice,
    WorkAdmissionReadiness,
    WorkAdmissionReadinessStatus,
    WorkInteractionCapability,
)
from spg.domain.product import ProductionCycleBindingCondition
from spg.domain.steering import RealityReferenceKind, SteeringOutcome, SteeringStepType
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.product_store import ProductStore
from spg.infrastructure.persistence.runtime_store import RuntimeStore
from spg.infrastructure.persistence.steering_store import SteeringStore


ASSESSMENT_SCHEMA_VERSION = "wic-assessment-v2"
READINESS_PROFILE = "LONG_LIVED_STEERING"
READINESS_PROFILE_VERSION = "v0"


def interaction_basis_fingerprint(
    interaction: Interaction,
    records: tuple[InteractionRecord, ...],
    active_work_context: ActiveWorkInterpretationContext | None = None,
) -> str:
    payload = {
        "interaction_id": str(interaction.id),
        "current_work_id": (
            None if interaction.current_work_id is None else str(interaction.current_work_id)
        ),
        "records": [
            {
                "id": str(record.id),
                "sequence": record.sequence,
                "actor": record.actor.value,
                "source": record.source,
                "content_fingerprint": record.content_fingerprint,
                "work_focus_id": (
                    None if record.work_focus_id is None else str(record.work_focus_id)
                ),
                "supporting_references": list(record.supporting_references),
            }
            for record in records
        ],
        "active_work_context": (
            None
            if active_work_context is None
            else active_work_context.model_dump(mode="json")
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class DeterministicWorkInteractionCapability:
    """Conservative deterministic test capability; not the Watt product Provider."""

    _IDLE = {"hi", "hello", "hey", "你好", "在吗", "谢谢", "thanks"}
    _CONTINUATION_MARKERS = (
        "also",
        "slightly",
        "improve",
        "再",
        "也",
        "稍微",
        "继续",
    )

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        human = [record for record in basis.records if record.actor is InteractionActor.HUMAN]
        latest = human[-1]
        active = basis.active_work_context
        if active is not None:
            value = latest.content.strip()
            normalized_latest = value.casefold()
            references = latest.supporting_references
            if any(
                marker in normalized_latest
                for marker in ("另一个需求", "另外一个需求", "unrelated", "new work")
            ):
                focus = WorkFocusClassification.UNRELATED_NEW_DEMAND
                impact = WorkImpactDisposition.NEW_WORK_RECOMMENDED
            elif any(
                marker in normalized_latest
                for marker in ("探索", "设想", "未来是否", "maybe", "what if")
            ):
                focus = WorkFocusClassification.RELEVANT_EXPLORATION
                impact = WorkImpactDisposition.NO_GOVERNED_CHANGE
            elif value.rstrip().endswith(("?", "？")) and not (
                active.satisfaction_state
                is WorkSatisfactionState.CURRENTLY_SATISFIED
                and any(
                    marker in normalized_latest
                    for marker in self._CONTINUATION_MARKERS
                )
            ):
                focus = WorkFocusClassification.SIDE_QUESTION
                impact = WorkImpactDisposition.NO_GOVERNED_CHANGE
            else:
                focus = WorkFocusClassification.ON_TOPIC
                impact = (
                    WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT
                    if (
                        active.active_production_binding_id is not None
                        or active.satisfaction_state
                        is WorkSatisfactionState.CURRENTLY_SATISFIED
                    )
                    else WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED
                )
            revision = active.work_revision
            contextual = (
                revision.context_facts
                if impact is WorkImpactDisposition.NO_GOVERNED_CHANGE
                else (*revision.context_facts, value)
            )
            return InteractionAssessmentCandidate(
                interpreted_motive=revision.motive,
                desired_outcome=revision.desired_outcome,
                candidate_context=contextual,
                candidate_constraints=revision.constraints,
                current_requests=revision.requests,
                focus_classification=focus,
                impact_disposition=impact,
                supporting_references=references,
                natural_response=(
                    "I kept the current Work focus and recorded this without changing governed Work."
                    if impact is WorkImpactDisposition.NO_GOVERNED_CHANGE
                    else "I assessed this against the current Work. Human governance is required before any Work revision."
                ),
                provider_identity="watt-native:deterministic-v1",
            )
        combined = "\n".join(record.content.strip() for record in human).strip()
        normalized = combined.lower().strip("。.!！?？ ")
        idle = normalized in self._IDLE or len(normalized) < 8
        constraints = tuple(
            fragment.strip(" 。.;；")
            for fragment in combined.replace("。", "\n").replace("；", "\n").splitlines()
            if any(marker in fragment.lower() for marker in ("不要", "不得", "必须", "do not", "must "))
        )
        if idle:
            return InteractionAssessmentCandidate(
                unresolved_material_questions=("What would you like Watt to help change?",),
                natural_response="Tell me what you would like to change or explore, and we can shape it together.",
                provider_identity="watt-native:deterministic-v0",
            )
        outcome_clear = len(combined) >= 28 and any(
            marker in combined.lower()
            for marker in ("希望", "需要", "改进", "实现", "want", "need", "improve", "build")
        )
        questions = () if outcome_clear else (
            "What observable outcome would show that this Motive has been satisfied?",
        )
        return InteractionAssessmentCandidate(
            interpreted_motive=combined,
            desired_outcome=combined if outcome_clear else None,
            candidate_constraints=constraints,
            current_requests=(latest.content.strip(),),
            unresolved_material_questions=questions,
            natural_response=(
                "I have enough to show a candidate Motive and outcome. Review the Shared Understanding before forming Work."
                if not questions
                else "I understand the direction, but need one material clarification before this is ready to form Work."
            ),
            provider_identity="watt-native:deterministic-v0",
        )


class UnavailableWorkInteractionCapability:
    """Fail truthfully when the sole MVP Watt Native Provider is not configured."""

    def interpret(
        self, _basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        raise InteractionInvariantViolation(
            "Watt Native interpretation Provider is not configured"
        )


class WorkInteractionService:
    def __init__(
        self,
        database: Database,
        *,
        capability: WorkInteractionCapability,
    ) -> None:
        self.database = database
        self.capability = capability
        self._turn_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="watt-interaction",
        )
        self._turn_futures: dict[UUID, Future[None]] = {}
        self._turn_lock = RLock()

    def create_interaction(self, *, human_identity: str) -> Interaction:
        identity = human_identity.strip()
        if not identity:
            raise InteractionInvariantViolation("Human identity is required")
        now = datetime.now(UTC)
        interaction_id = uuid4()
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            store.insert_interaction(
                {
                    "id": interaction_id,
                    "condition": InteractionCondition.OPEN.value,
                    "current_work_id": None,
                    "created_by": identity,
                    "updated_by": identity,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            uow.commit()
        return self.get_interaction(interaction_id)

    def list_interactions(self) -> tuple[SharedUnderstanding, ...]:
        with self.database.unit_of_work() as uow:
            interactions = InteractionStore(uow.session).list_interactions()
        return tuple(self.get_shared_understanding(item.id) for item in interactions)

    def get_interaction(self, interaction_id: UUID) -> Interaction:
        with self.database.unit_of_work() as uow:
            interaction = InteractionStore(uow.session).interaction(interaction_id)
        if interaction is None:
            raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
        return interaction

    def append_human_input(
        self,
        interaction_id: UUID,
        content: str,
        *,
        human_identity: str,
        supporting_references: tuple[str, ...] = (),
    ) -> InteractionRecord:
        value = content.strip()
        identity = human_identity.strip()
        if not value or not identity:
            raise InteractionInvariantViolation("Human input and identity are required")
        now = datetime.now(UTC)
        record_id = uuid4()
        content_fingerprint = hashlib.sha256(value.encode()).hexdigest()
        references = self._normalize_supporting_references(supporting_references)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            if interaction.condition is not InteractionCondition.OPEN:
                raise InteractionInvariantViolation("Archived Interaction cannot accept input")
            sequence = store.next_sequence(interaction_id)
            store.insert_record(
                {
                    "id": record_id,
                    "interaction_id": interaction_id,
                    "sequence": sequence,
                    "actor": InteractionActor.HUMAN.value,
                    "source": identity,
                    "content": value,
                    "content_fingerprint": content_fingerprint,
                    "work_focus_id": interaction.current_work_id,
                    "supporting_references": list(references),
                    "created_at": now,
                }
            )
            store.touch_interaction(
                interaction_id,
                updated_by=identity,
                updated_at=now,
            )
            uow.commit()
        return self.get_shared_understanding(interaction_id).records[-1]

    def append_and_assess(
        self,
        interaction_id: UUID,
        content: str,
        *,
        human_identity: str,
        supporting_references: tuple[str, ...] = (),
    ) -> SharedUnderstanding:
        # The Human record commits first. A failed Provider call therefore leaves an
        # honest, recoverable unassessed basis rather than losing communication.
        self.append_human_input(
            interaction_id,
            content,
            human_identity=human_identity,
            supporting_references=supporting_references,
        )
        self.assess_current(interaction_id)
        return self.get_shared_understanding(interaction_id)

    def submit_turn(
        self,
        interaction_id: UUID,
        content: str,
        *,
        human_identity: str,
        supporting_references: tuple[str, ...] = (),
    ) -> InteractionTurn:
        """Persist and acknowledge one Turn before Provider-backed processing."""

        value = content.strip()
        identity = human_identity.strip()
        if not value or not identity:
            raise InteractionInvariantViolation("Human input and identity are required")
        now = datetime.now(UTC)
        record_id = uuid4()
        turn_id = uuid4()
        references = self._normalize_supporting_references(supporting_references)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            if interaction.condition is not InteractionCondition.OPEN:
                raise InteractionInvariantViolation("Archived Interaction cannot accept input")
            if store.unfinished_turn(interaction_id) is not None:
                raise InteractionInvariantViolation(
                    "Interaction already has a Turn in progress"
                )
            store.insert_record(
                {
                    "id": record_id,
                    "interaction_id": interaction_id,
                    "sequence": store.next_sequence(interaction_id),
                    "actor": InteractionActor.HUMAN.value,
                    "source": identity,
                    "content": value,
                    "content_fingerprint": hashlib.sha256(value.encode()).hexdigest(),
                    "work_focus_id": interaction.current_work_id,
                    "supporting_references": list(references),
                    "created_at": now,
                }
            )
            store.insert_turn(
                {
                    "id": turn_id,
                    "interaction_id": interaction_id,
                    "request_record_id": record_id,
                    "assessment_id": None,
                    "status": InteractionTurnStatus.RECEIVED.value,
                    "failure_code": None,
                    "failure_message": None,
                    "created_at": now,
                    "started_at": None,
                    "completed_at": None,
                    "updated_at": now,
                }
            )
            store.insert_message(
                {
                    "id": uuid4(),
                    "interaction_id": interaction_id,
                    "turn_id": turn_id,
                    "sequence": store.next_message_sequence(interaction_id),
                    "actor": InteractionActor.HUMAN.value,
                    "content": value,
                    "processing_status": InteractionTurnStatus.RECEIVED.value,
                    "interaction_record_id": record_id,
                    "interpretation_assessment_id": None,
                    "design_result_references": [],
                    "governance_event_references": [],
                    "supporting_references": list(references),
                    "created_at": now,
                    "updated_at": now,
                }
            )
            store.touch_interaction(interaction_id, updated_by=identity, updated_at=now)
            uow.commit()
        turn = self.get_turn(turn_id)
        self.schedule_turn(turn_id)
        return turn

    def get_turn(self, turn_id: UUID) -> InteractionTurn:
        with self.database.unit_of_work() as uow:
            turn = InteractionStore(uow.session).turn(turn_id)
        if turn is None:
            raise InteractionRecordNotFound(f"Interaction Turn not found: {turn_id}")
        return turn

    def schedule_turn(self, turn_id: UUID) -> bool:
        with self._turn_lock:
            current = self._turn_futures.get(turn_id)
            if current is not None and not current.done():
                return False
            future = self._turn_executor.submit(self._process_turn, turn_id)
            self._turn_futures[turn_id] = future
            future.add_done_callback(lambda _future: self._forget_turn(turn_id))
        return True

    def resume_pending_turns(self) -> tuple[UUID, ...]:
        with self.database.unit_of_work() as uow:
            pending = InteractionStore(uow.session).pending_turns()
        return tuple(turn.id for turn in pending if self.schedule_turn(turn.id))

    def shutdown(self) -> None:
        self._turn_executor.shutdown(wait=True, cancel_futures=False)

    def _forget_turn(self, turn_id: UUID) -> None:
        with self._turn_lock:
            self._turn_futures.pop(turn_id, None)

    def _process_turn(self, turn_id: UUID) -> None:
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            turn = store.turn(turn_id, for_update=True)
            if turn is None or turn.status in {
                InteractionTurnStatus.COMPLETED,
                InteractionTurnStatus.FAILED,
            }:
                uow.rollback()
                return
            store.update_turn(
                turn_id,
                status=InteractionTurnStatus.PROCESSING,
                updated_at=now,
                started_at=turn.started_at or now,
            )
            store.update_turn_messages_status(
                turn_id,
                status=InteractionTurnStatus.PROCESSING,
                updated_at=now,
            )
            uow.commit()
        try:
            assessment = self.assess_current(turn.interaction_id)
            completed_at = datetime.now(UTC)
            with self.database.unit_of_work() as uow:
                store = InteractionStore(uow.session)
                current = store.turn(turn_id, for_update=True)
                if current is None:
                    raise InteractionRecordNotFound(
                        f"Interaction Turn not found: {turn_id}"
                    )
                if store.message_for_turn(turn_id, InteractionActor.WATT) is None:
                    interaction = store.interaction(turn.interaction_id)
                    design_refs = (
                        ()
                        if interaction is None
                        or interaction.selected_design_schema_identity is None
                        else (
                            "DESIGN_SCHEMA:"
                            f"{interaction.selected_design_schema_identity}@"
                            f"{interaction.selected_design_schema_version}",
                        )
                    )
                    response_content = assessment.natural_response
                    if (
                        interaction is not None
                        and interaction.current_work_id is None
                        and interaction.selected_design_schema_identity is not None
                    ):
                        schema = design_schema_by_identity(
                            interaction.selected_design_schema_identity,
                            interaction.selected_design_schema_version,
                        )
                        focus = schema.issues[0]
                        response_content = (
                            f"{assessment.natural_response}\n\n"
                            f"Design approach: {schema.title} v{schema.version}. "
                            f"{interaction.design_schema_selection_rationale} "
                            f"Current stage: {focus.title}. Next, {focus.objective.lower()} "
                            f"Why now: {focus.why_it_matters}"
                        )
                    store.insert_message(
                        {
                            "id": uuid4(),
                            "interaction_id": turn.interaction_id,
                            "turn_id": turn_id,
                            "sequence": store.next_message_sequence(turn.interaction_id),
                            "actor": InteractionActor.WATT.value,
                            "content": response_content,
                            "processing_status": InteractionTurnStatus.COMPLETED.value,
                            "interaction_record_id": None,
                            "interpretation_assessment_id": assessment.id,
                            "design_result_references": list(design_refs),
                            "governance_event_references": list(
                                assessment.supporting_references
                            ),
                            "supporting_references": list(
                                assessment.supporting_references
                            ),
                            "created_at": completed_at,
                            "updated_at": completed_at,
                        }
                    )
                store.update_turn(
                    turn_id,
                    status=InteractionTurnStatus.COMPLETED,
                    updated_at=completed_at,
                    assessment_id=assessment.id,
                    completed_at=completed_at,
                )
                store.update_turn_messages_status(
                    turn_id,
                    status=InteractionTurnStatus.COMPLETED,
                    updated_at=completed_at,
                )
                uow.commit()
        except Exception as error:  # persisted failure is the product-facing truth
            failed_at = datetime.now(UTC)
            with self.database.unit_of_work() as uow:
                store = InteractionStore(uow.session)
                store.update_turn(
                    turn_id,
                    status=InteractionTurnStatus.FAILED,
                    updated_at=failed_at,
                    failure_code=type(error).__name__,
                    failure_message=str(error),
                    completed_at=failed_at,
                )
                store.update_turn_messages_status(
                    turn_id,
                    status=InteractionTurnStatus.FAILED,
                    updated_at=failed_at,
                )
                uow.commit()

    def assess_current(self, interaction_id: UUID) -> InteractionAssessment:
        basis = self._basis(interaction_id)
        with self.database.unit_of_work() as uow:
            existing = InteractionStore(uow.session).assessment_for_basis(
                interaction_id, basis.basis_fingerprint
            )
        if existing is not None:
            return existing
        candidate = self.capability.interpret(basis)
        return self.admit_candidate(
            interaction_id,
            basis_fingerprint=basis.basis_fingerprint,
            candidate=candidate,
        )

    def admit_candidate(
        self,
        interaction_id: UUID,
        *,
        basis_fingerprint: str,
        candidate: InteractionAssessmentCandidate,
    ) -> InteractionAssessment:
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            records = store.records(interaction_id)
            if not records:
                raise InteractionInvariantViolation("Interaction has no assessment basis")
            active_context = self._active_work_context(uow.session, interaction)
            current_basis = interaction_basis_fingerprint(
                interaction,
                records,
                active_context,
            )
            if current_basis != basis_fingerprint:
                raise InteractionInvariantViolation(
                    "Interaction assessment basis is stale and cannot become current"
                )
            existing = store.assessment_for_basis(interaction_id, current_basis)
            if existing is not None:
                return existing
            record_ids = {record.id for record in records}
            if any(
                source_id not in record_ids
                for meaning in candidate.meanings
                for source_id in meaning.source_record_ids
            ):
                raise InteractionInvariantViolation(
                    "Interpretation meaning references a record outside its basis"
                )
            focus, impact, candidate_change = self._normalize_active_candidate(
                candidate,
                active_context,
            )
            record_references = self._normalize_supporting_references(
                tuple(
                    reference
                    for record in records
                    for reference in record.supporting_references
                )
            )
            candidate_references = self._normalize_supporting_references(
                candidate.supporting_references
            )
            if not set(candidate_references).issubset(record_references):
                raise InteractionInvariantViolation(
                    "Interpretation cannot invent supporting Reality references"
                )
            supporting_references = tuple(
                dict.fromkeys((*record_references, *candidate_references))
            )
            readiness = self._evaluate_readiness(candidate, current_basis)
            if interaction.current_work_id is None:
                schema, selection_rationale = match_design_schema_text(
                    candidate.interpreted_motive or records[-1].content
                )
                store.select_design_schema(
                    interaction_id,
                    identity=schema.identity,
                    version=schema.version,
                    rationale=selection_rationale,
                    updated_at=now,
                )
            assessment_id = uuid4()
            store.insert_assessment(
                {
                    "id": assessment_id,
                    "interaction_id": interaction_id,
                    "basis_fingerprint": current_basis,
                    "basis_last_sequence": records[-1].sequence,
                    "interpreted_motive": candidate.interpreted_motive,
                    "desired_outcome": candidate.desired_outcome,
                    "candidate_context": list(candidate.candidate_context),
                    "candidate_constraints": list(candidate.candidate_constraints),
                    "current_requests": list(candidate.current_requests),
                    "unresolved_material_questions": list(
                        candidate.unresolved_material_questions
                    ),
                    "meanings": [
                        meaning.model_dump(mode="json") for meaning in candidate.meanings
                    ],
                    "focus_classification": None if focus is None else focus.value,
                    "impact_disposition": None if impact is None else impact.value,
                    "candidate_change": (
                        None
                        if candidate_change is None
                        else candidate_change.model_dump(mode="json")
                    ),
                    "basis_work_revision_id": (
                        None
                        if active_context is None
                        else active_context.work_revision.id
                    ),
                    "basis_steering_plan_revision_id": (
                        None
                        if active_context is None
                        else active_context.steering_plan_revision_id
                    ),
                    "basis_steering_step_id": (
                        None
                        if active_context is None
                        else active_context.current_steering_step_id
                    ),
                    "basis_active_runtime_binding_id": (
                        None
                        if active_context is None
                        else active_context.active_production_binding_id
                    ),
                    "supporting_references": list(supporting_references),
                    "natural_response": candidate.natural_response,
                    "readiness": readiness.model_dump(mode="json"),
                    "provider_identity": candidate.provider_identity,
                    "model_identity": candidate.model_identity,
                    "schema_version": ASSESSMENT_SCHEMA_VERSION,
                    "created_at": now,
                }
            )
            if (
                active_context is not None
                and impact is WorkImpactDisposition.NEW_WORK_RECOMMENDED
            ):
                source_record = next(
                    record
                    for record in reversed(records)
                    if record.actor is InteractionActor.HUMAN
                )
                store.insert_work_transition(
                    {
                        "id": uuid5(
                            NAMESPACE_URL,
                            f"watt:wic-work-transition:{assessment_id}",
                        ),
                        "interaction_id": interaction.id,
                        "source_record_id": source_record.id,
                        "source_assessment_id": assessment_id,
                        "originating_work_id": active_context.work_revision.work_id,
                        "target_work_id": None,
                        "reason": candidate.natural_response,
                        "focus_classification": focus.value,
                        "impact_disposition": impact.value,
                        "choice": WorkTransitionChoice.PENDING_HUMAN.value,
                        "decided_by": None,
                        "decision_rationale": None,
                        "decided_at": None,
                        "created_at": now,
                    }
                )
            uow.commit()
        return self.get_assessment(assessment_id)

    def decide_work_transition(
        self,
        interaction_id: UUID,
        *,
        transition_id: UUID,
        expected_originating_work_id: UUID,
        choice: WorkTransitionChoice,
        authority_identity: str,
        rationale: str | None = None,
    ) -> SharedUnderstanding:
        if choice is WorkTransitionChoice.PENDING_HUMAN:
            raise InteractionInvariantViolation(
                "Human transition decision cannot remain pending"
            )
        identity = authority_identity.strip()
        if not identity:
            raise InteractionInvariantViolation("Human authority identity is required")
        now = datetime.now(UTC)
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id, for_update=True)
            transition = store.work_transition(transition_id, for_update=True)
            if interaction is None:
                raise InteractionRecordNotFound(
                    f"Interaction not found: {interaction_id}"
                )
            if interaction.condition is not InteractionCondition.OPEN:
                raise InteractionInvariantViolation(
                    "Archived Interaction cannot change Work focus"
                )
            if (
                transition is None
                or transition.interaction_id != interaction_id
                or transition.originating_work_id != expected_originating_work_id
            ):
                raise InteractionRecordNotFound(
                    f"Work transition not found: {transition_id}"
                )
            if transition.choice is not WorkTransitionChoice.PENDING_HUMAN:
                if transition.choice is choice:
                    uow.rollback()
                    return self.get_shared_understanding(interaction_id)
                raise InteractionInvariantViolation(
                    "Work transition already has a different Human choice"
                )
            if interaction.current_work_id != transition.originating_work_id:
                raise InteractionInvariantViolation(
                    "Work transition is stale against current Interaction focus"
                )
            decision_rationale = (
                rationale.strip()
                if rationale is not None and rationale.strip()
                else f"Human selected {choice.value} for the Work transition."
            )
            if choice is WorkTransitionChoice.START_NEW_WORK:
                store.clear_current_work(
                    interaction_id,
                    expected_work_id=transition.originating_work_id,
                    updated_by=identity,
                    updated_at=now,
                )
            else:
                store.touch_interaction(
                    interaction_id,
                    updated_by=identity,
                    updated_at=now,
                )
            store.decide_transition(
                transition.id,
                choice=choice,
                decided_by=identity,
                decision_rationale=decision_rationale,
                decided_at=now,
            )
            uow.commit()
        return self.get_shared_understanding(interaction_id)

    def get_assessment(self, assessment_id: UUID) -> InteractionAssessment:
        # Assessment ids are intentionally resolved through their owning Interaction;
        # this method is internal and keeps the store surface small.
        for projection in self.list_interactions():
            for assessment in self.assessment_history(projection.interaction.id):
                if assessment.id == assessment_id:
                    return assessment
        raise InteractionRecordNotFound(f"Interaction assessment not found: {assessment_id}")

    def assessment_history(self, interaction_id: UUID) -> tuple[InteractionAssessment, ...]:
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            if store.interaction(interaction_id) is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            return store.assessments(interaction_id)

    def get_shared_understanding(self, interaction_id: UUID) -> SharedUnderstanding:
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            product = ProductStore(uow.session)
            runtime = RuntimeStore(uow.session)
            interaction = store.interaction(interaction_id)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            records = store.records(interaction_id)
            messages = store.messages(interaction_id)
            turns = store.turns(interaction_id)
            latest = store.latest_assessment(interaction_id)
            resource = product.default_resource()
            governed_revision = (
                None
                if interaction.current_work_id is None
                else product.current_work_reality_revision(interaction.current_work_id)
            )
            active_context = self._active_work_context(uow.session, interaction)
            admitted_from_latest = (
                None
                if latest is None
                else product.work_reality_revision_for_assessment(latest.id)
            )
            evolution_decisions = (
                []
                if latest is None
                else runtime.governance_for_subject(
                    f"interaction-assessment:{latest.id}"
                )
            )
            transitions = store.transitions(interaction_id)
            latest_transition = transitions[-1] if transitions else None
        current_basis = (
            interaction_basis_fingerprint(interaction, records, active_context)
            if records
            else None
        )
        # A historical assessment remains evidence but is not projected as the
        # current understanding after a newer record arrives.
        assessment_current = bool(
            latest is not None and latest.basis_fingerprint == current_basis
        )
        if latest is not None and latest.basis_last_sequence != records[-1].sequence:
                latest = None
                assessment_current = False
                admitted_from_latest = None
                evolution_decisions = []
        admission_status = self._revision_admission_status(
            latest,
            admitted_from_latest is not None,
            tuple(record.decision_type for record in evolution_decisions),
        )
        work_focus_history: list[UUID] = []
        for work_id in (
            *(record.work_focus_id for record in records),
            *(
                identity
                for transition in transitions
                for identity in (
                    transition.originating_work_id,
                    transition.target_work_id,
                )
            ),
            interaction.current_work_id,
        ):
            if work_id is not None and work_id not in work_focus_history:
                work_focus_history.append(work_id)
        satisfaction_state = (
            WorkSatisfactionState.NO_FOCUSED_WORK
            if active_context is None
            else active_context.satisfaction_state
        )
        return SharedUnderstanding(
            interaction=interaction,
            records=records,
            conversation_messages=messages,
            turns=turns,
            latest_assessment=latest,
            latest_assessment_current=assessment_current,
            human_said=tuple(
                item.content for item in records if item.actor is InteractionActor.HUMAN
            ),
            interpreted_motive=None if latest is None else latest.interpreted_motive,
            desired_outcome=None if latest is None else latest.desired_outcome,
            candidate_context=() if latest is None else latest.candidate_context,
            candidate_constraints=() if latest is None else latest.candidate_constraints,
            current_requests=() if latest is None else latest.current_requests,
            unresolved_material_questions=(
                () if latest is None else latest.unresolved_material_questions
            ),
            readiness=None if latest is None else latest.readiness,
            candidate_engineering_resource_id=(
                None if resource is None else resource.id
            ),
            candidate_repository_identity=(
                None if resource is None else resource.repository_identity
            ),
            candidate_repository_ref=(
                None if resource is None else resource.authoritative_ref
            ),
            candidate_scope_summary=(
                None
                if resource is None
                else (
                    "Long-lived Work authority envelope for "
                    f"{resource.repository_identity} at {resource.authoritative_ref}"
                )
            ),
            governed_work_id=interaction.current_work_id,
            governed_revision=governed_revision,
            current_work_focus=(
                None
                if governed_revision is None
                else (
                    f"{governed_revision.motive} → {governed_revision.desired_outcome}"
                )
            ),
            focus_classification=(
                None if latest is None else latest.focus_classification
            ),
            impact_disposition=(
                None if latest is None else latest.impact_disposition
            ),
            candidate_change=(None if latest is None else latest.candidate_change),
            work_revision_admission_status=admission_status,
            active_cycle_work_revision_id=(
                None
                if active_context is None
                else active_context.active_cycle_work_revision_id
            ),
            active_cycle_impact_disposition=(
                None
                if latest is None or latest.basis_active_runtime_binding_id is None
                else latest.impact_disposition
            ),
            work_satisfaction_state=satisfaction_state,
            interaction_relationship_state=interaction.condition,
            work_focus_history=tuple(work_focus_history),
            latest_work_transition=latest_transition,
            new_work_formation_pending=bool(
                interaction.current_work_id is None
                and latest_transition is not None
                and latest_transition.choice is WorkTransitionChoice.START_NEW_WORK
                and latest_transition.target_work_id is None
            ),
            selected_design_schema_identity=(
                interaction.selected_design_schema_identity
            ),
            selected_design_schema_version=(
                interaction.selected_design_schema_version
            ),
            design_schema_selection_rationale=(
                interaction.design_schema_selection_rationale
            ),
            **self._interaction_design_guidance(interaction),
        )

    @staticmethod
    def _interaction_design_guidance(interaction: Interaction) -> dict[str, str | None]:
        if interaction.selected_design_schema_identity is None:
            return {
                "design_stage": None,
                "design_next_focus": None,
                "design_focus_rationale": None,
                "design_facilitation_strategy": None,
                "design_progress_narrative": None,
            }
        schema = design_schema_by_identity(
            interaction.selected_design_schema_identity,
            interaction.selected_design_schema_version,
        )
        focus = schema.issues[0]
        return {
            "design_stage": focus.title,
            "design_next_focus": focus.objective,
            "design_focus_rationale": focus.why_it_matters,
            "design_facilitation_strategy": "CLARIFY",
            "design_progress_narrative": (
                f"Selected {schema.title} v{schema.version}. Current stage: "
                f"{focus.title}. 0 of {len(schema.issues)} design areas are resolved. "
                f"Next, {focus.objective.lower()}"
            ),
        }

    def pending_assessment_interactions(self) -> tuple[UUID, ...]:
        return tuple(
            projection.interaction.id
            for projection in self.list_interactions()
            if projection.records and projection.latest_assessment is None
        )

    def recover_pending_assessments(self) -> tuple[InteractionAssessment, ...]:
        return tuple(
            self.assess_current(interaction_id)
            for interaction_id in self.pending_assessment_interactions()
        )

    def _basis(self, interaction_id: UUID) -> InteractionInterpretationInput:
        with self.database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            interaction = store.interaction(interaction_id)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            records = store.records(interaction_id)
            prior = store.latest_assessment(interaction_id)
            active_context = self._active_work_context(uow.session, interaction)
        if not records:
            raise InteractionInvariantViolation("Interaction has no assessment basis")
        fingerprint = interaction_basis_fingerprint(
            interaction,
            records,
            active_context,
        )
        if prior is not None and prior.basis_fingerprint == fingerprint:
            prior = None
        return InteractionInterpretationInput(
            interaction=interaction,
            records=records,
            prior_assessment=prior,
            active_work_context=active_context,
            basis_fingerprint=fingerprint,
        )

    @staticmethod
    def _active_work_context(session, interaction: Interaction) -> ActiveWorkInterpretationContext | None:
        if interaction.current_work_id is None:
            return None
        product = ProductStore(session)
        runtime = RuntimeStore(session)
        revision = product.current_work_reality_revision(interaction.current_work_id)
        scope = product.scope_for_work(interaction.current_work_id)
        if revision is None or scope is None:
            raise InteractionInvariantViolation(
                "Focused Work lacks exact Work Reality Revision or Engineering Scope"
            )
        steering = SteeringStore(session)
        plan = steering.plan_for_work(interaction.current_work_id)
        active_revision = None if plan is None else steering.active_revision(plan.id)
        current_step = None
        if active_revision is not None:
            current_step = next(
                (
                    step
                    for step in steering.steps(active_revision.id)
                    if step.state.value == "CURRENT"
                ),
                None,
            )
        binding = product.runtime_binding(interaction.current_work_id)
        active_binding = (
            binding
            if binding is not None
            and binding.condition is ProductionCycleBindingCondition.ADMITTED
            else None
        )
        binding_summary = (
            None if binding is None else product.runtime_summary(binding)
        )
        latest_decision = (
            None
            if active_revision is None
            else steering.latest_decision(active_revision.id)
        )
        currently_satisfied = bool(
            current_step is not None
            and current_step.type is SteeringStepType.COMPLETE
            and latest_decision is not None
            and latest_decision.steering_outcome is SteeringOutcome.COMPLETE
            and binding is not None
            and binding.work_reality_revision_id == revision.id
            and binding_summary is not None
            and binding_summary.runtime_commit_id is not None
            and binding_summary.completion_outcome == "PRODUCED"
            and binding_summary.verification_results
            and all(
                result == "PASS"
                for result in binding_summary.verification_results
            )
            and binding_summary.integration_state == "CONVERGED"
            and any(
                reference.kind is RealityReferenceKind.RUNTIME_COMMIT
                and reference.identity == binding_summary.runtime_commit_id
                for reference in latest_decision.reality_refs
            )
        )
        references = [
            f"WORK_REALITY_REVISION:{revision.id}",
            f"ENGINEERING_SCOPE:{scope.id}",
        ]
        if active_revision is not None:
            references.append(f"STEERING_PLAN_REVISION:{active_revision.id}")
        if current_step is not None:
            references.append(f"STEERING_STEP:{current_step.id}")
        if active_binding is not None:
            references.append(f"PRODUCTION_CYCLE:{active_binding.id}")
            summary = product.runtime_summary(active_binding)
            for kind, identity in (
                ("COMPLETION", summary.completion_id),
                ("RUNTIME_COMMIT", summary.runtime_commit_id),
            ):
                if identity is not None:
                    references.append(f"{kind}:{identity}")
            if summary.proposed_snapshot_id is not None:
                references.extend(
                    f"VERIFICATION:{record.id}"
                    for record in runtime.verification_records_for_snapshot(
                        summary.proposed_snapshot_id
                    )
                )
        elif binding is not None and binding_summary is not None:
            references.append(f"PRODUCTION_CYCLE:{binding.id}")
            for kind, identity in (
                ("COMPLETION", binding_summary.completion_id),
                ("RUNTIME_COMMIT", binding_summary.runtime_commit_id),
            ):
                if identity is not None:
                    references.append(f"{kind}:{identity}")
            if binding_summary.proposed_snapshot_id is not None:
                references.extend(
                    f"VERIFICATION:{record.id}"
                    for record in runtime.verification_records_for_snapshot(
                        binding_summary.proposed_snapshot_id
                    )
                )
        return ActiveWorkInterpretationContext(
            work_revision=revision,
            engineering_scope_fingerprint=scope.fingerprint,
            steering_plan_revision_id=(
                None if active_revision is None else active_revision.id
            ),
            steering_plan_revision_number=(
                None if active_revision is None else active_revision.revision_number
            ),
            current_steering_step_id=(
                None if current_step is None else current_step.id
            ),
            current_steering_step_type=(
                None if current_step is None else current_step.type.value
            ),
            active_production_binding_id=(
                None if active_binding is None else active_binding.id
            ),
            active_cycle_work_revision_id=(
                None
                if active_binding is None
                else active_binding.work_reality_revision_id
            ),
            active_cycle_number=(
                None if active_binding is None else active_binding.cycle_number
            ),
            relevant_reality_references=tuple(references),
            satisfaction_state=(
                WorkSatisfactionState.CURRENTLY_SATISFIED
                if currently_satisfied
                else WorkSatisfactionState.IN_PROGRESS
            ),
        )

    @staticmethod
    def _normalize_active_candidate(
        candidate: InteractionAssessmentCandidate,
        active: ActiveWorkInterpretationContext | None,
    ) -> tuple[
        WorkFocusClassification | None,
        WorkImpactDisposition | None,
        WorkEvolutionCandidateChange | None,
    ]:
        if active is None:
            return None, None, None
        focus = candidate.focus_classification or WorkFocusClassification.ON_TOPIC
        if focus in {
            WorkFocusClassification.MATERIAL_BRANCH,
            WorkFocusClassification.UNRELATED_NEW_DEMAND,
        }:
            return focus, WorkImpactDisposition.NEW_WORK_RECOMMENDED, None
        if focus in {
            WorkFocusClassification.RELEVANT_EXPLORATION,
            WorkFocusClassification.SIDE_QUESTION,
        }:
            return focus, WorkImpactDisposition.NO_GOVERNED_CHANGE, None

        current = active.work_revision
        motive = (candidate.interpreted_motive or current.motive).strip()
        outcome = (candidate.desired_outcome or current.desired_outcome).strip()
        context = candidate.candidate_context or current.context_facts
        constraints = candidate.candidate_constraints or current.constraints
        requests = candidate.current_requests or current.requests
        values = {
            "motive": motive,
            "desired_outcome": outcome,
            "context_facts": tuple(context),
            "constraints": tuple(constraints),
            "requests": tuple(requests),
        }
        changed = tuple(
            name
            for name, before in (
                ("motive", current.motive),
                ("desired_outcome", current.desired_outcome),
                ("context_facts", current.context_facts),
                ("constraints", current.constraints),
                ("requests", current.requests),
            )
            if values[name] != before
        )
        if not changed:
            return focus, WorkImpactDisposition.NO_GOVERNED_CHANGE, None
        scope_change = "constraints" in changed or any(
            meaning.kind is InterpretationMeaningKind.OBJECTIVE_OR_SCOPE_CHANGE
            for meaning in candidate.meanings
        )
        impact = candidate.impact_disposition
        if impact in {
            None,
            WorkImpactDisposition.NO_GOVERNED_CHANGE,
            WorkImpactDisposition.NEW_WORK_RECOMMENDED,
        }:
            impact = (
                WorkImpactDisposition.CURRENT_RESULT_MAY_BE_INSUFFICIENT
                if (
                    active.active_production_binding_id is not None
                    or active.satisfaction_state
                    is WorkSatisfactionState.CURRENTLY_SATISFIED
                )
                else WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED
            )
        return (
            focus,
            impact,
            WorkEvolutionCandidateChange(
                changed_fields=changed,
                motive=motive,
                desired_outcome=outcome,
                context_facts=tuple(context),
                constraints=tuple(constraints),
                requests=tuple(requests),
                scope_change_required=scope_change,
            ),
        )

    @staticmethod
    def _normalize_supporting_references(values: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {"VERIFICATION", "RUNTIME_FACT", "COMPLETION", "ENGINEERING_FINDING"}
        normalized: list[str] = []
        for raw in values:
            value = raw.strip()
            if not value:
                continue
            kind, separator, identity = value.partition(":")
            if separator != ":" or kind not in allowed:
                raise InteractionInvariantViolation(
                    "Supporting Reality reference must use an allowed typed identity"
                )
            try:
                UUID(identity)
            except ValueError as error:
                raise InteractionInvariantViolation(
                    "Supporting Reality reference identity must be a UUID"
                ) from error
            normalized.append(f"{kind}:{identity}")
        return tuple(dict.fromkeys(normalized))

    @staticmethod
    def _revision_admission_status(
        assessment: InteractionAssessment | None,
        admitted: bool,
        decision_types: tuple[str, ...],
    ) -> WorkRevisionAdmissionStatus:
        if assessment is None or assessment.basis_work_revision_id is None:
            return WorkRevisionAdmissionStatus.NOT_APPLICABLE
        if admitted:
            return WorkRevisionAdmissionStatus.ADMITTED
        if assessment.impact_disposition is WorkImpactDisposition.NEW_WORK_RECOMMENDED:
            return WorkRevisionAdmissionStatus.NEW_WORK_RECOMMENDED
        if assessment.candidate_change is None:
            return WorkRevisionAdmissionStatus.NOT_APPLICABLE
        if "REJECT_WORK_REALITY_REVISION" in decision_types:
            return WorkRevisionAdmissionStatus.REJECTED
        if "REQUEST_WORK_REALITY_REFINEMENT" in decision_types:
            return WorkRevisionAdmissionStatus.REFINEMENT_REQUESTED
        return WorkRevisionAdmissionStatus.PENDING_HUMAN

    @staticmethod
    def _evaluate_readiness(
        candidate: InteractionAssessmentCandidate,
        basis_fingerprint: str,
    ) -> WorkAdmissionReadiness:
        missing: list[str] = []
        satisfied: list[str] = []
        if candidate.interpreted_motive and candidate.interpreted_motive.strip():
            satisfied.append("MOTIVE")
        else:
            missing.append("MOTIVE")
        if candidate.desired_outcome and candidate.desired_outcome.strip():
            satisfied.append("DESIRED_OUTCOME")
        else:
            missing.append("DESIRED_OUTCOME")
        questions = tuple(
            value.strip()
            for value in candidate.unresolved_material_questions
            if value.strip()
        )
        ready = not missing and not questions
        reasons = (
            ("Motive and desired outcome are clear enough to form governed Work.",)
            if ready
            else ("Material Work-admission information remains unresolved.",)
        )
        return WorkAdmissionReadiness(
            status=(
                WorkAdmissionReadinessStatus.READY
                if ready
                else WorkAdmissionReadinessStatus.NOT_READY
            ),
            profile=READINESS_PROFILE,
            profile_version=READINESS_PROFILE_VERSION,
            satisfied_requirements=tuple(satisfied),
            missing_information=tuple(missing),
            unresolved_material_questions=questions,
            reasons=reasons,
            basis_fingerprint=basis_fingerprint,
        )
