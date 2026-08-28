"""Add S3-A immutable Completion Evaluation facts.

Revision ID: 20260828_04
Revises: 20260828_03
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260828_04"
down_revision: str | None = "20260828_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "completion_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column(
            "completion_contract_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("repository_observation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "repository_observation_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("work_product_lineage", postgresql.JSONB(), nullable=False),
        sa.Column(
            "work_product_set_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("obligation_results", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["execution_attempts.id"],
            name="fk_completion_evaluations_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_completion_evaluations_plan",
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_completion_evaluations_run",
        ),
        sa.ForeignKeyConstraint(
            ["repository_observation_id"],
            ["repository_observations.id"],
            name="fk_completion_evaluations_observation",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_completion_evaluations_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["work_unit_id"],
            ["production_work_units.id"],
            name="fk_completion_evaluations_work_unit",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "basis_fingerprint",
            name="uq_completion_evaluations_basis",
        ),
    )


def downgrade() -> None:
    op.drop_table("completion_evaluations")
