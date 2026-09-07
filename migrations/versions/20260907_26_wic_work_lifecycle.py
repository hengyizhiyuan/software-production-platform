"""Add WIC Work-satisfaction continuation transition provenance.

Revision ID: 20260907_26
Revises: 20260907_25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260907_26"
down_revision: str | None = "20260907_25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interaction_work_transitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=False),
        sa.Column("source_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("originating_work_id", sa.Uuid(), nullable=False),
        sa.Column("target_work_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("focus_classification", sa.String(length=32), nullable=False),
        sa.Column("impact_disposition", sa.String(length=48), nullable=False),
        sa.Column("choice", sa.String(length=32), nullable=False),
        sa.Column("decided_by", sa.String(length=255), nullable=True),
        sa.Column("decision_rationale", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "focus_classification IN ('MATERIAL_BRANCH', 'UNRELATED_NEW_DEMAND')",
            name="ck_interaction_work_transitions_focus_known",
        ),
        sa.CheckConstraint(
            "impact_disposition = 'NEW_WORK_RECOMMENDED'",
            name="ck_interaction_work_transitions_impact_known",
        ),
        sa.CheckConstraint(
            "choice IN ('PENDING_HUMAN', 'CONTINUE_CURRENT_WORK', "
            "'START_NEW_WORK', 'DISMISSED')",
            name="ck_interaction_work_transitions_choice_known",
        ),
        sa.CheckConstraint(
            "(choice = 'PENDING_HUMAN' AND decided_by IS NULL AND decided_at IS NULL) "
            "OR (choice <> 'PENDING_HUMAN' AND decided_by IS NOT NULL "
            "AND decided_at IS NOT NULL)",
            name="ck_interaction_work_transitions_decision_coherent",
        ),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["product_interactions.id"],
            name="fk_interaction_work_transitions_interaction",
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["interaction_records.id"],
            name="fk_interaction_work_transitions_source_record",
        ),
        sa.ForeignKeyConstraint(
            ["source_assessment_id"],
            ["interaction_assessments.id"],
            name="fk_interaction_work_transitions_source_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["originating_work_id"],
            ["product_works.id"],
            name="fk_interaction_work_transitions_originating_work",
        ),
        sa.ForeignKeyConstraint(
            ["target_work_id"],
            ["product_works.id"],
            name="fk_interaction_work_transitions_target_work",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_assessment_id"),
        sa.UniqueConstraint("target_work_id"),
    )


def downgrade() -> None:
    op.drop_table("interaction_work_transitions")
