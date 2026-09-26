"""GitHub grant and governed remote-effect evidence."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from spg.infrastructure.persistence.metadata import metadata


github_access_grants = Table(
    "github_access_grants", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("actor_id", String(255), nullable=False),
    Column("repository_url", Text, nullable=False),
    Column("capability", String(16), nullable=False),
    Column("credential_ref", String(64), nullable=False),
    Column("credential_sha256", String(64), nullable=False),
    Column("condition", String(16), nullable=False),
    Column("observed_permission", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("revoked_at", DateTime(timezone=True)),
    Column("expires_at", DateTime(timezone=True)),
    Column("last_verified_at", DateTime(timezone=True)),
    Column("usage_count", Integer, nullable=False, server_default="0"),
    Column("failure_count", Integer, nullable=False, server_default="0"),
    Column("last_failure_at", DateTime(timezone=True)),
    UniqueConstraint("actor_id", "repository_url", "capability",
        name="uq_github_grant_actor_repo_capability"),
)

remote_delivery_authorizations = Table(
    "remote_delivery_authorizations", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("work_id", Uuid(as_uuid=True), nullable=False),
    Column("manifest_id", Uuid(as_uuid=True), nullable=False),
    Column("actor_id", String(255), nullable=False),
    Column("repository_url", Text, nullable=False),
    Column("target_branch", String(255), nullable=False),
    Column("expected_revision", String(64), nullable=False),
    Column("expected_remote_revision", String(64)),
    Column("rationale", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

remote_delivery_receipts = Table(
    "remote_delivery_receipts", metadata,
    Column("authorization_id", Uuid(as_uuid=True),
        ForeignKey("remote_delivery_authorizations.id"), primary_key=True),
    Column("remote_before", String(64)),
    Column("remote_after", String(64), nullable=False),
    Column("push_condition", String(32), nullable=False),
    Column("pr_url", Text),
    Column("pr_number", String(32)),
    Column("observed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
