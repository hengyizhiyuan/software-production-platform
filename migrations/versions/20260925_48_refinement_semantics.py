"""Version Self-Refine semantics without reclassifying historical incidents.

Revision ID: 20260925_48
Revises: 20260925_47
"""

from alembic import op
import sqlalchemy as sa


revision = "20260925_48"
down_revision = "20260925_47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("self_refine_events", sa.Column(
        "semantic_version", sa.Integer(), nullable=False, server_default="1",
    ))
    op.add_column("self_refine_events", sa.Column(
        "refinement_class", sa.String(64), nullable=False,
        server_default="LEGACY_EXECUTION_INCIDENT",
    ))
    op.add_column("self_refine_events", sa.Column(
        "signal_kind", sa.String(64), nullable=False,
        server_default="EXECUTION_FAILURE",
    ))
    op.create_index("ix_self_refine_events_class_created", "self_refine_events",
        ["refinement_class", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_self_refine_events_class_created", table_name="self_refine_events")
    op.drop_column("self_refine_events", "signal_kind")
    op.drop_column("self_refine_events", "refinement_class")
    op.drop_column("self_refine_events", "semantic_version")
