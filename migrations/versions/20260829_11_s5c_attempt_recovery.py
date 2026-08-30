"""Extend narrow Recovery Actions for S5-C Attempt recovery.

Revision ID: 20260829_11
Revises: 20260829_10
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_11"
down_revision: str | None = "20260829_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "recovery_action_type_is_narrow",
        "recovery_action_records",
        type_="check",
    )
    op.drop_constraint(
        "recovery_action_subject_is_repository_integration",
        "recovery_action_records",
        type_="check",
    )
    op.drop_constraint(
        "recovery_action_outcome_is_known",
        "recovery_action_records",
        type_="check",
    )
    op.alter_column(
        "recovery_action_records",
        "integration_effect_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "recovery_action_records",
        "candidate_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "recovery_action_records",
        "observed_repository_revision",
        existing_type=sa.String(length=128),
        nullable=True,
    )
    op.alter_column(
        "recovery_action_records",
        "observed_tree_identity",
        existing_type=sa.String(length=128),
        nullable=True,
    )
    op.add_column(
        "recovery_action_records",
        sa.Column("old_attempt_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "recovery_action_records",
        sa.Column("new_attempt_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "recovery_action_records",
        sa.Column("old_generation", sa.Integer(), nullable=True),
    )
    op.add_column(
        "recovery_action_records",
        sa.Column("new_generation", sa.Integer(), nullable=True),
    )
    op.add_column(
        "recovery_action_records",
        sa.Column("workspace_identity", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "recovery_action_records",
        sa.Column("repository_observation_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "recovery_action_records",
        sa.Column("completion_evaluation_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_recovery_actions_old_attempt",
        "recovery_action_records",
        "execution_attempts",
        ["old_attempt_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_recovery_actions_new_attempt",
        "recovery_action_records",
        "execution_attempts",
        ["new_attempt_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_recovery_actions_observation",
        "recovery_action_records",
        "repository_observations",
        ["repository_observation_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_recovery_actions_completion",
        "recovery_action_records",
        "completion_evaluations",
        ["completion_evaluation_id"],
        ["id"],
    )
    op.create_check_constraint(
        "recovery_action_type_is_narrow",
        "recovery_action_records",
        "action_type IN ('RECORD_EXTERNAL_CONVERGENCE', 'RETRY_RUNTIME_COMMIT', "
        "'REOBSERVE_ATTEMPT_WORK', 'RETRY_WITH_NEW_ATTEMPT', "
        "'RESUME_EXISTING_ATTEMPT')",
    )
    op.create_check_constraint(
        "recovery_action_subject_is_narrow",
        "recovery_action_records",
        "subject_type IN ('REPOSITORY_INTEGRATION', 'ATTEMPT')",
    )
    op.create_check_constraint(
        "recovery_action_outcome_is_known",
        "recovery_action_records",
        "outcome IN ('APPLIED', 'NO_ACTION', 'SALVAGED', 'INCOMPLETE', "
        "'RETRY_CREATED', 'UNSUPPORTED_DEFERRED')",
    )
    op.create_check_constraint(
        "recovery_action_subject_binding_is_exact",
        "recovery_action_records",
        "(subject_type = 'REPOSITORY_INTEGRATION' "
        "AND integration_effect_id IS NOT NULL AND candidate_id IS NOT NULL "
        "AND old_attempt_id IS NULL) OR "
        "(subject_type = 'ATTEMPT' AND old_attempt_id IS NOT NULL "
        "AND integration_effect_id IS NULL AND candidate_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "recovery_action_subject_binding_is_exact",
        "recovery_action_records",
        type_="check",
    )
    op.drop_constraint(
        "recovery_action_outcome_is_known",
        "recovery_action_records",
        type_="check",
    )
    op.drop_constraint(
        "recovery_action_subject_is_narrow",
        "recovery_action_records",
        type_="check",
    )
    op.drop_constraint(
        "recovery_action_type_is_narrow",
        "recovery_action_records",
        type_="check",
    )
    for constraint in (
        "fk_recovery_actions_completion",
        "fk_recovery_actions_observation",
        "fk_recovery_actions_new_attempt",
        "fk_recovery_actions_old_attempt",
    ):
        op.drop_constraint(constraint, "recovery_action_records", type_="foreignkey")
    for column in (
        "completion_evaluation_id",
        "repository_observation_id",
        "workspace_identity",
        "new_generation",
        "old_generation",
        "new_attempt_id",
        "old_attempt_id",
    ):
        op.drop_column("recovery_action_records", column)
    op.alter_column(
        "recovery_action_records",
        "observed_tree_identity",
        existing_type=sa.String(length=128),
        nullable=False,
    )
    op.alter_column(
        "recovery_action_records",
        "observed_repository_revision",
        existing_type=sa.String(length=128),
        nullable=False,
    )
    op.alter_column(
        "recovery_action_records",
        "candidate_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.alter_column(
        "recovery_action_records",
        "integration_effect_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_check_constraint(
        "recovery_action_type_is_narrow",
        "recovery_action_records",
        "action_type IN ('RECORD_EXTERNAL_CONVERGENCE', 'RETRY_RUNTIME_COMMIT')",
    )
    op.create_check_constraint(
        "recovery_action_subject_is_repository_integration",
        "recovery_action_records",
        "subject_type = 'REPOSITORY_INTEGRATION'",
    )
    op.create_check_constraint(
        "recovery_action_outcome_is_known",
        "recovery_action_records",
        "outcome IN ('APPLIED', 'NO_ACTION')",
    )
