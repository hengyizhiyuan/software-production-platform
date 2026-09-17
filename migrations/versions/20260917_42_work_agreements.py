"""Add Work-scoped working-agreement event history.

Revision ID: 20260917_42
Revises: 20260915_41
"""

from alembic import op
import sqlalchemy as sa

revision = "20260917_42"
down_revision = "20260915_41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_agreement_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("work_id", sa.Uuid(), sa.ForeignKey("product_works.id"), nullable=False),
        sa.Column("agreement_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("agreement_type", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("actor_identity", sa.String(255), nullable=False),
        sa.Column("persistence_state", sa.String(24), nullable=False),
        sa.Column("persistence_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('CREATED', 'ABANDONED')", name="ck_agreement_event_kind"),
        sa.UniqueConstraint("agreement_id", "sequence", name="uq_work_agreement_event_sequence"),
        sa.CheckConstraint("agreement_type IN ('DECISION', 'CONSTRAINT', 'REMINDER', 'DEFERRED', 'CANDIDATE')", name="ck_agreement_type"),
        sa.CheckConstraint("persistence_state IN ('NOT_PERSISTED', 'PERSISTED')", name="ck_agreement_persistence_state"),
    )
    op.create_index("ix_work_agreement_events_work_time", "work_agreement_events", ["work_id", "created_at"])
    op.create_index("ix_work_agreement_events_agreement_time", "work_agreement_events", ["agreement_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_work_agreement_events_agreement_time", table_name="work_agreement_events")
    op.drop_index("ix_work_agreement_events_work_time", table_name="work_agreement_events")
    op.drop_table("work_agreement_events")
