"""Add the WIC Interaction truth spine and version-ready Work Reality links.

Revision ID: 20260907_23
Revises: 20260905_22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260907_23"
down_revision: str | None = "20260905_22"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_engineering_scopes_work_id",
        "engineering_scopes",
        type_="unique",
    )
    op.create_index(
        "ix_engineering_scopes_work_created",
        "engineering_scopes",
        ["work_id", "created_at"],
    )

    op.create_table(
        "product_interactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("current_work_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "condition IN ('OPEN', 'ARCHIVED')",
            name="ck_product_interactions_condition_known",
        ),
        sa.ForeignKeyConstraint(
            ["current_work_id"],
            ["product_works.id"],
            name="fk_product_interactions_current_work",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_interactions"),
    )
    op.create_table(
        "interaction_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("work_focus_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "actor IN ('HUMAN', 'WATT')",
            name="ck_interaction_records_actor_known",
        ),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["product_interactions.id"],
            name="fk_interaction_records_interaction",
        ),
        sa.ForeignKeyConstraint(
            ["work_focus_id"],
            ["product_works.id"],
            name="fk_interaction_records_work_focus",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_interaction_records"),
        sa.UniqueConstraint(
            "interaction_id",
            "sequence",
            name="uq_interaction_records_interaction_sequence",
        ),
    )
    op.create_table(
        "interaction_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("basis_last_sequence", sa.Integer(), nullable=False),
        sa.Column("interpreted_motive", sa.Text(), nullable=True),
        sa.Column("desired_outcome", sa.Text(), nullable=True),
        sa.Column("candidate_context", postgresql.JSONB(), nullable=False),
        sa.Column("candidate_constraints", postgresql.JSONB(), nullable=False),
        sa.Column("current_requests", postgresql.JSONB(), nullable=False),
        sa.Column("unresolved_material_questions", postgresql.JSONB(), nullable=False),
        sa.Column("meanings", postgresql.JSONB(), nullable=False),
        sa.Column("natural_response", sa.Text(), nullable=False),
        sa.Column("readiness", postgresql.JSONB(), nullable=False),
        sa.Column("provider_identity", sa.String(length=255), nullable=False),
        sa.Column("model_identity", sa.String(length=255), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["product_interactions.id"],
            name="fk_interaction_assessments_interaction",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_interaction_assessments"),
        sa.UniqueConstraint(
            "interaction_id",
            "basis_fingerprint",
            name="uq_interaction_assessments_interaction_basis",
        ),
    )
    op.create_table(
        "work_reality_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_revision_id", sa.Uuid(), nullable=True),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("motive", sa.Text(), nullable=False),
        sa.Column("desired_outcome", sa.Text(), nullable=False),
        sa.Column("context_facts", postgresql.JSONB(), nullable=False),
        sa.Column("constraints", postgresql.JSONB(), nullable=False),
        sa.Column("requests", postgresql.JSONB(), nullable=False),
        sa.Column("engineering_scope_id", sa.Uuid(), nullable=True),
        sa.Column("supporting_references", postgresql.JSONB(), nullable=False),
        sa.Column("change_set", postgresql.JSONB(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("admitted_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["engineering_scope_id"],
            ["engineering_scopes.id"],
            name="fk_work_reality_revisions_scope",
        ),
        sa.ForeignKeyConstraint(
            ["previous_revision_id"],
            ["work_reality_revisions.id"],
            name="fk_work_reality_revisions_previous",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["product_works.id"],
            name="fk_work_reality_revisions_work",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_work_reality_revisions"),
        sa.UniqueConstraint(
            "work_id",
            "revision_number",
            name="uq_work_reality_revisions_work_number",
        ),
        sa.UniqueConstraint(
            "work_id",
            "basis_fingerprint",
            name="uq_work_reality_revisions_work_basis",
        ),
    )
    op.add_column(
        "product_works",
        sa.Column("current_work_reality_revision_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "product_works",
        sa.Column("current_engineering_scope_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_product_works_current_reality_revision",
        "product_works",
        "work_reality_revisions",
        ["current_work_reality_revision_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_product_works_current_engineering_scope",
        "product_works",
        "engineering_scopes",
        ["current_engineering_scope_id"],
        ["id"],
    )
    op.add_column(
        "work_runtime_bindings",
        sa.Column("work_reality_revision_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_work_runtime_bindings_reality_revision",
        "work_runtime_bindings",
        "work_reality_revisions",
        ["work_reality_revision_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_work_runtime_bindings_reality_revision",
        "work_runtime_bindings",
        type_="foreignkey",
    )
    op.drop_column("work_runtime_bindings", "work_reality_revision_id")
    op.drop_constraint(
        "fk_product_works_current_engineering_scope",
        "product_works",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_product_works_current_reality_revision",
        "product_works",
        type_="foreignkey",
    )
    op.drop_column("product_works", "current_engineering_scope_id")
    op.drop_column("product_works", "current_work_reality_revision_id")
    op.drop_table("work_reality_revisions")
    op.drop_table("interaction_assessments")
    op.drop_table("interaction_records")
    op.drop_table("product_interactions")
    op.drop_index("ix_engineering_scopes_work_created", table_name="engineering_scopes")
    op.create_unique_constraint(
        "uq_engineering_scopes_work_id",
        "engineering_scopes",
        ["work_id"],
    )
