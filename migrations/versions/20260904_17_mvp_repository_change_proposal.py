"""Add durable repository-aware Code Change Proposal.

Revision ID: 20260904_17
Revises: 20260904_16
Create Date: 2026-09-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260904_17"
down_revision: str | None = "20260904_16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_works",
        sa.Column("code_change_proposal", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_works", "code_change_proposal")
