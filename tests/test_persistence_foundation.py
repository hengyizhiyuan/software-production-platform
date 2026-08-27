from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import ValidationError
import pytest

from spg.application import bootstrap
from spg.config import Settings
from spg.infrastructure.persistence import DatabaseConfigurationError, metadata


def test_settings_load_postgresql_url_from_environment(monkeypatch) -> None:
    database_url = "postgresql+psycopg://user:password@localhost:5432/spg"
    monkeypatch.setenv("SPG_DATABASE_URL", database_url)

    assert Settings().database_url == database_url


def test_settings_reject_non_postgresql_url() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+pysqlite:///:memory:")


def test_persistence_requires_explicit_database_url() -> None:
    application = bootstrap(Settings(database_url=None))

    with pytest.raises(DatabaseConfigurationError, match="SPG_DATABASE_URL"):
        application.persistence()


def test_postgresql_engine_composition_has_no_connection_side_effect() -> None:
    application = bootstrap(
        Settings(database_url="postgresql://user:password@127.0.0.1:1/spg")
    )

    database = application.persistence()
    try:
        assert database.engine.dialect.name == "postgresql"
        assert database.engine.dialect.driver == "psycopg"
    finally:
        database.dispose()


def test_production_metadata_has_no_speculative_tables() -> None:
    assert not metadata.tables


def test_alembic_environment_loads_without_runtime_revisions() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = Config(project_root / "alembic.ini")
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == []
