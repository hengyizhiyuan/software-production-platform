"""Persist versioned Production Plan DAG and per-PWU baseline lineage.

Historical single-PWU rows retain NULL graph/node identity. A NULL input
baseline on a new planned PWU means it cannot yet create an Attempt.

Revision ID: 20260926_50
Revises: 20260925_49
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260926_50"
down_revision = "20260925_49"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_runs", sa.Column("integrated_baseline_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_runs_integrated_baseline", "production_runs", "production_snapshots", ["integrated_baseline_id"], ["id"])
    op.add_column("plan_revisions", sa.Column("graph", JSONB(), nullable=True))
    op.add_column("plan_revisions", sa.Column("supersedes_plan_revision_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_plan_revision_supersedes", "plan_revisions", "plan_revisions", ["supersedes_plan_revision_id"], ["id"])
    op.alter_column("production_work_units", "source_baseline_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("production_work_units", sa.Column("node_id", sa.String(128), nullable=True))
    op.add_column("production_work_units", sa.Column("parent_baseline_ids", JSONB(), nullable=True))
    op.add_column("production_work_units", sa.Column("verified_output_baseline_id", sa.Uuid(), nullable=True))
    op.add_column("production_work_units", sa.Column("reconciliation_evidence", JSONB(), nullable=True))
    op.create_foreign_key("fk_work_units_verified_output", "production_work_units", "production_snapshots", ["verified_output_baseline_id"], ["id"])
    op.create_unique_constraint("uq_work_units_plan_node", "production_work_units", ["plan_revision_id", "node_id"])


def downgrade() -> None:
    # Older schemas can retain a legacy single-PWU binding, but cannot
    # represent multiple PWUs or revised/verified successor lineage.
    connection = op.get_bind()
    has_multi_pwu_history = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM production_work_units
            GROUP BY plan_revision_id HAVING COUNT(*) > 1
        ) OR EXISTS (
            SELECT 1 FROM plan_revisions WHERE supersedes_plan_revision_id IS NOT NULL
        ) OR EXISTS (
            SELECT 1 FROM production_work_units
            WHERE verified_output_baseline_id IS NOT NULL
                OR jsonb_array_length(COALESCE(parent_baseline_ids, '[]'::jsonb)) > 0
        )
    """)).scalar_one()
    if has_multi_pwu_history:
        raise RuntimeError("Cannot downgrade versioned multi-PWU production history")
    op.drop_constraint("uq_work_units_plan_node", "production_work_units", type_="unique")
    op.drop_constraint("fk_work_units_verified_output", "production_work_units", type_="foreignkey")
    op.drop_column("production_work_units", "reconciliation_evidence")
    op.drop_column("production_work_units", "verified_output_baseline_id")
    op.drop_column("production_work_units", "parent_baseline_ids")
    op.drop_column("production_work_units", "node_id")
    op.alter_column("production_work_units", "source_baseline_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("fk_plan_revision_supersedes", "plan_revisions", type_="foreignkey")
    op.drop_column("plan_revisions", "supersedes_plan_revision_id")
    op.drop_column("plan_revisions", "graph")
    op.drop_constraint("fk_runs_integrated_baseline", "production_runs", type_="foreignkey")
    op.drop_column("production_runs", "integrated_baseline_id")
