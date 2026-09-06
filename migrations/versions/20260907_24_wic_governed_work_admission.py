"""Bind governed Work revision one to exact Interaction admission Reality.

Revision ID: 20260907_24
Revises: 20260907_23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260907_24"
down_revision: str | None = "20260907_23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "work_reality_revisions",
        sa.Column("revision_fingerprint", sa.String(length=64), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("source_interaction_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("source_assessment_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("engineering_resource_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("scope_basis_fingerprint", sa.String(length=64), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("repository_ref", sa.String(length=512), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("source_baseline_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("source_revision", sa.String(length=64), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("governance_record_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "work_reality_revisions",
        sa.Column("schema_version", sa.String(length=32), nullable=False),
    )
    op.alter_column(
        "work_reality_revisions",
        "engineering_scope_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_work_reality_revisions_fingerprint",
        "work_reality_revisions",
        ["revision_fingerprint"],
    )
    op.create_unique_constraint(
        "uq_work_reality_revisions_source_assessment",
        "work_reality_revisions",
        ["source_assessment_id"],
    )
    op.create_unique_constraint(
        "uq_work_reality_revisions_governance",
        "work_reality_revisions",
        ["governance_record_id"],
    )
    op.create_foreign_key(
        "fk_work_reality_revisions_source_interaction",
        "work_reality_revisions",
        "product_interactions",
        ["source_interaction_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_work_reality_revisions_source_assessment",
        "work_reality_revisions",
        "interaction_assessments",
        ["source_assessment_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_work_reality_revisions_resource",
        "work_reality_revisions",
        "engineering_resources",
        ["engineering_resource_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_work_reality_revisions_baseline",
        "work_reality_revisions",
        "production_snapshots",
        ["source_baseline_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_work_reality_revisions_governance",
        "work_reality_revisions",
        "governance_records",
        ["governance_record_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_work_reality_revisions_governance",
        "work_reality_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_work_reality_revisions_baseline",
        "work_reality_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_work_reality_revisions_resource",
        "work_reality_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_work_reality_revisions_source_assessment",
        "work_reality_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_work_reality_revisions_source_interaction",
        "work_reality_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_work_reality_revisions_governance",
        "work_reality_revisions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_work_reality_revisions_source_assessment",
        "work_reality_revisions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_work_reality_revisions_fingerprint",
        "work_reality_revisions",
        type_="unique",
    )
    op.alter_column(
        "work_reality_revisions",
        "engineering_scope_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    for column in (
        "schema_version",
        "governance_record_id",
        "source_revision",
        "source_baseline_id",
        "repository_ref",
        "repository_identity",
        "scope_basis_fingerprint",
        "engineering_resource_id",
        "source_assessment_id",
        "source_interaction_id",
        "revision_fingerprint",
    ):
        op.drop_column("work_reality_revisions", column)
