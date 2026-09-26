"""Durable Work convergence lineage within the existing refinement capability.

Revision ID: 20260927_58
Revises: 20260926_57
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260927_58"
down_revision = "20260926_57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("work_convergence_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("intent_identity", sa.String(64), nullable=False),
        sa.Column("predecessor_id", sa.Uuid()),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("boundary", sa.String(128), nullable=False),
        sa.Column("failure_signature", sa.String(64)),
        sa.Column("candidate_identity", sa.String(255)),
        sa.Column("reality_identity", sa.String(64), nullable=False),
        sa.Column("missing_acceptance", JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("no_progress_count", sa.Integer(), nullable=False),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False),
        sa.Column("token_usage", JSONB(), nullable=False),
        sa.Column("model_cost", JSONB(), nullable=False),
        sa.Column("compute_cost", JSONB(), nullable=False),
        sa.Column("human_intervention_count", sa.Integer(), nullable=False),
        sa.Column("previous_repair_class", sa.String(64)),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("evidence", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("work_id", "sequence", name="uq_work_convergence_sequence"))
    op.create_index("ix_work_convergence_intent", "work_convergence_observations",
        ["work_id", "intent_identity"])


def downgrade() -> None:
    op.drop_index("ix_work_convergence_intent", table_name="work_convergence_observations")
    op.drop_table("work_convergence_observations")
