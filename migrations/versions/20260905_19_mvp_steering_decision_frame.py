"""Add MVP Steering decision and Human Attention detail.

Revision ID: 20260905_19
Revises: 20260905_18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260905_19"
down_revision: str | None = "20260905_18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "steering_decisions",
        sa.Column("attention_reason", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "steering_decisions",
        sa.Column("recommendation", sa.Text(), nullable=True),
    )
    op.add_column(
        "steering_decisions",
        sa.Column(
            "alternatives",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "steering_decisions",
        sa.Column(
            "trade_offs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "steering_decisions",
        sa.Column("expected_impact", sa.Text(), nullable=True),
    )
    op.add_column(
        "steering_decisions",
        sa.Column("authority_assessment", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "steering_decisions",
        sa.Column(
            "proposed_engineering_scope_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_steering_decisions_attention_reason_known",
        "steering_decisions",
        "attention_reason IS NULL OR attention_reason IN "
        "('MOTIVE_OR_OUTCOME_AMBIGUITY', "
        "'MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION', "
        "'SCOPE_OR_AUTHORITY_EXPANSION', "
        "'MATERIAL_RISK_OR_COST_DECISION', "
        "'PRODUCT_ACCEPTANCE_REQUIRED')",
    )
    op.create_check_constraint(
        "ck_steering_decisions_authority_assessment_known",
        "steering_decisions",
        "authority_assessment IS NULL OR authority_assessment IN "
        "('WITHIN_AUTHORITY', 'UNCERTAIN', 'EXPANDS_AUTHORITY')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_steering_decisions_authority_assessment_known",
        "steering_decisions",
        type_="check",
    )
    op.drop_constraint(
        "ck_steering_decisions_attention_reason_known",
        "steering_decisions",
        type_="check",
    )
    op.drop_column("steering_decisions", "proposed_engineering_scope_fingerprint")
    op.drop_column("steering_decisions", "authority_assessment")
    op.drop_column("steering_decisions", "expected_impact")
    op.drop_column("steering_decisions", "trade_offs")
    op.drop_column("steering_decisions", "alternatives")
    op.drop_column("steering_decisions", "recommendation")
    op.drop_column("steering_decisions", "attention_reason")
