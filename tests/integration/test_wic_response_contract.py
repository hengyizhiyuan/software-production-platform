"""Response decisions remain turn evidence across real PostgreSQL boundaries."""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
from threading import Event
import time
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select, text

from spg.api import create_http_application
from spg.application.interaction import WorkInteractionService
from spg.application.work import WorkApplicationService
from spg.domain.conversation import ConversationTurnIntent
from spg.domain.design_intent import (
    DesignCollaborationMode,
    DesignIntentFrame,
    DesignObjectType,
    DesignScopeLevel,
)
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionTurnStatus,
    WorkFocusClassification,
    WorkImpactDisposition,
)
from spg.domain.product import WorkStatus
from spg.domain.runtime_activation import RuntimeActivationProjection, RuntimeActivationState
from spg.domain.response_contract import (
    AdvancementObligation,
    InformationBudget,
    InteractionMode,
    ResponseContract,
    ResponseIntent,
)
from spg.domain.wic_response import (
    GovernedResponseEnvelope,
    GovernedResponseRealization,
    WicResponseEventType,
    WicRuntimeMode,
)
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_schema import (
    interaction_assessments,
    work_reality_revisions,
)
from spg.infrastructure.persistence.runtime_schema import (
    execution_attempts,
    execution_dispatches,
    production_runs,
    production_work_units,
)


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HUMAN = "human:response-contract-integration"
MOTIVE = "Make account access straightforward"
OUTCOME = "A working sign-in form shows validation and submission feedback."


@pytest.fixture(autouse=True)
def clean_response_contract_schema(postgres_database: Database) -> Iterator[None]:
    # Never use the Human Review database: the shared PostgreSQL fixture points
    # at the explicitly configured disposable test database.
    assert postgres_database.engine.url.database == "spg_test"
    previous = os.environ.get("SPG_DATABASE_URL")
    os.environ["SPG_DATABASE_URL"] = postgres_database.engine.url.render_as_string(
        hide_password=False
    )
    names = ", ".join(
        f'"{name}"'
        for name in sorted({table.name for table in (*product_tables, *runtime_tables)})
    )

    def truncate() -> None:
        with postgres_database.engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))

    command.upgrade(Config(PROJECT_ROOT / "alembic.ini"), "head")
    truncate()
    try:
        yield
    finally:
        truncate()
        if previous is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous


def _candidate(
    mode: InteractionMode,
    *,
    text: str = "Email sign-in keeps the first release easy to understand.",
    constraints: tuple[str, ...] = (),
) -> InteractionAssessmentCandidate:
    intent = {
        InteractionMode.EXPLORE: ConversationTurnIntent.EXPLORE,
        InteractionMode.DESIGN: ConversationTurnIntent.BUILD,
        InteractionMode.EXECUTE: ConversationTurnIntent.ACTION_REQUEST,
        InteractionMode.ANSWER: ConversationTurnIntent.DIRECT_QUESTION,
        InteractionMode.DIAGNOSE: ConversationTurnIntent.FEEDBACK,
    }[mode]
    return InteractionAssessmentCandidate(
        turn_intent=intent,
        interpreted_motive=MOTIVE,
        desired_outcome=OUTCOME,
        candidate_constraints=constraints,
        current_requests=("Implement the agreed sign-in form.",),
        design_intent_frame=DesignIntentFrame(
            design_subject="Sign-in form",
            object_type=DesignObjectType.FEATURE,
            desired_outcome=OUTCOME,
            scope_level=DesignScopeLevel.CAPABILITY,
            collaboration_mode=DesignCollaborationMode.DESIGN,
            confidence=0.95,
        ),
        natural_response=text,
        response_intent=ResponseIntent(
            interaction_mode=mode,
            rationale="Interpret the current collaboration request against supplied context.",
            executable_context=mode is InteractionMode.EXECUTE,
        ),
        provider_identity="test:response-contract-semantic",
    )


class _SequenceCapability:
    def __init__(self, *candidates: InteractionAssessmentCandidate) -> None:
        self.candidates = candidates
        self.bases: list[InteractionInterpretationInput] = []

    def interpret(self, basis: InteractionInterpretationInput) -> InteractionAssessmentCandidate:
        self.bases.append(basis)
        assert len(self.bases) <= len(self.candidates), "Unexpected provider request"
        return self.candidates[len(self.bases) - 1]


