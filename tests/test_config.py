from pathlib import Path

from spg.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("SPG_RUNTIME_PROFILE", "test-fvs")
    monkeypatch.setenv("SPG_REPOSITORY_PATH", ".")
    monkeypatch.setenv("SPG_WIC_PROVIDER_MODEL", "gpt-5.6-sol")

    settings = Settings()

    assert settings.runtime_profile == "test-fvs"
    assert settings.repository_path == Path(".")
    assert settings.database_url is None
    assert settings.executor_adapter == "unconfigured"
    assert settings.wic_provider_model == "gpt-5.6-sol"
    assert settings.executor_timeout_seconds == 120.0
    assert settings.executor_max_internal_turns == 3
    assert settings.verification_adapter == "unconfigured"
