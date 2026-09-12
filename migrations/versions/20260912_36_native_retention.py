"""add native workspace retention actions and pins

Revision ID: 20260912_36
Revises: 20260912_35
Create Date: 2026-09-12 09:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260912_36"
down_revision: str | Sequence[str] | None = "20260912_35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_resource_pins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resource_kind", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(1024), nullable=False),
        sa.Column("owner_kind", sa.String(64), nullable=False),
        sa.Column("owner_id", sa.String(1024), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resource_kind", "resource_id", "owner_kind", "owner_id",
            name="uq_native_resource_pin_owner",
        ),
    )
    op.create_table(
        "native_retention_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("action_key", sa.String(64), nullable=False),
        sa.Column("action_kind", sa.String(32), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("bundle_digest", sa.String(64), nullable=True),
        sa.Column("bundle_path", sa.String(2048), nullable=True),
        sa.Column("physical_receipt", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["execution_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("action_key"),
    )
    op.create_table(
        "native_workspace_tombstones",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("pwu_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("last_bundle_digest", sa.String(64), nullable=True),
        sa.Column("retention_action_id", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id"),
        sa.UniqueConstraint("retention_action_id"),
    )


def downgrade() -> None:
    op.drop_table("native_workspace_tombstones")
    op.drop_table("native_retention_actions")
    op.drop_table("native_resource_pins")
