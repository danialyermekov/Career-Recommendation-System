from uuid import uuid4
from unittest.mock import Mock
import httpx
import pytest
import sqlalchemy as sa
from fastapi import HTTPException
import auth
import database
import guest_sessions
import main
import security
from conftest import TEST_PROFILE

A, B = str(uuid4()), str(uuid4())

@pytest.fixture
def identities(monkeypatch):
    def verify(token):
        if token not in {A, B}:
            raise HTTPException(401, 'Invalid or expired access token.')
        return {'id': token, 'display_name': 'Test user'}
    monkeypatch.setattr(auth, 'verify_access_token', verify)
    return {'Authorization': f'Bearer {A}'}, {'Authorization': f'Bearer {B}'}

def test_full_user_isolation_and_ownership(client, identities):
    a, b = identities
    result = client.post('/recommend', json=TEST_PROFILE, headers=a)
    assert result.status_code == 200
    session = result.json()['session_id']
    assert result.json()['persistent'] is True
    assert client.get(f'/recommendation/{session}/state', headers=a).status_code == 200
    assert len(client.get('/recommendation/history', headers=a).json()['items']) == 1
    assert client.get('/recommendation/history', headers=b).json()['items'] == []
    assert client.get(f'/recommendation/{session}/state?user_id={A}', headers=b).status_code == 404
    progress = {'doneSkills': ['libraries::pytorch'], 'categoryOrder': ['libraries'], 'skillOrders': {'libraries': ['pytorch']}}
    assert client.put(f'/recommendation/{session}/progress?user_id={A}', json=progress, headers=b).status_code == 404
    assert client.put(f'/recommendation/{session}/course-filters', json={'filters': {}, 'user_id': A}, headers=b).status_code in {404, 422}
    assert client.put(f'/recommendation/{session}/progress', json=progress, headers=a).status_code == 200
    assert client.get(f'/recommendation/{session}/state', headers=a).json()['progress']['doneSkills'] == ['libraries::pytorch']
    assert client.put(f'/recommendation/{session}/course-filters', json={'filters': {'price': 'free'}}, headers=a).status_code == 200
    assert client.get(f'/recommendation/{session}/state', headers=a).json()['filters']['price'] == 'free'
    for path in ['/chat', '/chat/stream']:
        response = client.post(path, headers={**b, 'X-LLM-Provider': 'gemini', 'X-LLM-API-Key': 'test-key'},
            json={'session_id': session, 'history': [], 'message': 'Career advice'})
        assert response.status_code == 404
    assert client.delete(f'/recommendation/history?user_id={A}', headers=b).status_code == 200
    assert len(client.get('/recommendation/history', headers=a).json()['items']) == 1
    assert client.delete('/recommendation/history', headers=a).status_code == 200
    assert client.get(f'/recommendation/{session}/state', headers=a).status_code == 404
    with database.get_connection() as conn:
        assert conn.scalar(sa.select(sa.func.count()).select_from(database.roadmap)) == 0

def test_guest_credentials_and_expiry(client, monkeypatch):
    result = client.post('/recommend', json=TEST_PROFILE).json()
    assert result['persistent'] is False
    session = result['session_id']
    assert client.get(f'/recommendation/{session}/state').status_code == 200
    assert client.get(f'/recommendation/{session}/state', headers={'X-Guest-Token': 'b'*64}).status_code == 404
    assert client.get(f'/recommendation/{session}/state', headers={'X-Guest-Token': ''}).status_code == 401
    assert client.get('/recommendation/history').status_code == 401
    assert client.delete('/recommendation/history').status_code == 401
    with database.get_connection() as conn:
        assert conn.scalar(sa.select(sa.func.count()).select_from(database.sessions)) == 0
    guest_sessions.sessions[session]['expires'] = 0
    assert client.get(f'/recommendation/{session}/state').status_code == 404

@pytest.mark.parametrize('header', ['Basic abc', 'Bearer ', 'Bearer malformed', 'Bearer expired'])
def test_bad_tokens_never_fall_back_to_guest(client, identities, header):
    response = client.get('/recommendation/history', headers={'Authorization': header})
    assert response.status_code == 401

