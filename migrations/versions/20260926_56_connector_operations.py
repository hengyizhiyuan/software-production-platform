"""Add connector controls and credential audit without storing secrets.

Revision ID: 20260926_56
Revises: 20260926_55
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260926_56"
down_revision = "20260926_55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("connector_controls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("connector_id", sa.String(255), nullable=False),
        sa.Column("capability_id", sa.String(255), nullable=False),
        sa.Column("owner_scope", sa.String(32), nullable=False),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("deprecated", sa.Boolean(), nullable=False),
        sa.Column("health", sa.String(32), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_code", sa.String(128)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connector_id", "capability_id", "owner_scope", "owner_id", "version",
            name="uq_connector_controls_identity"))
    op.create_table("connector_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("subject_kind", sa.String(32), nullable=False),
        sa.Column("subject_id", sa.String(255), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("detail", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_connector_audit_subject", "connector_audit_events", ["subject_kind", "subject_id"])
    op.add_column("github_access_grants", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.add_column("github_access_grants", sa.Column("last_verified_at", sa.DateTime(timezone=True)))
    op.add_column("github_access_grants", sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("github_access_grants", sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("github_access_grants", sa.Column("last_failure_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    for name in ("last_failure_at", "failure_count", "usage_count", "last_verified_at", "expires_at"):
        op.drop_column("github_access_grants", name)
    op.drop_index("ix_connector_audit_subject", table_name="connector_audit_events")
    op.drop_table("connector_audit_events")
    op.drop_table("connector_controls")
