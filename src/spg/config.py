"""Typed environment-based configuration for the SPG foundation."""

from pathlib import Path

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
    verification_adapter: str = "unconfigured"
