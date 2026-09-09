"""Real HTTP streaming checks with gated providers and explicit durability timing."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import socket
from threading import Event, Thread
from types import SimpleNamespace
import time
from urllib.request import ProxyHandler, Request, build_opener
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import event, func, select
import uvicorn

from spg.api import create_http_application
from spg.application.interaction import (
    DeterministicWorkInteractionCapability,
    WorkInteractionService,
)
from spg.domain.interaction import InteractionAssessmentCandidate, InteractionTurnStatus
from spg.infrastructure.persistence import runtime_tables
from spg.infrastructure.persistence.interaction_store import InteractionStore
from spg.infrastructure.persistence.product_schema import product_works
from spg.providers.codex_interaction import CodexSdkWorkInteractionCapability


pytestmark = pytest.mark.postgresql


class GatedProvider:
    def __init__(self, *, fail=False):
        self.entered = Event()
        self.release_text = Event()
        self.text_published = Event()
        self.release_completion = Event()
        self.fail = fail

    def interpret(self, _basis):
        raise AssertionError("The asynchronous Turn must use streaming")

    def interpret_stream(self, basis, *, on_response_delta):
        self.entered.set()
        if not self.release_text.wait(10):
            raise RuntimeError("Test did not release the provider")
        if self.fail:
            raise RuntimeError("Gated provider failure before response text")
        on_response_delta("Let us design the Web application. ")
        self.text_published.set()
        if not self.release_completion.wait(10):
            raise RuntimeError("Test did not release provider completion")
        return InteractionAssessmentCandidate(
            interpreted_motive=basis.records[-1].content,
            natural_response="Let us design the Web application. Who will use it first?",
            provider_identity="test:gated-collaboration",
        )


@pytest.fixture(autouse=True)
def migrated_database(postgres_database, monkeypatch):
    monkeypatch.setenv(
        "SPG_DATABASE_URL",
        postgres_database.engine.url.render_as_string(hide_password=False),
    )
    command.upgrade(Config(Path(__file__).resolve().parents[2] / "alembic.ini"), "head")


@contextmanager
def live_pipeline(database, *, fail=False, capability=None, provider=None):
    provider = provider or GatedProvider(fail=fail)
    service = WorkInteractionService(database, capability=capability or provider)
    application = create_http_application(database=database, interaction_service=service)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    address = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(
        application, lifespan="off", access_log=False, log_level="error",
    ))
    worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    worker.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "Local HTTP server did not start"
        yield service, provider, address
    finally:
        provider.release_text.set()
        provider.release_completion.set()
        service.shutdown()
        server.should_exit = True
        worker.join(timeout=5)
        listener.close()
        assert not worker.is_alive(), "Local HTTP server did not stop"


def request_json(address, path, body=None):
    request = Request(
        address + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with build_opener(ProxyHandler({})).open(request, timeout=5) as response:
        return response.status, json.load(response)


def submit(address):
    _, interaction = request_json(address, "/api/interactions", {"human_identity": "human:test"})
    interaction_id = interaction["interaction_id"]
    started = time.monotonic()
    status, turn = request_json(address, f"/api/interactions/{interaction_id}/turns", {
        "human_identity": "human:test",
        "content": "I want to build an operation management platform.",
    })
    assert status == 202
    assert time.monotonic() - started < 5
    return interaction_id, UUID(turn["turn_id"])


def open_events(address, interaction_id, turn_id):
    return build_opener(ProxyHandler({})).open(
        f"{address}/api/interactions/{interaction_id}/turns/{turn_id}/events", timeout=5,
    )


def next_event(response, wanted):
    # Read live network frames: unlike buffered TestClient.get(), this returns
    # while the provider is held at its gate and the HTTP response is still open.
    event_name = None
    payload = None
    for _ in range(100):
        line = response.readline().decode().rstrip("\r\n")
        if line.startswith("event: "):
            event_name = line[7:]
        elif line.startswith("data: "):
            payload = json.loads(line[6:])
        elif not line and event_name:
            if event_name == wanted:
                return payload
            event_name = None
            payload = None
    pytest.fail(f"Did not receive {wanted}")


def await_timing(service, turn_id, milestone):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        timing = service.turn_timing(turn_id)
        if timing[milestone] is not None:
            return timing
        time.sleep(0.01)
    pytest.fail(f"Missing timing {milestone}")


def test_live_ack_and_status_precede_text_and_durable_completion(postgres_database):
    with live_pipeline(postgres_database) as (service, provider, address):
        interaction_id, turn_id = submit(address)
        assert provider.entered.wait(3)
        timing = service.turn_timing(turn_id)
        assert timing["acknowledged_ms"] is not None
        assert timing["first_response_delta_ms"] is None
        assert timing["completed_ms"] is None
        with open_events(address, interaction_id, turn_id) as stream:
            assert stream.headers["X-Accel-Buffering"] == "no"
            assert next_event(stream, "turn.status")["status"] == "PROCESSING"
            status_timing = service.turn_timing(turn_id)
            assert status_timing["first_sse_event_ms"] is not None
            assert status_timing["first_response_delta_ms"] is None
            assert not provider.release_text.is_set()

            provider.release_text.set()
            assert next_event(stream, "message.delta")["delta"] == "Let us design the Web application. "
            assert provider.text_published.is_set()
            assert service.turn_timing(turn_id)["completed_ms"] is None
            assert service.get_turn(turn_id).status is InteractionTurnStatus.PROCESSING

            before_assessment_commit = Event()
            release_assessment_commit = Event()
            before_commit = Event()
            release_commit = Event()

            def hold_completed_commit(session):
                store = InteractionStore(session)
                turn = store.turn(turn_id)
                if turn is not None and turn.status is InteractionTurnStatus.COMPLETED:
                    before_commit.set()
                    assert release_commit.wait(10), "Test did not release final commit"
                elif (
                    turn is not None and turn.status is InteractionTurnStatus.PROCESSING
                    and store.latest_assessment(UUID(interaction_id)) is not None
                ):
                    before_assessment_commit.set()
                    assert release_assessment_commit.wait(10), "Test did not release assessment commit"

            event.listen(postgres_database.session_factory, "before_commit", hold_completed_commit)
            try:
                provider.release_completion.set()
                assert before_assessment_commit.wait(3)
                validating = service.turn_timing(turn_id)
                assert validating["candidate_validated_ms"] is not None
                assert validating["assessment_persisted_ms"] is None
                assert validating["final_persistence_started_ms"] is None
                assert service.get_shared_understanding(UUID(interaction_id)).latest_assessment is None
                release_assessment_commit.set()
                assert before_commit.wait(3)
                persisting = service.turn_timing(turn_id)
                assert persisting["assessment_persisted_ms"] is not None
                assert persisting["final_persistence_started_ms"] is not None
                assert persisting["completed_ms"] is None
                assert service.get_turn(turn_id).status is InteractionTurnStatus.PROCESSING
                release_commit.set()
                assert next_event(stream, "message.completed")["message_id"]
            finally:
                release_assessment_commit.set()
                release_commit.set()
                event.remove(postgres_database.session_factory, "before_commit", hold_completed_commit)

        timing = await_timing(service, turn_id, "completed_ms")
        assert 0 <= timing["acknowledged_ms"] <= timing["processing_started_ms"]
        assert timing["first_sse_event_ms"] < timing["first_response_delta_ms"] < timing["completed_ms"]
        assert timing["failed_ms"] is None
        stages = (
            "processing_started", "basis_prepared", "provider_started", "provider_returned",
            "admission_started", "candidate_validated", "assessment_persisted",
            "final_persistence_started", "completed",
        )
        values = [timing[f"{stage}_ms"] for stage in stages]
        assert all(value is not None for value in values)
        assert values == sorted(values)
        # A legacy capability does not expose generation or wire-validation phases.
        assert timing["semantic_envelope_completed_ms"] is None
        assert timing["payload_validated_ms"] is None
        projection = service.get_shared_understanding(UUID(interaction_id))
        assert len(projection.conversation_messages) == 2
        assert projection.conversation_messages[-1].content.endswith("Who will use it first?")
        # Restarted services can recover durable state without fabricating old
        # first-event/first-token measurements from wall-clock timestamps.
        restarted = WorkInteractionService(postgres_database, capability=provider)
        try:
            assert restarted.get_turn(turn_id).status is InteractionTurnStatus.COMPLETED
            assert restarted.turn_timing(turn_id) is None
        finally:
            restarted.shutdown()


def test_failure_before_text_does_not_fabricate_response_latency(postgres_database):
    with live_pipeline(postgres_database, fail=True) as (service, provider, address):
        interaction_id, turn_id = submit(address)
        assert provider.entered.wait(3)
        with open_events(address, interaction_id, turn_id) as stream:
            next_event(stream, "turn.status")
            provider.release_text.set()
            assert next_event(stream, "turn.failed")["code"] == "RuntimeError"
        timing = await_timing(service, turn_id, "failed_ms")
        assert timing["completed_ms"] is None
        assert timing["first_response_delta_ms"] is None
        assert timing["provider_started_ms"] is not None
        assert timing["provider_returned_ms"] is None
        assert timing["candidate_validated_ms"] is None
        assert timing["assessment_persisted_ms"] is None
        assert service.get_turn(turn_id).status is InteractionTurnStatus.FAILED
        assert len(service.get_shared_understanding(UUID(interaction_id)).conversation_messages) == 1


def test_disconnect_keeps_processing_and_reconnect_replays_persisted_response(postgres_database):
    with live_pipeline(postgres_database) as (service, provider, address):
        interaction_id, turn_id = submit(address)
        assert provider.entered.wait(3)
        with open_events(address, interaction_id, turn_id) as stream:
            next_event(stream, "turn.status")
        first_event = service.turn_timing(turn_id)["first_sse_event_ms"]
        provider.release_text.set()
        provider.release_completion.set()
        await_timing(service, turn_id, "completed_ms")
        persisted = service.get_shared_understanding(UUID(interaction_id)).conversation_messages[-1]
        with open_events(address, interaction_id, turn_id) as stream:
            assert next_event(stream, "message.delta")["delta"] == persisted.content
            assert next_event(stream, "message.completed")["message_id"] == str(persisted.id)
        assert service.turn_timing(turn_id)["first_sse_event_ms"] == first_event


def test_coalesced_draft_before_invalid_semantics_never_becomes_admitted_truth(postgres_database):
    gates = GatedProvider()
    draft = "We can start by defining the Web application's main users."
    prefix = "{\"natural_response\": " + json.dumps(draft) + ", "
    invalid_suffix = '"semantics": {"unexpected_field": true}}'
    calls = []

    class FakeSdkTurn:
        id = "test-coalesced-turn"

        def stream(self):
            gates.entered.set()
            assert gates.release_text.wait(10), "Test did not release draft text"
            yield SimpleNamespace(
                method="item/agentMessage/delta", payload=SimpleNamespace(delta=prefix),
            )
            gates.text_published.set()
            assert gates.release_completion.wait(10), "Test did not release invalid semantics"
            yield SimpleNamespace(
                method="item/agentMessage/delta", payload=SimpleNamespace(delta=invalid_suffix),
            )
            yield SimpleNamespace(
                method="item/completed",
                payload=SimpleNamespace(item=SimpleNamespace(
                    type="agentMessage", text=prefix + invalid_suffix,
                )),
            )
            yield SimpleNamespace(
                method="turn/completed",
                payload=SimpleNamespace(turn=SimpleNamespace(status="completed", error=None)),
            )

        def interrupt(self):
            gates.release_text.set()
            gates.release_completion.set()

    def start_turn(_instruction, **options):
        calls.append(options)
        assert list(options["output_schema"]["properties"]) == ["natural_response", "semantics"]
        return FakeSdkTurn()

    @contextmanager
    def fake_codex():
        yield SimpleNamespace(thread_start=lambda **_options: SimpleNamespace(
            id="test-coalesced-thread", turn=start_turn,
        ))

    capability = CodexSdkWorkInteractionCapability(
        repository_location=".", codex_factory=fake_codex,
        coalesce_pre_work=True, timeout_seconds=15,
    )

    def production_counts():
        with postgres_database.engine.connect() as connection:
            return {
                table.name: connection.scalar(select(func.count()).select_from(table))
                for table in (product_works, *runtime_tables)
            }

    before = production_counts()
    with live_pipeline(postgres_database, capability=capability, provider=gates) as (service, _, address):
        interaction_id, turn_id = submit(address)
        assert gates.entered.wait(3)
        with open_events(address, interaction_id, turn_id) as stream:
            next_event(stream, "turn.status")
            gates.release_text.set()
            assert next_event(stream, "message.delta")["delta"] == draft
            assert not gates.release_completion.is_set()
            response_finished = await_timing(service, turn_id, "natural_response_completed_ms")
            assert response_finished["semantic_envelope_completed_ms"] is None
            assert response_finished["payload_validation_started_ms"] is None
            assert response_finished["payload_validated_ms"] is None
            during = service.get_shared_understanding(UUID(interaction_id))
            assert during.latest_assessment is None
            assert len(during.conversation_messages) == 1
            assert service.get_turn(turn_id).status is InteractionTurnStatus.PROCESSING
            gates.release_completion.set()
            failure = next_event(stream, "turn.failed")
            assert failure["code"] == "InteractionInvariantViolation"
            assert "invalid structured result" in failure["message"]
            assert "message.completed" not in stream.read().decode()

        timing = await_timing(service, turn_id, "failed_ms")
        assert timing["first_response_delta_ms"] is not None
        assert timing["failed_ms"] > timing["first_response_delta_ms"]
        assert timing["completed_ms"] is None
        assert timing["natural_response_completed_ms"] <= timing["semantic_envelope_completed_ms"]
        assert timing["semantic_envelope_completed_ms"] <= timing["provider_teardown_completed_ms"]
        assert timing["provider_teardown_completed_ms"] <= timing["payload_validation_started_ms"]
        assert timing["payload_validated_ms"] is None
        assert timing["provider_returned_ms"] is None
        assert timing["admission_started_ms"] is None
        assert timing["candidate_validated_ms"] is None
        assert timing["assessment_persisted_ms"] is None
        assert timing["final_persistence_started_ms"] is None
        assert capability.last_pipeline_evidence is None
        assert capability.last_collaboration_result is None
        assert len(calls) == 1
        failed = service.get_turn(turn_id)
        assert failed.status is InteractionTurnStatus.FAILED
        assert failed.assessment_id is None
        with postgres_database.unit_of_work() as uow:
            store = InteractionStore(uow.session)
            assert store.latest_assessment(UUID(interaction_id)) is None
            assert len(store.messages(UUID(interaction_id))) == 1
        assert production_counts() == before

        restarted = WorkInteractionService(postgres_database, capability=capability)
        try:
            assert restarted.get_turn(turn_id) == failed
            projection = restarted.get_shared_understanding(UUID(interaction_id))
            assert projection.latest_assessment is None
            assert len(projection.conversation_messages) == 1
            assert projection.conversation_messages[0].actor.value == "HUMAN"
            assert restarted.turn_timing(turn_id) is None
        finally:
            restarted.shutdown()


def test_cached_assessment_does_not_fabricate_provider_or_admission_phases(postgres_database):
    class CountingCapability(DeterministicWorkInteractionCapability):
        calls = 0

        def interpret(self, basis):
            self.calls += 1
            return super().interpret(basis)

    capability = CountingCapability()
    service = WorkInteractionService(postgres_database, capability=capability)
    try:
        interaction = service.create_interaction(human_identity="human:cache-test")
        schedule = service.schedule_turn
        service.schedule_turn = lambda _turn_id: False
        turn = service.submit_turn(
            interaction.id, "I want to build an operations management Web application.",
            human_identity="human:cache-test",
        )
        # Model an existing exact-basis assessment recovered before the queued
        # message lifecycle resumes. Reusing it must not invent new phase work.
        assessment = service.assess_current(interaction.id)
        assert capability.calls == 1
        service.schedule_turn = schedule
        assert service.schedule_turn(turn.id)
        timing = await_timing(service, turn.id, "completed_ms")
        assert capability.calls == 1
        assert timing["assessment_cache_hit_ms"] is not None
        assert timing["basis_prepared_ms"] is not None
        assert timing["final_persistence_started_ms"] is not None
        for phase in (
            "provider_started", "provider_returned", "natural_response_completed",
            "semantic_envelope_completed", "payload_validation_started", "payload_validated",
            "admission_started", "candidate_validated", "assessment_persisted",
            "first_response_delta",
        ):
            assert timing[f"{phase}_ms"] is None
        assert service.get_turn(turn.id).assessment_id == assessment.id
    finally:
        service.shutdown()


def test_changed_basis_records_admission_failure_without_success_markers(postgres_database):
    with live_pipeline(postgres_database) as (service, provider, address):
        interaction_id, turn_id = submit(address)
        assert provider.entered.wait(3)
        service.append_human_input(
            UUID(interaction_id), "Correction: build a backend system.",
            human_identity="human:test",
        )
        with open_events(address, interaction_id, turn_id) as stream:
            next_event(stream, "turn.status")
            provider.release_text.set()
            provider.release_completion.set()
            failure = next_event(stream, "turn.failed")
            assert "basis is stale" in failure["message"]
        timing = await_timing(service, turn_id, "failed_ms")
        assert timing["provider_returned_ms"] is not None
        assert timing["admission_started_ms"] is not None
        assert timing["candidate_validated_ms"] is None
        assert timing["assessment_persisted_ms"] is None
        assert timing["final_persistence_started_ms"] is None
        assert timing["completed_ms"] is None
        assert service.get_shared_understanding(UUID(interaction_id)).latest_assessment is None
