"""Typed environment-based configuration for the SPG foundation."""

from pathlib import Path
from typing import Literal

from pydantic import Field
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
    executor_adapter: str = "unconfigured"
    executor_timeout_seconds: float = Field(default=120.0, gt=0, le=600)
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
