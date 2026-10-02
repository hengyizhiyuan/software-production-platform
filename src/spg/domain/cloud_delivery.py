"""Exact Alibaba Cloud connection and Watt-owned delivery contracts.

Cloud connection, Human acceptance, target grant, and Delivery authorization are
separate authorities. No request contract accepts command text or credentials.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CloudConnectionState(StrEnum):
    AWAITING_CLOUD_AUTHORIZATION = "AWAITING_CLOUD_AUTHORIZATION"
    DISCOVERY_READY = "DISCOVERY_READY"
    TARGET_SELECTED = "TARGET_SELECTED"
    TARGET_AUTHORIZATION_REQUIRED = "TARGET_AUTHORIZATION_REQUIRED"
    READY = "READY"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    INVALID = "INVALID"


class CloudOperationKind(StrEnum):
    DISCOVER_INSTANCE = "DISCOVER_INSTANCE"
    CHECK_INSTANCE_STATE = "CHECK_INSTANCE_STATE"
    CHECK_CLOUD_ASSISTANT = "CHECK_CLOUD_ASSISTANT"
    CHECK_DEPLOYMENT_PREREQUISITES = "CHECK_DEPLOYMENT_PREREQUISITES"
    STAGE_ARTIFACT = "STAGE_ARTIFACT"
    DEPLOY_WATT_RELEASE = "DEPLOY_WATT_RELEASE"
    VERIFY_WATT_RUNTIME = "VERIFY_WATT_RUNTIME"
    VERIFY_PUBLIC_BUSINESS = "VERIFY_PUBLIC_BUSINESS"
    ROLLBACK_WATT_RELEASE = "ROLLBACK_WATT_RELEASE"
    VERIFY_ROLLBACK_BUSINESS = "VERIFY_ROLLBACK_BUSINESS"
    STOP_WATT_RUNTIME = "STOP_WATT_RUNTIME"


class CloudDeploymentState(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    PRECHECK = "PRECHECK"
    STAGING = "STAGING"
    PREPARING = "PREPARING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    NEEDS_HUMAN_ATTENTION = "NEEDS_HUMAN_ATTENTION"


class CloudTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str = Field(pattern=r"^[0-9]{8,32}$")
    region_id: str = Field(pattern=r"^[a-z]{2}-[a-z0-9-]{2,48}$")
    instance_id: str = Field(pattern=r"^i-[a-zA-Z0-9]{6,64}$")
    name: str = Field(max_length=255)
    os_name: str = Field(max_length=255)
    os_type: str = Field(default="Unknown", max_length=32)
    status: str = Field(max_length=32)
    public_address: str | None = None
    cloud_assistant_ready: bool = False

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.account_id, self.region_id, self.instance_id


class CloudConnection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    owner_id: str = Field(min_length=1, max_length=255)
    service_account_id: str = Field(pattern=r"^[0-9]{8,32}$")
    service_principal_arn: str = Field(pattern=r"^acs:ram::[0-9]{8,32}:(?:user|role)/[A-Za-z0-9_.@-]+$")
    external_id: str = Field(pattern=r"^[A-Za-z0-9_-]{32,128}$")
    recommended_role_name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    role_arn: str | None = Field(default=None, pattern=r"^acs:ram::[0-9]{8,32}:role/[A-Za-z0-9_.-]+$")
    customer_account_id: str | None = Field(default=None, pattern=r"^[0-9]{8,32}$")
    state: CloudConnectionState
    target: CloudTarget | None = None
    discovered_targets: tuple[CloudTarget, ...] = ()
    discovery_verified_at: datetime | None = None
    target_grant_verified_at: datetime | None = None
    evidence_references: tuple[str, ...] = ()
    version: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def exact_boundaries(self):
        if self.role_arn and self.customer_account_id and (
            self.role_arn.split(":")[3] != self.customer_account_id
        ):
            raise ValueError("Cloud role and customer account differ")
        if self.target and self.target.account_id != self.customer_account_id:
            raise ValueError("Selected ECS belongs to another customer account")
        if self.state in {CloudConnectionState.TARGET_SELECTED,
                          CloudConnectionState.TARGET_AUTHORIZATION_REQUIRED,
                          CloudConnectionState.READY} and self.target is None:
            raise ValueError("Selected target identity is required")
        if self.state is CloudConnectionState.READY and self.target_grant_verified_at is None:
            raise ValueError("READY requires an observed exact target grant")
        return self


class CloudDeliveryAuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    connection_id: UUID
    manifest_id: UUID
    manifest_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_account_id: str = Field(pattern=r"^[0-9]{8,32}$")
    target_region_id: str = Field(pattern=r"^[a-z]{2}-[a-z0-9-]{2,48}$")
    target_instance_id: str = Field(pattern=r"^i-[a-zA-Z0-9]{6,64}$")
    expected_current_deployment_id: UUID | None = None
    port: int = Field(ge=1024, le=65535)
    rationale: str = Field(min_length=1, max_length=4000)


class CloudDeliveryAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    work_id: UUID
    actor_id: str
    connection_id: UUID
    manifest_id: UUID
    manifest_fingerprint: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    target: CloudTarget
    operation_profile: str = "WATT_MANAGED_CONTAINER_V1"
    expected_current_deployment_id: UUID | None = None
    port: int = Field(ge=1024, le=65535)
    rationale: str
    authorized_at: datetime


class CloudPreparedArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    manifest_id: UUID
    manifest_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive_path: str
    image_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    internal_port: int = Field(ge=1, le=65535)
    artifact_kind: str
    created_at: datetime


class CloudOperationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: CloudOperationKind
    account_id: str
    region_id: str
    instance_id: str
    invocation_id: str | None = None
    command_id: str | None = None
    provider_request_id: str | None = None
    provider_error_code: str | None = Field(default=None,
        pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
    # Only reconstructed, recognized provider messages are durable. Raw ErrorInfo
    # remains transient because it can contain user data or credentials.
    provider_error_info: str | None = Field(default=None, max_length=256,
        pattern=r"^Deployment user [a-z_][a-z0-9_-]{0,31} is missing on target ECS\.$")
    deployment_user: str | None = Field(default=None,
        pattern=r"^[a-z_][a-z0-9_-]{0,31}$")
    started_at: datetime
    finished_at: datetime
    status: str
    exit_code: int | None = None
    output_summary: str = Field(max_length=1000)
    verified: bool = False


class CloudDeployment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    authorization_id: UUID
    connection_id: UUID
    manifest_id: UUID
    work_id: UUID
    target: CloudTarget
    state: CloudDeploymentState
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    image_identity: str | None = None
    staging_object: str | None = None
    runtime_name: str | None = None
    port: int = Field(ge=1024, le=65535)
    operations: tuple[CloudOperationReceipt, ...] = ()
    health_verified: bool = False
    business_verified: bool = False
    rollback_verified: bool = False
    blocker: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def success_requires_observed_health(self):
        if self.state is CloudDeploymentState.SUCCEEDED and not self.health_verified:
            raise ValueError("Cloud deployment cannot succeed from an API exit code alone")
        if self.state is CloudDeploymentState.ROLLED_BACK and not self.rollback_verified:
            raise ValueError("Rollback requires observed verification")
        return self


def discovery_policy(account_id: str) -> dict:
    """Only the two ECS reads used by discovery; DescribeRegions/STS need no grant."""
    if not re.fullmatch(r"[0-9]{8,32}", account_id):
        raise ValueError("Invalid customer account ID")
    return {"Version": "1", "Statement": [{"Effect": "Allow",
        "Action": ["ecs:DescribeInstances", "ecs:DescribeCloudAssistantStatus"],
        "Resource": [f"acs:ecs:*:{account_id}:instance/*"]}]}


def target_execution_policy(target: CloudTarget, username: str) -> dict:
    """RunCommand is the only write, bound to one exact instance and run-as user."""
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", username) or username == "root":
        raise ValueError("A dedicated non-root deployment user is required")
    instance = f"acs:ecs:{target.region_id}:{target.account_id}:instance/{target.instance_id}"
    command = f"acs:ecs:{target.region_id}:{target.account_id}:command/*"
    return {"Version": "1", "Statement": [
        {"Effect": "Allow", "Action": ["ecs:RunCommand"], "Resource": [instance],
         "Condition": {"StringEquals": {"ecs:CommandRunAs": username}}},
        {"Effect": "Allow", "Action": ["ecs:DescribeInvocations",
            "ecs:DescribeInvocationResults"], "Resource": [instance, command]},
    ]}


def trust_policy(principal_arn: str, external_id: str) -> dict:
    if not re.fullmatch(r"acs:ram::[0-9]{8,32}:(?:user|role)/[A-Za-z0-9_.@-]+",
            principal_arn) or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", external_id):
        raise ValueError("Exact service principal and ExternalId are required")
    return {"Version": "1", "Statement": [{"Effect": "Allow",
        "Action": "sts:AssumeRole", "Principal": {"RAM": [principal_arn]},
        "Condition": {"StringEquals": {"sts:ExternalId": external_id}}}]}
