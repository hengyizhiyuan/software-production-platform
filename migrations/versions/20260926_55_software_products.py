"""Introduce long-lived Products without assigning unknown historical Works.

Revision ID: 20260926_55
Revises: 20260926_54
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260926_55"
down_revision = "20260926_54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("software_products",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lifecycle", sa.String(32), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("lifecycle IN ('ACTIVE', 'PAUSED', 'ARCHIVED')", name="ck_software_products_lifecycle"))
    op.create_table("software_product_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("software_products.id"), nullable=False),
        sa.Column("asset_kind", sa.String(32), nullable=False),
        sa.Column("reference", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("engineering_resources.id")),
        sa.Column("metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "asset_kind", "reference", name="uq_software_product_asset_ref"))
    op.add_column("product_works", sa.Column("product_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_product_works_product", "product_works", "software_products", ["product_id"], ["id"])
    op.create_index("ix_product_works_product_created", "product_works", ["product_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_product_works_product_created", table_name="product_works")
    op.drop_constraint("fk_product_works_product", "product_works", type_="foreignkey")
    op.drop_column("product_works", "product_id")
    op.drop_table("software_product_assets")
    op.drop_table("software_products")
