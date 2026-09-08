"""Add durable Human-Watt turns, conversation history, and schema selection.

Revision ID: 20260908_28
Revises: 20260908_27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260908_28"
down_revision: str | None = "20260908_27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_interactions",
        sa.Column("selected_design_schema_identity", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "product_interactions",
        sa.Column("selected_design_schema_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "product_interactions",
        sa.Column("design_schema_selection_rationale", sa.Text(), nullable=True),
    )
    op.add_column(
        "guided_design_processes",
        sa.Column("schema_selection_rationale", sa.Text(), nullable=True),
    )
    op.execute(
        "UPDATE guided_design_processes SET schema_selection_rationale = "
        "$$General product/system design was the only admitted seed schema at creation time.$$ "
        "WHERE schema_selection_rationale IS NULL"
    )
    op.alter_column("guided_design_processes", "schema_selection_rationale", nullable=False)

    op.create_table(
        "interaction_turns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("request_record_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('RECEIVED', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="ck_interaction_turns_status_known",
        ),
        sa.ForeignKeyConstraint(["interaction_id"], ["product_interactions.id"], name="fk_interaction_turns_interaction"),
        sa.ForeignKeyConstraint(["request_record_id"], ["interaction_records.id"], name="fk_interaction_turns_request_record"),
        sa.ForeignKeyConstraint(["assessment_id"], ["interaction_assessments.id"], name="fk_interaction_turns_assessment"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_record_id"),
        sa.UniqueConstraint("assessment_id"),
    )
    op.create_table(
        "interaction_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interaction_id", sa.Uuid(), nullable=False),
        sa.Column("turn_id", sa.Uuid(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("interaction_record_id", sa.Uuid(), nullable=True),
        sa.Column("interpretation_assessment_id", sa.Uuid(), nullable=True),
        sa.Column("design_result_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("governance_event_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("supporting_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("actor IN ('HUMAN', 'WATT')", name="ck_interaction_messages_actor_known"),
        sa.CheckConstraint(
            "processing_status IN ('RECEIVED', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name="ck_interaction_messages_status_known",
        ),
        sa.ForeignKeyConstraint(["interaction_id"], ["product_interactions.id"], name="fk_interaction_messages_interaction"),
        sa.ForeignKeyConstraint(["turn_id"], ["interaction_turns.id"], name="fk_interaction_messages_turn"),
        sa.ForeignKeyConstraint(["interaction_record_id"], ["interaction_records.id"], name="fk_interaction_messages_record"),
        sa.ForeignKeyConstraint(["interpretation_assessment_id"], ["interaction_assessments.id"], name="fk_interaction_messages_assessment"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interaction_id", "sequence", name="uq_interaction_messages_interaction_sequence"),
        sa.UniqueConstraint("turn_id", "actor", name="uq_interaction_messages_turn_actor"),
        sa.UniqueConstraint("interaction_record_id"),
        sa.UniqueConstraint("interpretation_assessment_id"),
    )


def downgrade() -> None:
    op.drop_table("interaction_messages")
    op.drop_table("interaction_turns")
    op.drop_column("guided_design_processes", "schema_selection_rationale")
    op.drop_column("product_interactions", "design_schema_selection_rationale")
    op.drop_column("product_interactions", "selected_design_schema_version")
    op.drop_column("product_interactions", "selected_design_schema_identity")
