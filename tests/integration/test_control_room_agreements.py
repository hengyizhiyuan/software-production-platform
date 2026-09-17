"""Focused PostgreSQL proof of bounded Human working-agreement lifecycle."""

from types import SimpleNamespace
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import insert, select

from spg.application.control_room import ControlRoomError, ControlRoomService
from spg.infrastructure.persistence import Database
from spg.infrastructure.persistence.control_room_schema import work_agreement_events
from spg.infrastructure.persistence.product_schema import product_works


def test_work_agreement_active_abandoned_and_history(postgres_database: Database, monkeypatch) -> None:
    config = Config("alembic.ini")
    monkeypatch.setenv("SPG_DATABASE_URL", postgres_database.engine.url.render_as_string(hide_password=False))
    command.upgrade(config, "head")
    work_id = uuid4()
    with postgres_database.unit_of_work() as uow:
        uow.session.execute(insert(product_works).values(
            id=work_id, work_mode="IMMEDIATE_PRODUCTION", raw_user_requirement="Build a useful tool",
            constraints=[], tags=[], condition="DRAFT",
        ))
        uow.commit()
    service = ControlRoomService(postgres_database, SimpleNamespace(get_work=lambda _id: SimpleNamespace(work_id=work_id)))
    first = service.create_agreement(work_id, content="Keep a read-only first release", agreement_type="DECISION", actor_identity="human:test")
    second = service.create_agreement(work_id, content="Review accessibility later", agreement_type="DEFERRED", actor_identity="human:test")
    assert first["state"] == second["state"] == "ACTIVE"
    assert first["persistence_state"] == "NOT_PERSISTED"
    assert first["persistence_path"] is None
    abandoned = service.abandon_agreement(work_id, UUID(first["agreement_id"]), actor_identity="human:test")
    assert abandoned["state"] == "ABANDONED"
    assert [item["kind"] for item in abandoned["history"]] == ["CREATED", "ABANDONED"]
    assert [item["agreement_id"] for item in service.agreements(work_id) if item["state"] == "ACTIVE"] == [second["agreement_id"]]
    with postgres_database.unit_of_work() as uow:
        assert len(uow.session.execute(select(work_agreement_events).where(work_agreement_events.c.work_id == work_id)).all()) == 3
    try:
        service.abandon_agreement(work_id, UUID(first["agreement_id"]), actor_identity="human:test")
    except ControlRoomError:
        pass
    else:
        raise AssertionError("Abandoned agreements must not be abandoned twice")
