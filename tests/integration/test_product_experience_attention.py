"""Product Experience reflects canonical Work Attention without classifying it."""

from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest

from spg.application.delivery import DeliveryApplicationService
from spg.application.interaction import WorkInteractionService
from spg.application.product_assets import ProductAssetService
from spg.application.product_experience import ProductExperienceProjection
from spg.application.work import WorkApplicationService
from spg.domain.product import AttentionAction, AttentionItem, AttentionKind, WorkStatus
from spg.infrastructure.persistence import product_tables, runtime_tables
from tests.integration.test_wic_governed_work_admission import _ReadyCapability


pytestmark = pytest.mark.postgresql
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_product_reality(postgres_database, monkeypatch):
    monkeypatch.setenv("SPG_DATABASE_URL", postgres_database.engine.url.render_as_string(
        hide_password=False))
    monkeypatch.setenv("SPG_MANAGED_SOURCE_PROVIDER", "disabled")
    command.upgrade(Config(ROOT / "alembic.ini"), "head")
    tables = ", ".join(f'"{table.name}"' for table in (*product_tables, *runtime_tables))
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {tables} CASCADE")
    yield
    with postgres_database.engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {tables} CASCADE")


@pytest.fixture
def experience_reality(postgres_database, monkeypatch):
    product = ProductAssetService(postgres_database).create(
        "human:owner", "Attention Product", provision_source=False)
    product_id = UUID(product["id"])
    interaction = WorkInteractionService(postgres_database,
        capability=_ReadyCapability()).create_interaction(
        human_identity="human:owner", product_id=product_id,
        start_work_context=True)
    work_id = interaction.current_work_id
    assert work_id is not None
    work = WorkApplicationService(postgres_database)
    attention = []

    def canonical_attention(*, work_id=None):
        return tuple(item for item in attention if work_id is None or item.work_id == work_id)

    monkeypatch.setattr(work, "list_attention", canonical_attention)
    projection = ProductExperienceProjection(postgres_database,
        ProductAssetService(postgres_database), work,
        DeliveryApplicationService(postgres_database))
    return projection, attention, product_id, work_id, interaction.id


def _attention(work_id, *, structured=False):
    return AttentionItem(id=uuid4(), work_id=work_id,
        kind=AttentionKind.WORK_DRAFT_APPROVAL if structured else
            AttentionKind.STEERING_DECISION_REQUIRED,
        decision="Admit this Work?" if structured else "Answer the current Work question",
        reason="Choose the Product boundary",
        available_actions=(AttentionAction.APPROVE, AttentionAction.REJECT)
            if structured else (),
        recommended_action=AttentionAction.APPROVE if structured else None,
        governed_subject_ref=f"steering-decision:{uuid4()}",
        conversation_prompt=None if structured else "Which Product boundary should govern?",
        recommendation="Explain the chosen boundary" if not structured else None,
        expected_impact="Guides subsequent design")


def test_conversational_attention_reaches_home_workspace_and_exact_interaction(experience_reality):
    projection, attention, product_id, work_id, interaction_id = experience_reality
    attention.append(_attention(work_id))
    home = projection.home("human:owner")
    workspace = projection.workspace("human:owner", product_id)
    assert len(home["attention"]) == 1
    assert home["attention"][0]["conversation_prompt"] == "Which Product boundary should govern?"
    assert home["attention"][0]["interaction_id"] == str(interaction_id)
    assert home["attention"][0]["actions"] == []
    assert len(workspace["actions"]) == 1
    assert workspace["focus"]["human_action"] is True


def test_multiple_product_attentions_retain_their_owning_work_and_conversation(
        experience_reality):
    projection, attention, first_product_id, first_work_id, first_interaction_id = experience_reality
    other_product = ProductAssetService(projection.database).create(
        "human:owner", "Second Attention Product", provision_source=False)
    other_product_id = UUID(other_product["id"])
    other_interaction = WorkInteractionService(projection.database,
        capability=_ReadyCapability()).create_interaction(
        human_identity="human:owner", product_id=other_product_id,
        start_work_context=True)
    assert other_interaction.current_work_id is not None
    attention.extend((_attention(first_work_id), _attention(other_interaction.current_work_id)))
    rows = projection.home("human:owner")["attention"]
    assert len(rows) == 2
    assert {(row["product_id"], row["work_id"], row["interaction_id"])
        for row in rows} == {
            (str(first_product_id), str(first_work_id), str(first_interaction_id)),
            (str(other_product_id), str(other_interaction.current_work_id),
             str(other_interaction.id)),
        }


def test_structured_attention_keeps_existing_actions(experience_reality):
    projection, attention, product_id, work_id, _ = experience_reality
    attention.append(_attention(work_id, structured=True))
    action = projection.workspace("human:owner", product_id)["actions"][0]
    assert action["actions"] == ["APPROVE", "REJECT"]
    assert action["recommended_action"] == "APPROVE"


def test_blocked_work_without_canonical_attention_does_not_enter_human_queue(
        experience_reality, monkeypatch):
    projection, _, product_id, _, _ = experience_reality
    get_work = projection.work.get_work
    monkeypatch.setattr(projection.work, "get_work", lambda work_id:
        get_work(work_id).model_copy(update={"status": WorkStatus.BLOCKED}))
    assert projection.home("human:owner")["attention"] == []
    workspace = projection.workspace("human:owner", product_id)
    assert workspace["actions"] == []
    assert workspace["focus"]["human_action"] is False


def test_collection_status_uses_canonical_work_projection(experience_reality, monkeypatch):
    projection, _, product_id, _, _ = experience_reality
    get_work = projection.work.get_work
    monkeypatch.setattr(projection.work, "get_work", lambda work_id:
        get_work(work_id).model_copy(update={"status": WorkStatus.COMPLETED}))
    collection = projection.collections("human:owner")
    assert collection["works"][0]["status"] == "COMPLETED"
    assert next(item for item in collection["products"]
        if item["id"] == str(product_id))["current_work"] is None


def test_attention_disappears_only_after_canonical_owner_clears_it(experience_reality):
    projection, attention, product_id, work_id, _ = experience_reality
    attention.append(_attention(work_id))
    assert projection.home("human:owner")["attention"]
    assert projection.workspace("human:owner", product_id)["actions"]
    attention.clear()  # The test's canonical owner reports the resolved state.
    assert projection.home("human:owner")["attention"] == []
    assert projection.workspace("human:owner", product_id)["actions"] == []


def test_empty_attention_remains_truthful(experience_reality):
    projection, _, product_id, _, _ = experience_reality
    assert projection.home("human:owner")["attention"] == []
    workspace = projection.workspace("human:owner", product_id)
    assert workspace["actions"] == []
    assert workspace["focus"]["human_action"] is False
