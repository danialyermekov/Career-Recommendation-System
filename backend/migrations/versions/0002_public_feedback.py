"""Consent-based publication and authenticated feature votes; preserve legacy private feedback."""
import sqlalchemy as sa
from alembic import op

revision = '0002_public_feedback'
down_revision = '0001_public_beta'
branch_labels = None
depends_on = None


def upgrade():
    # Legacy feedback stays untyped, private and pending; no consent is inferred.
    columns = [
        sa.Column('type', sa.String(20)), sa.Column('title', sa.String(120)),
        sa.Column('reproduction_steps', sa.String(2000), nullable=False, server_default=''),
        sa.Column('public_consent', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('moderation_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('development_status', sa.String(20)),
        sa.Column('origin', sa.String(20), nullable=False, server_default='unverified'),
        sa.Column('moderation_note', sa.String(2000), nullable=False, server_default=''),
        sa.Column('roadmap_key', sa.String(80)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]
    for column in columns:
        op.add_column('feedback', column, schema='careerflow')
    op.execute('UPDATE careerflow.feedback SET updated_at = created_at')
    op.alter_column('feedback', 'updated_at', server_default=None, schema='careerflow')
    checks = {
        'ck_feedback_type': "type IS NULL OR type IN ('review', 'feature', 'bug')",
        'ck_feedback_moderation': "moderation_status IN ('pending', 'approved', 'rejected')",
        'ck_feedback_origin': "origin IN ('unverified', 'community', 'developer', 'test')",
        'ck_feedback_development': "development_status IS NULL OR (type = 'feature' AND development_status IN ('suggested', 'planned', 'in_progress', 'released'))",
        'ck_review_rating': "type != 'review' OR rating IS NOT NULL",
        'ck_feedback_title': "type NOT IN ('feature', 'bug') OR title IS NOT NULL",
    }
    for name, expression in checks.items():
        op.create_check_constraint(name, 'feedback', expression, schema='careerflow')
    op.create_index('ix_feedback_public', 'feedback', ['type', 'moderation_status', 'created_at'], schema='careerflow')
    op.create_table('feedback_votes',
        sa.Column('id', sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column('feedback_id', sa.Uuid(as_uuid=False), sa.ForeignKey('careerflow.feedback.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Uuid(as_uuid=False), sa.ForeignKey('careerflow.users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('feedback_id', 'user_id', name='uq_feedback_vote_user'), schema='careerflow')
    op.create_index('ix_feedback_votes_user', 'feedback_votes', ['user_id'], schema='careerflow')
    op.execute('ALTER TABLE careerflow.feedback_votes ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE careerflow.feedback_votes FROM PUBLIC, anon, authenticated')


def downgrade():
    raise RuntimeError('Destructive downgrade disabled; roll back application images and retain feedback data.')
