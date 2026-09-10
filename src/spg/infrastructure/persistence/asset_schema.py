from sqlalchemy import Column, Table, Uuid, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from spg.infrastructure.persistence.metadata import metadata
repository_intakes = Table(
    "repository_intakes", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("request", JSONB, nullable=False),
    Column("observation", JSONB, nullable=True),
    Column("resource_id", Uuid(as_uuid=True), ForeignKey("engineering_resources.id"), nullable=True, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
