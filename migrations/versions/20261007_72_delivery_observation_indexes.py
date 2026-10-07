"""Bounded delivery observation lookup in the existing audit ledger."""
from alembic import op
import sqlalchemy as sa
revision = "20261007_72"
down_revision = "20261006_71"
branch_labels = None
depends_on = None

def upgrade():
    for scope in ("work_id", "product_id"):
        op.create_index("ix_delivery_audit_" + scope, "connector_audit_events",
            [sa.text("(detail ->> '" + scope + "')"), "created_at"],
            postgresql_where=sa.text("subject_kind = 'DELIVERY_ACTION'"))

def downgrade():
    # Removing an index does not remove immutable delivery observation facts.
    for scope in ("work_id", "product_id"):
        op.drop_index("ix_delivery_audit_" + scope, table_name="connector_audit_events")
