"""Add S2-B dispatch, provider report, observation, and Work Product facts.

Revision ID: 20260828_03
Revises: 20260828_02
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260828_03"
down_revision: str | None = "20260828_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_dispatches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("context_package_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("executor_binding", postgresql.JSONB(), nullable=False),
        sa.Column("workspace_identity", sa.String(length=255), nullable=False),
        sa.Column("workspace_path", sa.String(length=2048), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("repository_path", sa.String(length=2048), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("authoritative_ref_revision", sa.String(length=64), nullable=False),
        sa.Column(
            "dispatched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["execution_attempts.id"],
            name="fk_execution_dispatches_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["context_package_id"],
            ["context_packages.id"],
            name="fk_execution_dispatches_context",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_execution_dispatches_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", name="uq_execution_dispatches_attempt"),
    )
    op.create_table(
        "provider_execution_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dispatch_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("executor_binding", postgresql.JSONB(), nullable=False),
        sa.Column("provider_reference", sa.String(length=1024), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["execution_attempts.id"],
            name="fk_provider_reports_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["dispatch_id"],
            ["execution_dispatches.id"],
            name="fk_provider_reports_dispatch",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dispatch_id"),
    )
    op.create_table(
        "repository_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dispatch_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("workspace_identity", sa.String(length=255), nullable=False),
        sa.Column("workspace_path", sa.String(length=2048), nullable=False),
        sa.Column("authoritative_ref_revision", sa.String(length=64), nullable=False),
        sa.Column("change_manifest", postgresql.JSONB(), nullable=False),
        sa.Column("observation_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["execution_attempts.id"],
            name="fk_repository_observations_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["dispatch_id"],
            ["execution_dispatches.id"],
            name="fk_repository_observations_dispatch",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_repository_observations_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dispatch_id"),
    )
    op.create_table(
        "work_product_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("repository_observation_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_path", sa.String(length=2048), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("observed_fingerprint", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["execution_attempts.id"],
            name="fk_work_product_refs_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_work_product_refs_plan",
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_work_product_refs_run",
        ),
        sa.ForeignKeyConstraint(
            ["repository_observation_id"],
            ["repository_observations.id"],
            name="fk_work_product_refs_observation",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_work_product_refs_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["work_unit_id"],
            ["production_work_units.id"],
            name="fk_work_product_refs_work_unit",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "repository_observation_id",
            "artifact_path",
            name="uq_work_product_refs_observation_path",
        ),
    )


def downgrade() -> None:
    op.drop_table("work_product_references")
    op.drop_table("repository_observations")
    op.drop_table("provider_execution_reports")
    op.drop_table("execution_dispatches")
