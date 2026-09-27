"""Persist governed Turn semantics and obligations; historical IR remains NULL."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260927_61"
down_revision = "20260927_60"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("interaction_assessments", sa.Column("semantic_ir", JSONB(), nullable=True))
    op.create_table("interaction_turn_realizations",
        sa.Column("turn_id", sa.Uuid(), sa.ForeignKey("interaction_turns.id"), primary_key=True),
        sa.Column("semantic_ir_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("assessment_id", sa.Uuid(), sa.ForeignKey("interaction_assessments.id"), nullable=False),
        sa.Column("payload", JSONB(), nullable=False))
    op.create_table("interaction_turn_obligations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("turn_id", sa.Uuid(), sa.ForeignKey("interaction_turn_realizations.turn_id"), nullable=False),
        sa.Column("semantic_item_id", sa.String(100), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.UniqueConstraint("turn_id", "semantic_item_id", name="uq_turn_obligations_item"))
    op.create_table("interaction_turn_realization_refinements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("turn_id", sa.Uuid(), sa.ForeignKey("interaction_turns.id"), nullable=False),
        sa.Column("obligation_id", sa.Uuid(), sa.ForeignKey("interaction_turn_obligations.id"), nullable=True),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("interaction_turn_realization_refinements.id"), nullable=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.UniqueConstraint("turn_id", "signature", "attempt", name="uq_realization_refinement_attempt"))


def downgrade():
    op.drop_table("interaction_turn_realization_refinements")
    op.drop_table("interaction_turn_obligations")
    op.drop_table("interaction_turn_realizations")
    op.drop_column("interaction_assessments", "semantic_ir")
