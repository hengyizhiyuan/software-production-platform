from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import re
from threading import Event
import time
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select, text

from spg.api import create_http_application
from spg.domain.conversation import ConversationTurnIntent
from spg.application.interaction import (
    DeterministicWorkInteractionCapability,
    WorkInteractionService,
)
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InteractionTurnStatus,
    InterpretationMeaning,
    InterpretationMeaningKind,
    WorkAdmissionReadinessStatus,
)
from spg.domain.runtime_activation import RuntimeActivationProjection, RuntimeActivationState
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_schema import (
    interaction_assessments,
    interaction_records,
    interaction_messages,
    interaction_turns,
    product_interactions,
    product_works,
    work_reality_revisions,
)
from spg.providers.codex_interaction import CodexSdkWorkInteractionCapability


pytestmark = pytest.mark.postgresql
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALL_TABLE_NAMES = {table.name for table in (*product_tables, *runtime_tables)}


class _ProgressiveCapability:
    def __init__(self) -> None:
        self.calls = 0

    def interpret(
        self, basis: InteractionInterpretationInput
    ) -> InteractionAssessmentCandidate:
        self.calls += 1
        latest = basis.records[-1]
        if len(basis.records) == 1:
            return InteractionAssessmentCandidate(
                interpreted_motive="Improve execution visibility",
                current_requests=(latest.content,),
                unresolved_material_questions=(
                    "What outcome should the developer be able to observe?",
                ),
                meanings=(
                    InterpretationMeaning(
                        kind=InterpretationMeaningKind.REQUEST,
                        statement="Improve execution visibility",
                        source_record_ids=(latest.id,),
                        confidence=0.82,
                        rationale="The Human describes an improvement direction.",
                        clarification_required=True,
                    ),
                ),
                natural_response="What should a developer be able to see?",
                provider_identity="test:progressive",
            )
        return InteractionAssessmentCandidate(
            interpreted_motive="Improve execution visibility",
            desired_outcome="Developers can see current phase, progress, and blockers.",
            candidate_context=("Automatic execution can be long-running.",),
            candidate_constraints=("Do not redesign the whole UI.",),
            current_requests=(latest.content,),
            meanings=(
                InterpretationMeaning(
                    kind=InterpretationMeaningKind.CONSTRAINT,
                    statement="Do not redesign the whole UI.",
                    source_record_ids=(latest.id,),
                    confidence=0.98,
                    rationale="Explicit negative constraint.",
                ),
            ),
            natural_response="The Motive and outcome are now clear enough to form Work.",
            provider_identity="test:progressive",
        )


class _BlockingStreamingCapability:
    def __init__(self) -> None:
        self.delta_published = Event()
        self.release = Event()

    def interpret(self, _basis: InteractionInterpretationInput):
        raise AssertionError("stream-aware service must use interpret_stream")

    def interpret_stream(
        self,
        basis: InteractionInterpretationInput,
        *,
        on_response_delta,
    ) -> InteractionAssessmentCandidate:
        on_response_delta("I am mapping the design path now. ")
        self.delta_published.set()
        if not self.release.wait(timeout=5):
            raise RuntimeError("test did not release streaming capability")
        return InteractionAssessmentCandidate(
            interpreted_motive=basis.records[-1].content,
            unresolved_material_questions=("Who is the primary operator?",),
            natural_response="I am mapping the design path now. Who is the primary operator?",
            provider_identity="test:streaming",
        )


class _NeverCalledWorkService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_works(self, *args, **kwargs) -> tuple[()]:
        return ()


class _FailingCapability:
    def interpret(self, _basis: InteractionInterpretationInput):
        raise InteractionInvariantViolation("provider unavailable for focused test")


class _NoopDriver:
    def resume_safely_eligible_works(self) -> tuple[()]:
        return ()

    def shutdown(self) -> None:
        return None


class _NoopOrchestrator(_NoopDriver):
    def schedule(self, _work_id: UUID) -> bool:
        return False


class _RuntimeActivation:
    def project(self) -> RuntimeActivationProjection:
        return RuntimeActivationProjection(
            state=RuntimeActivationState.ACTIVE_AT_TRUSTED_BASELINE,
            active_application_revision="test",
            current_trusted_baseline_revision="test",
            reason="test",
        )


def _migration_config(database: Database) -> Config:
    os.environ["SPG_DATABASE_URL"] = database.engine.url.render_as_string(
        hide_password=False
    )
    return Config(PROJECT_ROOT / "alembic.ini")


def _truncate(database: Database) -> None:
    names = ", ".join(f'"{name}"' for name in sorted(ALL_TABLE_NAMES))
    with database.engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def clean_wic_schema(postgres_database: Database) -> Iterator[None]:
    previous = os.environ.get("SPG_DATABASE_URL")
    command.upgrade(_migration_config(postgres_database), "head")
    _truncate(postgres_database)
    try:
        yield
    finally:
        _truncate(postgres_database)
        if previous is None:
            os.environ.pop("SPG_DATABASE_URL", None)
        else:
            os.environ["SPG_DATABASE_URL"] = previous


def _count(database: Database, table) -> int:
    with database.engine.connect() as connection:
        return int(connection.scalar(select(func.count()).select_from(table)) or 0)


