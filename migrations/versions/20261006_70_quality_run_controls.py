"""Safe campaign controls and immutable rerun selection."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261006_70"
down_revision = "20261006_69"
branch_labels = None
depends_on = None

STATES = "state IN ('QUEUED','RUNNING','PAUSE_REQUESTED','PAUSED','STOPPING','STOPPED','PASS','FAIL','BLOCKED')"


def upgrade():
    op.add_column('quality_campaign_runs', sa.Column('parent_run_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_quality_run_parent', 'quality_campaign_runs', 'quality_campaign_runs', ['parent_run_id'], ['id'])
    op.drop_constraint('ck_quality_run_state', 'quality_campaign_runs', type_='check')
    op.create_check_constraint('ck_quality_run_state', 'quality_campaign_runs', STATES)
    op.create_table('quality_run_members',
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('quality_campaign_runs.id'), primary_key=True),
        sa.Column('case_version_id', sa.Uuid(), sa.ForeignKey('quality_case_versions.id'), primary_key=True),
        sa.Column('ordinal', sa.Integer(), nullable=False), sa.Column('cohorts', JSONB(), nullable=False),
        sa.Column('disposition', sa.String(20), nullable=False),
        sa.Column('source_case_run_id', sa.Uuid(), sa.ForeignKey('quality_case_runs.id')),
        sa.CheckConstraint("disposition IN ('ELIGIBLE','SKIPPED','NOT_RUN')", name='ck_quality_member_disposition'))
    op.create_table('quality_run_controls', sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('quality_campaign_runs.id'), nullable=False),
        sa.Column('action', sa.String(40), nullable=False), sa.Column('authority_identity', sa.String(255), nullable=False),
        sa.Column('record', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade():
    # Do not discard durable control evidence via an implicit lossy rollback.
    bind = op.get_bind()
    if bind.scalar(sa.text('SELECT count(*) FROM quality_run_controls')):
        raise RuntimeError('Quality control evidence must be archived before downgrade')
    op.drop_table('quality_run_controls')
    op.drop_table('quality_run_members')
    op.drop_constraint('fk_quality_run_parent', 'quality_campaign_runs', type_='foreignkey')
    op.drop_column('quality_campaign_runs', 'parent_run_id')
    op.drop_constraint('ck_quality_run_state', 'quality_campaign_runs', type_='check')
    op.create_check_constraint('ck_quality_run_state', 'quality_campaign_runs', "state IN ('QUEUED','RUNNING','PASS','FAIL','BLOCKED')")
