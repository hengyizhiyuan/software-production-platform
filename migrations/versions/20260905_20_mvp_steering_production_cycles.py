"""Allow long-lived Works to own independent Steering production cycles.

Revision ID: 20260905_20
Revises: 20260905_19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260905_20"
down_revision: str | None = "20260905_19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("work_runtime_bindings", sa.Column("id", sa.Uuid(), nullable=True))
    op.add_column(
        "work_runtime_bindings",
        sa.Column("cycle_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "work_runtime_bindings",
        sa.Column("steering_step_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "work_runtime_bindings",
        sa.Column("steering_decision_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "work_runtime_bindings",
        sa.Column(
            "condition",
            sa.String(length=32),
            server_default="ADMITTED",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE work_runtime_bindings
        SET id = (
            substr(md5(work_id::text || production_run_id::text), 1, 8) || '-' ||
            substr(md5(work_id::text || production_run_id::text), 9, 4) || '-' ||
            substr(md5(work_id::text || production_run_id::text), 13, 4) || '-' ||
            substr(md5(work_id::text || production_run_id::text), 17, 4) || '-' ||
            substr(md5(work_id::text || production_run_id::text), 21, 12)
        )::uuid,
            cycle_number = 1
        """
    )
    op.alter_column("work_runtime_bindings", "id", nullable=False)
    op.alter_column("work_runtime_bindings", "cycle_number", nullable=False)
    op.drop_constraint(
        "pk_work_runtime_bindings", "work_runtime_bindings", type_="primary"
    )
    op.create_primary_key("pk_work_runtime_bindings", "work_runtime_bindings", ["id"])
    op.create_unique_constraint(
        "uq_work_runtime_bindings_work_cycle",
        "work_runtime_bindings",
        ["work_id", "cycle_number"],
    )
    op.create_unique_constraint(
        "uq_work_runtime_bindings_steering_step_id",
        "work_runtime_bindings",
        ["steering_step_id"],
    )
    op.create_foreign_key(
        "fk_work_runtime_bindings_steering_step",
        "work_runtime_bindings",
        "steering_steps",
        ["steering_step_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_work_runtime_bindings_steering_decision",
        "work_runtime_bindings",
        "steering_decisions",
        ["steering_decision_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_work_runtime_bindings_condition_known",
        "work_runtime_bindings",
        "condition IN ('ADMITTED', 'TRUSTED')",
    )
    op.alter_column("work_runtime_bindings", "condition", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_work_runtime_bindings_condition_known",
        "work_runtime_bindings",
        type_="check",
    )
    op.drop_constraint(
        "fk_work_runtime_bindings_steering_decision",
        "work_runtime_bindings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_work_runtime_bindings_steering_step",
        "work_runtime_bindings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_work_runtime_bindings_steering_step_id",
        "work_runtime_bindings",
        type_="unique",
    )
    op.drop_constraint(
        "uq_work_runtime_bindings_work_cycle",
        "work_runtime_bindings",
        type_="unique",
    )
    op.drop_constraint(
        "pk_work_runtime_bindings", "work_runtime_bindings", type_="primary"
    )
    op.create_primary_key("pk_work_runtime_bindings", "work_runtime_bindings", ["work_id"])
    op.drop_column("work_runtime_bindings", "condition")
    op.drop_column("work_runtime_bindings", "steering_decision_id")
    op.drop_column("work_runtime_bindings", "steering_step_id")
    op.drop_column("work_runtime_bindings", "cycle_number")
    op.drop_column("work_runtime_bindings", "id")
