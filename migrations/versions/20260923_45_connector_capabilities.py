"""persist scoped connector capability facts and resumable gaps

Revision ID: 20260923_45
Revises: 20260919_44
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260923_45"
down_revision = "20260919_44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_capabilities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_scope", sa.String(32), nullable=False),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("capability_id", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_scope", "owner_id", "capability_id", "version", name="uq_connector_capability_owner_version"),
    )
    op.create_table(
        "capability_gaps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_id", sa.Uuid(), sa.ForeignKey("product_works.id"), nullable=False),
        sa.Column("capability_id", sa.String(255), nullable=False),
        sa.Column("operation_ref", sa.String(255), nullable=False),
        sa.Column("resume_point", postgresql.JSONB(), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("work_id", "capability_id", "operation_ref", name="uq_capability_gap_work_operation"),
    )
    op.create_index("ix_capability_gaps_work_condition", "capability_gaps", ["work_id", "condition"])


def downgrade() -> None:
    op.drop_index("ix_capability_gaps_work_condition", table_name="capability_gaps")
    op.drop_table("capability_gaps")
    op.drop_table("connector_capabilities")