@pytest.mark.parametrize('token', ['malformed-token', 'expired-token', 'wrong-signature'])
def test_supabase_verification_rejects_invalid_tokens(monkeypatch, token):
    transport = Mock()
    transport.get.return_value = httpx.Response(401)
    monkeypatch.setattr(auth.httpx, 'Client', Mock(return_value=Mock(__enter__=Mock(return_value=transport), __exit__=Mock(return_value=False))))
    monkeypatch.setattr(auth, 'SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setattr(auth, 'SUPABASE_PUBLISHABLE_KEY', 'public-key')
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(token)
    assert error.value.status_code == 401
    assert transport.get.call_args.kwargs['headers']['Authorization'] == f'Bearer {token}'

def test_verified_identity_comes_only_from_auth_response(monkeypatch):
    transport = Mock()
    transport.get.return_value = httpx.Response(200, json={'id': A, 'user_metadata': {'name': 'Verified'}})
    monkeypatch.setattr(auth.httpx, 'Client', Mock(return_value=Mock(__enter__=Mock(return_value=transport), __exit__=Mock(return_value=False))))
    monkeypatch.setattr(auth, 'SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setattr(auth, 'SUPABASE_PUBLISHABLE_KEY', 'public-key')
    assert auth.verify_access_token('opaque-token') == {'id': A, 'display_name': 'Verified'}

def test_feedback_anonymous_authenticated_and_validation(client, identities):
    a, b = identities
    session = client.post('/recommend', json=TEST_PROFILE, headers=a).json()['session_id']
    assert client.post('/feedback', json={'type': 'review', 'rating': 5}).status_code == 201
    assert client.post('/feedback', json={'type': 'review', 'rating': 4, 'message': 'Useful roadmap', 'session_id': session}, headers=a).status_code == 201
    assert client.post('/feedback', json={'type': 'review', 'rating': 4, 'message': 'Attempt', 'session_id': session}, headers=b).status_code == 404
    assert client.post('/feedback', json={'type': 'review', 'rating': 6}).status_code == 422
    security.buckets.clear()
    for payload in [{'rating': True}, {'type': 'unknown'}, {'rating': None, 'message': ' '}, {'message': 'x'*2001}, {'message': 'spam', 'website': 'bot'}]:
        assert client.post('/feedback', json={'type': 'review', 'rating': 3, **payload}).status_code in {400, 422}
    assert client.get('/api/feedback').json()['items'] == []
    with database.get_connection() as conn:
        rows = conn.execute(sa.select(database.feedback)).mappings().all()
        assert len(rows) == 2
        assert rows[0]['user_id'] is None
        assert rows[1]['user_id'] == A

def test_feedback_rate_and_body_limits(client):
    for _ in range(5):
        assert client.post('/feedback', json={'type': 'review', 'rating': 3}).status_code == 201
    assert client.post('/feedback', json={'type': 'review', 'rating': 3}).status_code == 429
    assert client.post('/recommend', content=b'x'*(1024*1024+1)).status_code == 413

def test_atomic_recommendation_write_rolls_back(client, identities, monkeypatch):
    a, _ = identities
    original = main.save_recommendation_session
    def fail(**kwargs):
        kwargs['result_payload']['demand_scores']['Machine Learning Engineer']['unexpected_column'] = 1
        original(**kwargs)
    monkeypatch.setattr(main, 'save_recommendation_session', fail)
    assert client.post('/recommend', json=TEST_PROFILE, headers=a).status_code == 503
    assert client.get('/recommendation/history', headers=a).json()['items'] == []

def test_deletion_requires_config_and_handles_failure(client, identities, monkeypatch):
    a, _ = identities
    session = client.post('/recommend', json=TEST_PROFILE, headers=a).json()['session_id']
    monkeypatch.setattr(auth, 'SUPABASE_SECRET_KEY', '')
    assert client.delete('/account', headers=a).status_code == 503
    assert client.get(f'/recommendation/{session}/state', headers=a).status_code == 200
    monkeypatch.setattr(auth, 'SUPABASE_SECRET_KEY', 'server-only')
    def fail(user_id):
        raise HTTPException(503, 'Retry deletion')
    monkeypatch.setattr(main, 'delete_auth_user', fail)
    assert client.delete('/account', headers=a).status_code == 503
    assert client.get(f'/recommendation/{session}/state', headers=a).status_code == 403
    assert client.get('/account', headers=a).json()['deletion_pending'] is True
    delete = Mock()
    monkeypatch.setattr(main, 'delete_auth_user', delete)
    assert client.delete('/account', headers=a).status_code == 200
    delete.assert_called_once_with(A)
    with database.get_connection() as conn:
        assert conn.scalar(sa.select(sa.func.count()).select_from(database.sessions)) == 0
        assert conn.scalar(sa.select(sa.func.count()).select_from(database.users)) == 0