def _wait_for_turn(
    service: WorkInteractionService,
    turn_id: UUID,
    *,
    timeout: float = 3,
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        turn = service.get_turn(turn_id)
        if turn.status in {
            InteractionTurnStatus.COMPLETED,
            InteractionTurnStatus.FAILED,
        }:
            return turn
        time.sleep(0.02)
    pytest.fail(f"Interaction Turn did not reach a terminal state: {turn_id}")


def _wait_for_turn_and_observe_stream(
    service: WorkInteractionService,
    turn_id: UUID,
    *,
    timeout: float,
):
    deadline = time.monotonic() + timeout
    offset = 0
    streamed = ""
    delta_before_terminal = False
    while time.monotonic() < deadline:
        turn = service.get_turn(turn_id)
        delta, offset = service.turn_response_delta(turn_id, offset)
        if delta:
            streamed += delta
            if turn.status not in {
                InteractionTurnStatus.COMPLETED,
                InteractionTurnStatus.FAILED,
            }:
                delta_before_terminal = True
        if turn.status in {
            InteractionTurnStatus.COMPLETED,
            InteractionTurnStatus.FAILED,
        }:
            return turn, streamed, delta_before_terminal
        time.sleep(0.01)
    pytest.fail(f"Interaction Turn did not reach a terminal state: {turn_id}")


_SENSITIVE_FAILURE_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(postgres(?:ql)?(?:\+\w+)?://)[^@\s]+@"),
    re.compile(r"(?i)\b(?:thread|turn|req)_[A-Za-z0-9_-]+\b"),
    re.compile(r"(?i)([A-Z]:\\Users\\)[^\\\s]+"),
    re.compile(r"(?i)(/home/)[^/\s]+"),
)


def _sanitized_failure_text(value: str | None) -> str | None:
    if value is None:
        return None
    sanitized = " ".join(value.splitlines())
    for pattern in _SENSITIVE_FAILURE_PATTERNS:
        if "postgres" in pattern.pattern:
            sanitized = pattern.sub(r"\1<redacted>@", sanitized)
        elif "Users" in pattern.pattern or "/home/" in pattern.pattern:
            sanitized = pattern.sub(r"\1<user>", sanitized)
        elif "thread" in pattern.pattern:
            sanitized = pattern.sub("<redacted-provider-id>", sanitized)
        else:
            sanitized = pattern.sub(r"\1<redacted>", sanitized)
    return sanitized[:2000]


def _sanitized_turn_failure_report(turn) -> dict[str, str | None]:
    if turn.status is not InteractionTurnStatus.FAILED:
        raise ValueError("Failure evidence can only be produced for a FAILED Turn")
    return {
        "evidence_kind": "HUMAN_WATT_REAL_PROVIDER_TURN_FAILURE",
        "turn_id": str(turn.id),
        "status": turn.status.value,
        "failure_code": _sanitized_failure_text(turn.failure_code),
        "failure_message": _sanitized_failure_text(turn.failure_message),
        "created_at": turn.created_at.isoformat(),
        "started_at": None if turn.started_at is None else turn.started_at.isoformat(),
        "completed_at": (
            None if turn.completed_at is None else turn.completed_at.isoformat()
        ),
        "updated_at": turn.updated_at.isoformat(),
    }


def _preserve_turn_failure_report(turn, destination: Path) -> dict[str, str | None]:
    report = _sanitized_turn_failure_report(turn)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return report


def _fail_with_preserved_turn_evidence(turn) -> None:
    configured = os.environ.get("SPG_REAL_PROVIDER_EVIDENCE_PATH")
    destination = (
        Path(configured)
        if configured
        else PROJECT_ROOT
        / ".spg"
        / "validation-evidence"
        / f"human-watt-provider-failure-{turn.id}.json"
    )
    report = _preserve_turn_failure_report(turn, destination)
    pytest.fail(
        "Real Human-Watt Provider proof failed. "
        f"Sanitized evidence: {destination}\n"
        + json.dumps(report, ensure_ascii=False, sort_keys=True),
        pytrace=False,
    )

def _preserve_real_provider_success_report(
    turn,
    projection,
    destination: Path,
    *,
    streamed_response: str,
    delta_before_terminal: bool,
) -> None:
    report = {
        "evidence_kind": "HUMAN_WATT_REAL_PROVIDER_PROOF",
        "input": "我想做一个运营管理平台。",
        "turn_id": str(turn.id),
        "status": turn.status.value,
        "provider_model": os.environ.get("SPG_WIC_PROVIDER_MODEL"),
        "design_schema_identity": projection.selected_design_schema_identity,
        "design_schema_version": projection.selected_design_schema_version,
        "design_stage": projection.design_stage,
        "design_next_focus": projection.design_next_focus,
        "design_focus_rationale": projection.design_focus_rationale,
        "design_facilitation_strategy": projection.design_facilitation_strategy,
        "incremental_response_observed": bool(streamed_response),
        "delta_observed_before_terminal": delta_before_terminal,
        "stream_matches_persisted_response": (
            projection.conversation_messages[-1].content == streamed_response
        ),
        "progressive_disclosure": not (
            "设计路径：" in projection.conversation_messages[-1].content
            or "Design path:" in projection.conversation_messages[-1].content
        ),
        "question_count": (
            projection.conversation_messages[-1].content.count("?")
            + projection.conversation_messages[-1].content.count("？")
        ),
        "conversation_message_count": len(projection.conversation_messages),
        "created_at": turn.created_at.isoformat(),
        "started_at": None if turn.started_at is None else turn.started_at.isoformat(),
        "completed_at": (
            None if turn.completed_at is None else turn.completed_at.isoformat()
        ),
        "updated_at": turn.updated_at.isoformat(),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


_DEFAULT_RESPONSE_METADATA_MARKERS = (
    "设计方式：",
    "当前阶段：",
    "为什么先处理：",
    "下一个设计动作：",
    "Design approach:",
    "Current stage:",
    "Why now:",
    "Next design action:",
    "Facilitation strategy:",
    "watt:guided-design:",
)


def _assert_default_response_quality(response: str) -> None:
    paragraphs = [item.strip() for item in response.split("\n\n") if item.strip()]
    assert response.strip() == response
    assert 1 <= len(paragraphs) <= 5
    assert len(response) <= 900
    assert response.count("?") + response.count("？") <= 1
    for marker in _DEFAULT_RESPONSE_METADATA_MARKERS:
        assert marker not in response


def _run_real_human_watt_turn(
    service: WorkInteractionService,
    interaction_id: UUID,
    content: str,
    *,
    timeout: float = 320,
) -> tuple[str, object, bool]:
    submitted = service.submit_turn(
        interaction_id,
        content,
        human_identity="human:response-quality-proof",
    )
    completed, streamed_response, delta_before_terminal = (
        _wait_for_turn_and_observe_stream(service, submitted.id, timeout=timeout)
    )
    if completed.status is InteractionTurnStatus.FAILED:
        _fail_with_preserved_turn_evidence(completed)
    assert completed.status is InteractionTurnStatus.COMPLETED
    projection = service.get_shared_understanding(interaction_id)
    assert streamed_response
    assert delta_before_terminal is True
    assert projection.conversation_messages[-1].content == streamed_response
    return streamed_response, projection, delta_before_terminal


def test_pre_work_progression_is_reconstructable_and_never_creates_work(
    postgres_database: Database,
) -> None:
    capability = _ProgressiveCapability()
    service = WorkInteractionService(postgres_database, capability=capability)
    interaction = service.create_interaction(human_identity="human:test")
    assert _count(postgres_database, product_interactions) == 1
    assert _count(postgres_database, product_works) == 0

    first = service.append_and_assess(
        interaction.id,
        "I am exploring better execution visibility.",
        human_identity="human:test",
    )
    assert first.readiness is not None
    assert first.readiness.status is WorkAdmissionReadinessStatus.NOT_READY
    assert first.governed_work_id is None
    assert _count(postgres_database, product_works) == 0

    second = service.append_and_assess(
        interaction.id,
        "Developers should see phase, progress, and blockers. Do not redesign the whole UI.",
        human_identity="human:test",
    )
    assert second.readiness is not None
    assert second.readiness.status is WorkAdmissionReadinessStatus.READY
    assert second.candidate_constraints == ("Do not redesign the whole UI.",)
    assert second.human_said[0].startswith("I am exploring")
    assert second.interpreted_motive == "Improve execution visibility"
    assert second.governed_work_id is None
    assert _count(postgres_database, product_works) == 0
    assert _count(postgres_database, work_reality_revisions) == 0

    reconstructed = WorkInteractionService(
        postgres_database, capability=capability
    ).get_shared_understanding(interaction.id)
    assert reconstructed == second
    assert capability.calls == 2
    assert service.assess_current(interaction.id).id == second.latest_assessment.id
    assert capability.calls == 2


def test_idle_conversation_is_valid_interaction_but_not_ready_or_work(
    postgres_database: Database,
) -> None:
    service = WorkInteractionService(
        postgres_database,
        capability=DeterministicWorkInteractionCapability(),
    )
    interaction = service.create_interaction(human_identity="human:test")
    projection = service.append_and_assess(
        interaction.id,
        "你好",
        human_identity="human:test",
    )
    assert projection.readiness is not None
    assert projection.readiness.status is WorkAdmissionReadinessStatus.NOT_READY
    assert projection.interpreted_motive is None
    assert projection.governed_work_id is None
    assert _count(postgres_database, product_works) == 0


def test_interrupted_recovery_and_stale_provider_result_fail_closed(
    postgres_database: Database,
) -> None:
    capability = _ProgressiveCapability()
    service = WorkInteractionService(postgres_database, capability=capability)
    interaction = service.create_interaction(human_identity="human:test")
    service.append_human_input(
        interaction.id,
        "I am exploring better execution visibility.",
        human_identity="human:test",
    )
    pending = service.get_shared_understanding(interaction.id)
    assert pending.latest_assessment is None
    assert service.pending_assessment_interactions() == (interaction.id,)
    recovered = service.recover_pending_assessments()
    assert len(recovered) == 1
    assert service.pending_assessment_interactions() == ()
    assert _count(postgres_database, product_works) == 0

    old_basis = recovered[0].basis_fingerprint
    service.append_human_input(
        interaction.id,
        "Developers should see current phase and blockers.",
        human_identity="human:test",
    )
    with pytest.raises(InteractionInvariantViolation, match="stale"):
        service.admit_candidate(
            interaction.id,
            basis_fingerprint=old_basis,
            candidate=InteractionAssessmentCandidate(
                interpreted_motive="stale",
                desired_outcome="stale",
                natural_response="stale",
                provider_identity="test:stale",
            ),
        )
    assert service.get_shared_understanding(interaction.id).latest_assessment is None
    assert _count(postgres_database, interaction_assessments) == 1
    assert _count(postgres_database, product_works) == 0


def test_interaction_api_keeps_ready_assessment_pre_work(
    postgres_database: Database,
) -> None:
    interaction_service = WorkInteractionService(
        postgres_database,
        capability=_ProgressiveCapability(),
    )
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=_NeverCalledWorkService(postgres_database),
            orchestrator=_NoopOrchestrator(),
            steering_driver=_NoopDriver(),
            runtime_activation=_RuntimeActivation(),
            interaction_service=interaction_service,
        ),
        raise_server_exceptions=False,
    )
    with client:
        created = client.post(
            "/api/interactions", json={"human_identity": "human:test"}
        )
        assert created.status_code == 201
        interaction_id = created.json()["interaction_id"]
        for content in (
            "I am exploring better execution visibility.",
            "Developers should see phase, progress, and blockers. Do not redesign the whole UI.",
        ):
            response = client.post(
                f"/api/interactions/{interaction_id}/records",
                json={"content": content, "human_identity": "human:test"},
            )
            assert response.status_code == 201
        payload = response.json()
        assert payload["readiness"]["status"] == "READY"
        assert payload["governed_work_id"] is None
        assert len(payload["records"]) == 2
        refreshed = client.get(
            f"/api/interactions/{interaction_id}/shared-understanding"
        )
        assert refreshed.json() == payload
        assert _count(postgres_database, product_works) == 0
        assert _count(postgres_database, interaction_records) == 2


