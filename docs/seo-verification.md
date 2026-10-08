# SEO candidate verification — 2026-10-09

No deployment, DNS modification, Search Console property creation, ownership verification or indexing request was performed. Existing v1.1/branding work was preserved. No database migration or ML change was needed in this phase.

## Executed checks

| Check | Result |
|---|---|
| `uv run --offline --no-sync pytest tests/test_seo.py -q --tb=short` | 26 passed; anonymous public GET/HEAD, trailing-slash redirects, actual 404, asset caching, sitemap/robots MIME types, private/API noindex, callback shell and canonical host redirects |
| `uv run --offline --no-sync pytest --ignore=tests/test_recommendations.py -q --tb=short` | 119 passed, 1 skipped (opt-in real PostgreSQL test); includes existing ownership, moderation and recommendation/API unit tests |
| Full backend suite with `CAREERFLOW_TEST_API_URL=http://127.0.0.1:18018` | 134 passed, 3 failed, 1 skipped in 25.58s. Includes real-model HTTP requests to the disposable Docker candidate. The three failures are the same previously documented model-expectation cases, listed below. |
| `CI=true npm test -- --runInBand` | 12 suites, 101 tests passed, including route metadata, private noindex, language switching, OAuth callback/return paths and lazy Results rendering |
| `npm run build` | Passed React compilation, nine-page prerendering and SEO artifact checks |
| `docker compose --env-file frontend/.env build` | Passed; Linux-generated CSS modules matched compiled CSS; Supabase public configuration remained part of the frontend build |
| Curl against final Docker candidate | All nine public pages returned 200 and initial H1/content/title/description/canonical/Open Graph/Twitter metadata without running JavaScript. XML sitemap, robots, social PNG dimensions, private callback shell, authorization and 404 checks passed. |
| Browser direct access and refresh | All nine routes passed at the default desktop viewport. Metadata remained specific after React started. |
| Browser mobile | All nine routes had no horizontal overflow at 320×900. Theme switching passed. About remained functional after EN/RU/KZ changes and refresh, with the correct shared canonical. |
| Browser recommendation regression | About AI CTA → profile → real-model recommendation → lazy Results and existing advisor passed at mobile width. Refresh restored the temporary guest result. Private result had no canonical/JSON-LD and had `noindex`. Closing/opening the advisor is interactive state and is not persisted across refresh. No provider key was supplied and no AI chat was sent. |
| Browser OAuth error callback | Root `?error=access_denied` was scrubbed and restored `#account`/Sign in with `noindex` and no public canonical. Real Google/GitHub authentication remains an external release check. |
| Schema.org Validator code test | WebSite and WebApplication: 0 errors, 0 warnings |
| Google Rich Results code test | One valid Software Application item; noncritical optional-field warnings for `offers` and `aggregateRating`, intentionally omitted rather than fabricated. [Result](https://search.google.com/test/rich-results/result?id=kI7W7o2qwPCkmFyMFB9GMQ) |
| Git boundaries | Diff whitespace check passed; both local `.env` files remain ignored. No secret contents printed. |

Existing pytest reports an unknown `asyncio_default_fixture_loop_scope` configuration option; Node/CRA reports existing deprecation warnings. They did not fail the corresponding checks.

## Existing model-expectation failures

The full suite was executed rather than reported as green:

| Profile case | Expected | Observed |
|---|---|---|
| 0 | Machine Learning Engineer first | Data Scientist first, Machine Learning Engineer second |
| 1 | Data Analyst first | Business Analyst first, Data Analyst second |
| 10 | Data Scientist in top two | Business Analyst first, Data Analyst second |

These are the three cases recorded in verification-v1.1.md, where original HEAD and candidate scores were previously compared. This SEO phase did not change model services, artifacts or coefficients, and did not weaken those assertions. The complete backend suite remains non-green for these baseline expectations.

## Actual performance measurements

Build gzip sizes (Windows): initial JS 206.63 kB and initial CSS 9.18 kB, compared with the preceding candidate's 232.38 kB / 17.91 kB. Results is now a separate 30.12 kB JS / 9.77 kB CSS chunk. Docker/Linux generated 206.64 kB / 9.17 kB initial assets; minor platform-specific class/hash differences are expected and checked within each build.

Curl initial-response bodies were 8,590–17,620 bytes. Single local Docker loopback samples after startup measured TTFB 0.0031–0.0077 seconds. These measurements exclude public-network latency and production TLS; they are not Lighthouse scores, field Core Web Vitals or a production performance guarantee. Existing external Google Fonts remain a network dependency.

## Live-site boundary

The HTTPS homepage was retrieved with Windows Invoke-WebRequest: HTTP 200, no prerendered H1, still the previous React shell. Curl's HTTP root received 301 to HTTPS; its HTTPS attempt timed out. The local resolver could not resolve the www hostname. Application canonical redirects were verified locally, but owner-controlled www DNS/TLS and forwarded-proxy scheme handling need verification through the real ingress. See google-search-console.md for exact owner steps.

The disposable container `careerflow-seo-candidate` was used only on loopback port 18018. Recommendation tests used temporary guest memory, not persistent feedback/recommendation rows. It was stopped and removed after checks. Temporary curl helper and validator screenshots were stored outside the repository. Browser viewport overrides were restored.

## Files changed in this SEO phase

- README.md
- backend/main.py
- backend/tests/test_seo.py
- frontend/package.json
- frontend/public/index.html
- frontend/public/robots.txt
- frontend/scripts/prerender.cjs
- frontend/scripts/check-seo.cjs
- frontend/src/data/seo.json
- frontend/src/data/structuredData.js
- frontend/src/utils/seo.js
- frontend/src/utils/seo.test.js
- frontend/src/App.jsx
- frontend/src/App.test.jsx
- frontend/src/context/AppContext.jsx
- frontend/src/components/Navbar.jsx
- frontend/src/components/Footer.jsx
- docs/google-search-console.md
- docs/seo-verification.md

Generated frontend/build HTML, sitemap and bundles are build artifacts, not committed source. No new dependency or framework was introduced. Translated crawlable URLs/hreflang, production Lighthouse/field measurements, real provider OAuth, DNS/TLS and owner Search Console operations remain follow-ups; no Google indexing claim is made.
