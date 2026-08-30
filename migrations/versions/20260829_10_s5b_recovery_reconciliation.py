"""Add narrow S5-B Recovery Action records.

Revision ID: 20260829_10
Revises: 20260829_09
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_10"
down_revision: str | None = "20260829_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recovery_action_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recovery_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_identity", sa.String(length=255), nullable=False),
        sa.Column("integration_effect_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("runtime_commit_id", sa.Uuid(), nullable=True),
        sa.Column("action_basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("observed_repository_revision", sa.String(length=128), nullable=False),
        sa.Column("observed_tree_identity", sa.String(length=128), nullable=False),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action_type IN ('RECORD_EXTERNAL_CONVERGENCE', 'RETRY_RUNTIME_COMMIT')",
            name="recovery_action_type_is_narrow",
        ),
        sa.CheckConstraint(
            "subject_type = 'REPOSITORY_INTEGRATION'",
            name="recovery_action_subject_is_repository_integration",
        ),
        sa.CheckConstraint(
            "outcome IN ('APPLIED', 'NO_ACTION')",
            name="recovery_action_outcome_is_known",
        ),
        sa.ForeignKeyConstraint(
            ["recovery_assessment_id"],
            ["recovery_assessments.id"],
            name="fk_recovery_actions_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["integration_effect_id"],
            ["repository_integration_effects.id"],
            name="fk_recovery_actions_effect",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["baseline_candidates.id"],
            name="fk_recovery_actions_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_commit_id"],
            ["runtime_commits.id"],
            name="fk_recovery_actions_runtime_commit",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "action_basis_fingerprint",
            name="uq_recovery_actions_basis",
        ),
        sa.UniqueConstraint(
            "recovery_assessment_id",
            "action_type",
            name="uq_recovery_action_assessment_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("recovery_action_records")
