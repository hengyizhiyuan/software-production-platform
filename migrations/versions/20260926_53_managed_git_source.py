"""Persist managed Git source independently of execution workspaces.

Revision ID: 20260926_53
Revises: 20260926_52
"""

from alembic import op
import sqlalchemy as sa

revision = "20260926_53"
down_revision = "20260926_52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("managed_repository_sources",
        sa.Column("repository_identity", sa.String(255), primary_key=True),
        sa.Column("owner_actor_id", sa.String(255), nullable=False),
        sa.Column("repository_ref", sa.String(512), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("tree", sa.String(64), nullable=False),
        sa.Column("bundle_sha256", sa.String(64), nullable=False),
        sa.Column("git_bundle", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("managed_repository_sources")