def test_async_turn_persists_history_schema_guidance_and_restarts(
    postgres_database: Database,
) -> None:
    service = WorkInteractionService(
        postgres_database,
        capability=DeterministicWorkInteractionCapability(),
    )
    interaction = service.create_interaction(human_identity="human:test")
    turn = service.submit_turn(
        interaction.id,
        "我想做一个运营管理平台。",
        human_identity="human:test",
    )
    assert turn.status in {
        InteractionTurnStatus.RECEIVED,
        InteractionTurnStatus.PROCESSING,
        InteractionTurnStatus.COMPLETED,
    }
    completed = _wait_for_turn(service, turn.id)
    assert completed.status is InteractionTurnStatus.COMPLETED
    projection = service.get_shared_understanding(interaction.id)
    assert [message.actor.value for message in projection.conversation_messages] == [
        "HUMAN",
        "WATT",
    ]
    assert projection.conversation_messages[1].interpretation_assessment_id
    assert projection.selected_design_schema_identity == (
        "watt:guided-design:general-product-system"
    )
    assert projection.selected_design_schema_version == "0.1"
    assert projection.design_stage == "Motive, users, and problem"
    assert projection.design_next_focus
    assert "General Product/System Design" in (
        projection.design_progress_narrative or ""
    )
    response = projection.conversation_messages[1].content
    assert response == projection.latest_assessment.natural_response
    assert "Design approach:" not in response
    assert "Current stage:" not in response
    assert "Next design action:" not in response
    assert "Design path:" not in response
    assert _count(postgres_database, interaction_turns) == 1
    assert _count(postgres_database, interaction_messages) == 2
    service.shutdown()

    restarted = WorkInteractionService(
        postgres_database,
        capability=DeterministicWorkInteractionCapability(),
    )
    reconstructed = restarted.get_shared_understanding(interaction.id)
    assert reconstructed.conversation_messages == projection.conversation_messages
    assert reconstructed.turns == projection.turns
    assert reconstructed.design_progress_narrative == (
        projection.design_progress_narrative
    )
    restarted.shutdown()


