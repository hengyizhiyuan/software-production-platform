"""add progressive WIC semantics to interaction assessments

Revision ID: 20260915_40
Revises: 20260912_39
Create Date: 2026-09-15 18:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260915_40"
down_revision: str | Sequence[str] | None = "20260912_39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interaction_assessments",
        sa.Column("progressive_semantics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interaction_assessments", "progressive_semantics")
