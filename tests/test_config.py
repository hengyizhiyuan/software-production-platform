from pathlib import Path

from spg.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("SPG_RUNTIME_PROFILE", "test-fvs")
    monkeypatch.setenv("SPG_REPOSITORY_PATH", ".")

    settings = Settings()

    assert settings.runtime_profile == "test-fvs"
    assert settings.repository_path == Path(".")
    assert settings.database_dsn is None
    assert settings.executor_adapter == "unconfigured"

