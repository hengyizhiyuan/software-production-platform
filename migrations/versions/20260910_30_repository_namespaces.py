"""Partition trusted baseline pointers by immutable repository identity and ref."""
from alembic import op
import sqlalchemy as sa
revision = "20260910_30"
down_revision = "20260909_29"
branch_labels = depends_on = None


def upgrade():
    op.add_column("current_trusted_baseline_pointer", sa.Column("repository_identity", sa.String(255)))
    op.add_column("current_trusted_baseline_pointer", sa.Column("repository_ref", sa.String(512)))
    op.execute("UPDATE current_trusted_baseline_pointer p SET repository_identity=s.repository_identity, repository_ref=s.repository_ref FROM production_snapshots s WHERE s.id=p.snapshot_id")
    op.alter_column("current_trusted_baseline_pointer", "repository_identity", nullable=False)
    op.alter_column("current_trusted_baseline_pointer", "repository_ref", nullable=False)
    op.drop_constraint("singleton_id_is_one", "current_trusted_baseline_pointer", type_="check")
    op.drop_constraint("pk_current_trusted_baseline_pointer", "current_trusted_baseline_pointer", type_="primary")
    op.drop_column("current_trusted_baseline_pointer", "singleton_id")
    op.create_primary_key("pk_current_trusted_baseline_pointer", "current_trusted_baseline_pointer", ["repository_identity", "repository_ref"])
    op.create_unique_constraint("uq_snapshot_repository", "production_snapshots", ["id", "repository_identity", "repository_ref"])
    op.create_foreign_key("fk_pointer_repository_baseline", "current_trusted_baseline_pointer", "production_snapshots", ["snapshot_id", "repository_identity", "repository_ref"], ["id", "repository_identity", "repository_ref"])
    op.create_foreign_key("fk_snapshot_same_repository_source", "production_snapshots", "production_snapshots", ["source_baseline_id", "repository_identity", "repository_ref"], ["id", "repository_identity", "repository_ref"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM current_trusted_baseline_pointer")) > 1:
        raise RuntimeError("Cannot collapse multiple repository baselines; restore a compatible backup")
    op.drop_constraint("fk_snapshot_same_repository_source", "production_snapshots", type_="foreignkey")
    op.drop_constraint("fk_pointer_repository_baseline", "current_trusted_baseline_pointer", type_="foreignkey")
    op.drop_constraint("uq_snapshot_repository", "production_snapshots", type_="unique")
    op.drop_constraint("pk_current_trusted_baseline_pointer", "current_trusted_baseline_pointer", type_="primary")
    op.add_column("current_trusted_baseline_pointer", sa.Column("singleton_id", sa.SmallInteger(), nullable=False, server_default="1"))
    op.create_primary_key("pk_current_trusted_baseline_pointer", "current_trusted_baseline_pointer", ["singleton_id"])
    op.create_check_constraint("singleton_id_is_one", "current_trusted_baseline_pointer", "singleton_id = 1")
    op.drop_column("current_trusted_baseline_pointer", "repository_identity")
    op.drop_column("current_trusted_baseline_pointer", "repository_ref")
