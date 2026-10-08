"""Private SQLAlchemy Core persistence. Apply schema changes with Alembic."""
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID, uuid4
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from config import DATABASE_URL

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
feedback.append_column(sa.Column('type', sa.String(20)))
feedback.append_column(sa.Column('title', sa.String(120)))
feedback.append_column(sa.Column('reproduction_steps', sa.String(2000), nullable=False, server_default=''))
feedback.append_column(sa.Column('public_consent', sa.Boolean, nullable=False, server_default=sa.false()))
feedback.append_column(sa.Column('moderation_status', sa.String(20), nullable=False, server_default='pending'))
feedback.append_column(sa.Column('development_status', sa.String(20)))
feedback.append_column(sa.Column('origin', sa.String(20), nullable=False, server_default='unverified'))
feedback.append_column(sa.Column('moderation_note', sa.String(2000), nullable=False, server_default=''))
feedback.append_column(sa.Column('roadmap_key', sa.String(80)))
feedback.append_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
feedback.append_constraint(sa.CheckConstraint("type IS NULL OR type IN ('review', 'feature', 'bug')", name='ck_feedback_type'))
feedback.append_constraint(sa.CheckConstraint("moderation_status IN ('pending', 'approved', 'rejected')", name='ck_feedback_moderation'))
feedback.append_constraint(sa.CheckConstraint("origin IN ('unverified', 'community', 'developer', 'test')", name='ck_feedback_origin'))
feedback.append_constraint(sa.CheckConstraint("development_status IS NULL OR (type = 'feature' AND development_status IN ('suggested', 'planned', 'in_progress', 'released'))", name='ck_feedback_development'))
feedback.append_constraint(sa.CheckConstraint("type != 'review' OR rating IS NOT NULL", name='ck_review_rating'))
feedback.append_constraint(sa.CheckConstraint("type NOT IN ('feature', 'bug') OR title IS NOT NULL", name='ck_feedback_title'))
sa.Index('ix_feedback_created', feedback.c.created_at)
sa.Index('ix_feedback_public', feedback.c.type, feedback.c.moderation_status, feedback.c.created_at)
feedback_votes = sa.Table('feedback_votes', metadata,
    sa.Column('id', uuid_type, primary_key=True),
    sa.Column('feedback_id', uuid_type, sa.ForeignKey(feedback.c.id, ondelete='CASCADE'), nullable=False),
    sa.Column('user_id', uuid_type, sa.ForeignKey(users.c.id, ondelete='CASCADE'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint('feedback_id', 'user_id', name='uq_feedback_vote_user'))
sa.Index('ix_feedback_votes_user', feedback_votes.c.user_id)
ROADMAP_KEYS = {'career-ranking', 'skill-gaps', 'learning-roadmaps', 'career-comparison', 'course-discovery',
                'private-accounts', 'community-feedback', 'market-refresh', 'more-careers', 'recommendation-quality'}

ai_trial_usage = sa.Table('ai_trial_usage', metadata,
    sa.Column('identity', sa.String(64), primary_key=True),
    sa.Column('user_id', uuid_type, sa.ForeignKey(users.c.id, ondelete='CASCADE'), unique=True),
    sa.Column('used', sa.Integer, nullable=False, server_default='0'),
    sa.Column('reservation', sa.String(36)),
    sa.Column('lease_until', sa.DateTime(timezone=True)),
    sa.CheckConstraint('used >= 0', name='ck_ai_trial_used'))
ai_trial_budget = sa.Table('ai_trial_budget', metadata,
    sa.Column('id', sa.String(20), primary_key=True),
    sa.Column('day', sa.Date, nullable=False),
    sa.Column('attempts', sa.Integer, nullable=False))
ai_trial_ip = sa.Table('ai_trial_ip', metadata,
    sa.Column('identity', sa.String(64), primary_key=True),
    sa.Column('window', sa.DateTime(timezone=True), nullable=False),
    sa.Column('attempts', sa.Integer, nullable=False))

def now():
    return datetime.now(timezone.utc)

@lru_cache(maxsize=1)
def get_engine():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL is required. Apply Alembic migrations before startup.')
    url = sa.make_url(DATABASE_URL)
    if url.get_backend_name() not in {'postgresql', 'postgres'}:
        raise RuntimeError('CareerFlow requires PostgreSQL.')
    query = dict(url.query)
    if query.get('sslmode', 'require') not in {'require', 'verify-ca', 'verify-full'}:
        raise RuntimeError('PostgreSQL SSL is required.')
    query.setdefault('sslmode', 'require')
    return sa.create_engine(url.set(drivername='postgresql+psycopg', query=query), pool_size=5, max_overflow=5,
        pool_pre_ping=True, pool_recycle=300, hide_parameters=True, connect_args={'connect_timeout': 10})

@contextmanager
def get_connection():
    with get_engine().begin() as conn:
        yield conn

def ensure_user(identity: dict):
    with get_connection() as conn:
        stmt = insert(users).values(id=identity['id'], display_name=identity['display_name'], created_at=now(), updated_at=now())
        conn.execute(stmt.on_conflict_do_update(index_elements=[users.c.id], set_={'display_name': identity['display_name'], 'updated_at': now()}))

def is_deleting(user_id):
    with get_connection() as conn:
        return bool(conn.scalar(sa.select(users.c.deletion_pending).where(users.c.id == user_id)))

def _owned(conn, session_id, user_id, lock=False):
    try:
        session_id = str(UUID(session_id))
    except ValueError:
        return None
    query = sa.select(sessions).where(sessions.c.id == session_id, sessions.c.user_id == user_id)
    return conn.execute(query.with_for_update() if lock else query).mappings().first()

def save_recommendation_session(*, session_id, user_id, profile, result_payload, context, roadmaps_by_profession, roadmap_with_courses):
    with get_connection() as conn:
        conn.execute(sessions.insert().values(id=session_id, user_id=user_id, top_profession=result_payload['top_profession'],
            alternative_profession=result_payload.get('alternative_profession'), profile_json=profile, result_json=result_payload,
            context=context, progress_json={}, created_at=now(), updated_at=now()))
        for profession, score in result_payload.get('final_scores', {}).items():
            demand = result_payload.get('demand_scores', {}).get(profession, {})
            conn.execute(scores.insert().values(session_id=session_id, profession=profession, final_score=score,
                skill_score=result_payload.get('skill_scores', {}).get(profession),
                classification_score=result_payload.get('classification_scores', {}).get(profession), **demand))
        for profession, summary in roadmaps_by_profession.items():
            missing = {(category, skill) for category, skills in summary.get('gap', {}).items() for skill in skills}
            for category, skills in summary.get('full', {}).items():
                for skill in dict.fromkeys(skills):
                    conn.execute(gaps.insert().values(session_id=session_id, profession=profession, category=category, skill=skill, is_missing=(category, skill) in missing))
        for category_position, (category, skills) in enumerate(roadmap_with_courses.items()):
            for position, (skill, data) in enumerate(skills.items()):
                courses = data.get('courses', [])
                conn.execute(roadmap.insert().values(session_id=session_id, profession=result_payload['top_profession'], category=category,
                    skill=skill, category_position=category_position, position=position, is_done=False, courses_json=courses))
                seen = set()
                for course in courses:
                    key = (course.get('title', ''), course.get('platform') or '')
                    if key in seen:
                        continue
                    seen.add(key)
                    conn.execute(course_progress.insert().values(session_id=session_id, category=category, skill=skill,
                        course_title=key[0], platform=key[1], course_url=course.get('course_url'), is_started=False, is_completed=False))

def list_recommendation_history(user_id, limit=12):
    with get_connection() as conn:
        rows = conn.execute(sa.select(sessions).where(sessions.c.user_id == user_id).order_by(sessions.c.updated_at.desc()).limit(limit)).mappings().all()
    return [{'id': row['id'], 'createdAt': row['created_at'].isoformat(), 'updatedAt': row['updated_at'].isoformat(),
        'top_profession': row['top_profession'], 'selectedProfession': row['progress_json'].get('selectedProfession') or row['top_profession'],
        'results': row['result_json'], 'progress': {'done': row['progress_json'].get('doneSkills', []),
        'categoryOrder': row['progress_json'].get('categoryOrder', []), 'skillOrders': row['progress_json'].get('skillOrders', {})}} for row in rows]

def get_recommendation_state(session_id, user_id):
    with get_connection() as conn:
        row = _owned(conn, session_id, user_id)
        if row is None:
            return None
        filters = conn.scalar(sa.select(preferences.c.filters_json).where(preferences.c.session_id == row['id']))
        return {'results': row['result_json'], 'progress': row['progress_json'], 'filters': filters or {}}

def update_recommendation_progress(*, session_id, user_id, done_skills, category_order, skill_orders, selected_profession=None):
    progress = dict(doneSkills=done_skills, categoryOrder=category_order, skillOrders=skill_orders, selectedProfession=selected_profession)
    with get_connection() as conn:
        if _owned(conn, session_id, user_id, lock=True) is None:
            return {'saved': False}
        conn.execute(sessions.update().where(sessions.c.id == session_id, sessions.c.user_id == user_id).values(progress_json=progress, updated_at=now()))
        conn.execute(roadmap.update().where(roadmap.c.session_id == session_id).values(is_done=False))
        for key in done_skills:
            if '::' in key:
                category, skill = key.split('::', 1)
                conn.execute(roadmap.update().where(roadmap.c.session_id == session_id, roadmap.c.category == category, roadmap.c.skill == skill).values(is_done=True))
        for position, category in enumerate(category_order):
            conn.execute(roadmap.update().where(roadmap.c.session_id == session_id, roadmap.c.category == category).values(category_position=position))
        for category, skills in skill_orders.items():
            for position, skill in enumerate(skills):
                conn.execute(roadmap.update().where(roadmap.c.session_id == session_id, roadmap.c.category == category, roadmap.c.skill == skill).values(position=position))
    return {'saved': True, 'progress': progress}

def save_course_filter_preferences(*, session_id, user_id, filters):
    with get_connection() as conn:
        if _owned(conn, session_id, user_id, lock=True) is None:
            return {'saved': False}
        conn.execute(preferences.delete().where(preferences.c.session_id == session_id))
        conn.execute(preferences.insert().values(session_id=session_id, filters_json=filters))
    return {'saved': True, 'filters': filters}

def delete_recommendation_history(user_id):
    with get_connection() as conn:
        conn.execute(sessions.delete().where(sessions.c.user_id == user_id))
    return {'deleted': True}

def save_feedback(payload, user_id=None):
    from config import DEVELOPER_USER_IDS
    kind = payload['type']
    with get_connection() as conn:
        conn.execute(feedback.insert().values(id=str(uuid4()), user_id=user_id, created_at=now(), updated_at=now(),
            category={'review': 'general', 'feature': 'suggestion', 'bug': 'bug'}[kind],
            origin='developer' if user_id in DEVELOPER_USER_IDS else 'unverified',
            development_status='suggested' if kind == 'feature' else None, **payload))


def _public_feedback():
    return sa.and_(feedback.c.public_consent.is_(True), feedback.c.moderation_status == 'approved',
        feedback.c.type.in_(['review', 'feature']), feedback.c.origin.in_(['community', 'developer']))


def list_public_feedback(kind, user_id=None, offset=0, limit=20, roadmap_only=False):
    vote_count = sa.select(sa.func.count()).where(feedback_votes.c.feedback_id == feedback.c.id).scalar_subquery()
    voted = sa.exists().where(feedback_votes.c.feedback_id == feedback.c.id, feedback_votes.c.user_id == user_id) if user_id else sa.false()
    # Public identity is deliberately Anonymous; publication consent covers the text, not account metadata.
    query = sa.select(feedback.c.id, feedback.c.type, feedback.c.title, feedback.c.message, feedback.c.rating,
        feedback.c.created_at, feedback.c.development_status, feedback.c.roadmap_key,
        (feedback.c.origin == 'developer').label('developer_feedback'), vote_count.label('votes'), voted.label('voted'))
    query = query.where(_public_feedback(), feedback.c.type == kind)
    if roadmap_only:
        query = query.where(feedback.c.roadmap_key.is_not(None))
    with get_connection() as conn:
        rows = conn.execute(query.order_by(feedback.c.created_at.desc(), feedback.c.id).offset(offset).limit(limit + 1)).mappings().all()
    return {'items': [dict(row, display_name='Anonymous') for row in rows[:limit]], 'has_more': len(rows) > limit}


def set_feedback_vote(feedback_id, user_id, voted):
    with get_connection() as conn:
        row = conn.execute(sa.select(feedback.c.id).where(feedback.c.id == feedback_id, _public_feedback(),
            feedback.c.type == 'feature').with_for_update()).first()
        if row is None:
            return None
        if voted:
            conn.execute(insert(feedback_votes).values(id=str(uuid4()), feedback_id=feedback_id, user_id=user_id, created_at=now())
                .on_conflict_do_nothing(index_elements=['feedback_id', 'user_id']))
        else:
            conn.execute(feedback_votes.delete().where(feedback_votes.c.feedback_id == feedback_id, feedback_votes.c.user_id == user_id))
        count = conn.scalar(sa.select(sa.func.count()).select_from(feedback_votes).where(feedback_votes.c.feedback_id == feedback_id))
    return {'votes': count, 'voted': voted}


def moderate_feedback(feedback_id, action, *, origin=None, status=None, roadmap_key=None, note=''):
    from config import DEVELOPER_USER_IDS
    with get_connection() as conn:
        row = conn.execute(sa.select(feedback).where(feedback.c.id == feedback_id).with_for_update()).mappings().first()
        if row is None:
            raise ValueError('Feedback not found.')
        values = {'updated_at': now()}
        if action == 'approve':
            if not row['type'] or not row['public_consent'] or row['type'] == 'bug':
                raise ValueError('Only typed reviews/features with publication consent may be approved.')
            if origin not in {'community', 'developer', 'test'} or not note.strip():
                raise ValueError('Explicit origin and a moderation note are required.')
            if (row['user_id'] in DEVELOPER_USER_IDS or row['origin'] in {'developer', 'test'}) and origin == 'community':
                raise ValueError('Developer/test feedback cannot be relabeled as community feedback.')
            values.update(moderation_status='approved', origin=origin, moderation_note=note[:2000])
        elif action in {'reject', 'remove'}:
            values['moderation_status'] = 'rejected'
        elif action == 'status':
            if row['type'] != 'feature' or status not in {'suggested', 'planned', 'in_progress', 'released'} or not note.strip():
                raise ValueError('Feature status requires a valid status and verification note.')
            values.update(development_status=status, moderation_note=note[:2000])
        elif action == 'link':
            if row['type'] != 'feature' or roadmap_key not in ROADMAP_KEYS:
                raise ValueError('Use a known roadmap key for a feature suggestion.')
            values['roadmap_key'] = roadmap_key
        else:
            raise ValueError('Unknown moderation action.')
        conn.execute(feedback.update().where(feedback.c.id == feedback_id).values(**values))

def begin_account_deletion(user_id):
    with get_connection() as conn:
        conn.execute(users.update().where(users.c.id == user_id).values(deletion_pending=True, updated_at=now()))

def delete_application_user(user_id):
    with get_connection() as conn:
        conn.execute(users.delete().where(users.c.id == user_id))
