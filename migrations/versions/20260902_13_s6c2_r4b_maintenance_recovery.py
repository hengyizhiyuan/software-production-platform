"""Add verified maintenance recovery admission and supersession concurrency.

Revision ID: 20260902_13
Revises: 20260829_12
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260902_13"
down_revision: str | None = "20260829_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plan_revisions",
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "maintenance_recovery_admissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("old_trusted_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("new_trusted_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("expected_pointer_version", sa.Integer(), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("authoritative_ref", sa.String(length=512), nullable=False),
        sa.Column("target_commit", sa.String(length=128), nullable=False),
        sa.Column("target_tree", sa.String(length=128), nullable=False),
        sa.Column("maintenance_purpose", sa.Text(), nullable=False),
        sa.Column("approved_changed_paths", postgresql.JSONB(), nullable=False),
        sa.Column("verification_evidence", postgresql.JSONB(), nullable=False),
        sa.Column("maintenance_evidence_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("authority", postgresql.JSONB(), nullable=False),
        sa.Column("maintenance_authority_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("governance_record_id", sa.Uuid(), nullable=False),
        sa.Column("recovery_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("recovery_assessment_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("old_run_id", sa.Uuid(), nullable=False),
        sa.Column("old_plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("old_work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("old_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("new_run_id", sa.Uuid(), nullable=False),
        sa.Column("new_plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("new_work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("governance_contract_snapshot_identity", sa.String(length=255), nullable=False),
        sa.Column("governance_contract_snapshot_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("external_intent_ref", sa.String(length=255), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column(
            "admitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "expected_pointer_version >= 0",
            name="maintenance_recovery_pointer_version_nonnegative",
        ),
        sa.CheckConstraint(
            "outcome = 'APPLIED'",
            name="maintenance_recovery_outcome_is_applied",
        ),
        sa.ForeignKeyConstraint(
            ["governance_record_id"],
            ["governance_records.id"],
            name="fk_maintenance_recovery_governance",
        ),
        sa.ForeignKeyConstraint(
            ["new_plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_maintenance_recovery_new_plan",
        ),
        sa.ForeignKeyConstraint(
            ["new_run_id"],
            ["production_runs.id"],
            name="fk_maintenance_recovery_new_run",
        ),
        sa.ForeignKeyConstraint(
            ["new_trusted_baseline_id"],
            ["production_snapshots.id"],
            name="fk_maintenance_recovery_new_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["new_work_unit_id"],
            ["production_work_units.id"],
            name="fk_maintenance_recovery_new_work_unit",
        ),
        sa.ForeignKeyConstraint(
            ["old_attempt_id"],
            ["execution_attempts.id"],
            name="fk_maintenance_recovery_old_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["old_plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_maintenance_recovery_old_plan",
        ),
        sa.ForeignKeyConstraint(
            ["old_run_id"],
            ["production_runs.id"],
            name="fk_maintenance_recovery_old_run",
        ),
        sa.ForeignKeyConstraint(
            ["old_trusted_baseline_id"],
            ["production_snapshots.id"],
            name="fk_maintenance_recovery_old_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["old_work_unit_id"],
            ["production_work_units.id"],
            name="fk_maintenance_recovery_old_work_unit",
        ),
        sa.ForeignKeyConstraint(
            ["recovery_assessment_id"],
            ["recovery_assessments.id"],
            name="fk_maintenance_recovery_assessment",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("governance_record_id"),
        sa.UniqueConstraint("new_plan_revision_id"),
        sa.UniqueConstraint("new_run_id"),
        sa.UniqueConstraint("new_trusted_baseline_id"),
        sa.UniqueConstraint("new_work_unit_id"),
        sa.UniqueConstraint("old_attempt_id"),
        sa.UniqueConstraint("old_plan_revision_id"),
        sa.UniqueConstraint("old_run_id"),
        sa.UniqueConstraint("old_work_unit_id"),
        sa.UniqueConstraint("operation_fingerprint"),
        sa.UniqueConstraint("recovery_assessment_id"),
    )


def downgrade() -> None:
    op.drop_table("maintenance_recovery_admissions")
    op.drop_column("plan_revisions", "version")