def test_async_turn_projects_real_delta_before_completion_and_persists_final_message(
    postgres_database: Database,
) -> None:
    capability = _BlockingStreamingCapability()
    service = WorkInteractionService(postgres_database, capability=capability)
    interaction = service.create_interaction(human_identity="human:test")
    submitted = service.submit_turn(
        interaction.id,
        "Design an operations management platform.",
        human_identity="human:test",
    )

    assert capability.delta_published.wait(timeout=2)
    processing = service.get_turn(submitted.id)
    delta, offset = service.turn_response_delta(submitted.id, 0)
    assert processing.status is InteractionTurnStatus.PROCESSING
    assert delta == "I am mapping the design path now. "
    assert offset == len(delta)

    capability.release.set()
    completed = _wait_for_turn(service, submitted.id)
    assert completed.status is InteractionTurnStatus.COMPLETED
    projection = service.get_shared_understanding(interaction.id)
    final_response = projection.conversation_messages[-1].content
    assert service.turn_response_delta(submitted.id, 0)[0] == final_response
    assert final_response.startswith(delta)
    assert final_response == (
        "I am mapping the design path now. Who is the primary operator?"
    )
    assert "Design path:" not in final_response
    assert _count(postgres_database, product_works) == 0
    service.shutdown()


def test_async_turn_failure_is_persisted_without_work(
    postgres_database: Database,
) -> None:
    service = WorkInteractionService(
        postgres_database,
        capability=_FailingCapability(),
    )
    interaction = service.create_interaction(human_identity="human:test")
    submitted = service.submit_turn(
        interaction.id,
        "Explore one bounded design question.",
        human_identity="human:test",
    )
    failed = _wait_for_turn(service, submitted.id)
    assert failed.status is InteractionTurnStatus.FAILED
    assert failed.failure_code == "InteractionInvariantViolation"
    assert "provider unavailable" in (failed.failure_message or "")
    projection = service.get_shared_understanding(interaction.id)
    assert projection.conversation_messages[0].processing_status is (
        InteractionTurnStatus.FAILED
    )
    assert projection.latest_assessment is None
    assert _count(postgres_database, product_works) == 0
    service.shutdown()


