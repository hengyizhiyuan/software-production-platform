"""Persist advisory Design Intent Frames for reconstructable WIC understanding.

Revision ID: 20260909_29
Revises: 20260908_28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260909_29"
down_revision: str | None = "20260908_28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interaction_assessments",
        sa.Column(
            "design_intent_frame",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("interaction_assessments", "design_intent_frame")
