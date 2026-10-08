from io import StringIO
from alembic import command
from alembic.config import Config
from pathlib import Path

def test_initial_migration_is_additive_private_and_auth_linked():
    output = StringIO()
    config = Config(str(Path(__file__).parents[1] / 'alembic.ini'), output_buffer=output)
    command.upgrade(config, '0001_public_beta', sql=True)
    sql = output.getvalue()
    assert sql.index('CREATE SCHEMA IF NOT EXISTS careerflow') < sql.index('CREATE TABLE careerflow.alembic_version')
    assert 'REFERENCES auth.users (id) ON DELETE CASCADE' in sql
    assert sql.count('ENABLE ROW LEVEL SECURITY') == 8
    assert 'REVOKE ALL ON SCHEMA careerflow FROM PUBLIC, anon, authenticated' in sql
    assert 'DROP TABLE' not in sql

def test_public_feedback_migration_preserves_private_rows_and_secures_votes():
    output = StringIO()
    config = Config(str(Path(__file__).parents[1] / 'alembic.ini'), output_buffer=output)
    command.upgrade(config, 'head', sql=True)
    sql = output.getvalue()
    assert 'CREATE TABLE careerflow.feedback_votes' in sql
    assert 'CONSTRAINT uq_feedback_vote_user UNIQUE (feedback_id, user_id)' in sql
    assert 'ADD COLUMN public_consent BOOLEAN DEFAULT false NOT NULL' in sql
    assert sql.count('ENABLE ROW LEVEL SECURITY') == 12
    for name in ('ai_trial_usage', 'ai_trial_budget', 'ai_trial_ip'):
        assert f'CREATE TABLE careerflow.{name}' in sql
        assert f'REVOKE ALL ON TABLE careerflow.{name} FROM PUBLIC, anon, authenticated' in sql
    assert 'DROP TABLE' not in sql
    assert 'UPDATE careerflow.feedback SET updated_at = created_at' in sql
