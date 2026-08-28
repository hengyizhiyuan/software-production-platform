"""Add S3-B proposed snapshot, Verification, and admissibility facts.

Revision ID: 20260828_05
Revises: 20260828_04
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260828_05"
down_revision: str | None = "20260828_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proposed_repository_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("completion_evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("repository_observation_id", sa.Uuid(), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("repository_ref", sa.String(length=255), nullable=False),
        sa.Column("authoritative_ref_revision", sa.String(length=128), nullable=False),
        sa.Column("proposed_commit_identity", sa.String(length=128), nullable=False),
        sa.Column("tree_identity", sa.String(length=128), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["execution_attempts.id"], name="fk_proposed_snapshots_attempt"),
        sa.ForeignKeyConstraint(["completion_evaluation_id"], ["completion_evaluations.id"], name="fk_proposed_snapshots_completion"),
        sa.ForeignKeyConstraint(["plan_revision_id"], ["plan_revisions.id"], name="fk_proposed_snapshots_plan"),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], name="fk_proposed_snapshots_run"),
        sa.ForeignKeyConstraint(["repository_observation_id"], ["repository_observations.id"], name="fk_proposed_snapshots_observation"),
        sa.ForeignKeyConstraint(["source_baseline_id"], ["production_snapshots.id"], name="fk_proposed_snapshots_baseline"),
        sa.ForeignKeyConstraint(["work_unit_id"], ["production_work_units.id"], name="fk_proposed_snapshots_work_unit"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("basis_fingerprint", name="uq_proposed_snapshots_basis"),
        sa.UniqueConstraint("completion_evaluation_id", name="uq_proposed_snapshots_completion"),
    )
    op.create_table(
        "verification_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("completion_evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_commit_identity", sa.String(length=128), nullable=False),
        sa.Column("tree_identity", sa.String(length=128), nullable=False),
        sa.Column("obligation", sa.Text(), nullable=False),
        sa.Column("obligation_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider_binding", postgresql.JSONB(), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["completion_evaluation_id"], ["completion_evaluations.id"], name="fk_verification_records_completion"),
        sa.ForeignKeyConstraint(["plan_revision_id"], ["plan_revisions.id"], name="fk_verification_records_plan"),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], name="fk_verification_records_run"),
        sa.ForeignKeyConstraint(["proposed_snapshot_id"], ["proposed_repository_snapshots.id"], name="fk_verification_records_snapshot"),
        sa.ForeignKeyConstraint(["source_baseline_id"], ["production_snapshots.id"], name="fk_verification_records_baseline"),
        sa.ForeignKeyConstraint(["work_unit_id"], ["production_work_units.id"], name="fk_verification_records_work_unit"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("basis_fingerprint", name="uq_verification_records_basis"),
    )
    op.create_table(
        "production_admissibility_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("completion_evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("required_obligations_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("verification_record_ids", postgresql.JSONB(), nullable=False),
        sa.Column("obligation_results", postgresql.JSONB(), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["completion_evaluation_id"], ["completion_evaluations.id"], name="fk_admissibility_records_completion"),
        sa.ForeignKeyConstraint(["plan_revision_id"], ["plan_revisions.id"], name="fk_admissibility_records_plan"),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], name="fk_admissibility_records_run"),
        sa.ForeignKeyConstraint(["proposed_snapshot_id"], ["proposed_repository_snapshots.id"], name="fk_admissibility_records_snapshot"),
        sa.ForeignKeyConstraint(["source_baseline_id"], ["production_snapshots.id"], name="fk_admissibility_records_baseline"),
        sa.ForeignKeyConstraint(["work_unit_id"], ["production_work_units.id"], name="fk_admissibility_records_work_unit"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("basis_fingerprint", name="uq_admissibility_records_basis"),
    )


def downgrade() -> None:
    op.drop_table("production_admissibility_records")
    op.drop_table("verification_records")
    op.drop_table("proposed_repository_snapshots")
