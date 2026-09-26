"""Git bundle snapshots are canonical source bytes in durable PostgreSQL."""

from sqlalchemy import Column, DateTime, LargeBinary, String, Table
from sqlalchemy.sql import func

from spg.infrastructure.persistence.metadata import metadata


managed_repository_sources = Table(
    "managed_repository_sources", metadata,
    Column("repository_identity", String(255), primary_key=True),
    Column("owner_actor_id", String(255), nullable=False),
    Column("repository_ref", String(512), nullable=False),
    Column("revision", String(64), nullable=False),
    Column("tree", String(64), nullable=False),
    Column("bundle_sha256", String(64), nullable=False),
    Column("git_bundle", LargeBinary, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False,
        server_default=func.now()),
)
