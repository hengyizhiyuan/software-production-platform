"""add exact native vector verification records

Revision ID: 20260912_37
Revises: 20260912_36
Create Date: 2026-09-12 09:35:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260912_37"
down_revision: str | Sequence[str] | None = "20260912_36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_vector_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pwu_id", sa.Uuid(), nullable=False),
        sa.Column("mount_id", sa.String(255), nullable=False),
        sa.Column("proposed_revision", sa.String(128), nullable=False),
        sa.Column("proposed_tree_identity", sa.String(128), nullable=False),
        sa.Column("obligation", sa.Text(), nullable=False),
        sa.Column("provider_identity", sa.String(255), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pwu_id"], ["production_work_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pwu_id", "mount_id", "proposed_revision", "obligation", "provider_identity",
            name="uq_native_vector_verification_basis",
        ),
    )


def downgrade() -> None:
    op.drop_table("native_vector_verifications")
