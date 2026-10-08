# Public product pages and moderated feedback

This is candidate code, not a deployment confirmation. Keep the existing production app until the release checks pass. Branding, OAuth, PostgreSQL and existing recommendation behavior are preserved.

## Routes and API

Public UI paths are `/about`, `/feedback`, `/changelog`, `/roadmap`, plus `/contact`, `/privacy`, `/terms`, `/disclaimer`. FastAPI serves the built SPA for direct GET requests; refresh works without a separate router dependency. Legacy hash links, `/#profile` and `/#results/<id>` continue to work. OAuth always returns to the configured origin root, then restores only a whitelisted public path or private hash route. Configure the Supabase redirect allow-list for the root URL, as described in deployment-v1.1.md.

- `POST /feedback`: review, feature or bug submission; anonymous or authenticated. New records are pending and consent defaults to false.
- `GET /api/feedback?type=review|feature&offset=0`: at most 20 public records, newest first, plus `has_more`. Only consented, approved reviews/features whose origin was explicitly classified by the maintainer are returned. No account IDs, email, session IDs, reproduction steps or moderation notes are returned. Public authors are Anonymous; developer feedback is labeled. No rating averages or user/traction aggregates exist.
- `PUT /api/feedback/<uuid>/vote`, body `{"voted": true}` or `false`: verified Supabase login required. Only published features can receive votes. The database unique constraint and idempotent insert allow one active vote per account, and removal affects only the caller's vote.
- `GET /api/roadmap`: at most 100 approved, consented, explicitly linked features, with actual vote counts. Static product status is maintained in frontend/src/data/productUpdates.js.

There are no web moderation endpoints. Rendering treats all user text as text, not HTML. API input forbids user-supplied identity, moderation fields and development status. A session reference must belong to the verified account or guest credential; anonymous feedback never persists the temporary guest-session reference.

## Migration and preservation

Run from backend: `uv run alembic upgrade head`.

Revision `0002_public_feedback` adds consent, moderation, typed content, provenance, development status, roadmap link and updated timestamp to the existing feedback table. It adds feedback_votes with cascading foreign keys and a unique (feedback_id, user_id) constraint. Votes have RLS enabled and no browser-role grants. Existing private submissions keep their original contents and remain untyped, private and pending. No historical consent or customer identity is inferred, and legacy rows cannot be approved by this CLI. Export them privately for review.

The private careerflow schema now contains 9 domain tables plus the Alembic version table. Destructive downgrade remains disabled. Do not replace the old running application as part of migration alone.

## Maintainer workflow

Run locally from backend using the existing server DATABASE_URL. Commands never use browser credentials. Pending listing and exports contain private feedback: do not paste them into shared logs or commit them.

```powershell
uv run python feedback_manage.py pending
uv run python feedback_manage.py approve <feedback-uuid> --origin community --note "Checked independent origin, publication consent and personal information."
uv run python feedback_manage.py approve <feedback-uuid> --origin developer --note "Submitted by the project maintainer."
uv run python feedback_manage.py approve <feedback-uuid> --origin test --note "Owner-generated test submission; excluded from public listings."
uv run python feedback_manage.py reject <feedback-uuid>
uv run python feedback_manage.py remove <feedback-uuid>
uv run python feedback_manage.py status <feature-uuid> planned --note "Maintainer reviewed scope; no delivery date promised."
uv run python feedback_manage.py status <feature-uuid> in_progress --note "Active implementation verified in the working branch."
uv run python feedback_manage.py status <feature-uuid> released --note "Production publication verified; reference the actual deployed change."
uv run python feedback_manage.py link <feature-uuid> market-refresh
uv run python feedback_manage.py export feedback-private-review.csv
```

Use `--help` for each command. Approving requires an explicit origin and review note, a typed review/feature, and publication consent. Bug reports remain private regardless of consent. Remove withdraws public visibility without destroying the private record. A previously developer/test-classified record cannot be reclassified as community feedback. The operator must verify provenance; anonymous submissions are not automatically independent reviews.

Optionally set server-only `DEVELOPER_SUPABASE_USER_IDS` to the maintainer's verified Supabase UUID(s), comma-separated. Such authenticated submissions are automatically marked developer and cannot be approved as community feedback. Configure this from Supabase account records, never by matching a user-controlled display name. Anonymous owner/test submissions must be explicitly classified developer/test by the moderator; default unverified records cannot appear publicly. No extra Supabase project, OAuth secrets or database service is needed.

Known roadmap keys: career-ranking, skill-gaps, learning-roadmaps, career-comparison, course-discovery, private-accounts, community-feedback, market-refresh, more-careers, recommendation-quality. The maintainer explicitly links a genuine suggestion; it is never promoted or marked planned automatically. Future roadmap text is exploratory, with no release promises.

## Verified changelog evidence

