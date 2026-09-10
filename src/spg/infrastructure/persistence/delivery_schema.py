"""Append-only product delivery records, independent of SPG lifecycle."""
from sqlalchemy import Column, DateTime, ForeignKey, Table, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from spg.infrastructure.persistence.metadata import metadata

work_delivery_targets = Table(
    "work_delivery_targets", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("work_id", Uuid(as_uuid=True), ForeignKey("product_works.id"), nullable=False, unique=True),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
work_delivery_manifests = Table(
    "work_delivery_manifests", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("work_id", Uuid(as_uuid=True), ForeignKey("product_works.id"), nullable=False),
    Column("target_id", Uuid(as_uuid=True), ForeignKey("work_delivery_targets.id"), nullable=False),
    Column("runtime_commit_id", Uuid(as_uuid=True), ForeignKey("runtime_commits.id"), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
work_delivery_acceptances = Table(
    "work_delivery_acceptances", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("manifest_id", Uuid(as_uuid=True), ForeignKey("work_delivery_manifests.id"), nullable=False, unique=True),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
delivery_tables = (work_delivery_targets, work_delivery_manifests, work_delivery_acceptances)
