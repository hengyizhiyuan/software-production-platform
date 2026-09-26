"""P1-Q9: upgrade a realistic P0 database without fabricating Product history."""

from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text


pytestmark = pytest.mark.postgresql


def test_p1_q9_upgrade_p0_schema_preserves_work_and_alembic_check_passes(
    postgres_database, monkeypatch,
) -> None:
    name = f"spg_p1_q9_{uuid4().hex[:12]}"
    root = Path(__file__).resolve().parents[2]
    admin = postgres_database.engine.execution_options(isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    url = postgres_database.engine.url.set(database=name)
    engine = create_engine(url)
    work_id = uuid4()
    try:
        monkeypatch.setenv("SPG_DATABASE_URL", url.render_as_string(hide_password=False))
        config = Config(root / "alembic.ini")
        command.upgrade(config, "20260926_54")
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO product_works
                    (id, work_mode, raw_user_requirement, constraints, tags, condition)
                VALUES (:id, 'IMMEDIATE_PRODUCTION', 'Historical P0 Work',
                        '[]'::jsonb, '[]'::jsonb, 'DRAFT')
            """), {"id": work_id})
        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(text("SELECT raw_user_requirement, product_id FROM product_works WHERE id = :id"),
                                     {"id": work_id}).one()
            assert row.raw_user_requirement == "Historical P0 Work"
            assert row.product_id is None
        command.check(config)
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
