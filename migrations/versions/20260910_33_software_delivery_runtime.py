"""Persist isolated local software runtime identities without altering SPG."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "20260910_33"
down_revision = "20260910_32"
branch_labels = depends_on = None

def upgrade():
    op.create_table("work_delivery_runtimes",
        sa.Column("manifest_id", sa.Uuid(), sa.ForeignKey("work_delivery_manifests.id"), primary_key=True),
        sa.Column("port", sa.Integer(), nullable=False, unique=True),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

def downgrade():
    op.drop_table("work_delivery_runtimes")
