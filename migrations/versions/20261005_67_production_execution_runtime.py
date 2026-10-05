"""Persist production workspace size and cleanup governance.

Revision ID: 20261005_67
Revises: 20261005_66
"""

from alembic import op
import sqlalchemy as sa


revision = "20261005_67"
down_revision = "20261005_66"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "execution_resource_envelopes",
        sa.Column("max_workspace_bytes", sa.BigInteger(), nullable=False,
                  server_default="536870912"),
    )
    op.add_column(
        "execution_workspaces",
        sa.Column("cleanup_status", sa.String(32), nullable=False,
                  server_default="RETAINED"),
    )


def downgrade() -> None:
    op.drop_column("execution_workspaces", "cleanup_status")
    op.drop_column("execution_resource_envelopes", "max_workspace_bytes")
