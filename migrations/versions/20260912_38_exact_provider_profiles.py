"""bind native resource envelopes to exact permitted provider profiles

Revision ID: 20260912_38
Revises: 20260912_37
Create Date: 2026-09-12 14:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260912_38"
down_revision: str | Sequence[str] | None = "20260912_37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "execution_resource_envelopes",
        sa.Column(
            "permitted_provider_profiles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.execute(
        """
        UPDATE execution_resource_envelopes
        SET permitted_provider_profiles = jsonb_build_array(provider_profile)
        WHERE permitted_provider_profiles = '[]'::jsonb
        """
    )


def downgrade() -> None:
    op.drop_column(
        "execution_resource_envelopes", "permitted_provider_profiles"
    )
