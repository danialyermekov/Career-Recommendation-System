import pytest
from fastapi.testclient import TestClient
import main


@pytest.fixture
def built_client(tmp_path, monkeypatch):
    for page in main.PUBLIC_PAGES:
        directory = tmp_path / page
        directory.mkdir(exist_ok=True)
        (directory / 'index.html').write_text(f'<html><h1>Public {page or "home"}</h1></html>', encoding='utf8')
    (tmp_path / 'app-shell.html').write_text('<meta name="robots" content="noindex, follow"><div id="root"></div>', encoding='utf8')
    (tmp_path / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: https://careerflow.live/sitemap.xml\n')
    (tmp_path / 'sitemap.xml').write_text('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
    (tmp_path / 'static/js').mkdir(parents=True)
    (tmp_path / 'static/js/main.123abc.js').write_text('console.log("public bundle")')
    monkeypatch.setattr(main, 'FRONTEND_BUILD_DIR', tmp_path)
    with TestClient(main.app) as client:
        yield client


@pytest.mark.parametrize('page', sorted(main.PUBLIC_PAGES))
def test_public_initial_response_is_accessible_without_auth(built_client, page):
    response = built_client.get('/' + page + '?utm_source=qa')
    assert response.status_code == 200
    assert 'text/html' in response.headers['content-type']
    assert '<h1>Public ' in response.text
    assert 'X-Robots-Tag' not in response.headers
    assert 'no-cache' in response.headers['cache-control']
    head = built_client.head('/' + page)
    assert head.status_code == 200 and head.content == b''
    if page:
        redirect = built_client.get('/' + page + '/', follow_redirects=False)
        assert redirect.status_code == 308
        assert redirect.headers['location'] == 'http://testserver/' + page


@pytest.mark.parametrize('path', ['/not-a-page', '/api/missing', '/static/missing.js', '/app-shell.html', '/about/index.html', '/.env', '/build/index.html', '/static/%2e%2e/app-shell.html'])
def test_unknown_routes_and_unlisted_files_are_real_404(built_client, path):
    response = built_client.get(path)
    assert response.status_code == 404
    assert response.headers['X-Robots-Tag'] == 'noindex, follow'


def test_robots_sitemap_and_hashed_assets(built_client):
    robots = built_client.get('/robots.txt')
    assert robots.status_code == 200 and robots.headers['content-type'].startswith('text/plain')
    assert 'Allow: /' in robots.text and 'Disallow: /static' not in robots.text
    sitemap = built_client.get('/sitemap.xml')
    assert sitemap.status_code == 200 and sitemap.headers['content-type'].startswith('application/xml')
    from xml.etree import ElementTree
    assert ElementTree.fromstring(sitemap.text).tag.endswith('urlset')
    bundle = built_client.get('/static/js/main.123abc.js')
    assert 'immutable' in bundle.headers['cache-control']


@pytest.mark.parametrize('path', ['/?code=qa-code', '/?error=access_denied', '/auth/callback?code=qa-code'])
def test_callback_shell_is_noindex_and_not_cached(built_client, path):
    response = built_client.get(path)
    assert response.status_code == 200
    assert 'noindex' in response.text
    assert response.headers['X-Robots-Tag'] == 'noindex, follow'
    assert response.headers['cache-control'] == 'no-store'
    assert 'Public home' not in response.text


def test_private_api_stays_protected_and_noindex(built_client):
    for path in ['/account', '/recommendation/history', '/recommendation/unknown/state']:
        response = built_client.get(path)
        assert response.status_code in {401, 404}
        assert response.headers['X-Robots-Tag'] == 'noindex, follow'
        assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('origin', ['http://careerflow.live', 'http://www.careerflow.live', 'https://www.careerflow.live'])
def test_preferred_domain_and_scheme_redirect_once(built_client, origin):
    response = built_client.get(origin + '/about?utm_source=qa', follow_redirects=False)
    assert response.status_code == 308
    assert response.headers['location'] == 'https://careerflow.live/about?utm_source=qa'
    assert built_client.get(response.headers['location'], follow_redirects=False).status_code == 200


def test_untrusted_forwarded_scheme_cannot_override_redirect(built_client):
    response = built_client.get('http://careerflow.live/about', headers={'X-Forwarded-Proto': 'https'}, follow_redirects=False)
    assert response.status_code == 308