class _RecordingRealizer:
    provider_identity = "test:contract-aware-realizer"
    model_identity = "test-only"

    def __init__(self) -> None:
        self.envelopes: list[GovernedResponseEnvelope] = []

    def realize_stream(self, envelope, *, on_response_delta):
        self.envelopes.append(envelope)
        assert envelope.response_contract is not None
        on_response_delta(envelope.governed_content)
        return GovernedResponseRealization(
            content=envelope.governed_content,
            provider_identity=self.provider_identity,
        )


def _service(database, capability, realizer=None) -> WorkInteractionService:
    return WorkInteractionService(
        database,
        capability=capability,
        response_realizer=realizer,
        runtime_mode=WicRuntimeMode.WIC_VNEXT_CONTROLLED,
    )


def _terminal(service: WorkInteractionService, turn_id: UUID):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        turn = service.get_turn(turn_id)
        if turn.status in {InteractionTurnStatus.COMPLETED, InteractionTurnStatus.FAILED}:
            return turn
        time.sleep(0.01)
    pytest.fail(f"Turn did not finish: {turn_id}")


def _turn(service: WorkInteractionService, interaction_id: UUID, content: str):
    turn = service.submit_turn(interaction_id, content, human_identity=HUMAN)
    final = _terminal(service, turn.id)
    assert final.status is InteractionTurnStatus.COMPLETED, final.failure_message
    return final


def _contract(service: WorkInteractionService, turn_id: UUID) -> ResponseContract:
    events = service.response_events(turn_id)
    ready = [event for event in events if event.event_type is WicResponseEventType.RESPONSE_CONTRACT_READY]
    assert len(ready) == 1
    contract = ResponseContract.model_validate(ready[0].metadata["response_contract"])
    assert ready[0].basis_fingerprint == contract.basis_fingerprint
    return contract


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table)) or 0


def _runtime_counts(database: Database) -> dict[str, int]:
    return {table.name: _count(database, table) for table in runtime_tables}


def _admit(service, database, interaction_id, tmp_path):
    assessment = service.get_shared_understanding(interaction_id).latest_assessment
    assert assessment is not None
    works = WorkApplicationService(database, workspace_root=tmp_path / "workspaces")
    return works.admit_interaction_work(
        interaction_id,
        assessment_id=assessment.id,
        basis_fingerprint=assessment.basis_fingerprint,
        authority_identity=HUMAN,
        use_default_resource=False,
    )


def test_pre_work_contract_replays_after_reload_without_becoming_semantic_truth(
    postgres_database: Database,
) -> None:
    first_capability = _SequenceCapability(_candidate(InteractionMode.EXPLORE))
    realizer = _RecordingRealizer()
    first = _service(postgres_database, first_capability, realizer)
    interaction = first.create_interaction(human_identity=HUMAN, start_work_context=True)
    try:
        turn = _turn(first, interaction.id, "Let's explore possible sign-in experiences.")
        contract = _contract(first, turn.id)
        assert contract.interaction_mode is InteractionMode.EXPLORE
        assert realizer.envelopes[0].response_contract == contract
        assert contract.authority == "ADVISORY_ONLY"
        persisted_events = first.response_events(turn.id)
    finally:
        first.shutdown()

    second_capability = _SequenceCapability(_candidate(InteractionMode.ANSWER))
    restarted = _service(postgres_database, second_capability)
    try:
        assert restarted.response_events(turn.id) == persisted_events
        followup = _turn(restarted, interaction.id, "Would email-only access fit that scope?")
        assert second_capability.bases[0].previous_response_contract == contract
        assert _contract(restarted, followup.id).basis_fingerprint != contract.basis_fingerprint
        assessment = restarted.get_shared_understanding(interaction.id).latest_assessment
        assert assessment is not None
        assert assessment.engineering_semantic_facts == ()
        assert "response_contract" not in assessment.model_dump()
        assert _count(postgres_database, work_reality_revisions) == 0
        assert WorkApplicationService(postgres_database).get_work(interaction.current_work_id).status is WorkStatus.PRE_WORK
        assert all(_count(postgres_database, table) == 0 for table in runtime_tables)
    finally:
        restarted.shutdown()


