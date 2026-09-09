from pathlib import Path

from spg.config import Settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("SPG_RUNTIME_PROFILE", "test-fvs")
    monkeypatch.setenv("SPG_REPOSITORY_PATH", ".")
    monkeypatch.setenv("SPG_WIC_PROVIDER_MODEL", "gpt-5.6-sol")
    monkeypatch.setenv("SPG_WIC_PROVIDER_ADAPTER", "codex-sdk")
    monkeypatch.setenv("SPG_CONVERSATION_PROVIDER_ADAPTER", "codex-sdk")
    monkeypatch.setenv("SPG_CONVERSATION_PROVIDER_MODEL", "gpt-5.6-sol")

    settings = Settings()

    assert settings.runtime_profile == "test-fvs"
    assert settings.repository_path == Path(".")
    assert settings.database_url is None
    assert settings.executor_adapter == "unconfigured"
    assert settings.wic_provider_adapter == "codex-sdk"
    assert settings.wic_provider_model == "gpt-5.6-sol"
    assert settings.conversation_provider_adapter == "codex-sdk"
    assert settings.conversation_provider_model == "gpt-5.6-sol"
    assert settings.executor_timeout_seconds == 120.0
    assert settings.executor_max_internal_turns == 3
    assert settings.verification_adapter == "unconfigured"


def test_collaboration_provider_settings_are_independent_of_executor(monkeypatch) -> None:
    from unittest.mock import patch
    from spg.application.bootstrap import bootstrap

    monkeypatch.setenv("SPG_EXECUTOR_TIMEOUT_SECONDS", "600")
    monkeypatch.setenv("SPG_COLLABORATION_PROVIDER_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("SPG_WIC_PROVIDER_REASONING_EFFORT", "medium")
    monkeypatch.setenv("SPG_CONVERSATION_PROVIDER_REASONING_EFFORT", "low")
    settings = Settings(wic_provider_adapter="codex-sdk", executor_adapter="unconfigured")
    assert settings.executor_timeout_seconds == 600
    assert settings.wic_coalesce_pre_work is True
    with patch("spg.providers.codex_interaction.CodexSdkWorkInteractionCapability") as provider:
        service = bootstrap(settings).interaction(database=object())
        try:
            options = provider.call_args.kwargs
            assert options["coalesce_pre_work"] is True
            assert options["timeout_seconds"] == 45
            assert options["reasoning_effort"] == "medium"
            assert options["conversation_reasoning_effort"] == "low"
        finally:
            service.shutdown()


def test_collaboration_reasoning_settings_reject_unsupported_values() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(wic_provider_reasoning_effort="unsupported")
    with pytest.raises(ValidationError):
        Settings(conversation_provider_reasoning_effort="unsupported")
