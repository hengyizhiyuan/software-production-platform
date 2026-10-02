"""Persist governed Alibaba Cloud connection and exact ECS Delivery Reality."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261002_65"
down_revision = "20261001_64"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("cloud_connections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("state", sa.String(48), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_cloud_connections_owner_id", "cloud_connections", ["owner_id"])
    op.create_table("cloud_prepared_artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("manifest_id", sa.Uuid(), sa.ForeignKey("work_delivery_manifests.id"),
                  nullable=False, unique=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("cloud_delivery_authorizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("connection_id", sa.Uuid(), sa.ForeignKey("cloud_connections.id"), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), sa.ForeignKey("work_delivery_manifests.id"), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("cloud_deployments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("authorization_id", sa.Uuid(), sa.ForeignKey("cloud_delivery_authorizations.id"),
                  nullable=False, unique=True),
        sa.Column("connection_id", sa.Uuid(), sa.ForeignKey("cloud_connections.id"), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), sa.ForeignKey("work_delivery_manifests.id"), nullable=False),
        sa.Column("state", sa.String(48), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("cloud_deployments")
    op.drop_table("cloud_delivery_authorizations")
    op.drop_table("cloud_prepared_artifacts")
    op.drop_index("ix_cloud_connections_owner_id", table_name="cloud_connections")
    op.drop_table("cloud_connections")
