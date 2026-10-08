"""Opt-in test against the configured Supabase, in a rolled-back private test schema."""
from contextlib import contextmanager
from uuid import uuid4
import os
import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
import database
import main
from test_public_beta import test_full_user_isolation_and_ownership as isolation_scenario, A, B
from test_public_feedback import test_publication_requires_consent_moderation_and_verified_origin as publication_scenario
from test_public_feedback import test_voting_is_authenticated_idempotent_scoped_and_cascades as voting_scenario

@pytest.mark.skipif(os.getenv('CAREERFLOW_TEST_POSTGRES') != '1', reason='Set CAREERFLOW_TEST_POSTGRES=1 for a transactional Supabase test')
def test_postgres_user_isolation_and_atomicity(monkeypatch, mocked_services):
    import auth
    engine = database.get_engine()
    with engine.connect() as raw:
        transaction = raw.begin()
        schema = 'careerflow_test_' + uuid4().hex
        try:
            raw.execute(sa.schema.CreateSchema(schema))
            conn = raw.execution_options(schema_translate_map={'careerflow': schema})
            database.metadata.create_all(conn)
            class TransactionalEngine:
                @contextmanager
                def begin(self):
                    with conn.begin_nested():
                        yield conn
            monkeypatch.setattr(database, 'get_engine', lambda: TransactionalEngine())
            monkeypatch.setattr(auth, 'verify_access_token', lambda token: {'id': token, 'display_name': 'Test user'})
            with TestClient(main.app, headers={'X-Guest-Token': 'a'*64}) as client:
                isolation_scenario(client, ({'Authorization': f'Bearer {A}'}, {'Authorization': f'Bearer {B}'}))
                publication_scenario(client)
                voting_scenario(client, ({'Authorization': f'Bearer {A}'}, {'Authorization': f'Bearer {B}'}))
        finally:
            transaction.rollback()
    with engine.connect() as check:
        assert check.scalar(sa.text('SELECT count(*) FROM pg_namespace WHERE nspname=:name'), {'name': schema}) == 0
