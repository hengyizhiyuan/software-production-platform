"""Durable explicit Human source promotion intent; accepted baseline stays Product owned."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "20261005_68"
down_revision = "20261005_67"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("product_source_promotion_intents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("software_products.id"), nullable=False),
        sa.Column("work_id", sa.Uuid(), sa.ForeignKey("product_works.id"), nullable=False),
        sa.Column("acceptance_id", sa.Uuid(), sa.ForeignKey("work_delivery_acceptances.id"), nullable=False, unique=True),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("baseline_candidates.id"), nullable=False),
        sa.Column("runtime_commit_id", sa.Uuid(), sa.ForeignKey("runtime_commits.id"), nullable=False),
        sa.Column("expected_version", sa.Integer(), nullable=False),
        sa.Column("expected_revision", sa.String(64), nullable=False),
        sa.Column("expected_tree", sa.String(64), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("tree", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.Column("assurance_references", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('PENDING', 'COMPLETED', 'BLOCKED')", name="ck_source_promotion_state"))
    op.create_index("uq_product_pending_promotion", "product_source_promotion_intents", ["product_id"],
                    unique=True, postgresql_where=sa.text("state <> 'COMPLETED'"))

def downgrade():
    op.drop_table("product_source_promotion_intents")
