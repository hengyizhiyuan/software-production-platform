"""Product accepted source and exact Work source lineage."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261001_63"
down_revision = "20260928_62"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("product_managed_sources",
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("software_products.id"), primary_key=True),
        sa.Column("repository_identity", sa.String(255), nullable=False, unique=True),
        sa.Column("provider_kind", sa.String(32), nullable=False),
        sa.Column("provider_reference", sa.Text(), nullable=False),
        sa.Column("accepted_ref", sa.String(512), nullable=False),
        sa.Column("accepted_revision", sa.String(64), nullable=False),
        sa.Column("accepted_tree", sa.String(64), nullable=False),
        sa.Column("origin", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("product_source_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("software_products.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("tree", sa.String(64), nullable=False),
        sa.Column("work_id", sa.Uuid(), sa.ForeignKey("product_works.id"), nullable=True),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("acceptance_id", sa.Uuid(), nullable=True, unique=True),
        sa.Column("authority_identity", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "version", name="uq_product_source_version"))
    op.create_table("work_source_bases",
        sa.Column("work_id", sa.Uuid(), sa.ForeignKey("product_works.id"), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("software_products.id"), nullable=False),
        sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("engineering_resources.id"), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.String(64), nullable=False),
        sa.Column("source_tree", sa.String(64), nullable=False),
        sa.Column("work_ref", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade():
    op.drop_table("work_source_bases")
    op.drop_table("product_source_versions")
    op.drop_table("product_managed_sources")
