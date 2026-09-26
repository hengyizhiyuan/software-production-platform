"""Persist qualified evaluation reports and baseline lineage.

Revision ID: 20260926_57
Revises: 20260926_56
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260926_57"
down_revision = "20260926_56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("evaluation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.String(128), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("corpus_version", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("qualification", sa.String(16), nullable=False),
        sa.Column("baseline_run_id", sa.Uuid(), sa.ForeignKey("evaluation_runs.id")),
        sa.Column("report", JSONB(), nullable=False),
        sa.Column("trend", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_evaluation_runs_purpose_created", "evaluation_runs", ["purpose", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_runs_purpose_created", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
