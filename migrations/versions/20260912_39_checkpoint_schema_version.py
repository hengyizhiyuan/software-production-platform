"""version native execution checkpoint bundles

Revision ID: 20260912_39
Revises: 20260912_38
Create Date: 2026-09-12 20:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_39"
down_revision: str | Sequence[str] | None = "20260912_38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "checkpoint_bundles",
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.create_check_constraint(
        "ck_checkpoint_bundles_schema_version_positive",
        "checkpoint_bundles",
        "schema_version > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_checkpoint_bundles_schema_version_positive",
        "checkpoint_bundles",
        type_="check",
    )
    op.drop_column("checkpoint_bundles", "schema_version")
