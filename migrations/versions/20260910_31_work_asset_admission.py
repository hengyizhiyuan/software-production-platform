"""Allow Work before repository and explicit asset-scope admission provenance."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "20260910_31"
down_revision = "20260910_30"
branch_labels = depends_on = None
FIELDS = ("source_assessment_id", "engineering_resource_id", "source_baseline_id", "repository_identity", "repository_ref", "source_revision")

def upgrade():
    op.create_table("repository_intakes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request", JSONB(), nullable=False),
        sa.Column("observation", JSONB(), nullable=True),
        sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("engineering_resources.id"), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for field in FIELDS:
        op.alter_column("work_reality_revisions", field, nullable=True)
    op.add_column("work_reality_revisions", sa.Column("source_kind", sa.String(32), nullable=False, server_default="INTERACTION_ASSESSMENT"))
    op.create_check_constraint("ck_work_revision_source_kind", "work_reality_revisions", "(source_kind = 'INTERACTION_ASSESSMENT' AND source_assessment_id IS NOT NULL) OR (source_kind = 'ASSET_SCOPE_ADMISSION' AND source_assessment_id IS NULL)")

def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM work_reality_revisions WHERE engineering_resource_id IS NULL OR source_assessment_id IS NULL")):
        raise RuntimeError("Repository-optional Work cannot be represented by the old schema")
    op.drop_table("repository_intakes")
    op.drop_constraint("ck_work_revision_source_kind", "work_reality_revisions", type_="check")
    op.drop_column("work_reality_revisions", "source_kind")
    for field in FIELDS:
        op.alter_column("work_reality_revisions", field, nullable=False)