The public changelog has one entry: the MVP launch on 2026-10-07, explicitly confirmed by the owner in this task. Its source reference is [3ccb8e409e7ab44c40e4da0763ed4f660c245c6d](https://github.com/danialyermekov/Career-Recommendation-System/commit/3ccb8e409e7ab44c40e4da0763ed4f660c245c6d). Git's commit date independently matches 2026-10-07. The live site returned HTTP 200 with the existing MVP bundle during inspection. Source inspection verified ranking, comparisons, explainability, roadmaps/courses and optional BYOK Claude/Gemini integration. No new version number, measured improvement, customer metric or unshipped v1.1 release was invented.

About shows only Danial Yermekov as the current Developer & Maintainer. Historical contributor credits remain in README. Methodology was checked in classifier.py, skill_matcher.py, demand.py, main.py and roadmap/course services. The AI CTA enters the existing profile/recommendation flow and opens the existing advisor with actual result context; it does not send an AI request or promise free API access.

## Deployment boundary and abuse limits

Keep one replica and one Uvicorn worker. Request limits are lock-protected and process-local, using the socket peer address rather than a client-supplied user ID or arbitrary forwarding header. Feedback allows 5 submissions/minute/IP; API mutations allow 30/minute/IP/route group; JSON bodies are limited to 1 MiB. Use the existing trusted ingress with proper proxy-address configuration and edge limits. Add shared limits before horizontal scaling. Do not advertise distributed rate limiting.

Existing external gates still apply: real Google/GitHub login, the server key for Supabase account deletion, HTTPS/proxy log review and owner retention decisions. Public pages and tests do not prove those external checks passed. Do not deploy automatically.

## Verification on 2026-10-09

| Check | Result |
|---|---|
| Backend, `uv run --offline --no-sync pytest --ignore=tests/test_recommendations.py -q --tb=short` | 93 passed, 1 skipped (opt-in PostgreSQL test) |
| Real PostgreSQL, `CAREERFLOW_TEST_POSTGRES=1 uv run --offline --no-sync pytest tests/test_postgres.py -q` | 1 passed; ownership, consent/publication, voting and cascades exercised in a temporary schema, then rolled back |
| Frontend, `CI=true npm test -- --watchAll=false --runInBand` | 11 suites, 86 tests passed after the final routing change |
| Frontend production build and `docker compose --env-file frontend/.env build` | Passed; public Supabase configuration compiled into React, server configuration supplied at runtime |
| Existing Supabase migration | `0002_public_feedback` applied; repeated upgrade passed; 9 domain tables have RLS enabled |
| Disposable Docker candidate | Health/readiness, four direct public routes, feedback/roadmap APIs returned 200; unknown API returned 404; local environment files and legacy archives absent from image |
| Browser feedback flow with real PostgreSQL | Anonymous review/feature, hidden pending state, explicit moderation, safe text rendering, authenticated vote/unvote, roadmap linking and withdrawal passed. Auth identity was synthetic; all QA rows and the private QA schema were rolled back. No synthetic feedback was published to the real schema. |
| Public-page browser matrix | All four routes loaded and refreshed in EN/RU/KZ, dark/light themes and 320/1280px widths (48 combinations), with branding/footer present and no horizontal overflow. Desktop screenshots inspected. |
| Docker browser AI CTA | About → profile → real-model recommendation → existing AI Advisor passed; own-key disclosure visible and zero AI requests sent. Guest recommendation returned seven career tracks and a roadmap without persistent database writes. |
| Git/configuration boundary | Both local `.env` files ignored and retained; diff whitespace check passed. No credentials printed. |

The final recommendation step in the separate Windows PostgreSQL browser helper timed out while analyzing; the same real-model/UI flow passed in Docker with a fresh anonymous browser. Do not interpret that Windows helper timeout as a successful model check.

The complete real-model pytest suite is not green: the preceding v1.1 verification recorded 15 passed and 3 baseline profession-expectation failures, reproduced with identical scores on the original HEAD. That full suite was not rerun for these public-page changes; see verification-v1.1.md. ML logic and model artifacts remain unchanged.

No application deployment was performed. The live careerflow.live inspection returned the existing MVP assets, not this candidate. Only the additive database migration was applied to the existing Supabase project. Real provider OAuth, account deletion and production ingress checks remain external release gates.

## Files changed for the public-product-pages phase

Earlier uncommitted v1.1, branding and results-page changes were preserved. This phase touched:

- Project documentation: README.md, CHANGELOG.md, docs/deployment-v1.1.md, docs/public-product-pages.md.
- Backend configuration and persistence: backend/.env.example, backend/config.py, backend/database.py, backend/schemas.py, backend/main.py, backend/migrations/versions/0002_public_feedback.py.
- Local moderation/export: backend/feedback_manage.py, backend/feedback_export.py.
- Backend checks: backend/tests/test_public_feedback.py, backend/tests/test_public_beta.py, backend/tests/test_maintainer_tools.py, backend/tests/test_migrations.py, backend/tests/test_postgres.py.
- Frontend routes and content: frontend/src/App.jsx, frontend/src/pages/About.jsx, frontend/src/pages/Changelog.jsx, frontend/src/pages/FeedbackPage.jsx, frontend/src/pages/ProductRoadmap.jsx, frontend/src/pages/PublicPage.jsx, frontend/src/pages/Results.jsx, frontend/src/data/productUpdates.js.
- Shared frontend UI and translations: frontend/src/components/Feedback.jsx, frontend/src/components/Footer.jsx, frontend/src/components/Navbar.jsx, frontend/src/components/Navbar.module.css, frontend/src/beta.css, frontend/src/i18n.js, frontend/src/productI18n.js.
- Frontend API/auth: frontend/src/utils/api.js, frontend/src/utils/supabase.js, frontend/src/context/AuthContext.jsx.
- Frontend checks: frontend/src/App.test.jsx, frontend/src/components/Feedback.test.jsx, frontend/src/pages/FeedbackPage.test.jsx, frontend/src/utils/supabase.test.js, frontend/src/i18n.test.js.

No new dependencies, ML-service changes or model-artifact changes were introduced in this phase. The existing Supabase project and production application were retained. Temporary browser helpers/screenshots were written outside the repository; their database rows were rolled back and both local QA ports were closed after verification.