def test_failed_turn_evidence_is_sanitized_and_written_before_cleanup(
    postgres_database: Database,
    tmp_path: Path,
) -> None:
    service = WorkInteractionService(
        postgres_database,
        capability=_FailingCapability(),
    )
    interaction = service.create_interaction(human_identity="human:test")
    submitted = service.submit_turn(
        interaction.id,
        "Exercise failure evidence extraction.",
        human_identity="human:test",
    )
    failed = _wait_for_turn(service, submitted.id)
    synthetic_sensitive_failure = failed.model_copy(
        update={
            "failure_message": (
                "Authorization: Bearer sample-token password=sample-password "
                "thread_sample req_sample C:\\Users\\sample-user\\.codex\\auth.json"
            )
        }
    )
    destination = tmp_path / "provider-failure.json"
    report = _preserve_turn_failure_report(
        synthetic_sensitive_failure,
        destination,
    )
    persisted = json.loads(destination.read_text(encoding="utf-8"))

    assert persisted == report
    assert persisted["turn_id"] == str(failed.id)
    assert persisted["status"] == "FAILED"
    assert persisted["failure_code"] == "InteractionInvariantViolation"
    assert persisted["created_at"]
    assert persisted["started_at"]
    assert persisted["completed_at"]
    assert persisted["updated_at"]
    rendered = destination.read_text(encoding="utf-8")
    assert "sample-token" not in rendered
    assert "sample-password" not in rendered
    assert "sample-user" not in rendered
    assert "thread_sample" not in rendered
    assert "req_sample" not in rendered
    assert "provider_identity" not in persisted
    assert "model_identity" not in persisted
    service.shutdown()


def test_async_http_turn_streams_persisted_status_and_response(
    postgres_database: Database,
) -> None:
    interaction_service = WorkInteractionService(
        postgres_database,
        capability=DeterministicWorkInteractionCapability(),
    )
    client = TestClient(
        create_http_application(
            application=object(),
            database=postgres_database,
            work_service=_NeverCalledWorkService(postgres_database),
            orchestrator=_NoopOrchestrator(),
            steering_driver=_NoopDriver(),
            runtime_activation=_RuntimeActivation(),
            interaction_service=interaction_service,
        ),
        raise_server_exceptions=False,
    )
    with client:
        created = client.post(
            "/api/interactions", json={"human_identity": "human:test"}
        ).json()
        submitted = client.post(
            f"/api/interactions/{created['interaction_id']}/turns",
            json={
                "content": "我想做一个运营管理平台。",
                "human_identity": "human:test",
            },
        )
        assert submitted.status_code == 202
        turn_id = submitted.json()["turn_id"]
        streamed = client.get(
            f"/api/interactions/{created['interaction_id']}/turns/{turn_id}/events"
        )
        assert streamed.status_code == 200
        assert "event: turn.status" in streamed.text
        assert "event: message.delta" in streamed.text
        assert "event: message.completed" in streamed.text
        deltas = [
            json.loads(line.removeprefix("data: "))["delta"]
            for line in streamed.text.splitlines()
            if line.startswith("data: ") and '"delta"' in line
        ]
        projection = client.get(
            f"/api/interactions/{created['interaction_id']}"
        ).json()
        assert "".join(deltas) == projection["conversation_messages"][-1]["content"]


@pytest.mark.real_codex
@pytest.mark.skipif(
    os.environ.get("SPG_RUN_REAL_HUMAN_WATT_COLLABORATION") != "1",
    reason="explicit one-Turn Human–Watt Provider proof authorization is required",
)
def test_real_provider_guides_mandatory_human_watt_scenario_in_one_turn(
    postgres_database: Database,
) -> None:
    service = WorkInteractionService(
        postgres_database,
        capability=CodexSdkWorkInteractionCapability(
            repository_location=os.environ.get(
                "SPG_WIC_PROVIDER_PROOF_ROOT",
                str(PROJECT_ROOT),
            ),
            model=os.environ.get("SPG_WIC_PROVIDER_MODEL"),
            timeout_seconds=300,
        ),
    )
    try:
        interaction = service.create_interaction(
            human_identity="human:collaboration-proof"
        )
        submitted = service.submit_turn(
            interaction.id,
            "我想做一个运营管理平台。",
            human_identity="human:collaboration-proof",
        )
        completed, streamed_response, delta_before_terminal = (
            _wait_for_turn_and_observe_stream(
                service,
                submitted.id,
                timeout=320,
            )
        )
        if completed.status is InteractionTurnStatus.FAILED:
            _fail_with_preserved_turn_evidence(completed)
        assert completed.status is InteractionTurnStatus.COMPLETED

        projection = service.get_shared_understanding(interaction.id)
        assert projection.latest_assessment is not None
        assert projection.latest_assessment.provider_identity.startswith(
            "codex-sdk:semantic-thread:"
        )
        assert projection.selected_design_schema_identity == (
            "watt:guided-design:general-product-system"
        )
        assert projection.selected_design_schema_version == "0.1"
        assert projection.design_stage == "Motive, users, and problem"
        assert projection.design_next_focus
        assert projection.design_focus_rationale
        assert projection.design_facilitation_strategy
        assert streamed_response
        assert delta_before_terminal is True
        final_response = projection.conversation_messages[-1].content
        assert final_response == streamed_response
        assert "设计方式：" not in final_response
        assert "Design approach:" not in final_response
        assert "设计路径：" not in final_response and "Design path:" not in final_response
        assert "当前阶段：" not in final_response and "Current stage:" not in final_response
        assert "下一个设计动作：" not in final_response and "Next design action:" not in final_response
        assert streamed_response.count("?") + streamed_response.count("？") <= 1
        assert _count(postgres_database, product_works) == 0
        assert _count(postgres_database, work_reality_revisions) == 0
        for table in runtime_tables:
            assert _count(postgres_database, table) == 0, table.name
        evidence_path = os.environ.get("SPG_REAL_PROVIDER_EVIDENCE_PATH")
        if evidence_path:
            _preserve_real_provider_success_report(
                completed,
                projection,
                Path(evidence_path),
                streamed_response=streamed_response,
                delta_before_terminal=delta_before_terminal,
            )
    finally:
        service.shutdown()


