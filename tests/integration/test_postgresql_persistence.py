from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Table, func, insert, select

from spg.infrastructure.persistence import (
    Database,
    OptimisticConcurrencyConflict,
    update_versioned_row,
)
pytestmark = pytest.mark.postgresql


def _row_count(database: Database, table: Table) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def _record(database: Database, table: Table, record_id: int):
    with database.engine.connect() as connection:
        return connection.execute(
            select(table).where(table.c.id == record_id)
        ).one()


def test_db_01_connectivity(postgres_database: Database) -> None:
    health = postgres_database.check()

    assert health.database_name == "spg_test"
    assert health.server_version_num > 0


def test_db_02_transaction_commit(
    postgres_database: Database,
    versioned_table: Table,
) -> None:
    with postgres_database.unit_of_work() as unit_of_work:
        unit_of_work.session.execute(
            insert(versioned_table).values(id=1, name="committed", value="v0")
        )
        unit_of_work.commit()

    assert _row_count(postgres_database, versioned_table) == 1


def test_db_03_transaction_rollback(
    postgres_database: Database,
    versioned_table: Table,
) -> None:
    with pytest.raises(RuntimeError, match="injected failure"):
        with postgres_database.unit_of_work() as unit_of_work:
            unit_of_work.session.execute(
                insert(versioned_table).values(id=1, name="rolled-back", value="v0")
            )
            raise RuntimeError("injected failure")

    assert _row_count(postgres_database, versioned_table) == 0


def test_db_04_local_atomicity(
    postgres_database: Database,
    versioned_table: Table,
) -> None:
    with postgres_database.unit_of_work() as unit_of_work:
        unit_of_work.session.execute(
            insert(versioned_table),
            [
                {"id": 1, "name": "commit-a", "value": "v0"},
                {"id": 2, "name": "commit-b", "value": "v0"},
            ],
        )
        unit_of_work.commit()

    with pytest.raises(RuntimeError, match="atomic rollback"):
        with postgres_database.unit_of_work() as unit_of_work:
            unit_of_work.session.execute(
                insert(versioned_table),
                [
                    {"id": 3, "name": "rollback-a", "value": "v0"},
                    {"id": 4, "name": "rollback-b", "value": "v0"},
                ],
            )
            raise RuntimeError("atomic rollback")

    assert _row_count(postgres_database, versioned_table) == 2


def test_db_05_optimistic_version_success(
    postgres_database: Database,
    versioned_table: Table,
) -> None:
    with postgres_database.engine.begin() as connection:
        connection.execute(
            insert(versioned_table).values(id=1, name="versioned", value="v0")
        )

    with postgres_database.unit_of_work() as unit_of_work:
        new_version = update_versioned_row(
            unit_of_work.session,
            versioned_table,
            identity={"id": 1},
            expected_version=0,
            values={"value": "v1"},
        )
        unit_of_work.commit()

    record = _record(postgres_database, versioned_table, 1)
    assert new_version == 1
    assert record.value == "v1"
    assert record.version == 1


def test_db_06_optimistic_version_conflict(
    postgres_database: Database,
    versioned_table: Table,
) -> None:
    with postgres_database.engine.begin() as connection:
        connection.execute(
            insert(versioned_table).values(id=1, name="versioned", value="v0")
        )

    with postgres_database.unit_of_work() as first_writer:
        update_versioned_row(
            first_writer.session,
            versioned_table,
            identity={"id": 1},
            expected_version=0,
            values={"value": "winner"},
        )
        first_writer.commit()

    with pytest.raises(OptimisticConcurrencyConflict, match="expected 0"):
        with postgres_database.unit_of_work() as stale_writer:
            update_versioned_row(
                stale_writer.session,
                versioned_table,
                identity={"id": 1},
                expected_version=0,
                values={"value": "stale"},
            )
            stale_writer.commit()

    record = _record(postgres_database, versioned_table, 1)
    assert record.value == "winner"
    assert record.version == 1


def test_alembic_environment_connects_without_runtime_schema(
    postgres_database: Database,
    monkeypatch,
) -> None:
    database_url = postgres_database.engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("SPG_DATABASE_URL", database_url)
    project_root = Path(__file__).resolve().parents[2]

    command.current(Config(project_root / "alembic.ini"))
