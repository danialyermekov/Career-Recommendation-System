import sqlalchemy as sa
from alembic import op
revision = '0001_public_beta'
down_revision = None
branch_labels = None
depends_on = None
metadata = sa.MetaData(schema='careerflow')
uuid_type = sa.Uuid(as_uuid=False)
users = sa.Table('users', metadata,
    sa.Column('id', uuid_type, primary_key=True),
    sa.Column('display_name', sa.String(200), nullable=False),
    sa.Column('deletion_pending', sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
sessions = sa.Table('recommendation_sessions', metadata,
    sa.Column('id', uuid_type, primary_key=True),
    sa.Column('user_id', uuid_type, sa.ForeignKey(users.c.id, ondelete='CASCADE'), nullable=False),
    sa.Column('top_profession', sa.String(100), nullable=False),
    sa.Column('alternative_profession', sa.String(100)),
    sa.Column('profile_json', sa.JSON, nullable=False),
    sa.Column('result_json', sa.JSON, nullable=False),
    sa.Column('context', sa.Text, nullable=False),
    sa.Column('progress_json', sa.JSON, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
sa.Index('ix_sessions_user_updated', sessions.c.user_id, sessions.c.updated_at)

def _session_table(name, *columns, unique):
    return sa.Table(name, metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('session_id', uuid_type, sa.ForeignKey(sessions.c.id, ondelete='CASCADE'), nullable=False),
        *columns, sa.UniqueConstraint('session_id', *unique))

scores = _session_table('specialization_scores', sa.Column('profession', sa.String(100), nullable=False),
    *[sa.Column(name, sa.Float) for name in ('final_score', 'skill_score', 'classification_score', 'trend_score', 'market_share', 'predicted_vacancies')], unique=['profession'])
gaps = _session_table('skill_gaps', sa.Column('profession', sa.String(100), nullable=False),
    sa.Column('category', sa.String(100), nullable=False), sa.Column('skill', sa.String(200), nullable=False),
    sa.Column('is_missing', sa.Boolean, nullable=False), unique=['profession', 'category', 'skill'])
roadmap = _session_table('roadmap_items', sa.Column('profession', sa.String(100), nullable=False),
    sa.Column('category', sa.String(100), nullable=False), sa.Column('skill', sa.String(200), nullable=False),
    sa.Column('category_position', sa.Integer, nullable=False), sa.Column('position', sa.Integer, nullable=False),
    sa.Column('is_done', sa.Boolean, nullable=False), sa.Column('courses_json', sa.JSON, nullable=False), unique=['profession', 'category', 'skill'])
course_progress = _session_table('course_progress', sa.Column('category', sa.String(100), nullable=False),
    sa.Column('skill', sa.String(200), nullable=False), sa.Column('course_title', sa.Text, nullable=False),
    sa.Column('platform', sa.Text, nullable=False), sa.Column('course_url', sa.Text),
    sa.Column('is_started', sa.Boolean, nullable=False), sa.Column('is_completed', sa.Boolean, nullable=False), unique=['category', 'skill', 'course_title', 'platform'])
preferences = sa.Table('course_filter_preferences', metadata,
    sa.Column('session_id', uuid_type, sa.ForeignKey(sessions.c.id, ondelete='CASCADE'), primary_key=True),
    sa.Column('filters_json', sa.JSON, nullable=False))
feedback = sa.Table('feedback', metadata,
    sa.Column('id', uuid_type, primary_key=True),
    sa.Column('user_id', uuid_type, sa.ForeignKey(users.c.id, ondelete='CASCADE')),
    sa.Column('session_id', uuid_type, sa.ForeignKey(sessions.c.id, ondelete='SET NULL')),
    sa.Column('rating', sa.Integer), sa.Column('category', sa.String(20), nullable=False),
    sa.Column('message', sa.String(4000), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('rating IS NULL OR rating BETWEEN 1 AND 5'),
    sa.CheckConstraint("category IN ('suggestion', 'bug', 'general')"))
sa.Index('ix_feedback_created', feedback.c.created_at)


def upgrade():
    op.execute('CREATE SCHEMA IF NOT EXISTS careerflow')
    metadata.create_all(op.get_bind(), checkfirst=False)
    op.create_foreign_key('fk_users_supabase_auth', 'users', 'users', ['id'], ['id'],
        source_schema='careerflow', referent_schema='auth', ondelete='CASCADE')
    for table in metadata.sorted_tables:
        op.execute(f'ALTER TABLE careerflow.{table.name} ENABLE ROW LEVEL SECURITY')
        op.execute(f'REVOKE ALL ON careerflow.{table.name} FROM anon, authenticated')
    op.execute('REVOKE ALL ON SCHEMA careerflow FROM PUBLIC, anon, authenticated')

def downgrade():
    raise RuntimeError('Destructive downgrade disabled. Restore the previous image and retain PostgreSQL; see deployment docs.')
