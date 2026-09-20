"""persist expiring native Executor worker capacity observations

Revision ID: 20260919_44
Revises: 20260918_43
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260919_44"
down_revision = "20260918_43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executor_worker_registrations",
        sa.Column("worker_id", sa.String(length=255), primary_key=True),
        sa.Column("worker_profile", sa.String(length=255), nullable=False),
        sa.Column("provider_profiles", postgresql.JSONB(), nullable=False),
        sa.Column("resource_profiles", postgresql.JSONB(), nullable=False),
        sa.Column("capability_identities", postgresql.JSONB(), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_executor_worker_registrations_expires",
        "executor_worker_registrations",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_executor_worker_registrations_expires",
        table_name="executor_worker_registrations",
    )
    op.drop_table("executor_worker_registrations")
