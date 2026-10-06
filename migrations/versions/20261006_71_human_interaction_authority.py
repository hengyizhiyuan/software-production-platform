"""Durable qualified decisions and derived WIC realization cache."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "20261006_71"
down_revision = "20261006_70"
branch_labels = None
depends_on = None

def upgrade():
    for name in ('steering_decisions', 'semantic_step_results'):
        op.add_column(name, sa.Column('human_decision_need', JSONB(), nullable=True))
    op.create_table('wic_human_realizations',
        sa.Column('basis_fingerprint', sa.String(64), primary_key=True),
        sa.Column('work_id', sa.Uuid(), sa.ForeignKey('product_works.id'), nullable=True),
        sa.Column('projection', JSONB(), nullable=False),
        sa.Column('realization', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

def downgrade():
    bind = op.get_bind()
    if any(bind.scalar(sa.text('SELECT count(*) FROM '+name+' WHERE human_decision_need IS NOT NULL'))
           for name in ('steering_decisions','semantic_step_results')):
        raise RuntimeError('Qualified decision evidence must be preserved before downgrade')
    op.drop_table('wic_human_realizations')
    for name in ('semantic_step_results','steering_decisions'):
        op.drop_column(name,'human_decision_need')
