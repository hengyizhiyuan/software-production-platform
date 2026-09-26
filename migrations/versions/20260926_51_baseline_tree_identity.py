"""Record exact Git tree identity alongside versioned baseline revision.

Revision ID: 20260926_51
Revises: 20260926_50
"""

from alembic import op
import sqlalchemy as sa


revision = "20260926_51"
down_revision = "20260926_50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_snapshots", sa.Column("repository_tree_identity", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("production_snapshots", "repository_tree_identity")
