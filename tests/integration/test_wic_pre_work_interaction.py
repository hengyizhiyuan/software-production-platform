from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select, text

from spg.api import create_http_application
from spg.application.interaction import (
    DeterministicWorkInteractionCapability,
    WorkInteractionService,
)
from spg.domain.interaction import (
    InteractionAssessmentCandidate,
    InteractionInterpretationInput,
    InteractionInvariantViolation,
    InterpretationMeaning,
    InterpretationMeaningKind,
    WorkAdmissionReadinessStatus,
)
from spg.domain.runtime_activation import RuntimeActivationProjection, RuntimeActivationState
from spg.infrastructure.persistence import Database, product_tables, runtime_tables
from spg.infrastructure.persistence.product_schema import (
    interaction_assessments,
    interaction_records,
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


class _NeverCalledWorkService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_works(self, *args, **kwargs) -> tuple[()]:
        return ()


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
    assert first.latest_assessment.provider_identity.startswith("codex-sdk:thread:")

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
    assert second.latest_assessment.provider_identity.startswith("codex-sdk:thread:")
    assert _count(postgres_database, product_works) == 0
    assert _count(postgres_database, work_reality_revisions) == 0
    for table in runtime_tables:
        assert _count(postgres_database, table) == 0, table.name
