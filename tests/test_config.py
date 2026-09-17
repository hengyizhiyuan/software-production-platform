from pathlib import Path

from spg.config import Settings


def test_default_wic_uses_deepseek_with_logically_separate_role_profiles() -> None:
    settings = Settings()
    assert settings.wic_provider_adapter == "deepseek"
    assert settings.wic_provider_model == "deepseek-flash"
    assert settings.collaboration_provider_max_output_tokens == 8192
    assert settings.conversation_provider_adapter is None
    assert settings.conversation_provider_model is None
    assert settings.wic_provider_reasoning_effort == "low"
    assert settings.conversation_provider_reasoning_effort == "low"


def test_default_runtime_exposes_all_three_exact_role_profiles() -> None:
    from spg.application.bootstrap import bootstrap
    from spg.domain.model_runtime import ModelPurpose

    service = bootstrap(Settings(deepseek_api_key="test-only")).interaction(
        database=object()
    )
    try:
        runtime = service.capability.runtime
        assert runtime.profile(ModelPurpose.WIC_SEMANTIC).model == "deepseek-flash"
        assert runtime.profile(ModelPurpose.CONVERSATION_RESPONSE).model == "deepseek-flash"
        assert runtime.profile(ModelPurpose.EXECUTOR_PRODUCTION).model == "unconfigured"
    finally:
        service.shutdown()


def test_settings_load_from_environment(monkeypatch) -> None:
    # Real PostgreSQL integration fixtures may temporarily point Alembic at their
    # isolated database. This unit contract owns its complete environment basis.
    monkeypatch.delenv("SPG_DATABASE_URL", raising=False)
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
