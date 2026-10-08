from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
import os

import pytest
import sqlalchemy as sa
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import auth
import database as db
import main
from conftest import TEST_PROFILE
from services import ai_trial
from services.llm import GeminiProvider


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv('GEMINI_DEMO_ENABLED', 'true')
    monkeypatch.setenv('GEMINI_DEMO_API_KEY', 'server-only-test-secret')
    monkeypatch.delenv('API_KEY', raising=False)
    monkeypatch.setenv('GEMINI_DEMO_MODEL', 'gemini-3.5-flash-lite')
    monkeypatch.setenv('GEMINI_DEMO_FREE_MESSAGES', '3')
    monkeypatch.setenv('GEMINI_DEMO_GLOBAL_DAILY_LIMIT', '100')


@pytest.fixture
def provider(monkeypatch):
    provider = Mock(return_value='Learn SQL first.')
    monkeypatch.setattr(GeminiProvider, 'chat_preview', provider)
    return provider


def payload(session):
    return {'session_id': session, 'message': 'Which skill should I learn first?', 'history': [], 'consent': True}


def test_guest_quota_survives_refresh_and_client_key_is_ignored(client, recommendation_response, provider):
    session = recommendation_response['session_id']
    status = client.get('/ai/preview')
    assert status.json()['remaining'] == 3
    assert 'HttpOnly' in status.headers['set-cookie'] and 'SameSite=lax' in status.headers['set-cookie']
    response = client.post('/ai/preview', json=payload(session), headers={'X-LLM-API-Key': 'client-key', 'X-LLM-Provider': 'anthropic'})
    assert response.status_code == 200 and response.json()['provider'] == 'gemini'
    assert provider.call_args.args[0] == 'server-only-test-secret'
    assert 'server-only-test-secret' not in response.text + status.text
    with TestClient(main.app, cookies=client.cookies, headers={'X-Guest-Token': 'a'*64}) as refreshed:
        assert refreshed.get('/ai/preview').json()['remaining'] == 2
        assert refreshed.post('/ai/preview', json=payload(session)).json()['remaining'] == 1
        assert refreshed.post('/ai/preview', json=payload(session)).json()['remaining'] == 0
        assert refreshed.post('/ai/preview', json=payload(session)).status_code == 429
    assert provider.call_count == 3


def test_verified_account_quota_and_context_isolation(client, monkeypatch, provider):
    a, b = str(uuid4()), str(uuid4())
    monkeypatch.setattr(auth, 'verify_access_token', lambda token: {'id': token, 'display_name': 'Private user'})
    ha, hb = {'Authorization': f'Bearer {a}'}, {'Authorization': f'Bearer {b}'}
    session = client.post('/recommend', json=TEST_PROFILE, headers=ha).json()['session_id']
    assert client.post('/ai/preview', json=payload(session), headers=hb).status_code == 404
    assert not provider.called
    assert client.post('/ai/preview', json={**payload(session), 'user_id': a}, headers=hb).status_code == 422
    assert client.post('/ai/preview', json=payload(session), headers=ha).json()['remaining'] == 2
    client.cookies.clear()
    assert client.get('/ai/preview', headers=ha).json()['remaining'] == 2
    assert client.get('/ai/preview', headers=hb).json()['remaining'] == 3
    context = provider.call_args.args[-1]
    assert 'Private user' not in context and 'gpa' not in context and 'field_of_study' not in context
    assert 'existing_skills' in context and 'roadmap_with_courses' in context


def test_signed_in_demo_is_guest_owned_and_does_not_save_into_account(client, monkeypatch, provider):
    user = str(uuid4())
    monkeypatch.setattr(auth, 'verify_access_token', lambda token: {'id': user, 'display_name': 'Owner'})
    session = client.post('/recommend', json=TEST_PROFILE).json()['session_id']
    headers = {'Authorization': 'Bearer verified', 'X-Demo-Session': 'true'}
    assert client.post('/ai/preview', json=payload(session), headers=headers).json()['remaining'] == 2
    assert client.get('/recommendation/history', headers=headers).json()['items'] == []
    assert client.post('/ai/preview', json=payload(session), headers={**headers, 'X-Guest-Token': 'b'*64}).status_code == 404


