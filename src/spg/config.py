"""Typed environment-based configuration for the SPG foundation."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration required to bootstrap the current local foundation."""

    model_config = SettingsConfigDict(
        env_prefix="SPG_",
        case_sensitive=False,
        extra="ignore",
    )

    application_name: str = "SPG Runtime"
    runtime_profile: str = Field(default="local-fvs", min_length=1)
    repository_path: Path = Field(default_factory=Path.cwd)
    workspace_root: Path = Path(".spg/workspaces")
    database_url: str | None = Field(
        default=None,
        pattern=r"^postgresql(?:\+psycopg)?://\S+$",
        description="PostgreSQL URL supplied through SPG_DATABASE_URL",
    )
    delivery_runtime_enabled: bool = False
    delivery_runtime_bind_host: str = "127.0.0.1"
    delivery_runtime_first_port: int = Field(default=8010, ge=1024, le=65000)
    delivery_runtime_port_count: int = Field(default=10, ge=1, le=20)
    executor_adapter: str = "unconfigured"
    native_executor_enabled: bool = False
    native_executor_backend: Literal["watt-native", "legacy-codex"] = "watt-native"
    native_executor_worker_id: str = "native-worker-local-1"
    native_executor_worker_profile: str = "local-container-v1"
    native_executor_resource_profile: str = "standard"
    native_executor_storage_root: Path = Path(".watt/native-executor")
    native_executor_inference_provider: Literal["deepseek", "openai"] = "deepseek"
    native_executor_inference_model: str | None = None
    native_executor_inference_reasoning_effort: Literal[
        "none", "low", "high", "max"
    ] = "high"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    native_executor_deepseek_api_key: SecretStr | None = None
    native_executor_deepseek_base_url: str = "https://api.deepseek.com"
    native_executor_openai_api_key: SecretStr | None = None
    native_executor_openai_base_url: str = "https://api.openai.com/v1"
    native_executor_tool_host_url: str = "http://native-tool-host:8011"
    native_executor_internal_token: SecretStr | None = None
    native_executor_workspace_root: Path = Path(".watt/native-executor/workspaces")
    native_executor_production_environment_store_root: Path = Path(
        ".watt/production-environments"
    )
    native_executor_production_environment_image: str = (
        "watt-native-executor-runtime:local"
    )
    native_executor_production_environment_workspace_volume: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]+$",
    )
    native_executor_poll_seconds: float = Field(default=1.0, ge=0.1, le=30)
    native_executor_compatibility_wait_seconds: float = Field(
        default=7200.0, ge=30.0, le=86400.0
    )
    wic_provider_adapter: str | None = Field(default="deepseek", min_length=1)
    wic_provider_model: str | None = Field(default="deepseek-flash", min_length=1)
    conversation_provider_adapter: str | None = Field(default=None, min_length=1)
    conversation_provider_model: str | None = Field(default=None, min_length=1)
    wic_coalesce_pre_work: bool = True
    wic_runtime_mode: Literal[
        "LEGACY_WIC", "WIC_VNEXT_SHADOW", "WIC_VNEXT_CONTROLLED"
    ] = "WIC_VNEXT_SHADOW"
    wic_fast_reception_shadow_enabled: bool = True
    wic_fast_reception_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    wic_fast_reception_max_output_tokens: int = Field(default=256, ge=64, le=1024)
    wic_provider_reasoning_effort: Literal[
        "none", "minimal", "low", "medium", "high", "xhigh"
    ] | None = "low"
    conversation_provider_reasoning_effort: Literal[
        "none", "minimal", "low", "medium", "high", "xhigh"
    ] | None = "low"
    collaboration_provider_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    collaboration_provider_max_output_tokens: int = Field(default=8192, ge=512, le=32768)
    executor_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
    executor_max_internal_turns: int = Field(default=3, ge=1)
    executor_sandbox_mode: Literal["workspace-write", "full-access"] = (
        "workspace-write"
    )
    verification_adapter: str = "unconfigured"
    orchestration_max_automatic_transitions: int = Field(default=12, ge=1, le=50)
    active_runtime_revision: str | None = None
    active_runtime_tree_identity: str | None = None
    active_runtime_package_fingerprint: str | None = None
    active_runtime_static_asset_fingerprint: str | None = None
    active_runtime_source_root: Path | None = None
    runtime_activation_mode: Literal["NORMAL", "HUMAN_REVIEW"] = "NORMAL"
    human_review_version_file: Path | None = None
    human_review_version_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @property
    def native_executor_provider_profile(self) -> str:
        model = self.native_executor_inference_model or "unconfigured"
        effort = self.native_executor_inference_reasoning_effort
        return (
            f"{self.native_executor_inference_provider}-responses:"
            f"{model}:{effort}"
        )
