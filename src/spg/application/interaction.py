"""Pre-Work Interaction application service and governed assessment admission."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from uuid import UUID, uuid4

from spg.domain.interaction import (
    Interaction,
    InteractionActor,
    InteractionAssessment,
    InteractionAssessmentCandidate,
    InteractionCondition,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionRecord,
    InteractionRecordNotFound,
    SharedUnderstanding,
    WorkAdmissionReadiness,
    WorkAdmissionReadinessStatus,
    WorkInteractionCapability,
)
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.interaction_store import InteractionStore


ASSESSMENT_SCHEMA_VERSION = "wic-assessment-v1"
READINESS_PROFILE = "LONG_LIVED_STEERING"
READINESS_PROFILE_VERSION = "v0"


def interaction_basis_fingerprint(
    interaction: Interaction,
    records: tuple[InteractionRecord, ...],
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
            }
            for record in records
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class DeterministicWorkInteractionCapability:
    """Conservative deterministic test capability; not the Watt product Provider."""

    _IDLE = {"hi", "hello", "hey", "你好", "在吗", "谢谢", "thanks"}

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        human = [record for record in basis.records if record.actor is InteractionActor.HUMAN]
        latest = human[-1]
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
    ) -> InteractionRecord:
        value = content.strip()
        identity = human_identity.strip()
        if not value or not identity:
            raise InteractionInvariantViolation("Human input and identity are required")
        now = datetime.now(UTC)
        record_id = uuid4()
        content_fingerprint = hashlib.sha256(value.encode()).hexdigest()
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
    ) -> SharedUnderstanding:
        # The Human record commits first. A failed Provider call therefore leaves an
        # honest, recoverable unassessed basis rather than losing communication.
        self.append_human_input(
            interaction_id,
            content,
            human_identity=human_identity,
        )
        self.assess_current(interaction_id)
        return self.get_shared_understanding(interaction_id)

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
            current_basis = interaction_basis_fingerprint(interaction, records)
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
            readiness = self._evaluate_readiness(candidate, current_basis)
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
                    "natural_response": candidate.natural_response,
                    "readiness": readiness.model_dump(mode="json"),
                    "provider_identity": candidate.provider_identity,
                    "model_identity": candidate.model_identity,
                    "schema_version": ASSESSMENT_SCHEMA_VERSION,
                    "created_at": now,
                }
            )
            uow.commit()
        return self.get_assessment(assessment_id)

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
            interaction = store.interaction(interaction_id)
            if interaction is None:
                raise InteractionRecordNotFound(f"Interaction not found: {interaction_id}")
            records = store.records(interaction_id)
            latest = store.latest_assessment(interaction_id)
        current_basis = (
            interaction_basis_fingerprint(interaction, records) if records else None
        )
        # A historical assessment remains evidence but is not projected as the
        # current understanding after a newer record arrives.
        if latest is not None and latest.basis_fingerprint != current_basis:
            latest = None
        return SharedUnderstanding(
            interaction=interaction,
            records=records,
            latest_assessment=latest,
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
            governed_work_id=interaction.current_work_id,
        )

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
        if not records:
            raise InteractionInvariantViolation("Interaction has no assessment basis")
        fingerprint = interaction_basis_fingerprint(interaction, records)
        if prior is not None and prior.basis_fingerprint == fingerprint:
            prior = None
        return InteractionInterpretationInput(
            interaction=interaction,
            records=records,
            prior_assessment=prior,
            basis_fingerprint=fingerprint,
        )

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
