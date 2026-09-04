"""Truthful local Runtime activation evidence and projection contracts."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RuntimeActivationState(StrEnum):
    """Relationship between repository trust and the active application process."""

    ACTIVE_AT_TRUSTED_BASELINE = "ACTIVE_AT_TRUSTED_BASELINE"
    ACTIVATION_REQUIRED = "ACTIVATION_REQUIRED"
    ACTIVATION_BLOCKED = "ACTIVATION_BLOCKED"
    IMAGE_REBUILD_REQUIRED = "IMAGE_REBUILD_REQUIRED"


class ActiveRuntimeEvidence(BaseModel):
    """Process-local evidence; it is not repository or deployment authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    active_application_revision: str = Field(min_length=1)
    active_repository_tree_identity: str = Field(min_length=1)
    active_source_package_fingerprint: str = Field(min_length=1)
    active_static_asset_fingerprint: str = Field(min_length=1)
    active_source_root: str = Field(min_length=1)
    activation_mode: str = "LOCAL_DOCKER_EXACT_TRUSTED_SOURCE"


class RuntimeActivationProjection(BaseModel):
    """Observable relationship between active Runtime and Current Trusted Baseline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: RuntimeActivationState
    active_application_revision: str | None = None
    active_repository_tree_identity: str | None = None
    active_source_package_fingerprint: str | None = None
    active_static_asset_fingerprint: str | None = None
    current_trusted_baseline_revision: str | None = None
    current_trusted_baseline_tree_identity: str | None = None
    activation_mode: str | None = None
    reason: str = Field(min_length=1)
    image_rebuild_paths: tuple[str, ...] = ()
