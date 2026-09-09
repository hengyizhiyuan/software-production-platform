from __future__ import annotations

from pathlib import Path
import time

from alembic import command
from alembic.config import Config
import pytest

from spg.application.conversation import WattNativeConversationContextAssembler
from spg.application.interaction import WorkInteractionService, interaction_basis_fingerprint
from spg.domain.conversation import ConversationTurnIntent, StructuredCollaborationResult
from spg.domain.interaction import InteractionAssessmentCandidate, InteractionTurnStatus
from spg.infrastructure.persistence.interaction_store import InteractionStore


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_bounded_persisted_dialogue_survives_restart_and_preserves_source_basis(
    postgres_database, monkeypatch
) -> None:
    monkeypatch.setenv(
        "SPG_DATABASE_URL",
        postgres_database.engine.url.render_as_string(hide_password=False),
    )
    command.upgrade(Config(PROJECT_ROOT / "alembic.ini"), "head")

    class Capability:
        def __init__(self):
            self.bases = []

        def interpret(self, basis):
            self.bases.append(basis)
            return InteractionAssessmentCandidate(
                interpreted_motive="Build an operations management system",
                desired_outcome="A Web system to support Watt promotion",
                natural_response=(
                    "Two options: a content calendar or a lead inbox."
                    if len(basis.records) == 3
                    else "Reply to Human turn " + str(len(basis.records))
                ),
                provider_identity="test:dialogue-continuity",
            )

    capability = Capability()
    service = WorkInteractionService(postgres_database, capability=capability)
    interaction = service.create_interaction(human_identity="human:dialogue-test")

    def complete_turn(message):
        submitted = service.submit_turn(
            interaction.id, message, human_identity="human:dialogue-test"
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            turn = service.get_turn(submitted.id)
            if turn.status is InteractionTurnStatus.COMPLETED:
                return
            assert turn.status is not InteractionTurnStatus.FAILED, turn.failure_message
            time.sleep(0.01)
        pytest.fail("Dialogue test turn did not complete")

    try:
        for message in (
            "I want to build an operations management platform.",
            "It promotes Watt to individual developers and small teams.",
            "Recommend possible starting points.",
            "Our marketing team will operate the system.",
            "The first version must support a small team.",
        ):
            complete_turn(message)
        with postgres_database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            all_messages = store.messages(interaction.id)
            assert len(all_messages) == 10
            assert store.messages(interaction.id, limit=8) == all_messages[-8:]
            assert store.messages(interaction.id, limit=1) == all_messages[-1:]
        service.shutdown()
        service = WorkInteractionService(postgres_database, capability=capability)
        complete_turn("Explain your second suggestion.")
        basis = capability.bases[-1]
        assert len(basis.records) == 6  # The complete source ledger is retained.
        assert len(basis.recent_conversation_messages) == 8
        assert basis.recent_conversation_messages[-1].content == "Explain your second suggestion."
        assert any("lead inbox" in message.content for message in basis.recent_conversation_messages)
        assert basis.basis_fingerprint == interaction_basis_fingerprint(
            basis.interaction, basis.records, basis.active_work_context
        )
        context = WattNativeConversationContextAssembler().assemble(
            basis,
            StructuredCollaborationResult(
                turn_intent=ConversationTurnIntent.REQUEST_DETAIL,
                detailed_explanation_requested=True,
                response_language="English",
            ),
        )
        assert context.recent_relevant_messages == basis.recent_conversation_messages
        projection = service.get_shared_understanding(interaction.id)
        assert len(projection.conversation_messages) == 12
        assert projection.governed_work_id is None
    finally:
        service.shutdown()
