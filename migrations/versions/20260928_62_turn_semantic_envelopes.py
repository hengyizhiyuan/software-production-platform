"""Persist a governed semantic lifecycle for each new Human Turn."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260928_62"
down_revision = "20260927_61"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("interaction_turn_semantic_envelopes",
        sa.Column("turn_id", sa.Uuid(), sa.ForeignKey("interaction_turns.id"), primary_key=True),
        sa.Column("source_record_id", sa.Uuid(), sa.ForeignKey("interaction_records.id"), nullable=False),
        sa.Column("human_content_hash", sa.String(64), nullable=False),
        sa.Column("provenance_basis", JSONB(), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("basis_fingerprint", sa.String(64), nullable=True),
        sa.Column("semantic_ir_id", sa.Uuid(), nullable=True),
        sa.Column("blocker", JSONB(), nullable=True),
        sa.Column("history", JSONB(), nullable=False))


def downgrade():
    op.drop_table("interaction_turn_semantic_envelopes")
