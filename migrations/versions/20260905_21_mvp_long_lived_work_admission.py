"""Separate long-lived Work admission from immediate production admission.

Revision ID: 20260905_21
Revises: 20260905_20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260905_21"
down_revision: str | None = "20260905_20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_works",
        sa.Column(
            "work_mode",
            sa.String(length=32),
            nullable=False,
            server_default="IMMEDIATE_PRODUCTION",
        ),
    )
    op.create_check_constraint(
        "ck_product_works_work_mode_known",
        "product_works",
        "work_mode IN ('IMMEDIATE_PRODUCTION', 'LONG_LIVED_STEERING')",
    )
    op.alter_column("product_works", "work_mode", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_product_works_work_mode_known",
        "product_works",
        type_="check",
    )
    op.drop_column("product_works", "work_mode")
