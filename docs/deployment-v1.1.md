# CareerFlow v1.1 deployment and operations

The release uses the existing Supabase PostgreSQL and Supabase Auth project. It does not run a second PostgreSQL service. Do not replace the current production image until the candidate passes the tests and smoke checks below. No deployment is performed by these instructions alone.

## Configuration

The optional guided demo and free Gemini preview are documented in [guided-demo-ai-preview.md](guided-demo-ai-preview.md), including all five backend-only variables, migration `0003_ai_trial`, quota/cost limits, provider conditions and manual activation gates. The preview is disabled by default and never needs an owner Anthropic key.

Both local `.env` files are excluded from Git and Docker context. `frontend/.env` was previously tracked; it has been removed from the index, preserving the local file. This does not erase old Git history. The React configuration is public and compiled into the browser bundle. Never put a secret/server key in any `REACT_APP_*` variable.

| Variable | Location | Purpose |
|---|---|---|
| REACT_APP_SUPABASE_URL | frontend/.env; Docker build argument | Existing Supabase project URL |
| REACT_APP_SUPABASE_PUBLISHABLE_KEY | frontend/.env; Docker build argument | Public publishable key |
| REACT_APP_API_URL | frontend/.env locally | Local backend URL; empty for same-origin Docker build |
| SUPABASE_URL | backend/.env | Existing project URL |
| DATABASE_URL | backend/.env | Supabase PostgreSQL Session Pooler or direct URL |
| SUPABASE_PUBLISHABLE_KEY | backend environment | Public key used to verify tokens through Auth /user; local development can read the public value from frontend/.env, Compose passes it explicitly |
| SUPABASE_SECRET_KEY | backend/.env, server only | Optional server key, required for Auth account deletion; legacy SUPABASE_SERVICE_ROLE_KEY is also supported |
| CORS_ORIGINS | backend environment | Comma-separated allowed browser origins; Compose fixes this to https://careerflow.live |
| DEVELOPER_SUPABASE_USER_IDS | backend/.env, optional | Verified maintainer account UUIDs, used to prevent owner feedback from being classified as community feedback |

FastAPI loads `backend/.env` relative to config.py, without overriding supplied environment variables. Database URLs are never printed. Use port 5432 Session Pooler for IPv4-only hosts; direct connections require the networking supported by your Supabase project. The SQLAlchemy engine uses psycopg 3, SSL required by default (verify-full/verify-ca also accepted), pool size 5 plus 5 overflow, pre-ping, recycle 300 seconds, connect timeout 10 seconds. URL-encode password characters in DATABASE_URL. Do not use transaction pooling for this release.

