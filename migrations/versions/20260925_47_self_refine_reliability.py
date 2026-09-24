"""Persist repairability, observation confidence, budget and diagnostic evidence.

Revision ID: 20260925_47
Revises: 20260924_46
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260925_47"
down_revision = "20260924_46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("self_refine_events", sa.Column(
        "repairability", sa.String(64), nullable=False,
        server_default="REPAIRABLE_WITH_SUFFICIENT_EVIDENCE",
    ))
    op.add_column("self_refine_events", sa.Column(
        "observation_confidence", sa.String(64), nullable=False,
        server_default="CONFIRMED_FAILURE",
    ))
    op.add_column("self_refine_events", sa.Column(
        "budget_decision", postgresql.JSONB(), nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    ))
    op.add_column("self_refine_events", sa.Column(
        "diagnostic_evidence", postgresql.JSONB(), nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    ))


def downgrade() -> None:
    op.drop_column("self_refine_events", "diagnostic_evidence")
    op.drop_column("self_refine_events", "budget_decision")
    op.drop_column("self_refine_events", "observation_confidence")
    op.drop_column("self_refine_events", "repairability")