@pytest.mark.parametrize('change', [{'message': 'x'*1001}, {'history': [{'role': 'user', 'content': 'x'}]*5}, {'consent': False}, {'deep': True}, {'message': ''}, {'message': '   '}])
def test_cost_boundary_rejects_invalid_requests(client, recommendation_response, provider, change):
    assert client.post('/ai/preview', json={**payload(recommendation_response['session_id']), **change}).status_code == 422
    assert not provider.called


def test_provider_failure_refunds_user_but_counts_global_attempt(client, recommendation_response, provider, monkeypatch):
    provider.side_effect = RuntimeError('server-only-test-secret')
    monkeypatch.setenv('GEMINI_DEMO_GLOBAL_DAILY_LIMIT', '1')
    response = client.post('/ai/preview', json=payload(recommendation_response['session_id']))
    assert response.status_code == 503 and 'server-only-test-secret' not in response.text
    status = client.get('/ai/preview').json()
    assert status['remaining'] == 3 and status['available'] is False
    assert client.post('/ai/preview', json=payload(recommendation_response['session_id'])).status_code == 503
    assert provider.call_count == 1


@pytest.mark.parametrize('name,value', [('GEMINI_DEMO_API_KEY', ''), ('GEMINI_DEMO_ENABLED', 'false'), ('GEMINI_DEMO_MODEL', 'gemini-2.5-pro')])
def test_disabled_preview_preserves_byok(client, recommendation_response, provider, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    assert client.get('/ai/preview').json()['available'] is False
    assert client.post('/ai/preview', json=payload(recommendation_response['session_id'])).status_code == 503
    assert not provider.called
    assert client.post('/chat', json={'session_id': recommendation_response['session_id'], 'message': 'Career advice', 'history': []},
                       headers={'X-LLM-API-Key': 'byok-test', 'X-LLM-Provider': 'anthropic'}).status_code == 200


def test_fallback_to_api_key_when_gemini_demo_key_unset(client, recommendation_response, provider, monkeypatch):
    monkeypatch.delenv('GEMINI_DEMO_API_KEY', raising=False)
    monkeypatch.setenv('API_KEY', 'server-only-fallback-key')
    status = client.get('/ai/preview')
    assert status.json()['available'] is True
    res = client.post('/ai/preview', json=payload(recommendation_response['session_id']))
    assert res.status_code == 200
    assert provider.call_args.args[0] == 'server-only-fallback-key'


def test_explicit_gemini_demo_key_takes_precedence_over_api_key(client, recommendation_response, provider, monkeypatch):
    monkeypatch.setenv('GEMINI_DEMO_API_KEY', 'explicit-demo-key')
    monkeypatch.setenv('API_KEY', 'fallback-key')
    res = client.post('/ai/preview', json=payload(recommendation_response['session_id']))
    assert res.status_code == 200
    assert provider.call_args.args[0] == 'explicit-demo-key'


def test_both_keys_unset_disables_preview(client, recommendation_response, provider, monkeypatch):
    monkeypatch.delenv('GEMINI_DEMO_API_KEY', raising=False)
    monkeypatch.delenv('API_KEY', raising=False)
    assert client.get('/ai/preview').json()['available'] is False
    assert client.post('/ai/preview', json=payload(recommendation_response['session_id'])).status_code == 503
    assert not provider.called


def test_ip_rate_limit_and_global_concurrency(client, recommendation_response, provider):
    for _ in range(10):
        assert client.get('/ai/preview').status_code == 200
    assert client.get('/ai/preview').status_code == 429
    with db.get_connection() as conn:
        conn.execute(db.ai_trial_ip.delete())
        for index in range(2):
            conn.execute(db.ai_trial_usage.insert().values(identity=str(index), used=1, lease_until=db.now() + ai_trial.timedelta(seconds=60)))
    assert client.post('/ai/preview', json=payload(recommendation_response['session_id'])).status_code == 429
    assert not provider.called


def test_storage_unavailable_never_calls_provider(client, recommendation_response, provider, monkeypatch):
    @contextmanager
    def unavailable():
        raise OperationalError('unavailable', None, Exception('internal'))
        yield
    monkeypatch.setattr(db, 'get_connection', unavailable)
    response = client.post('/ai/preview', json=payload(recommendation_response['session_id']))
    assert response.status_code == 503 and not provider.called


def test_provider_options_cap_cost_without_tools_or_retries(monkeypatch):
    from google import genai
    generate = Mock(return_value=SimpleNamespace(text='Advice'))
    client = Mock()
    client.__enter__ = Mock(return_value=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    client.__exit__ = Mock(return_value=False)
    factory = Mock(return_value=client)
    monkeypatch.setattr(genai, 'Client', factory)
    assert GeminiProvider().chat_preview('server-secret', 'gemini-3.5-flash-lite', 'system', [], 'question') == 'Advice'
    options = factory.call_args.kwargs['http_options']
    assert options.timeout == 20000 and options.retry_options.attempts == 1
    config = generate.call_args.kwargs['config']
    assert config.max_output_tokens == 600 and config.tools == []
    assert config.thinking_config.thinking_level.value == 'MINIMAL'


@pytest.mark.skipif(os.getenv('CAREERFLOW_TEST_POSTGRES') != '1', reason='Explicit opt-in for isolated PostgreSQL concurrency test')
def test_postgres_concurrent_lifetime_quota(monkeypatch):
    engine = db.get_engine()
    schema = 'careerflow_trial_test_' + uuid4().hex
    test_engine = engine.execution_options(schema_translate_map={'careerflow': schema})
    with engine.begin() as conn:
        conn.execute(sa.schema.CreateSchema(schema))
    try:
        db.metadata.create_all(test_engine)
        monkeypatch.setattr(db, 'get_engine', lambda: test_engine)
        user = {'id': str(uuid4()), 'display_name': 'Quota test'}
        db.ensure_user(user)
        request = SimpleNamespace(client=SimpleNamespace(host='test'), cookies={}, url=SimpleNamespace(hostname='testserver'))
        def attempt(_):
            try:
                key, reservation, remaining, model = ai_trial.reserve(request, Response(), user)
                ai_trial.finish(key, reservation)
                return True
            except HTTPException as error:
                assert error.status_code == 429
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(8)))
        # Busy rejections are allowed; sequential retries must still stop at exactly three.
        for _ in range(3):
            attempt(None)
        with test_engine.connect() as conn:
            assert conn.scalar(sa.select(db.ai_trial_usage.c.used)) == 3
            assert conn.scalar(sa.select(db.ai_trial_budget.c.attempts)) == 3
        assert sum(results) <= 3
        with test_engine.begin() as conn:
            conn.execute(db.ai_trial_usage.delete())
            conn.execute(db.ai_trial_budget.delete())
            conn.execute(db.ai_trial_ip.delete())
        monkeypatch.setenv('GEMINI_DEMO_GLOBAL_DAILY_LIMIT', '2')
        def guest_attempt(index):
            request = SimpleNamespace(client=SimpleNamespace(host=str(index)), cookies={}, url=SimpleNamespace(hostname='testserver'))
            try:
                ai_trial.reserve(request, Response(), None)
                return True
            except HTTPException as error:
                assert error.status_code in {429, 503}
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            assert sum(pool.map(guest_attempt, range(8))) == 2
        with test_engine.connect() as conn:
            assert conn.scalar(sa.select(db.ai_trial_budget.c.attempts)) == 2
            assert conn.scalar(sa.select(sa.func.sum(db.ai_trial_usage.c.used))) == 2
    finally:
        assert schema.startswith('careerflow_trial_test_') and len(schema) == len('careerflow_trial_test_') + 32
        with engine.begin() as conn:
            conn.execute(sa.schema.DropSchema(schema, cascade=True))