Sources: [Supabase database connections](https://supabase.com/docs/guides/database/connecting-to-postgres), [server-verified getUser](https://supabase.com/docs/reference/javascript/auth-getuser), [PKCE](https://supabase.com/docs/guides/auth/sessions/pkce-flow), [Auth account deletion](https://supabase.com/docs/reference/javascript/auth-admin-deleteuser).

## Existing OAuth project

Google/GitHub client IDs and secrets belong in Supabase, not CareerFlow. In Supabase Auth URL Configuration, set the Site URL to https://careerflow.live and allow exact redirect URLs for https://careerflow.live/ and your development URL (for example http://localhost:3000/). Add staging origins only when used. Each provider's callback is your existing Supabase Auth callback, as shown by the Supabase dashboard.

Google scopes are openid, email, profile. GitHub requests read:user and user:email, with no repository or organization administration scope. Review the provider application scopes as well. Google Testing mode admits configured test users; public publication/branding verification is a separate owner task. Check both providers manually with an allowed test account. OAuth uses PKCE with an origin-root query callback, removes the code/error query parameters and restores a permitted hash route. Existing #profile and #results/<id> links remain hash routes.

Supabase SDK persists/refreshes the Auth session in browser storage. The storage adapter removes Google/GitHub provider access and refresh tokens before persistence; only the Supabase session and PKCE verifier are stored. The backend never trusts that stored user object or a supplied user_id: it verifies every Bearer token with the project's Auth /user endpoint. This deliberately supports both symmetric and asymmetric signing modes and checks current user status, at the cost of one Auth network call per authenticated request.

## Schema and existing SQLite data

Run from backend:

```powershell
uv sync --extra dev
uv run alembic upgrade head
```

Revision 0001_public_beta creates only the new careerflow schema: users, recommendation_sessions, specialization_scores, skill_gaps, roadmap_items, course_progress, course_filter_preferences, feedback, plus Alembic's version table. Domain IDs use UUID, timestamps are timezone-aware, related writes are atomic, session ownership is checked on reads and writes, and deletes cascade. The local user ID is the Supabase Auth ID; an ON DELETE CASCADE foreign key to auth.users removes domain data atomically when the Auth admin API deletes the identity. Authenticated feedback is deleted with the user; anonymous feedback is independent. Versioned schema definitions are frozen in the migration, not imported from evolving application code.

Revision 0002_public_feedback adds consent/moderation fields and feedback_votes, bringing the domain table count to 9. Legacy feedback remains private and untyped; no publication consent is inferred. All 9 domain tables have RLS enabled. See [public-product-pages.md](public-product-pages.md) for public API rules and maintainer-only moderation commands.

Migrations use a PostgreSQL advisory transaction lock. All domain tables have RLS enabled with no client-access policies; anon/authenticated roles have no access to this private schema. Keep careerflow out of Supabase Data API exposed schemas. Only FastAPI's privileged database connection accesses domain data, after Auth and ownership verification. The deployment database role needs CREATE SCHEMA and REFERENCES on auth.users; use the configured Supabase server connection, never the publishable key for database access.

Old SQLite is not read by v1.1 and is never imported into registered accounts. Shared demo rows have no verified owner. Before the switch, capture an archival snapshot using SQLite's backup API, which includes committed WAL data:

```powershell
cd backend
uv run python archive_sqlite.py data/career_advisor.sqlite3 data/legacy-backups/pre-v1.1.sqlite3
```

Copy the snapshot to private backup storage; the directory is ignored. The source is opened read-only. Destination overwrite is refused. Do not assign archived demo data to a new account without separate proof of ownership, consent and a reviewed importer. This archive is the migration path for anonymous legacy data. No automatic user-data import or destructive reset is performed.

## Verify, build, migrate, smoke-test

```powershell
cd backend
uv run pytest --ignore=tests/test_recommendations.py
$env:CAREERFLOW_TEST_POSTGRES='1'
uv run pytest tests/test_postgres.py -q
Remove-Item Env:CAREERFLOW_TEST_POSTGRES
cd ../frontend
npm ci --no-audit --no-fund
npm test -- --runInBand
npm run build
cd ..
docker compose --env-file frontend/.env build app
docker compose --env-file frontend/.env run --rm --no-deps app alembic upgrade head
```

The PostgreSQL integration test creates a uniquely named test schema in the existing database and rolls its entire transaction back; it neither creates a separate database nor changes existing application rows. Mocked Auth identities exercise database authorization; it does not prove external Google/GitHub login. tests/test_recommendations.py is a pre-existing real-model test that calls localhost:8000 by default (override with CAREERFLOW_TEST_API_URL) and requires an intentionally launched compatible test server; it is excluded from unattended unit tests, not silently counted as passing. The executed checks and three baseline model-expectation failures are recorded in [verification-v1.1.md](verification-v1.1.md). Review those failures and complete the external OAuth gates before promotion.

Run a candidate without replacing the current production container, using a separate name and loopback-only port:

```powershell
docker run --rm -d --name careerflow-v11-candidate --env-file backend/.env --env-file frontend/.env -p 127.0.0.1:18011:8000 career-recommendation-system-app
```

For a standalone container, the backend also accepts the public REACT_APP_SUPABASE_PUBLISHABLE_KEY from the frontend env file. Alternatively set SUPABASE_PUBLISHABLE_KEY in backend/.env. Compose maps the public key explicitly. Do not print `docker compose config` or `docker inspect` in shared logs: their resolved environment can contain secrets. Use `docker compose ... config --quiet` to validate configuration.

Check /health, /ready, homepage and a guest recommendation; verify that a different guest key receives 404 for the same session. Then use real User A/User B test accounts to verify OAuth, persistence across refresh/logout, denied cross-user reads/writes/AI requests and feedback. Account deletion requires the server key; test only a disposable test account. Missing server key returns 503 without changing account data. On an Auth deletion failure, the account is marked pending and private reads/writes stop; the user can retry deletion. Do not claim a live OAuth or account-deletion test without performing it.

After approval of the candidate, release commands are:

```powershell
docker compose --env-file frontend/.env up -d --no-build app
```

The command above replaces the Compose service. Do not execute it until the release gate passes. The Docker command disables Uvicorn access logs to avoid recording OAuth callback query codes. Configure proxy/ingress logs to omit or redact OAuth query parameters and never record credential headers. Configure HTTPS at the existing ingress/reverse proxy and redirect HTTP to HTTPS. Keep one replica/one Uvicorn worker: guest sessions and abuse limits are process-local. Guest credentials are random per browser tab; results expire after 2 hours or restart. No guest profiles are saved to PostgreSQL. Add shared TTL/rate-limit infrastructure before scaling horizontally. At a proxy, trust only your proxy's address for forwarded headers; configure upstream IP/body/request limits as well. Default application limits: 5 feedback submissions/minute/IP, 30 mutations/minute/IP/route group, 1 MiB JSON, 8 MiB CV/audio. A single shared proxy address can cause conservative limiting unless proxy headers are configured correctly.

## Rollback and deletion operations

Record and retain the old image ID and private SQLite snapshot before releasing. To roll back the application, start the prior image with its previous configuration and retained SQLite snapshot. Do not downgrade/drop the new schema: Alembic destructive downgrade is intentionally disabled. Preserve v1.1 PostgreSQL data even if reverting the UI. Back up Supabase before any later schema change.

If Auth deletion succeeds, the foreign key cascades application deletion in the same PostgreSQL database. If a pending deletion must be completed after the user's token no longer validates, the maintainer can delete the verified pending Supabase user in the dashboard; do not clear a tombstone merely to restore access to data pending deletion. Never log administrator keys or access tokens.

Local feedback review:

```powershell
cd backend
uv run python feedback_export.py feedback-private-2026-10-09.csv
```

The export command uses server database credentials locally, never a public API. It refuses overwrite and escapes spreadsheet formula prefixes. Store the output privately and delete it after review. No testimonials or usage metrics are generated from it automatically.

## Remaining owner review

- Add a server-only Supabase secret key if self-service account deletion is required.
- Confirm exact OAuth redirect allow-list, allowed Google test users and minimal provider scopes.
- Confirm ingress HTTPS, logging redaction, proxy trust and upstream rate limits.
- Define hosting/Supabase backup retention, geographic processing and an explicit anonymous-feedback retention schedule. Current policy states these are review items; no invented expiry/certification is advertised.
- Verify UI at narrow mobile widths and both OAuth providers with real allowed accounts before promoting the candidate.

## Contributions

Use a feature branch, keep model/scoring changes separate from product work, never commit .env or private feedback exports, and run the checks above before requesting review. GitHub Actions runs the isolated backend tests and frontend tests/build; the PostgreSQL and browser OAuth checks remain explicit integration gates.
