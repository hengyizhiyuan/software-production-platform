"""Persist WIC response identity and reconciliation evidence.

Revision ID: 20260915_41
Revises: 20260915_40
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260915_41"
down_revision = "20260915_40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interaction_turns",
        sa.Column(
            "wic_mode", sa.String(length=32), nullable=False,
            server_default="LEGACY_WIC",
        ),
    )
    op.create_check_constraint(
        "ck_interaction_turns_wic_mode_known",
        "interaction_turns",
        "wic_mode IN ('LEGACY_WIC', 'WIC_VNEXT_SHADOW', 'WIC_VNEXT_CONTROLLED')",
    )
    op.create_table(
        "interaction_response_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("turn_id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("reconciliation", sa.String(length=32), nullable=True),
        sa.Column(
            "event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "response_id = turn_id",
            name="ck_interaction_response_events_response_identity",
        ),
        sa.ForeignKeyConstraint(
            ["interaction_id"], ["product_interactions.id"],
            name="fk_interaction_response_events_interaction",
        ),
        sa.ForeignKeyConstraint(
            ["turn_id"], ["interaction_turns.id"],
            name="fk_interaction_response_events_turn",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "turn_id", "sequence",
            name="uq_interaction_response_events_turn_sequence",
        ),
    )


def downgrade() -> None:
    op.drop_table("interaction_response_events")
    op.drop_constraint(
        "ck_interaction_turns_wic_mode_known",
        "interaction_turns",
        type_="check",
    )
    op.drop_column("interaction_turns", "wic_mode")
