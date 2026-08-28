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


def test_production_metadata_contains_only_admitted_s1_through_s3b_tables() -> None:
    assert set(metadata.tables) == {
        "production_snapshots",
        "current_trusted_baseline_pointer",
        "production_runs",
        "plan_revisions",
        "production_work_units",
        "execution_attempts",
        "governance_records",
        "transition_history",
        "context_packages",
        "attempt_preparations",
        "execution_dispatches",
        "provider_execution_reports",
        "repository_observations",
        "work_product_references",
        "completion_evaluations",
        "proposed_repository_snapshots",
        "verification_records",
        "production_admissibility_records",
    }


def test_alembic_environment_has_s3b_migration_head() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config = Config(project_root / "alembic.ini")
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["20260828_05"]