@pytest.mark.real_codex
@pytest.mark.skipif(
    os.environ.get("SPG_RUN_REAL_HUMAN_WATT_V22") != "1",
    reason="explicit Human-Watt v2.2 real response-quality proof is required",
)
def test_real_provider_v22_response_quality_scenarios(
    postgres_database: Database,
) -> None:
    service = WorkInteractionService(
        postgres_database,
        capability=CodexSdkWorkInteractionCapability(
            repository_location=os.environ.get(
                "SPG_WIC_PROVIDER_PROOF_ROOT",
                str(PROJECT_ROOT),
            ),
            model="gpt-5.6-sol",
            timeout_seconds=300,
        ),
    )
    try:
        new_goal = service.create_interaction(
            human_identity="human:response-quality-proof"
        )
        response_a, projection_a, _ = _run_real_human_watt_turn(
            service,
            new_goal.id,
            "我想做一个运营管理平台。",
        )
        _assert_default_response_quality(response_a)
        assert any(marker in response_a for marker in ("先", "建议", "可以"))

        known_context = service.create_interaction(
            human_identity="human:response-quality-proof"
        )
        service.append_human_input(
            known_context.id,
            (
                "主要用于推广 Watt，包括技术公众号、小红书和直播，"
                "目标受众是个人开发者和小型开发工作室。"
            ),
            human_identity="human:response-quality-proof",
        )
        response_b, projection_b, _ = _run_real_human_watt_turn(
            service,
            known_context.id,
            "请基于这些已知信息继续推进设计。",
        )
        _assert_default_response_quality(response_b)
        assert any(
            fact in response_b
            for fact in ("个人开发者", "小型开发工作室", "公众号", "小红书", "直播")
        )
        assert not any(
            repeated_question in response_b
            for repeated_question in ("面向谁", "目标受众是谁", "谁是目标用户")
        )

        direct_question = service.create_interaction(
            human_identity="human:response-quality-proof"
        )
        response_c, projection_c, _ = _run_real_human_watt_turn(
            service,
            direct_question.id,
            "设计方案的文档会输出到哪里？",
        )
        _assert_default_response_quality(response_c)
        first_paragraph = response_c.split("\n\n", 1)[0]
        assert "文档" in first_paragraph
        assert any(marker in first_paragraph for marker in ("不会", "未", "没有"))
        assert not any(marker in response_c for marker in ("方法论", "设计路径"))

        detail_request = service.create_interaction(
            human_identity="human:response-quality-proof"
        )
        response_d, projection_d, _ = _run_real_human_watt_turn(
            service,
            detail_request.id,
            "把整个设计方法和后续步骤详细给我讲一下。",
        )
        assert len(response_d) > len(response_c)
        assert sum(
            topic in response_d
            for topic in ("用户", "场景", "边界", "能力", "架构", "验证", "生产")
        ) >= 3

        for projection in (projection_a, projection_b, projection_c, projection_d):
            assert projection.latest_assessment is not None
            assert projection.latest_assessment.provider_identity.startswith(
                "codex-sdk:semantic-thread:"
            )
        assert _count(postgres_database, product_works) == 0
        assert _count(postgres_database, work_reality_revisions) == 0
        for table in runtime_tables:
            assert _count(postgres_database, table) == 0, table.name

        report = {
            "evidence_kind": "HUMAN_WATT_RESPONSE_QUALITY_V22_REAL_PROVIDER_PROOF",
            "provider_model": "gpt-5.6-sol",
            "provider_threads": 8,
            "provider_turns": 8,
            "streaming_match": True,
            "work_and_production_facts": 0,
            "responses": {
                "new_design_goal": response_a,
                "known_context_reuse": response_b,
                "direct_question": response_c,
                "explicit_detail_request": response_d,
            },
        }
        destination = Path(
            os.environ.get(
                "SPG_REAL_PROVIDER_V22_EVIDENCE_PATH",
                PROJECT_ROOT
                / ".spg"
                / "validation-evidence"
                / "human-watt-collaboration-v2.2-real-provider-20260908.json",
            )
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
        print("HUMAN_WATT_V22_REAL_PROOF", json.dumps(report, ensure_ascii=False))
    finally:
        service.shutdown()


@pytest.mark.real_codex
@pytest.mark.skipif(
    os.environ.get("SPG_RUN_REAL_CONVERSATION_INTELLIGENCE") != "1",
    reason="explicit Conversation Intelligence real Provider proof is required",
)
def test_real_provider_conversation_intelligence_mandatory_scenarios(
    postgres_database: Database,
) -> None:
    capability = CodexSdkWorkInteractionCapability(
        repository_location=os.environ.get(
            "SPG_WIC_PROVIDER_PROOF_ROOT",
            str(PROJECT_ROOT),
        ),
        model=os.environ.get("SPG_WIC_PROVIDER_MODEL", "gpt-5.6-sol"),
        conversation_model=os.environ.get(
            "SPG_CONVERSATION_PROVIDER_MODEL",
            "gpt-5.6-sol",
        ),
        timeout_seconds=300,
    )
    service = WorkInteractionService(postgres_database, capability=capability)
    pipeline_runs: list[dict[str, object]] = []

    def execute(
        name: str,
        message: str,
        expected_intent: ConversationTurnIntent,
        *,
        context: str | None = None,
    ) -> tuple[str, object]:
        interaction = service.create_interaction(
            human_identity="human:conversation-intelligence-proof"
        )
        if context is not None:
            service.append_human_input(
                interaction.id,
                context,
                human_identity="human:conversation-intelligence-proof",
            )
        response, projection, delta_before_terminal = _run_real_human_watt_turn(
            service,
            interaction.id,
            message,
            timeout=650,
        )
        assert delta_before_terminal is True
        assert capability.last_collaboration_result is not None
        assert capability.last_collaboration_result.turn_intent is expected_intent
        assert capability.last_pipeline_evidence is not None
        evidence = capability.last_pipeline_evidence
        pipeline_runs.append(
            {
                "scenario": name,
                "turn_intent": expected_intent.value,
                "semantic_thread_id": evidence.semantic_thread_id,
                "semantic_turn_id": evidence.semantic_turn_id,
                "conversation_thread_id": evidence.conversation_thread_id,
                "conversation_turn_id": evidence.conversation_turn_id,
                "response": response,
            }
        )
        return response, projection

    try:
        response_a, projection_a = execute(
            "vague_new_goal",
            "我想做一个运营管理平台。",
            ConversationTurnIntent.NEW_GOAL,
        )
        _assert_default_response_quality(response_a)
        assert any(marker in response_a for marker in ("先", "建议", "可以"))

        response_b, projection_b = execute(
            "known_context_reuse",
            "请基于这些已知信息继续推进设计。",
            ConversationTurnIntent.CONTINUE_CURRENT_WORK,
            context=(
                "主要用于推广 Watt，包括技术公众号、小红书和直播，"
                "目标受众是个人开发者和小型开发工作室。"
            ),
        )
        _assert_default_response_quality(response_b)
        assert any(
            fact in response_b
            for fact in ("个人开发者", "小型开发工作室", "公众号", "小红书", "直播")
        )
        assert not any(
            repeated in response_b
            for repeated in ("面向谁", "目标受众是谁", "谁是目标用户")
        )

        response_c, projection_c = execute(
            "direct_question",
            "设计方案的文档会输出到哪里？",
            ConversationTurnIntent.DIRECT_QUESTION,
        )
        _assert_default_response_quality(response_c)
        first_paragraph = response_c.split("\n\n", 1)[0]
        assert "文档" in first_paragraph
        assert any(marker in first_paragraph for marker in ("不会", "未", "没有"))

        response_d, projection_d = execute(
            "explicit_detail_request",
            "把整个设计方法和后续步骤详细讲一下。",
            ConversationTurnIntent.REQUEST_DETAIL,
        )
        assert len(response_d) > len(response_c)
        assert sum(
            topic in response_d
            for topic in ("用户", "场景", "边界", "能力", "架构", "验证", "生产")
        ) >= 3

        response_e, projection_e = execute(
            "correction",
            "不对，首批用户其实是个人开发者，不是大型企业。请按这个修正。",
            ConversationTurnIntent.CORRECTION,
            context="首批目标用户是大型企业。",
        )
        _assert_default_response_quality(response_e)
        assert "个人开发者" in response_e
        assert any(marker in response_e for marker in ("明白", "修正", "按", "以"))

        response_f, projection_f = execute(
            "recommendation",
            "你建议我们下一步先设计哪个部分？",
            ConversationTurnIntent.REQUEST_RECOMMENDATION,
            context="目标用户是个人开发者，首要问题是看不清自动任务状态。",
        )
        _assert_default_response_quality(response_f)
        assert any(marker in response_f.split("\n\n", 1)[0] for marker in ("建议", "推荐", "先", "优先"))

        all_ids = {
            str(value)
            for item in pipeline_runs
            for key, value in item.items()
            if key.endswith("_id")
        }
        assert len(pipeline_runs) == 6
        assert len(all_ids) == 24
        for projection in (
            projection_a,
            projection_b,
            projection_c,
            projection_d,
            projection_e,
            projection_f,
        ):
            assert projection.latest_assessment is not None
            assert projection.latest_assessment.provider_identity.startswith(
                "codex-sdk:semantic-thread:"
            )
        assert _count(postgres_database, product_works) == 0
        assert _count(postgres_database, work_reality_revisions) == 0
        for table in runtime_tables:
            assert _count(postgres_database, table) == 0, table.name

        report = {
            "evidence_kind": "HUMAN_WATT_CONVERSATION_INTELLIGENCE_REAL_PROVIDER_PROOF",
            "provider_model": capability.model,
            "scenarios": pipeline_runs,
            "provider_threads": 12,
            "provider_turns": 12,
            "streaming_match": True,
            "work_and_production_facts": 0,
        }
        destination = Path(
            os.environ.get(
                "SPG_REAL_CONVERSATION_INTELLIGENCE_EVIDENCE_PATH",
                PROJECT_ROOT
                / ".spg"
                / "validation-evidence"
                / "human-watt-conversation-intelligence-real-provider.json",
            )
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
        print(
            "HUMAN_WATT_CONVERSATION_INTELLIGENCE_REAL_PROOF",
            json.dumps(report, ensure_ascii=False),
        )
    finally:
        service.shutdown()


@pytest.mark.real_codex
@pytest.mark.skipif(
    os.environ.get("SPG_RUN_REAL_CONVERSATION_INTELLIGENCE_SINGLE") != "1",
    reason="explicit single-scenario Conversation Intelligence proof is required",
)
def test_real_provider_conversation_intelligence_single_scenario(
    postgres_database: Database,
) -> None:
    message = os.environ["SPG_CONVERSATION_INTELLIGENCE_MESSAGE"]
    context = os.environ.get("SPG_CONVERSATION_INTELLIGENCE_CONTEXT")
    expected_intent = ConversationTurnIntent(
        os.environ["SPG_CONVERSATION_INTELLIGENCE_EXPECTED_INTENT"]
    )
    capability = CodexSdkWorkInteractionCapability(
        repository_location=os.environ.get(
            "SPG_WIC_PROVIDER_PROOF_ROOT",
            str(PROJECT_ROOT),
        ),
        model=os.environ.get("SPG_WIC_PROVIDER_MODEL", "gpt-5.6-sol"),
        conversation_model=os.environ.get(
            "SPG_CONVERSATION_PROVIDER_MODEL",
            "gpt-5.6-sol",
        ),
        timeout_seconds=300,
    )
    service = WorkInteractionService(postgres_database, capability=capability)
    try:
        interaction = service.create_interaction(
            human_identity="human:conversation-intelligence-single-proof"
        )
        if context:
            service.append_human_input(
                interaction.id,
                context,
                human_identity="human:conversation-intelligence-single-proof",
            )
        response, projection, streamed = _run_real_human_watt_turn(
            service,
            interaction.id,
            message,
            timeout=650,
        )
        assert streamed is True
        assert capability.last_collaboration_result is not None
        assert capability.last_collaboration_result.turn_intent is expected_intent
        assert capability.last_pipeline_evidence is not None
        assert projection.latest_assessment is not None
        assert _count(postgres_database, product_works) == 0
        for table in runtime_tables:
            assert _count(postgres_database, table) == 0, table.name
        print(
            "HUMAN_WATT_CONVERSATION_INTELLIGENCE_SINGLE_PROOF",
            json.dumps(
                {
                    "turn_intent": expected_intent.value,
                    "response": response,
                    "semantic_thread_id": (
                        capability.last_pipeline_evidence.semantic_thread_id
                    ),
                    "conversation_thread_id": (
                        capability.last_pipeline_evidence.conversation_thread_id
                    ),
                },
                ensure_ascii=False,
            ),
        )
    finally:
        service.shutdown()


@pytest.mark.real_codex
@pytest.mark.skipif(
    os.environ.get("SPG_RUN_REAL_WIC_PROVIDER") != "1",
    reason="explicit real WIC Provider proof authorization is required",
)
def test_real_provider_advances_multi_turn_readiness_without_work_or_production(
    postgres_database: Database,
) -> None:
    service = WorkInteractionService(
        postgres_database,
        capability=CodexSdkWorkInteractionCapability(
            repository_location=os.environ.get(
                "SPG_WIC_PROVIDER_PROOF_ROOT",
                str(PROJECT_ROOT),
            ),
            timeout_seconds=300,
        ),
    )
    interaction = service.create_interaction(human_identity="human:wic-proof")
    first = service.append_and_assess(
        interaction.id,
        "我最近一直在想，Watt 的执行体验好像还有些地方可以聊聊。",
        human_identity="human:wic-proof",
    )
    assert first.readiness is not None
    assert first.readiness.status is WorkAdmissionReadinessStatus.NOT_READY
    assert first.latest_assessment is not None
    assert first.latest_assessment.provider_identity.startswith(
        "codex-sdk:semantic-thread:"
    )

    second = service.append_and_assess(
        interaction.id,
        (
            "我的 Motive 是改善 Watt 长时间自动执行时的状态可观测性；"
            "希望开发者能看清当前阶段、最近进展和阻塞原因。"
            "这轮只做必要体验，不做完整 UX/UI 重构，也不引入复杂新基础设施。"
        ),
        human_identity="human:wic-proof",
    )
    assert second.readiness is not None
    assert second.readiness.status is WorkAdmissionReadinessStatus.READY
    assert second.latest_assessment is not None
    assert second.latest_assessment.provider_identity.startswith(
        "codex-sdk:semantic-thread:"
    )
    assert _count(postgres_database, product_works) == 0
    assert _count(postgres_database, work_reality_revisions) == 0
    for table in runtime_tables:
        assert _count(postgres_database, table) == 0, table.name
