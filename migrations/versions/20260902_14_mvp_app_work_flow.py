"""Add MVP Goal, Work, Engineering Scope, and Runtime lineage bindings.

Revision ID: 20260902_14
Revises: 20260902_13
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260902_14"
down_revision: str | None = "20260902_13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "engineering_resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("location_ref", sa.Text(), nullable=False),
        sa.Column("authoritative_ref", sa.String(length=512), nullable=False),
        sa.Column("context_references", postgresql.JSONB(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_identity"),
    )
    op.create_index(
        "uq_engineering_resources_one_default",
        "engineering_resources",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )
    op.create_table(
        "product_works",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=True),
        sa.Column("raw_user_requirement", sa.Text(), nullable=False),
        sa.Column("refined_title", sa.String(length=255), nullable=True),
        sa.Column("desired_outcome", sa.Text(), nullable=True),
        sa.Column("constraints", postgresql.JSONB(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("scope_summary", sa.Text(), nullable=True),
        sa.Column("production_objective", sa.Text(), nullable=True),
        sa.Column("expected_artifact_path", sa.Text(), nullable=True),
        sa.Column("verification_expectation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["product_goals.id"], name="fk_product_works_goal"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "engineering_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["work_id"], ["product_works.id"], name="fk_engineering_scopes_work"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
        sa.UniqueConstraint("work_id"),
    )
    op.create_table(
        "engineering_resource_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("engineering_scope_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["engineering_scope_id"], ["engineering_scopes.id"], name="fk_resource_bindings_scope"),
        sa.ForeignKeyConstraint(["resource_id"], ["engineering_resources.id"], name="fk_resource_bindings_resource"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("engineering_scope_id", "resource_id", name="uq_resource_bindings_scope_resource"),
    )
    op.create_table(
        "work_runtime_bindings",
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("engineering_scope_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("production_run_id", sa.Uuid(), nullable=False),
        sa.Column("plan_revision_id", sa.Uuid(), nullable=False),
        sa.Column("work_unit_id", sa.Uuid(), nullable=False),
        sa.Column("governance_record_id", sa.Uuid(), nullable=False),
        sa.Column("admitted_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["engineering_scope_id"], ["engineering_scopes.id"], name="fk_work_runtime_bindings_scope"),
        sa.ForeignKeyConstraint(["governance_record_id"], ["governance_records.id"], name="fk_work_runtime_bindings_governance"),
        sa.ForeignKeyConstraint(["plan_revision_id"], ["plan_revisions.id"], name="fk_work_runtime_bindings_plan"),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], name="fk_work_runtime_bindings_run"),
        sa.ForeignKeyConstraint(["resource_id"], ["engineering_resources.id"], name="fk_work_runtime_bindings_resource"),
        sa.ForeignKeyConstraint(["work_id"], ["product_works.id"], name="fk_work_runtime_bindings_work"),
        sa.ForeignKeyConstraint(["work_unit_id"], ["production_work_units.id"], name="fk_work_runtime_bindings_pwu"),
        sa.PrimaryKeyConstraint("work_id"),
        sa.UniqueConstraint("governance_record_id"),
        sa.UniqueConstraint("plan_revision_id"),
        sa.UniqueConstraint("production_run_id"),
        sa.UniqueConstraint("work_unit_id"),
    )


def downgrade() -> None:
    op.drop_table("work_runtime_bindings")
    op.drop_table("engineering_resource_bindings")
    op.drop_table("engineering_scopes")
    op.drop_table("product_works")
    op.drop_index("uq_engineering_resources_one_default", table_name="engineering_resources")
    op.drop_table("engineering_resources")
    op.drop_table("product_goals")
