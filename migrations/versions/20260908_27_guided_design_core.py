"""Add reconstructable guided design process and agenda truth.

Revision ID: 20260908_27
Revises: 20260907_26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260908_27"
down_revision: str | None = "20260907_26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_steering_decisions_attention_reason_known",
        "steering_decisions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_steering_decisions_attention_reason_known",
        "steering_decisions",
        "attention_reason IS NULL OR attention_reason IN "
        "('MOTIVE_OR_OUTCOME_AMBIGUITY', "
        "'MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION', "
        "'SCOPE_OR_AUTHORITY_EXPANSION', "
        "'MATERIAL_RISK_OR_COST_DECISION', "
        "'PRODUCT_ACCEPTANCE_REQUIRED', "
        "'PRODUCTION_PROPOSAL_REVIEW_REQUIRED')",
    )
    op.add_column(
        "steering_steps",
        sa.Column("design_issue_key", sa.String(length=128), nullable=True),
    )
    op.create_table(
        "guided_design_processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("schema_identity", sa.String(length=255), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("basis_work_reality_revision_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "condition IN ('ACTIVE', 'READY', 'COMPLETE')",
            name="ck_guided_design_processes_condition_known",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["product_works.id"],
            name="fk_guided_design_processes_work",
        ),
        sa.ForeignKeyConstraint(
            ["basis_work_reality_revision_id"],
            ["work_reality_revisions.id"],
            name="fk_guided_design_processes_work_reality",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_id"),
    )
    op.create_table(
        "guided_design_agenda_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False),
        sa.Column("supersedes_revision_id", sa.Uuid(), nullable=True),
        sa.Column("basis_work_reality_revision_id", sa.Uuid(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reality_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("issues", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_guided_design_agenda_revision_positive",
        ),
        sa.CheckConstraint(
            "condition IN ('ACTIVE', 'SUPERSEDED')",
            name="ck_guided_design_agenda_condition_known",
        ),
        sa.ForeignKeyConstraint(
            ["process_id"],
            ["guided_design_processes.id"],
            name="fk_guided_design_agenda_revisions_process",
        ),
        sa.ForeignKeyConstraint(
            ["work_id"],
            ["product_works.id"],
            name="fk_guided_design_agenda_revisions_work",
        ),
        sa.ForeignKeyConstraint(
            ["basis_work_reality_revision_id"],
            ["work_reality_revisions.id"],
            name="fk_guided_design_agenda_revisions_work_reality",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["guided_design_agenda_revisions.id"],
            name="fk_guided_design_agenda_revisions_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "process_id",
            "revision_number",
            name="uq_guided_design_agenda_process_revision",
        ),
        sa.UniqueConstraint("supersedes_revision_id"),
    )
    op.create_index(
        "uq_guided_design_agenda_one_active",
        "guided_design_agenda_revisions",
        ["process_id"],
        unique=True,
        postgresql_where=sa.text("condition = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_guided_design_agenda_one_active",
        table_name="guided_design_agenda_revisions",
    )
    op.drop_table("guided_design_agenda_revisions")
    op.drop_table("guided_design_processes")
    op.drop_column("steering_steps", "design_issue_key")
    op.drop_constraint(
        "ck_steering_decisions_attention_reason_known",
        "steering_decisions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_steering_decisions_attention_reason_known",
        "steering_decisions",
        "attention_reason IS NULL OR attention_reason IN "
        "('MOTIVE_OR_OUTCOME_AMBIGUITY', "
        "'MAJOR_PRODUCT_OR_ARCHITECTURE_DECISION', "
        "'SCOPE_OR_AUTHORITY_EXPANSION', "
        "'MATERIAL_RISK_OR_COST_DECISION', "
        "'PRODUCT_ACCEPTANCE_REQUIRED')",
    )
