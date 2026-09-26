"""Work/User executable capability overlays and resumable capability gaps."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from spg.infrastructure.persistence.metadata import metadata


connector_capabilities = Table(
    "connector_capabilities",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("owner_scope", String(32), nullable=False),
    Column("owner_id", String(255), nullable=False),
    Column("capability_id", String(255), nullable=False),
    Column("version", String(64), nullable=False),
    Column("definition", JSONB, nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("owner_scope", "owner_id", "capability_id", "version", name="uq_connector_capability_owner_version"),
)


capability_gaps = Table(
    "capability_gaps",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("work_id", Uuid(as_uuid=True), ForeignKey("product_works.id"), nullable=False),
    Column("capability_id", String(255), nullable=False),
    Column("operation_ref", String(255), nullable=False),
    Column("resume_point", JSONB, nullable=False),
    Column("condition", String(32), nullable=False),
    Column("reason", String(1024), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("work_id", "capability_id", "operation_ref", name="uq_capability_gap_work_operation"),
)

Index("ix_capability_gaps_work_condition", capability_gaps.c.work_id, capability_gaps.c.condition)

# Operator policy is separate from capability and credential facts.  A disabled
# connector is never promoted into authority by the resolver.
connector_controls = Table(
    "connector_controls", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("connector_id", String(255), nullable=False),
    Column("capability_id", String(255), nullable=False),
    Column("owner_scope", String(32), nullable=False),
    Column("owner_id", String(255), nullable=False),
    Column("version", String(64), nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("deprecated", Boolean, nullable=False),
    Column("health", String(32), nullable=False),
    Column("usage_count", Integer, nullable=False),
    Column("failure_count", Integer, nullable=False),
    Column("last_success_at", DateTime(timezone=True)),
    Column("last_failure_at", DateTime(timezone=True)),
    Column("last_failure_code", String(128)),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("connector_id", "capability_id", "owner_scope", "owner_id", "version",
                     name="uq_connector_controls_identity"),
)

connector_audit_events = Table(
    "connector_audit_events", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("actor_id", String(255), nullable=False),
    Column("subject_kind", String(32), nullable=False),
    Column("subject_id", String(255), nullable=False),
    Column("action", String(64), nullable=False),
    Column("detail", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
Index("ix_connector_audit_subject", connector_audit_events.c.subject_kind, connector_audit_events.c.subject_id)
