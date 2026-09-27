"""Distinguish unrecorded legacy action interpretation from interpreted no-action."""
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = '20260927_60'
down_revision = '20260927_59'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('interaction_assessments', 'action_candidates',
        existing_type=JSONB(), nullable=True, server_default=None)


def downgrade() -> None:
    op.execute("UPDATE interaction_assessments SET action_candidates='[]'::jsonb WHERE action_candidates IS NULL")
    op.alter_column('interaction_assessments', 'action_candidates',
        existing_type=JSONB(), nullable=False, server_default='[]')
