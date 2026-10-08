from uuid import uuid4
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
import config
import database
import feedback_manage
import security
from test_public_beta import identities, A, B
from conftest import TEST_PROFILE


def submit(client, *, type='review', consent=True, headers=None, **kwargs):
    security.buckets.clear()
    payload = {'type': type, 'public_consent': consent}
    payload.update({'rating': 4, 'message': '<script>window.bad=true</script>'} if type == 'review' else
                   {'title': 'Better courses', 'message': 'Please add more current learning courses.'})
    payload.update(kwargs)
    response = client.post('/feedback', json=payload, headers=headers)
    assert response.status_code == 201, response.text
    with database.get_connection() as conn:
        return conn.scalar(sa.select(database.feedback.c.id).order_by(database.feedback.c.created_at.desc()).limit(1))


def approve(id, origin='community'):
    database.moderate_feedback(id, 'approve', origin=origin, note='Checked consent, privacy and origin for this test.')


def test_publication_requires_consent_moderation_and_verified_origin(client):
    id = submit(client)
    assert client.get('/api/feedback').json()['items'] == []
    with pytest.raises(ValueError):
        database.moderate_feedback(id, 'approve', origin='community')
    approve(id)
    row = client.get('/api/feedback').json()['items'][0]
    assert row['display_name'] == 'Anonymous'
    assert row['message'] == '<script>window.bad=true</script>'
    assert not {'user_id', 'session_id', 'email', 'origin', 'moderation_note', 'reproduction_steps'} & row.keys()
    assert row['developer_feedback'] is False
    database.moderate_feedback(id, 'remove')
    assert client.get('/api/feedback').json()['items'] == []
    private = submit(client, consent=False)
    with pytest.raises(ValueError):
        approve(private)
    with database.get_connection() as conn:
        conn.execute(database.feedback.update().where(database.feedback.c.id == private).values(moderation_status='approved', origin='community'))
    assert client.get('/api/feedback').json()['items'] == []


def test_bug_reports_and_test_feedback_never_publish(client):
    bug = submit(client, type='bug', reproduction_steps='Open the page.')
    with pytest.raises(ValueError):
        approve(bug)
    test = submit(client)
    approve(test, origin='test')
    assert client.get('/api/feedback').json()['items'] == []
    database.moderate_feedback(bug, 'reject')


def test_guest_feedback_cannot_attach_to_another_guest_session(client):
    session = client.post('/recommend', json=TEST_PROFILE).json()['session_id']
    payload = {'type': 'review', 'rating': 4, 'session_id': session}
    assert client.post('/feedback', json=payload, headers={'X-Guest-Token': 'b'*64}).status_code == 404
    assert client.post('/feedback', json=payload).status_code == 201
    with database.get_connection() as conn:
        assert conn.scalar(sa.select(database.feedback.c.session_id)) is None


def test_readiness_rejects_missing_feedback_vote_migration(client):
    with database.get_connection() as conn:
        conn.execute(sa.schema.DropTable(database.feedback_votes))
    assert client.get('/ready').status_code == 503


def test_developer_feedback_is_identified_and_not_reclassified(client, identities, monkeypatch):
    monkeypatch.setattr(config, 'DEVELOPER_USER_IDS', {A})
    id = submit(client, headers=identities[0])
    with pytest.raises(ValueError):
        approve(id)
    approve(id, origin='developer')
    row = client.get('/api/feedback').json()['items'][0]
    assert row['developer_feedback'] is True
    assert 'average_rating' not in client.get('/api/feedback').json()


def test_voting_is_authenticated_idempotent_scoped_and_cascades(client, identities):
    a, b = identities
    id = submit(client, type='feature')
    url = f'/api/feedback/{id}/vote'
    assert client.put(url, json={'voted': True}).status_code == 401
    assert client.put(url, json={'voted': True}, headers=a).status_code == 404
    approve(id)
    assert client.put(url, json={'voted': True}, headers=a).json() == {'votes': 1, 'voted': True}
    assert client.put(url, json={'voted': True}, headers=a).json()['votes'] == 1
    assert client.put(url, json={'voted': True}, headers=b).json()['votes'] == 2
    assert client.put(url, json={'voted': False}, headers=a).json()['votes'] == 1
    row = client.get('/api/feedback?type=feature', headers=b).json()['items'][0]
    assert row['voted'] is True
    assert client.get('/api/feedback?type=feature', headers=a).json()['items'][0]['voted'] is False
    assert client.put(url, json={'voted': False, 'user_id': B}, headers=a).status_code == 422
    with pytest.raises(IntegrityError), database.get_connection() as conn:
        conn.execute(database.feedback_votes.insert().values(id=str(uuid4()), feedback_id=id, user_id=B, created_at=database.now()))
    database.delete_application_user(B)
    assert client.get('/api/feedback?type=feature').json()['items'][0]['votes'] == 0
    database.moderate_feedback(id, 'remove')
    assert client.put(url, json={'voted': True}, headers=a).status_code == 404


def test_maintainer_cli_status_link_export_and_no_web_admin(client, tmp_path, capsys):
    id = submit(client, type='feature')
    feedback_manage.main(['pending'])
    assert id in capsys.readouterr().out
    feedback_manage.main(['approve', id, '--origin', 'community', '--note', 'Reviewed an independent suggestion.'])
    feedback_manage.main(['status', id, 'planned', '--note', 'Maintainer verified scope; no promised delivery date.'])
    feedback_manage.main(['link', id, 'market-refresh'])
    item = client.get('/api/roadmap').json()['items'][0]
    assert item['roadmap_key'] == 'market-refresh' and item['development_status'] == 'planned'
    feedback_manage.main(['export', str(tmp_path / 'feedback-private.csv')])
    assert (tmp_path / 'feedback-private.csv').exists()
    feedback_manage.main(['reject', id])
    assert client.get('/api/roadmap').json()['items'] == []
    assert client.post(f'/api/feedback/{id}/approve').status_code in {404, 405}
    assert client.put(f'/api/feedback/{id}', json={'moderation_status': 'approved'}).status_code in {404, 405}


@pytest.mark.parametrize('payload', [
    {'type': 'review'}, {'type': 'review', 'rating': True}, {'type': 'review', 'rating': 0},
    {'type': 'review', 'rating': 5, 'message': 'x'*2001}, {'type': 'review', 'rating': 5, 'user_id': A},
    {'type': 'review', 'rating': 5, 'moderation_status': 'approved'}, {'type': 'review', 'rating': 5, 'origin': 'community'},
    {'type': 'feature', 'title': 'tiny', 'message': 'Enough description'},
    {'type': 'feature', 'title': 'Valid title', 'message': 'short'}, {'type': 'feature', 'title': 'x'*121, 'message': 'Enough description'},
    {'type': 'bug', 'title': ' ', 'message': 'Details'}, {'type': 'bug', 'title': 'Issue', 'message': ' '},
    {'type': 'review', 'rating': 5, 'public_consent': 'true'},
])
def test_feedback_boundaries(client, payload):
    assert client.post('/feedback', json=payload).status_code == 422