def test_active_exploration_does_not_promote_proposed_design_to_work_truth(
    postgres_database: Database, tmp_path: Path,
) -> None:
    # The model proposes a new constraint and leaves focus ON_TOPIC. An explicit
    # exploration response intent must still prevent a production/change request.
    capability = _SequenceCapability(
        _candidate(InteractionMode.DESIGN),
        _candidate(
            InteractionMode.EXPLORE,
            constraints=("Require a biometric device for every sign-in.",),
            text="Biometrics and email are alternative routes to explore before choosing.",
        ).model_copy(update={
            "focus_classification": WorkFocusClassification.ON_TOPIC,
            "impact_disposition": WorkImpactDisposition.HUMAN_GOVERNANCE_REQUIRED,
        }),
    )
    service = _service(postgres_database, capability)
    interaction = service.create_interaction(human_identity=HUMAN, start_work_context=True)
    try:
        _turn(service, interaction.id, "Design a sign-in form with useful submission feedback.")
        admitted = _admit(service, postgres_database, interaction.id, tmp_path)
        before = WorkApplicationService(postgres_database).get_work(admitted.work_id)
        revisions = _count(postgres_database, work_reality_revisions)
        runtime_before = _runtime_counts(postgres_database)
        turn = _turn(service, interaction.id, "Could we brainstorm some more access methods first?")
        contract = _contract(service, turn.id)
        latest = service.get_shared_understanding(interaction.id).latest_assessment
        assert contract.interaction_mode is InteractionMode.EXPLORE
        assert contract.advancement_obligation is AdvancementObligation.ANSWER_ONLY
        assert latest.impact_disposition is WorkImpactDisposition.NO_GOVERNED_CHANGE
        assert latest.candidate_change is None
        assert _count(postgres_database, work_reality_revisions) == revisions
        assert WorkApplicationService(postgres_database).get_work(admitted.work_id) == before
        assert _runtime_counts(postgres_database) == runtime_before
    finally:
        service.shutdown()


@pytest.mark.parametrize(("question", "expected_mode"), [
    ("现在做到哪了？", InteractionMode.STATUS),
    ("为什么一直卡在 QUEUED？", InteractionMode.DIAGNOSE),
])
def test_active_reality_questions_are_provider_free_and_do_not_mutate_work(
    postgres_database: Database, tmp_path: Path, question: str,
    expected_mode: InteractionMode,
) -> None:
    capability = _SequenceCapability(_candidate(InteractionMode.DESIGN))
    realizer = _RecordingRealizer()
    service = _service(postgres_database, capability, realizer)
    interaction = service.create_interaction(human_identity=HUMAN, start_work_context=True)
    try:
        _turn(service, interaction.id, "Design the sign-in form and submission feedback.")
        admitted = _admit(service, postgres_database, interaction.id, tmp_path)
        before = WorkApplicationService(postgres_database).get_work(admitted.work_id)
        runtime_before = _runtime_counts(postgres_database)
        turn = _turn(service, interaction.id, question)
        contract = _contract(service, turn.id)
        projection = service.get_shared_understanding(interaction.id)
        assert contract.interaction_mode is expected_mode
        assert contract.question_budget == 0
        assert contract.advancement_obligation is AdvancementObligation.ANSWER_ONLY
        assert projection.latest_assessment.provider_identity == "watt-native:work-reality-query"
        assert len(capability.bases) == len(realizer.envelopes) == 1
        assert "尚未创建生产周期" in projection.conversation_messages[-1].content
        assert WorkApplicationService(postgres_database).get_work(admitted.work_id) == before
        assert _runtime_counts(postgres_database) == runtime_before
        evidence_path = os.environ.get("SPG_RESPONSE_CONTRACT_REALITY_EVIDENCE_PATH")
        if evidence_path:
            destination = Path(evidence_path)
            existing = json.loads(destination.read_text()) if destination.exists() else []
            case = "E" if expected_mode is InteractionMode.STATUS else "A"
            report = {
                "case": case,
                "evidence_class": "DETERMINISTIC_WORK_REALITY_REAL_POSTGRESQL",
                "input": question,
                "turn_id": str(turn.id),
                "provider_identity": projection.latest_assessment.provider_identity,
                "external_provider_requests_for_status_turn": 0,
                "response_contract": contract.model_dump(mode="json"),
                "human_facing_content": projection.conversation_messages[-1].content,
                "work_projection_unchanged": True,
                "runtime_table_counts_unchanged": True,
                "fixture_reality": "Admitted Work; no production cycle, PWU or queue entry.",
            }
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(
                [item for item in existing if item["case"] != case] + [report],
                ensure_ascii=False, indent=2,
            ) + "\n")
    finally:
        service.shutdown()


