"""Add governed Engineering Semantic Truth projections.

Revision ID: 20260918_43
Revises: 20260917_42
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260918_43"
down_revision = "20260917_42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    empty = sa.text("'[]'::jsonb")
    op.add_column(
        "interaction_assessments",
        sa.Column(
            "neutral_semantic_extractions",
            postgresql.JSONB(),
            nullable=False,
            server_default=empty,
        ),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column(
            "engineering_semantic_facts",
            postgresql.JSONB(),
            nullable=False,
            server_default=empty,
        ),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column(
            "engineering_semantic_facts",
            postgresql.JSONB(),
            nullable=False,
            server_default=empty,
        ),
    )
    op.alter_column(
        "interaction_assessments",
        "neutral_semantic_extractions",
        server_default=None,
    )
    op.alter_column(
        "interaction_assessments",
        "engineering_semantic_facts",
        server_default=None,
    )
    op.alter_column(
        "work_reality_revisions",
        "engineering_semantic_facts",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("work_reality_revisions", "engineering_semantic_facts")
    op.drop_column("interaction_assessments", "engineering_semantic_facts")
    op.drop_column("interaction_assessments", "neutral_semantic_extractions")
