"""Persist access grants and exact remote delivery authority/effects.

Revision ID: 20260926_54
Revises: 20260926_53
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260926_54"
down_revision = "20260926_53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("github_access_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("repository_url", sa.Text(), nullable=False),
        sa.Column("capability", sa.String(16), nullable=False),
        sa.Column("credential_ref", sa.String(64), nullable=False),
        sa.Column("credential_sha256", sa.String(64), nullable=False),
        sa.Column("condition", sa.String(16), nullable=False),
        sa.Column("observed_permission", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("actor_id", "repository_url", "capability",
            name="uq_github_grant_actor_repo_capability"))
    op.create_table("remote_delivery_authorizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("repository_url", sa.Text(), nullable=False),
        sa.Column("target_branch", sa.String(255), nullable=False),
        sa.Column("expected_revision", sa.String(64), nullable=False),
        sa.Column("expected_remote_revision", sa.String(64)),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now()))
    op.create_table("remote_delivery_receipts",
        sa.Column("authorization_id", sa.Uuid(),
            sa.ForeignKey("remote_delivery_authorizations.id"), primary_key=True),
        sa.Column("remote_before", sa.String(64)),
        sa.Column("remote_after", sa.String(64), nullable=False),
        sa.Column("push_condition", sa.String(32), nullable=False),
        sa.Column("pr_url", sa.Text()),
        sa.Column("pr_number", sa.String(32)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("remote_delivery_receipts")
    op.drop_table("remote_delivery_authorizations")
    op.drop_table("github_access_grants")
