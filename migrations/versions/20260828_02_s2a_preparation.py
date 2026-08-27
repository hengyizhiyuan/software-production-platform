"""Add S2-A Context Package and Attempt preparation bindings.

Revision ID: 20260828_02
Revises: 20260827_01
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260828_02"
down_revision: str | None = "20260827_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "context_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "completion_contract_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_context_packages_plan_revision",
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_context_packages_run",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_context_packages_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["work_unit_id"],
            ["production_work_units.id"],
            name="fk_context_packages_work_unit",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_unit_id",
            "version",
            name="uq_context_packages_work_unit_version",
        ),
    )
    op.create_table(
        "attempt_preparations",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("context_package_id", sa.Uuid(), nullable=False),
        sa.Column("executor_binding", postgresql.JSONB(), nullable=False),
        sa.Column("workspace_identity", sa.String(length=255), nullable=False),
        sa.Column("workspace_path", sa.String(length=2048), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("repository_path", sa.String(length=2048), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column(
            "prepared_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["execution_attempts.id"],
            name="fk_attempt_preparations_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["context_package_id"],
            ["context_packages.id"],
            name="fk_attempt_preparations_context",
        ),
        sa.PrimaryKeyConstraint("attempt_id"),
        sa.UniqueConstraint("workspace_identity"),
        sa.UniqueConstraint("workspace_path"),
    )


def downgrade() -> None:
    op.drop_table("attempt_preparations")
    op.drop_table("context_packages")
