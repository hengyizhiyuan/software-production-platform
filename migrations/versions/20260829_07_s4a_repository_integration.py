"""Add the narrow S4-A repository ref integration effect.

Revision ID: 20260829_07
Revises: 20260828_06
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_07"
down_revision: str | None = "20260828_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repository_integration_effects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("effect_type", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("human_authorization_id", sa.Uuid(), nullable=False),
        sa.Column("repository_identity", sa.String(length=255), nullable=False),
        sa.Column("target_authoritative_ref", sa.String(length=512), nullable=False),
        sa.Column(
            "expected_source_repository_revision",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("proposed_repository_revision", sa.String(length=128), nullable=False),
        sa.Column("proposed_tree_identity", sa.String(length=128), nullable=False),
        sa.Column("operation_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "prepared_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("observed_repository_revision", sa.String(length=128), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converged_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "effect_type = 'REPOSITORY_REF_ADVANCE'",
            name="repository_effect_is_ref_advance",
        ),
        sa.CheckConstraint(
            "state IN ('PREPARED', 'CONVERGED')",
            name="repository_effect_state_is_narrow",
        ),
        sa.CheckConstraint(
            "(state = 'PREPARED' AND converged_at IS NULL) OR "
            "(state = 'CONVERGED' AND converged_at IS NOT NULL "
            "AND observed_repository_revision = proposed_repository_revision)",
            name="repository_effect_convergence_is_observed",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["baseline_candidates.id"],
            name="fk_repository_effects_candidate",
        ),
        sa.ForeignKeyConstraint(
            ["human_authorization_id"],
            ["human_authorizations.id"],
            name="fk_repository_effects_authorization",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "operation_fingerprint",
            name="uq_repository_effects_operation",
        ),
    )


def downgrade() -> None:
    op.drop_table("repository_integration_effects")
