"""Work delivery targets, exact manifests and Human acceptance.

Revision ID: 20260910_32
Revises: 20260910_31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260910_32"
down_revision = "20260910_31"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_delivery_targets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_id", sa.Uuid(), sa.ForeignKey("product_works.id"), nullable=False, unique=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "work_delivery_manifests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_id", sa.Uuid(), sa.ForeignKey("product_works.id"), nullable=False),
        sa.Column("target_id", sa.Uuid(), sa.ForeignKey("work_delivery_targets.id"), nullable=False),
        sa.Column("runtime_commit_id", sa.Uuid(), sa.ForeignKey("runtime_commits.id"), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "work_delivery_acceptances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("manifest_id", sa.Uuid(), sa.ForeignKey("work_delivery_manifests.id"), nullable=False, unique=True),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    for name in ("work_delivery_acceptances", "work_delivery_manifests", "work_delivery_targets"):
        op.drop_table(name)
