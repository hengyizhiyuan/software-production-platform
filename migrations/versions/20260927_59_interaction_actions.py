"""Persist WIC canonical action candidates with their immutable assessment basis."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260927_59"
down_revision = "20260927_58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("interaction_assessments", sa.Column(
        "action_candidates", JSONB(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("interaction_assessments", "action_candidates")
