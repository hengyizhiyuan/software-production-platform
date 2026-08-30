"""Add exact durable Materialized Execution Input for S6-B1.

Revision ID: 20260829_12
Revises: 20260829_11
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260829_12"
down_revision: str | None = "20260829_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "materialized_execution_inputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("context_package_id", sa.Uuid(), nullable=False),
        sa.Column("context_package_version", sa.Integer(), nullable=False),
        sa.Column(
            "context_package_content_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "completion_contract_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("prepared_execution_request", postgresql.JSONB(), nullable=False),
        sa.Column("instruction_content", sa.Text(), nullable=False),
        sa.Column("context_projection", postgresql.JSONB(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "context_package_version > 0",
            name="materialized_input_context_version_positive",
        ),
        sa.CheckConstraint(
            "generation > 0",
            name="materialized_input_generation_positive",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["execution_attempts.id"],
            name="fk_materialized_inputs_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["context_package_id"],
            ["context_packages.id"],
            name="fk_materialized_inputs_context",
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_materialized_inputs_plan",
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_materialized_inputs_run",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_materialized_inputs_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["work_unit_id"],
            ["production_work_units.id"],
            name="fk_materialized_inputs_work_unit",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id"),
        sa.UniqueConstraint("input_fingerprint"),
    )


def downgrade() -> None:
    op.drop_table("materialized_execution_inputs")
