"""Work/User executable capability overlays and resumable capability gaps."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Uuid, UniqueConstraint
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
