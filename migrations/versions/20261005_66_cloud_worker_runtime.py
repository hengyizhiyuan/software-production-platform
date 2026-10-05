"""Govern existing native queue and workers as Cloud Worker runtime resources.

Revision ID: 20261005_66
Revises: 20261002_65
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20261005_66"
down_revision = "20261002_65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("executor_queue", sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("execution_resource_envelopes", sa.Column("max_log_bytes", sa.BigInteger(), nullable=False, server_default="65536"))
    op.add_column("execution_resource_envelopes", sa.Column("max_artifact_bytes", sa.BigInteger(), nullable=False, server_default="67108864"))
    op.add_column("executor_worker_registrations", sa.Column("name", sa.String(255), nullable=False, server_default="unidentified"))
    op.add_column("executor_worker_registrations", sa.Column("hostname", sa.String(255), nullable=False, server_default="unknown"))
    op.add_column("executor_worker_registrations", sa.Column("runtime_version", sa.String(128), nullable=False, server_default="legacy"))
    op.add_column("executor_worker_registrations", sa.Column("status", sa.String(32), nullable=False, server_default="READY"))
    op.add_column("executor_worker_registrations", sa.Column("current_task_id", sa.Uuid(), nullable=True))
    op.add_column("executor_worker_registrations", sa.Column("capacity", JSONB(), nullable=False, server_default='{"max_concurrency": 1}'))
    op.add_column("executor_worker_registrations", sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_table(
        "executor_worker_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("worker_id", sa.String(255), sa.ForeignKey("executor_worker_registrations.worker_id"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("payload_reference", sa.String(80), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_executor_worker_events_worker_time", "executor_worker_events", ["worker_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_executor_worker_events_worker_time", table_name="executor_worker_events")
    op.drop_table("executor_worker_events")
    for column in ("registered_at", "capacity", "current_task_id", "status", "runtime_version", "hostname", "name"):
        op.drop_column("executor_worker_registrations", column)
    op.drop_column("executor_queue", "priority")
    op.drop_column("execution_resource_envelopes", "max_artifact_bytes")
    op.drop_column("execution_resource_envelopes", "max_log_bytes")
