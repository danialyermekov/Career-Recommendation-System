"""Private lifetime AI allocations and serialized cost controls."""
from alembic import op
import sqlalchemy as sa

revision = '0003_ai_trial'
down_revision = '0002_public_feedback'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ai_trial_usage',
        sa.Column('identity', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Uuid(as_uuid=False), sa.ForeignKey('careerflow.users.id', ondelete='CASCADE'), unique=True),
        sa.Column('used', sa.Integer, nullable=False, server_default='0'),
        sa.Column('reservation', sa.String(36)),
        sa.Column('lease_until', sa.DateTime(timezone=True)),
        sa.CheckConstraint('used >= 0', name='ck_ai_trial_used'), schema='careerflow')
    op.create_table('ai_trial_budget',
        sa.Column('id', sa.String(20), primary_key=True),
        sa.Column('day', sa.Date, nullable=False),
        sa.Column('attempts', sa.Integer, nullable=False), schema='careerflow')
    op.create_table('ai_trial_ip',
        sa.Column('identity', sa.String(64), primary_key=True),
        sa.Column('window', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer, nullable=False), schema='careerflow')
    for name in ('ai_trial_usage', 'ai_trial_budget', 'ai_trial_ip'):
        op.execute(f'ALTER TABLE careerflow.{name} ENABLE ROW LEVEL SECURITY')
        op.execute(f'REVOKE ALL ON TABLE careerflow.{name} FROM PUBLIC, anon, authenticated')


def downgrade():
    raise RuntimeError('Destructive downgrade disabled; disable the preview and roll back the application image.')