def test_execution_contract_uses_existing_admission_without_granting_authority(
    postgres_database: Database, tmp_path: Path,
) -> None:
    service = _service(postgres_database, _SequenceCapability(_candidate(
        InteractionMode.EXECUTE, text="I will proceed through the current admission step.",
    )))
    interaction = service.create_interaction(human_identity=HUMAN, start_work_context=True)
    try:
        turn = _turn(service, interaction.id, "Implement the sign-in form we just agreed.")
        contract = _contract(service, turn.id)
        assert contract.information_budget is InformationBudget.MINIMAL_ACKNOWLEDGEMENT
        assert contract.question_budget == 0
        assert contract.advancement_obligation is AdvancementObligation.ACK_AND_EXECUTE
        works = WorkApplicationService(postgres_database)
        assert works.get_work(interaction.current_work_id).status is WorkStatus.PRE_WORK
        assert _count(postgres_database, work_reality_revisions) == 0

        admitted = _admit(service, postgres_database, interaction.id, tmp_path)
        assert admitted.work_id == interaction.current_work_id
        assert admitted.status is WorkStatus.READY
        assert _count(postgres_database, work_reality_revisions) == 1
        # Work admission may establish a managed repository baseline. It must not
        # dispatch production merely because the response requested execution.
        for table in (production_runs, production_work_units, execution_attempts, execution_dispatches):
            assert _count(postgres_database, table) == 0, table.name
        with postgres_database.engine.connect() as connection:
            revision = connection.execute(select(work_reality_revisions)).mappings().one()
        assert "response_contract" not in revision
        assert revision["engineering_semantic_facts"] == []
    finally:
        service.shutdown()


@pytest.mark.parametrize("active_work", [False, True])
def test_contract_is_durable_before_first_delta_and_streams_before_terminal(
    postgres_database: Database, tmp_path: Path, active_work: bool,
) -> None:
    class BlockingRealizer(_RecordingRealizer):
        def __init__(self):
            super().__init__()
            self.first_emitted = Event()
            self.release = Event()

        def realize_stream(self, envelope, *, on_response_delta):
            self.envelopes.append(envelope)
            assert envelope.response_contract is not None
            first = "Email access reduces the initial setup. "
            on_response_delta(first)
            self.first_emitted.set()
            assert self.release.wait(timeout=5), "test failed to release realizer"
            rest = "Social sign-in is an alternative with extra integration work."
            on_response_delta(rest)
            return GovernedResponseRealization(
                content=first + rest, provider_identity=self.provider_identity,
            )

    capability = _SequenceCapability(
        *([_candidate(InteractionMode.DESIGN)] if active_work else []),
        _candidate(InteractionMode.EXPLORE),
    )
    service = _service(postgres_database, capability)
    interaction = service.create_interaction(human_identity=HUMAN, start_work_context=True)
    realizer = BlockingRealizer()
    try:
        if active_work:
            _turn(service, interaction.id, "Design the sign-in form and submission feedback.")
            _admit(service, postgres_database, interaction.id, tmp_path)
        service.response_realizer = realizer
        turn = service.submit_turn(
            interaction.id, "Let's compare possible sign-in experiences.", human_identity=HUMAN,
        )
        assert realizer.first_emitted.wait(timeout=3)
        events = service.response_events(turn.id)
        kinds = [event.event_type for event in events]
        assert WicResponseEventType.RESPONSE_DELTA in kinds
        assert WicResponseEventType.FINAL_RESPONSE not in kinds
        assert kinds.index(WicResponseEventType.RESPONSE_CONTRACT_READY) < kinds.index(WicResponseEventType.RESPONSE_DELTA)
        assert service.get_turn(turn.id).status is InteractionTurnStatus.PROCESSING
        assert _contract(service, turn.id) == realizer.envelopes[0].response_contract
        realizer.release.set()
        assert _terminal(service, turn.id).status is InteractionTurnStatus.COMPLETED
        deltas = "".join(event.content or "" for event in service.response_events(turn.id)
                         if event.event_type is WicResponseEventType.RESPONSE_DELTA)
        assert deltas == service.get_shared_understanding(interaction.id).conversation_messages[-1].content
    finally:
        realizer.release.set()
        service.shutdown()


