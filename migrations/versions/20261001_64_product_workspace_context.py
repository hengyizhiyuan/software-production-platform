"""Preserve Product context for Workspace conversations without granting Work authority."""

from alembic import op
import sqlalchemy as sa

revision = "20261001_64"
down_revision = "20261001_63"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_workspace_interactions",
        sa.Column("interaction_id", sa.Uuid(),
                  sa.ForeignKey("product_interactions.id"), primary_key=True),
        sa.Column("product_id", sa.Uuid(),
                  sa.ForeignKey("software_products.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_product_workspace_interactions_product",
                    "product_workspace_interactions", ["product_id"])


def downgrade():
    op.drop_index("ix_product_workspace_interactions_product",
                  table_name="product_workspace_interactions")
    op.drop_table("product_workspace_interactions")
