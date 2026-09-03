"""Add governed MVP Artifact Target proposal fields.

Revision ID: 20260903_15
Revises: 20260902_14
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_15"
down_revision: str | None = "20260902_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product_works", sa.Column("artifact_operation", sa.String(length=16), nullable=True))
    op.add_column("product_works", sa.Column("artifact_placement_rationale", sa.Text(), nullable=True))
    op.add_column("product_works", sa.Column("artifact_target_confidence", sa.String(length=16), nullable=True))
    op.add_column("product_works", sa.Column("artifact_source_baseline_id", sa.Uuid(), nullable=True))
    op.add_column("product_works", sa.Column("artifact_source_revision", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("product_works", "artifact_source_revision")
    op.drop_column("product_works", "artifact_source_baseline_id")
    op.drop_column("product_works", "artifact_target_confidence")
    op.drop_column("product_works", "artifact_placement_rationale")
    op.drop_column("product_works", "artifact_operation")
