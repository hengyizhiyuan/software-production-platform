"""Truthful local Runtime activation evidence and projection contracts."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RuntimeActivationState(StrEnum):
    """Relationship between repository trust and the active application process."""

    ACTIVE_AT_TRUSTED_BASELINE = "ACTIVE_AT_TRUSTED_BASELINE"
    ACTIVATION_REQUIRED = "ACTIVATION_REQUIRED"
    ACTIVATION_BLOCKED = "ACTIVATION_BLOCKED"
    IMAGE_REBUILD_REQUIRED = "IMAGE_REBUILD_REQUIRED"
    ACTIVE_HUMAN_REVIEW = "ACTIVE_HUMAN_REVIEW"


class ActiveRuntimeEvidence(BaseModel):
    """Process-local evidence; it is not repository or deployment authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    active_application_revision: str = Field(min_length=1)
    active_repository_tree_identity: str = Field(min_length=1)
    active_source_package_fingerprint: str = Field(min_length=1)
    active_static_asset_fingerprint: str = Field(min_length=1)
    active_source_root: str = Field(min_length=1)
    activation_mode: str = "LOCAL_DOCKER_EXACT_TRUSTED_SOURCE"


class HumanReviewRuntimeVersion(BaseModel):
    """Exact application-build identity, never production or release authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    base_revision: str = Field(min_length=1)
    base_tree_identity: str = Field(min_length=1)
    source_root: str = Field(min_length=1)
    configuration_root: str = Field(min_length=1)
    source_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    static_asset_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    dependency_lock_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    configuration_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    human_review_version_id: str | None = None
    reason: str = Field(min_length=1)
    image_rebuild_paths: tuple[str, ...] = ()
