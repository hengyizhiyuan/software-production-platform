"""Add WIC active-Work focus, impact, and revision-lineage evidence.

Revision ID: 20260907_25
Revises: 20260907_24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260907_25"
down_revision: str | None = "20260907_24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    empty_json = sa.text("'[]'::jsonb")
    op.add_column(
        "interaction_records",
        sa.Column(
            "supporting_references",
            postgresql.JSONB(),
            server_default=empty_json,
            nullable=False,
        ),
    )
    op.alter_column("interaction_records", "supporting_references", server_default=None)

    op.add_column(
        "interaction_assessments",
        sa.Column("focus_classification", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column("impact_disposition", sa.String(length=48), nullable=True),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column("candidate_change", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column("basis_work_revision_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column("basis_steering_plan_revision_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column("basis_steering_step_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column("basis_active_runtime_binding_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "interaction_assessments",
        sa.Column(
            "supporting_references",
            postgresql.JSONB(),
            server_default=empty_json,
            nullable=False,
        ),
    )
    op.alter_column("interaction_assessments", "supporting_references", server_default=None)
    op.create_check_constraint(
        "ck_interaction_assessments_focus_known",
        "interaction_assessments",
        "focus_classification IS NULL OR focus_classification IN "
        "('ON_TOPIC', 'RELEVANT_EXPLORATION', 'SIDE_QUESTION', "
        "'MATERIAL_BRANCH', 'UNRELATED_NEW_DEMAND')",
    )
    op.create_check_constraint(
        "ck_interaction_assessments_impact_known",
        "interaction_assessments",
        "impact_disposition IS NULL OR impact_disposition IN "
        "('NO_GOVERNED_CHANGE', 'CURRENT_CYCLE_REMAINS_VALID', "
        "'DEFER_TO_PRODUCTION_BOUNDARY', 'CURRENT_RESULT_MAY_BE_INSUFFICIENT', "
        "'HUMAN_GOVERNANCE_REQUIRED', 'NEW_WORK_RECOMMENDED')",
    )
    op.create_foreign_key(
        "fk_interaction_assessments_basis_work_revision",
        "interaction_assessments",
        "work_reality_revisions",
        ["basis_work_revision_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_interaction_assessments_basis_steering_revision",
        "interaction_assessments",
        "steering_plan_revisions",
        ["basis_steering_plan_revision_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_interaction_assessments_basis_steering_step",
        "interaction_assessments",
        "steering_steps",
        ["basis_steering_step_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_interaction_assessments_basis_runtime_binding",
        "interaction_assessments",
        "work_runtime_bindings",
        ["basis_active_runtime_binding_id"],
        ["id"],
    )

    op.add_column(
        "work_reality_revisions",
        sa.Column(
            "source_record_ids",
            postgresql.JSONB(),
            server_default=empty_json,
            nullable=False,
        ),
    )
    op.alter_column("work_reality_revisions", "source_record_ids", server_default=None)


def downgrade() -> None:
    op.drop_column("work_reality_revisions", "source_record_ids")
    op.drop_constraint(
        "fk_interaction_assessments_basis_runtime_binding",
        "interaction_assessments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_interaction_assessments_basis_steering_step",
        "interaction_assessments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_interaction_assessments_basis_steering_revision",
        "interaction_assessments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_interaction_assessments_basis_work_revision",
        "interaction_assessments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_interaction_assessments_impact_known",
        "interaction_assessments",
        type_="check",
    )
    op.drop_constraint(
        "ck_interaction_assessments_focus_known",
        "interaction_assessments",
        type_="check",
    )
    for column in (
        "supporting_references",
        "basis_active_runtime_binding_id",
        "basis_steering_step_id",
        "basis_steering_plan_revision_id",
        "basis_work_revision_id",
        "candidate_change",
        "impact_disposition",
        "focus_classification",
    ):
        op.drop_column("interaction_assessments", column)
    op.drop_column("interaction_records", "supporting_references")
