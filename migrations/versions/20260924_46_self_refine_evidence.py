"""Persist auditable Self-Refine episodes and append-only repair actions.

Revision ID: 20260924_46
Revises: 20260923_45
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260924_46"
down_revision = "20260923_45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "self_refine_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_family", sa.String(64), nullable=False),
        sa.Column("failure_signature", sa.String(64), nullable=False),
        sa.Column("affected_component", sa.String(255), nullable=False),
        sa.Column("expected_reality", postgresql.JSONB(), nullable=False),
        sa.Column("observed_reality", postgresql.JSONB(), nullable=False),
        sa.Column("diagnosis_summary", sa.Text(), nullable=False),
        sa.Column("root_cause_classification", sa.String(64), nullable=False),
        sa.Column("repair_hypothesis", sa.Text(), nullable=False),
        sa.Column("evidence_references", postgresql.JSONB(), nullable=False),
        sa.Column("final_result", sa.String(32), nullable=True),
        sa.Column("work_resume_result", sa.String(64), nullable=True),
        sa.Column("extra_elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column("model_token_usage", postgresql.JSONB(), nullable=False),
        sa.Column("compute_overhead", postgresql.JSONB(), nullable=False),
        sa.Column("known_failure_match", sa.Boolean(), nullable=False),
        sa.Column("platform_improvement_candidate_ref", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_self_refine_events_work_created", "self_refine_events", ["work_id", "created_at"])
    op.create_index("ix_self_refine_events_signature", "self_refine_events", ["failure_signature"])
    op.create_index("ix_self_refine_events_status", "self_refine_events", ["status"])
    op.create_table(
        "self_refine_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("self_refine_events.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("repair_action", sa.Text(), nullable=False),
        sa.Column("observed_reality", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_references", postgresql.JSONB(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.UniqueConstraint("event_id", "sequence", name="uq_self_refine_actions_sequence"),
    )


def downgrade() -> None:
    op.drop_table("self_refine_actions")
    op.drop_index("ix_self_refine_events_status", table_name="self_refine_events")
    op.drop_index("ix_self_refine_events_signature", table_name="self_refine_events")
    op.drop_index("ix_self_refine_events_work_created", table_name="self_refine_events")
    op.drop_table("self_refine_events")
