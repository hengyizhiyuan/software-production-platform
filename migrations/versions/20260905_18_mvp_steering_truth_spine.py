"""Add the long-lived Steering Plan truth spine.

Revision ID: 20260905_18
Revises: 20260904_17
Create Date: 2026-09-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260905_18"
down_revision: str | None = "20260904_17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "steering_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["work_id"], ["product_works.id"], name="fk_steering_plans_work"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_steering_plans"),
        sa.UniqueConstraint("work_id", name="uq_steering_plans_work_id"),
    )
    op.create_table(
        "steering_plan_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("steering_plan_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("supersedes_revision_id", sa.Uuid(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reality_refs", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "condition IN ('ACTIVE', 'SUPERSEDED')",
            name="ck_steering_plan_revisions_revision_condition_known",
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_steering_plan_revisions_revision_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["steering_plan_id"],
            ["steering_plans.id"],
            name="fk_steering_plan_revisions_plan",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["steering_plan_revisions.id"],
            name="fk_steering_plan_revisions_supersedes",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["product_works.id"],
            name="fk_steering_plan_revisions_work",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_steering_plan_revisions"),
        sa.UniqueConstraint(
            "steering_plan_id",
            "revision_number",
            name="uq_steering_plan_revisions_plan_revision",
        ),
        sa.UniqueConstraint(
            "supersedes_revision_id",
            name="uq_steering_plan_revisions_supersedes_revision_id",
        ),
    )
    op.create_index(
        "uq_steering_plan_revisions_one_active",
        "steering_plan_revisions",
        ["steering_plan_id"],
        unique=True,
        postgresql_where=sa.text("condition = 'ACTIVE'"),
    )
    op.create_table(
        "steering_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("steering_plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("completion_condition", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("elaborates_step_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_steering_steps_step_position_positive",
        ),
        sa.CheckConstraint(
            "state IN ('KNOWN', 'CURRENT', 'CLOSED', 'SUPERSEDED')",
            name="ck_steering_steps_step_state_known",
        ),
        sa.CheckConstraint(
            "type IN ('REFINE', 'HUMAN_DECISION', 'DESIGN', 'PRODUCE', "
            "'VERIFY_ACCEPT', 'COMPLETE')",
            name="ck_steering_steps_step_type_known",
        ),
        sa.ForeignKeyConstraint(
            ["elaborates_step_id"],
            ["steering_steps.id"],
            name="fk_steering_steps_elaborates",
        ),
        sa.ForeignKeyConstraint(
            ["steering_plan_revision_id"],
            ["steering_plan_revisions.id"],
            name="fk_steering_steps_revision",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_steering_steps"),
    )
    op.create_index(
        "uq_steering_steps_active_position",
        "steering_steps",
        ["steering_plan_revision_id", "position"],
        unique=True,
        postgresql_where=sa.text("state <> 'SUPERSEDED'"),
    )
    op.create_index(
        "uq_steering_steps_one_current_per_revision",
        "steering_steps",
        ["steering_plan_revision_id"],
        unique=True,
        postgresql_where=sa.text("state = 'CURRENT'"),
    )
    op.create_table(
        "steering_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("steering_plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("current_step_id", sa.Uuid(), nullable=False),
        sa.Column("next_step_type", sa.String(length=32), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reality_refs", postgresql.JSONB(), nullable=False),
        sa.Column("human_required", sa.Boolean(), nullable=False),
        sa.Column("completion_condition", sa.Text(), nullable=False),
        sa.Column("steering_outcome", sa.String(length=32), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("reasoning_provider_identity", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(steering_outcome = 'HUMAN_ATTENTION' AND human_required) OR "
            "(steering_outcome <> 'HUMAN_ATTENTION' AND NOT human_required)",
            name="ck_steering_decisions_human_outcome_consistent",
        ),
        sa.CheckConstraint(
            "(steering_outcome = 'COMPLETE' AND next_step_type = 'COMPLETE') OR "
            "(steering_outcome <> 'COMPLETE' AND next_step_type <> 'COMPLETE')",
            name="ck_steering_decisions_complete_outcome_consistent",
        ),
        sa.CheckConstraint(
            "steering_outcome IN ('AUTO_CONTINUE', 'HUMAN_ATTENTION', 'COMPLETE')",
            name="ck_steering_decisions_decision_outcome_known",
        ),
        sa.CheckConstraint(
            "next_step_type IN ('REFINE', 'HUMAN_DECISION', 'DESIGN', 'PRODUCE', "
            "'VERIFY_ACCEPT', 'COMPLETE')",
            name="ck_steering_decisions_decision_step_type_known",
        ),
        sa.ForeignKeyConstraint(
            ["current_step_id"],
            ["steering_steps.id"],
            name="fk_steering_decisions_current_step",
        ),
        sa.ForeignKeyConstraint(
            ["steering_plan_revision_id"],
            ["steering_plan_revisions.id"],
            name="fk_steering_decisions_revision",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_steering_decisions"),
        sa.UniqueConstraint(
            "basis_fingerprint", name="uq_steering_decisions_basis_fingerprint"
        ),
    )
    op.create_table(
        "steering_history_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("steering_plan_id", sa.Uuid(), nullable=False),
        sa.Column("steering_plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_revision_id", sa.Uuid(), nullable=True),
        sa.Column("to_revision_id", sa.Uuid(), nullable=True),
        sa.Column("from_step_id", sa.Uuid(), nullable=True),
        sa.Column("to_step_id", sa.Uuid(), nullable=True),
        sa.Column("steering_decision_id", sa.Uuid(), nullable=True),
        sa.Column("related_step_ids", postgresql.JSONB(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reality_refs", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('STEP_TRANSITION', 'STEP_ELABORATION', 'PLAN_REVISION')",
            name="ck_steering_history_events_event_type_known",
        ),
        sa.ForeignKeyConstraint(
            ["from_revision_id"],
            ["steering_plan_revisions.id"],
            name="fk_steering_history_from_revision",
        ),
        sa.ForeignKeyConstraint(
            ["from_step_id"],
            ["steering_steps.id"],
            name="fk_steering_history_from_step",
        ),
        sa.ForeignKeyConstraint(
            ["steering_decision_id"],
            ["steering_decisions.id"],
            name="fk_steering_history_decision",
        ),
        sa.ForeignKeyConstraint(
            ["steering_plan_id"],
            ["steering_plans.id"],
            name="fk_steering_history_plan",
        ),
        sa.ForeignKeyConstraint(
            ["steering_plan_revision_id"],
            ["steering_plan_revisions.id"],
            name="fk_steering_history_revision",
        ),
        sa.ForeignKeyConstraint(
            ["to_revision_id"],
            ["steering_plan_revisions.id"],
            name="fk_steering_history_to_revision",
        ),
        sa.ForeignKeyConstraint(
            ["to_step_id"],
            ["steering_steps.id"],
            name="fk_steering_history_to_step",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_steering_history_events"),
    )


def downgrade() -> None:
    op.drop_table("steering_history_events")
    op.drop_table("steering_decisions")
    op.drop_index(
        "uq_steering_steps_one_current_per_revision",
        table_name="steering_steps",
        postgresql_where=sa.text("state = 'CURRENT'"),
    )
    op.drop_index(
        "uq_steering_steps_active_position",
        table_name="steering_steps",
        postgresql_where=sa.text("state <> 'SUPERSEDED'"),
    )
    op.drop_table("steering_steps")
    op.drop_index(
        "uq_steering_plan_revisions_one_active",
        table_name="steering_plan_revisions",
        postgresql_where=sa.text("condition = 'ACTIVE'"),
    )
    op.drop_table("steering_plan_revisions")
    op.drop_table("steering_plans")
