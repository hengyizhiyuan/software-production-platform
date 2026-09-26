"""Keep WIC candidate correction evidence with its owning assessment or turn.

Revision ID: 20260925_49
Revises: 20260925_48
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260925_49"
down_revision = "20260925_48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("interaction_assessments", sa.Column(
        "refinement_observation", JSONB(), nullable=True,
    ))
    op.add_column("interaction_turns", sa.Column(
        "refinement_observation", JSONB(), nullable=True,
    ))


def downgrade() -> None:
    op.drop_column("interaction_turns", "refinement_observation")
    op.drop_column("interaction_assessments", "refinement_observation")
