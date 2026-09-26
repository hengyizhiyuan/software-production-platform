"""Minimal single-owner authority seam for current self-dogfood runtime."""

from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.sql import func

from spg.infrastructure.persistence.metadata import metadata


authority_actors = Table(
    "authority_actors", metadata,
    Column("id", String(255), primary_key=True),
    Column("kind", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

authority_memberships = Table(
    "authority_memberships", metadata,
    Column("organization_id", String(255), primary_key=True),
    Column("actor_id", String(255), ForeignKey("authority_actors.id"), primary_key=True),
    Column("role", String(32), nullable=False),
)

authority_resource_access = Table(
    "authority_resource_access", metadata,
    Column("resource_kind", String(32), primary_key=True),
    Column("resource_id", String(64), primary_key=True),
    Column("actor_id", String(255), ForeignKey("authority_actors.id"), primary_key=True),
    Column("role", String(32), nullable=False),
)
