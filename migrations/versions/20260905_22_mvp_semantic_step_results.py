"""Persist governed semantic Steering Step results.

Revision ID: 20260905_22
Revises: 20260905_21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260905_22"
down_revision: str | None = "20260905_21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semantic_step_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("steering_plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("step_type", sa.String(length=32), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("result_kind", sa.String(length=32), nullable=False),
        sa.Column("bounded_summary", sa.Text(), nullable=False),
        sa.Column("decisions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "derived_constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "unresolved_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("authority_assessment", sa.String(length=32), nullable=False),
        sa.Column("human_attention_recommendation", sa.Text(), nullable=True),
        sa.Column(
            "proposed_production",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("reasoning_provider_identity", sa.String(length=255), nullable=True),
        sa.Column("completion_satisfied", sa.Boolean(), nullable=False),
        sa.Column("material_direction_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "authority_assessment IN ('WITHIN_AUTHORITY', 'UNCERTAIN', 'EXPANDS_AUTHORITY')",
            name="ck_semantic_step_results_authority_assessment_known",
        ),
        sa.CheckConstraint(
            "result_kind IN ('DESIGN_DIRECTION', 'WORK_REFINEMENT')",
            name="ck_semantic_step_results_result_kind_known",
        ),
        sa.CheckConstraint(
            "step_type IN ('DESIGN', 'REFINE')",
            name="ck_semantic_step_results_step_type_known",
        ),
        sa.ForeignKeyConstraint(
            ["steering_plan_revision_id"],
            ["steering_plan_revisions.id"],
            name="fk_semantic_step_results_revision",
        ),
        sa.ForeignKeyConstraint(
            ["step_id"],
            ["steering_steps.id"],
            name="fk_semantic_step_results_step",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["product_works.id"],
            name="fk_semantic_step_results_work",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_semantic_step_results"),
        sa.UniqueConstraint(
            "step_id",
            "basis_fingerprint",
            name="uq_semantic_step_results_step_basis",
        ),
    )


def downgrade() -> None:
    op.drop_table("semantic_step_results")
