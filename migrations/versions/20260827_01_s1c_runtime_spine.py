"""Create the S1-C minimum durable Runtime spine.

Revision ID: 20260827_01
Revises:
Create Date: 2026-08-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260827_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "production_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("repository_ref", sa.String(length=512), nullable=False),
        sa.Column("repository_revision", sa.String(length=64), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_snapshots_source_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "current_trusted_baseline_pointer",
        sa.Column("singleton_id", sa.SmallInteger(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("singleton_id = 1", name="singleton_id_is_one"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["production_snapshots.id"],
            name="fk_baseline_pointer_snapshot",
        ),
        sa.PrimaryKeyConstraint("singleton_id"),
    )
    op.create_table(
        "production_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("intent_ref", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("production_horizon", sa.String(length=64), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("current_plan_revision_id", sa.Uuid(), nullable=True),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_runs_source_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "plan_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_plan_revisions_run",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_plan_revisions_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "production_run_id",
            "revision_number",
            name="uq_plan_revisions_run_revision",
        ),
    )
    op.create_index(
        "uq_plan_revisions_one_active_per_run",
        "plan_revisions",
        ["production_run_id"],
        unique=True,
        postgresql_where=sa.text("condition = 'ACTIVE'"),
    )
    op.create_foreign_key(
        "fk_runs_current_plan_revision",
        "production_runs",
        "plan_revisions",
        ["current_plan_revision_id"],
        ["id"],
    )
    op.create_table(
        "production_work_units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("completion_contract", postgresql.JSONB(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("current_execution_generation", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_work_units_plan_revision",
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_work_units_run",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_work_units_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "execution_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("context_ref", sa.String(length=255), nullable=True),
        sa.Column("provider_ref", sa.String(length=255), nullable=True),
        sa.Column("workspace_ref", sa.String(length=1024), nullable=True),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("retry_of", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_attempts_plan_revision",
        ),
        sa.ForeignKeyConstraint(
            ["retry_of"],
            ["execution_attempts.id"],
            name="fk_attempts_retry_of",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_attempts_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["work_unit_id"],
            ["production_work_units.id"],
            name="fk_attempts_work_unit",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_unit_id",
            "generation",
            name="uq_execution_attempts_work_unit_generation",
        ),
    )
    op.create_table(
        "governance_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decision_type", sa.String(length=64), nullable=False),
        sa.Column("authority_identity", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_identity", sa.String(length=255), nullable=False),
        sa.Column("scope", postgresql.JSONB(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "transition_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_identity", sa.String(length=255), nullable=False),
        sa.Column("from_condition", sa.String(length=64), nullable=True),
        sa.Column("to_condition", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("actor_identity", sa.String(length=255), nullable=False),
        sa.Column("correlation_identity", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("transition_history")
    op.drop_table("governance_records")
    op.drop_table("execution_attempts")
    op.drop_table("production_work_units")
    op.drop_constraint(
        "fk_runs_current_plan_revision",
        "production_runs",
        type_="foreignkey",
    )
    op.drop_index(
        "uq_plan_revisions_one_active_per_run",
        table_name="plan_revisions",
    )
    op.drop_table("plan_revisions")
    op.drop_table("production_runs")
    op.drop_table("current_trusted_baseline_pointer")
    op.drop_table("production_snapshots")
