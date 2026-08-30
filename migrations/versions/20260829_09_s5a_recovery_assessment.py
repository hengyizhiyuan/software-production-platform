"""Add the narrow S5-A immutable Recovery Assessment.

Revision ID: 20260829_09
Revises: 20260829_08
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260829_09"
down_revision: str | None = "20260829_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recovery_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_identity", sa.String(length=255), nullable=False),
        sa.Column("governed_basis", postgresql.JSONB(), nullable=False),
        sa.Column("observed_facts", postgresql.JSONB(), nullable=False),
        sa.Column("differences", postgresql.JSONB(), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("guidance", sa.String(length=64), nullable=False),
        sa.Column("subject_is_current", sa.SmallInteger(), nullable=False),
        sa.Column("safely_recoverable", sa.SmallInteger(), nullable=False),
        sa.Column("requires_human_attention", sa.SmallInteger(), nullable=False),
        sa.Column("recovery_barrier", sa.SmallInteger(), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "assessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subject_type IN ('ATTEMPT', 'REPOSITORY_INTEGRATION')",
            name="recovery_assessment_subject_is_narrow",
        ),
        sa.CheckConstraint(
            "classification IN "
            "('COHERENT', 'RECOVERABLE', 'UNKNOWN', 'DIVERGED', 'STALE', 'BLOCKED')",
            name="recovery_assessment_classification_is_known",
        ),
        sa.CheckConstraint(
            "subject_is_current IN (0, 1) AND safely_recoverable IN (0, 1) "
            "AND requires_human_attention IN (0, 1) "
            "AND recovery_barrier IN (0, 1)",
            name="recovery_assessment_flags_are_boolean",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "basis_fingerprint",
            name="uq_recovery_assessments_basis",
        ),
    )


def downgrade() -> None:
    op.drop_table("recovery_assessments")
