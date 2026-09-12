"""add native multi-repository candidate vectors

Revision ID: 20260912_35
Revises: 20260911_34
Create Date: 2026-09-12 03:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260912_35"
down_revision: str | Sequence[str] | None = "20260911_34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "native_candidate_vectors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pwu_id", sa.Uuid(), nullable=False),
        sa.Column("source_vector_digest", sa.String(64), nullable=False),
        sa.Column("checkpoint_id", sa.Uuid(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pwu_id"], ["production_work_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checkpoint_id"], ["checkpoint_bundles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_digest"),
    )
    op.create_table(
        "native_candidate_vector_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vector_id", sa.Uuid(), nullable=False),
        sa.Column("mount_id", sa.String(255), nullable=False),
        sa.Column("target", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("observed_revision", sa.String(128), nullable=True),
        sa.Column("operation_key", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["vector_id"], ["native_candidate_vectors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation_key"),
        sa.UniqueConstraint("vector_id", "mount_id", name="uq_native_candidate_vector_mount"),
    )
    op.create_table(
        "native_candidate_vector_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vector_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("authority_identity", sa.String(255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vector_id"], ["native_candidate_vectors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vector_id"),
    )
    op.create_table(
        "native_trusted_source_pointers",
        sa.Column("repository_identity", sa.String(1024), nullable=False),
        sa.Column("target_authoritative_ref", sa.String(1024), nullable=False),
        sa.Column("repository_revision", sa.String(128), nullable=False),
        sa.Column("tree_identity", sa.String(128), nullable=False),
        sa.Column("trusted_vector_digest", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("repository_identity", "target_authoritative_ref"),
    )
    op.create_table(
        "native_aggregate_runtime_commits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vector_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("authorization_id", sa.Uuid(), nullable=False),
        sa.Column("trusted_vector_digest", sa.String(64), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["authorization_id"], ["native_candidate_vector_authorizations.id"]),
        sa.ForeignKeyConstraint(["vector_id"], ["native_candidate_vectors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trusted_vector_digest"),
        sa.UniqueConstraint("vector_id"),
    )


def downgrade() -> None:
    op.drop_table("native_aggregate_runtime_commits")
    op.drop_table("native_trusted_source_pointers")
    op.drop_table("native_candidate_vector_authorizations")
    op.drop_table("native_candidate_vector_targets")
    op.drop_table("native_candidate_vectors")
