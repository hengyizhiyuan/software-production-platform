"""Durable customer connection and exact ECS Delivery evidence owners."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Uuid
from sqlalchemy.dialects.postgresql import JSONB

from spg.infrastructure.persistence.metadata import metadata


cloud_connections = Table(
    "cloud_connections", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("owner_id", String(255), nullable=False, index=True),
    Column("state", String(48), nullable=False),
    Column("version", Integer, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

cloud_prepared_artifacts = Table(
    "cloud_prepared_artifacts", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("manifest_id", Uuid(as_uuid=True), ForeignKey("work_delivery_manifests.id"),
           nullable=False, unique=True),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

cloud_delivery_authorizations = Table(
    "cloud_delivery_authorizations", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("connection_id", Uuid(as_uuid=True), ForeignKey("cloud_connections.id"), nullable=False),
    Column("manifest_id", Uuid(as_uuid=True), ForeignKey("work_delivery_manifests.id"), nullable=False),
    Column("actor_id", String(255), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

cloud_deployments = Table(
    "cloud_deployments", metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("authorization_id", Uuid(as_uuid=True), ForeignKey("cloud_delivery_authorizations.id"),
           nullable=False, unique=True),
    Column("connection_id", Uuid(as_uuid=True), ForeignKey("cloud_connections.id"), nullable=False),
    Column("manifest_id", Uuid(as_uuid=True), ForeignKey("work_delivery_manifests.id"), nullable=False),
    Column("state", String(48), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
