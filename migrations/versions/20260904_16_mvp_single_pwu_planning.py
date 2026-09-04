"""Add durable single-PWU Production Plan proposals.

Revision ID: 20260904_16
Revises: 20260903_15
Create Date: 2026-09-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260904_16"
down_revision: str | None = "20260903_15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_works",
        sa.Column("production_plan_proposal", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_works", "production_plan_proposal")