def test_failed_realization_contract_is_evidence_not_next_turn_trajectory(
    postgres_database: Database,
) -> None:
    class FailingRealizer(_RecordingRealizer):
        def realize_stream(self, envelope, *, on_response_delta):
            self.envelopes.append(envelope)
            raise RuntimeError("Deliberate test-only realization failure")

    capability = _SequenceCapability(
        _candidate(InteractionMode.ANSWER),
        _candidate(InteractionMode.DIAGNOSE),
        _candidate(InteractionMode.EXPLORE),
    )
    service = _service(postgres_database, capability)
    interaction = service.create_interaction(human_identity=HUMAN, start_work_context=True)
    try:
        first = _turn(service, interaction.id, "Is email sufficient for this release?")
        established = _contract(service, first.id)
        service.response_realizer = FailingRealizer()
        failed = service.submit_turn(interaction.id, "The form didn't load.", human_identity=HUMAN)
        assert _terminal(service, failed.id).status is InteractionTurnStatus.FAILED
        assert _contract(service, failed.id).interaction_mode is InteractionMode.DIAGNOSE
        assert not any(event.event_type is WicResponseEventType.FINAL_RESPONSE
                       for event in service.response_events(failed.id))
        service.response_realizer = _RecordingRealizer()
        _turn(service, interaction.id, "Let's consider another access path.")
        assert capability.bases[-1].previous_response_contract == established
        assert _count(postgres_database, interaction_assessments) == 3
    finally:
        service.shutdown()


def test_human_sse_skips_internal_contract_event_and_replays_without_model_recall(
    postgres_database: Database,
) -> None:
    class NoopBackgroundServices:
        def resume_safely_eligible_works(self):
            return ()

        def shutdown(self):
            return None

        def schedule(self, _work_id):
            return False

    class NoopWorks:
        database = postgres_database

        def list_works(self, *args, **kwargs):
            return ()

    class Activation:
        def project(self):
            return RuntimeActivationProjection(
                state=RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE,
                active_application_revision="test",
                current_trusted_baseline_revision="test",
                reason="test-only activation",
            )

    capability = _SequenceCapability(_candidate(InteractionMode.ANSWER))
    service = _service(postgres_database, capability)
    interaction = service.create_interaction(human_identity=HUMAN)
    turn = _turn(service, interaction.id, "Can this form use just email sign-in?")
    stored = service.response_events(turn.id)
    internal = next(event for event in stored
                    if event.event_type is WicResponseEventType.RESPONSE_CONTRACT_READY)
    client = TestClient(create_http_application(
        application=object(), database=postgres_database,
        interaction_service=service, work_service=NoopWorks(),
        orchestrator=NoopBackgroundServices(), steering_driver=NoopBackgroundServices(),
        runtime_activation=Activation(),
    ), raise_server_exceptions=False)

    def payloads(response):
        assert response.status_code == 200
        return [json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines() if line.startswith("data: ")]

    with client:
        route = f"/api/interactions/{interaction.id}/turns/{turn.id}/events"
        full = payloads(client.get(route))
        assert not any(item["event_type"] == "RESPONSE_CONTRACT_READY" for item in full)
        full_ids = [item["sequence"] for item in full]
        assert internal.sequence not in full_ids
        assert full_ids == sorted(set(full_ids))
        replay = payloads(client.get(route, headers={"last-event-id": str(internal.sequence)}))
        assert replay == [item for item in full if item["sequence"] > internal.sequence]
        deltas = "".join(item["content"] for item in replay if item["event_type"] == "RESPONSE_DELTA")
        assert deltas == service.get_shared_understanding(interaction.id).conversation_messages[-1].content
        assert len(capability.bases) == 1
        assert service.response_events(turn.id) == stored
