"""Add the narrow S4-B Runtime Commit audit linkage.

Revision ID: 20260829_08
Revises: 20260829_07
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260829_08"
down_revision: str | None = "20260829_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_commits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("human_authorization_id", sa.Uuid(), nullable=False),
        sa.Column("repository_integration_effect_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("new_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("target_authoritative_ref", sa.String(length=512), nullable=False),
        sa.Column(
            "expected_source_repository_revision",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("repository_revision", sa.String(length=128), nullable=False),
        sa.Column("repository_tree_identity", sa.String(length=128), nullable=False),
        sa.Column("satisfied_work_unit_ids", postgresql.JSONB(), nullable=False),
        sa.Column("completion_evaluation_ids", postgresql.JSONB(), nullable=False),
        sa.Column("verification_record_ids", postgresql.JSONB(), nullable=False),
        sa.Column("production_admissibility_id", sa.Uuid(), nullable=False),
        sa.Column(
            "production_admissibility_basis_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("commit_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "committed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["baseline_candidates.id"],
            name="fk_runtime_commits_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["human_authorization_id"],
            ["human_authorizations.id"],
            name="fk_runtime_commits_authorization",
        ),
        sa.ForeignKeyConstraint(
            ["repository_integration_effect_id"],
            ["repository_integration_effects.id"],
            name="fk_runtime_commits_integration_effect",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_runtime_commits_source_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["new_baseline_id"],
            ["production_snapshots.id"],
            name="fk_runtime_commits_new_baseline",
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_runtime_commits_run",
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_runtime_commits_plan",
        ),
        sa.ForeignKeyConstraint(
            ["production_admissibility_id"],
            ["production_admissibility_records.id"],
            name="fk_runtime_commits_admissibility",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", name="uq_runtime_commits_candidate"),
        sa.UniqueConstraint(
            "repository_integration_effect_id",
            name="uq_runtime_commits_integration_effect",
        ),
        sa.UniqueConstraint("new_baseline_id", name="uq_runtime_commits_new_baseline"),
        sa.UniqueConstraint("commit_fingerprint", name="uq_runtime_commits_basis"),
    )


def downgrade() -> None:
    op.drop_table("runtime_commits")
