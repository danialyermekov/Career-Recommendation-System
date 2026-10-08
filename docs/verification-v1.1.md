# CareerFlow v1.1 candidate verification

Executed locally on 2026-10-09. This records a release candidate, not a production deployment.

| Check | Observed result |
|---|---|
| Backend isolated suite, `uv run pytest --ignore=tests/test_recommendations.py` | 138 passed, 2 skipped (opt-in PostgreSQL tests) |
| PostgreSQL integration, `CAREERFLOW_TEST_POSTGRES=1`, `pytest tests/test_postgres.py tests/test_ai_trial.py -k postgres` | 2 passed against the existing Supabase database; temporary test schema rolled back and confirmed absent; concurrent lifetime quota verified |
| Frontend, `npm test -- --runInBand` | 13 suites, 116 tests passed |
| React production build, `npm run build` | Passed (prerendered 9 public pages and sitemap; SEO checks passed) |
| Alembic, `uv run alembic upgrade head` | Passed; revision `0003_ai_trial` (head) applied to the existing Supabase database |
| Database catalog inspection | 12 domain/trial tables plus Alembic version table; RLS enabled on all 12 domain/trial tables; no schema access for anon/authenticated roles |
| Gemini API key and model availability | Verified using existing `API_KEY`: `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, and `gemini-2.5-flash-lite` all available in owner project; 1 minimal live `chat_preview` test call verified response `OK.` |
| Docker Compose configuration, `docker compose --env-file frontend/.env config --quiet` | Passed without printing resolved environment |
| Docker build, `docker compose --env-file frontend/.env build app` | Passed (image `career-recommendation-system-app:latest` built) |
| Disposable Docker candidate on loopback port 18011 | `/health`, `/ready`, `/ai/preview` (available, 3 messages), and real-model guest recommendation passed; seven career tracks returned |
| Guest isolation in Docker | Owner state read 200; another guest credential received 404; anonymous account history received 401 |
| Docker configuration boundary | Both local `.env` files, legacy SQLite archives and private feedback exports absent from final image; backend runtime configuration present; public Supabase configuration present in compiled React assets; final image connected to the migrated Supabase schema |
| Dependency lock and final migration check | `uv lock --check --offline` passed; migration test repeated successfully after advisory-lock review |
| Git configuration boundary | Both local `.env` files remain on disk, are ignored and are absent from the Git index; previously tracked frontend file staged for removal from the index only |
| Legacy data | Read-only SQLite backup created under ignored `backend/data/legacy-backups/`; original retained; no anonymous rows imported into accounts |

The existing pytest configuration produces an unknown-option warning for `asyncio_default_fixture_loop_scope`; it does not fail the suite.

## Existing real-model test failures

`CAREERFLOW_TEST_API_URL=http://127.0.0.1:18012 uv run pytest tests/test_recommendations.py` completed with **15 passed, 3 failed**. These tests assert a particular expected profession for hand-written profiles.

| Case | Test expectation | Observed highest-ranked profession |
|---|---|---|
| 0 | ML Engineer first | Data Scientist |
| 1 | Data Analyst first | Business Analyst |
| 10 | Data Scientist in top two | Business Analyst, Data Analyst |

Each failing profile was also run through the original `HEAD` backend and SQLite persistence in an isolated temporary directory, using the same model artifacts. The original and v1.1 `final_scores` and top professions matched exactly for all three cases. No ML logic, model artifacts or scoring coefficients were changed, and the assertions were not weakened. These are baseline model-expectation failures; the complete real-model suite is therefore not green.

## External checks still required

- Real Google/GitHub login with allowed accounts, callback handling in the deployed origin and persistence across browser refresh/logout.
- Manual two-account browser scenario; automated coverage already checks the same ownership operations with mocked Auth and real PostgreSQL.
- Disposable-account deletion against Supabase Auth after supplying a server-only administrator key. Neither supported administrator-key variable is currently configured locally; deletion returns a safe configuration error before changing data.
- Narrow mobile viewport review and production ingress HTTPS, proxy trust, callback-query log redaction and upstream abuse limits.
- Owner decisions on backup/anonymous-feedback retention and processing locations. Public policies identify these review items without inventing guarantees.

GitHub Actions checks were added but have not been run on GitHub. The existing production application was not replaced. Local candidate processes are disposable and are stopped after verification.
