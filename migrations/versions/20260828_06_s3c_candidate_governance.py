"""Add S3-C Baseline Candidate and Human Authorization facts.

Revision ID: 20260828_06
Revises: 20260828_05
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260828_06"
down_revision: str | None = "20260828_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "baseline_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("target_authoritative_ref", sa.String(length=512), nullable=False),
        sa.Column(
            "expected_source_repository_revision",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("proposed_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_commit_identity", sa.String(length=128), nullable=False),
        sa.Column("proposed_tree_identity", sa.String(length=128), nullable=False),
        sa.Column("satisfied_work_unit_ids", postgresql.JSONB(), nullable=False),
        sa.Column("completion_evaluation_ids", postgresql.JSONB(), nullable=False),
        sa.Column("work_product_reference_ids", postgresql.JSONB(), nullable=False),
        sa.Column("verification_record_ids", postgresql.JSONB(), nullable=False),
        sa.Column("production_admissibility_id", sa.Uuid(), nullable=False),
        sa.Column(
            "production_admissibility_basis_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "sealed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "condition = 'SEALED'",
            name="baseline_candidate_is_sealed",
        ),
        sa.ForeignKeyConstraint(
            ["plan_revision_id"],
            ["plan_revisions.id"],
            name="fk_baseline_candidates_plan",
        ),
        sa.ForeignKeyConstraint(
            ["production_admissibility_id"],
            ["production_admissibility_records.id"],
            name="fk_baseline_candidates_admissibility",
        ),
        sa.ForeignKeyConstraint(
            ["production_run_id"],
            ["production_runs.id"],
            name="fk_baseline_candidates_run",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_snapshot_id"],
            ["proposed_repository_snapshots.id"],
            name="fk_baseline_candidates_proposed_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_baseline_candidates_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_baseline_candidates_fingerprint"),
    )
    op.create_table(
        "human_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("authority_identity", sa.String(length=255), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("authorization_scope", postgresql.JSONB(), nullable=False),
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("target_authoritative_ref", sa.String(length=512), nullable=False),
        sa.Column(
            "expected_source_repository_revision",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("proposed_repository_revision", sa.String(length=128), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("governance_record_id", sa.Uuid(), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "authorized_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["baseline_candidates.id"],
            name="fk_human_authorizations_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["governance_record_id"],
            ["governance_records.id"],
            name="fk_human_authorizations_governance",
        ),
        sa.ForeignKeyConstraint(
            ["source_baseline_id"],
            ["production_snapshots.id"],
            name="fk_human_authorizations_baseline",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "basis_fingerprint",
            name="uq_human_authorizations_basis",
        ),
        sa.UniqueConstraint(
            "governance_record_id",
            name="uq_human_authorizations_governance",
        ),
    )


def downgrade() -> None:
    op.drop_table("human_authorizations")
    op.drop_table("baseline_candidates")
