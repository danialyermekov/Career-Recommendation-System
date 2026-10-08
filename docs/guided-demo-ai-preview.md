# Guided demo and optional Gemini preview — release candidate

The homepage's **Try Live Demo** submits the existing `DEMO_PROFILE` to the real `/recommend` endpoint and opens the actual results. No scores are embedded in the tour. Its five contextual cards reuse the recommendation, explanation, comparison, roadmap, completion and course controls. Next, Back, Skip Tour and Escape work without a modal or focus trap. The final card offers account creation/sign-in and the existing AI Advisor. The tour never sends a provider request.

Demo requests deliberately use a guest credential even when signed in. Demo results/progress remain in the existing two-hour process-local guest store, and the account save action is disabled. Refresh restores them while the same tab credential and server session exist; a restart discards them. Personal recommendations still use verified Supabase identity and PostgreSQL. Creating an account does not import shared demo data.

## Backend runtime configuration

Set these only in `backend/.env` or the deployment's secret/runtime environment. Both local `.env` files are ignored by Git and Docker context. No Gemini key is a React variable or Docker build argument. Compose already injects `backend/.env` at runtime; local FastAPI loads it through the existing config module. Do not run `docker compose config`, dump container environments, or print credentials while following this procedure.

| Variable | Default/example | Meaning |
| --- | --- | --- |
| `GEMINI_DEMO_API_KEY` | empty | Dedicated backend-owned Google key; falls back to legacy `API_KEY` if unset; empty disables preview |
| `GEMINI_DEMO_MODEL` | `gemini-3.5-flash-lite` | Exact allowlisted text model; no automatic fallback |
| `GEMINI_DEMO_ENABLED` | `false` | Server kill switch; restart the service after changing runtime config |
| `GEMINI_DEMO_FREE_MESSAGES` | `3` | Lifetime allocation, bounded to 1–3 |
| `GEMINI_DEMO_GLOBAL_DAILY_LIMIT` | `100` | Maximum provider attempts per UTC day, including provider errors |

Supported explicit choices are `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, and `gemini-2.5-flash-lite`. Invalid models, disabled mode, invalid quotas or a missing demo key fail closed. `GEMINI_DEMO_API_KEY` is preferred; if unset, it falls back to the existing server-side `API_KEY` for the preview only. Model access in the owner's Google project has been verified: `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, and `gemini-2.5-flash-lite` are all accessible. No Pro fallback is permitted. BYOK routes keep using the supplied user key and never fall back to server keys. No project-owner Anthropic key is required.

References checked on 9 October 2026: [Google model catalog](https://ai.google.dev/gemini-api/docs/models), [3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [thinking configuration](https://ai.google.dev/gemini-api/docs/thinking).

## Identity, quotas and cost controls

`GET /ai/preview` returns server quota state and issues an opaque random guest cookie when enabled. `POST /ai/preview` accepts an authorized recommendation ID, question, at most four recent messages, language and explicit consent. It does not accept credentials, user IDs, tools, deep mode, files or audio. Verified Bearer identity determines an account allocation. A guest cookie is accepted only if a matching hashed allocation already exists in PostgreSQL; client-chosen identifiers cannot select arbitrary trial rows. Cookies are HttpOnly, SameSite=Lax, one-year lifetime and Secure outside local development. HTTPS is required for deployment.

Revision `0003_ai_trial` adds three private tables with RLS enabled and public/anon/authenticated access revoked:

- `ai_trial_usage`: hashed identity, optional account FK, lifetime used count and a temporary reservation/lease.
- `ai_trial_budget`: one global guard row, UTC day and attempted provider request count.
- `ai_trial_ip`: daily hashed IP identity, rolling minute-window start and request count; rows older than one day are pruned on access.

Every status/reservation operation locks the same global budget row. PostgreSQL `INSERT ... ON CONFLICT` and `SELECT ... FOR UPDATE` serialize creation and reservation across processes. A reservation increases the lifetime user counter and global daily counter in the same transaction. At most two unexpired preview requests are admitted globally and one per identity; leases last 90 seconds. Provider completion clears the reservation. A known provider failure refunds the user allocation when storage is available, while preserving the global attempt count. A crash or unavailable storage can conservatively leave a message spent; no retry bypasses the cap. Expired leases allow recovery without resetting lifetime usage. No conversation content or provider key is stored in these tables.

Supplementary preview IP limits allow ten status/submission requests per minute. Existing mutation/body limits also apply. Configure Uvicorn's proxy trust for the actual ingress only; client-supplied forwarded headers must never freely determine the limiter IP. If all requests appear to come from one proxy, the IP limit is deliberately conservative. Database availability is required for an enabled preview; no in-memory quota fallback exists.

The provider receives a maximum 1,000-character question, four history items of at most 1,000 characters each and at most 20,000 characters of selected recommendation context. Output is capped at 600 tokens. Flash-Lite 3.x uses minimal thinking; 2.5 disables thinking. No tools, search grounding, files, audio or uploads are enabled. SDK timeout is 20 seconds and automatic retries are disabled. Preview suggestions submit a normal quota-consuming question only after consent and a user click.

The context includes verified canonical skills, recommended career, skill match, missing skills, roadmap and courses from the authorized result. Account name/email, raw CV and academic profile fields are excluded; emails in course/context metadata are redacted. User-written questions/history can still contain personal information, so the consent text asks users not to include it. Cross-user recommendation IDs and wrong guest credentials return 404 before reserving quota or calling Google.

## Privacy and provider conditions

The preview explicitly identifies Gemini and requires consent before transmitting context to Google. Privacy pages and the existing Privacy dialog explain the data, quota cookie and retention. Free access for CareerFlow users does not determine the owner's Google billing tier. The project tier has not been independently verified. Google's unpaid service conditions permit product improvement and human review; billing-enabled service conditions differ and retain limited abuse-monitoring processing. See the current [Gemini API terms](https://ai.google.dev/gemini-api/terms) before activation.

Google also restricts audience age, supported regions and unpaid use for EEA/UK/Switzerland users. The UI includes an adult affirmation, which is not reliable age verification. Before enabling a public preview, the owner must verify that the application's intended/likely audience and regional availability meet provider conditions; this code does not infer age, geolocate visitors or establish legal eligibility. Leave the kill switch off if that cannot be established. A billing-enabled project is the prudent choice for a public personalized service, but does not remove audience/region obligations. Neither provider is described as a CareerFlow partner.

Guest cookies can be cleared/copied, networks changed and accounts recreated. Guest and verified-account allocations are separate; this is not a guarantee of three messages per real person. The daily global cap bounds server provider attempts regardless. Guest quota records currently have no automatic retention expiry. Account allocations cascade on account deletion. Existing guest recommendation storage remains single-process; keep one API worker until that store is replaced. This feature adds no analytics or outbound email service.

## Secure manual release procedure

1. Keep the current production image running. Retain its immutable image ID and existing backups. Run frontend tests/build, backend pytest and opt-in PostgreSQL isolation/concurrency tests against a disposable test schema. Resolve critical failures; see the verification section for existing real-model expectation failures.
2. Configure the five backend runtime variables privately. Keep `GEMINI_DEMO_ENABLED=false` while checking the exact model, project access, tier, audience/regions, HTTPS and trusted proxy settings. No Google/GitHub OAuth secrets belong in CareerFlow; those remain in the existing Supabase project.
3. From the repository root, build the candidate with `docker compose --env-file frontend/.env build app`. Only public Supabase build args enter React. Save the resulting candidate under an immutable release tag without replacing the running production container.
4. After backing up the existing Supabase database and approving the release window, run `docker compose --env-file frontend/.env run --rm --no-deps app uv run --no-sync alembic upgrade head`. This adds private quota tables; never downgrade/drop the schema for rollback. This document does not execute that migration on the production schema.
5. Start the candidate under a separate name/loopback port or staging hostname with the same existing Supabase project. Check `/health`, `/ready`, public prerendered pages, login, private ownership, direct demo, all tour steps, roadmap/course actions, contact links and both themes/mobile layouts. Test the preview with an explicitly authorized provider request and verify remaining quota on refresh. Claude/Gemini mocked tests are not live provider validation.
6. Only after these gates pass, explicitly switch production to the immutable candidate and, if provider conditions are satisfied, enable the preview with the backend-only key. Do not print the key in commands or logs. An exhausted global budget or provider failure must preserve recommendations and BYOK.
7. Roll back the application image/config if needed; keep PostgreSQL data. To stop preview spending immediately, disable its runtime switch and restart the preview-serving application. No automatic deploy is included.

## Verification

Final tests and verification passed on 9 October 2026. The existing `API_KEY` in `backend/.env` was verified against Google's GenAI API; model access for `gemini-3.5-flash-lite` was confirmed and tested live. All 138 backend unit tests, 2 opt-in PostgreSQL concurrency/quota tests, 116 frontend tests, React build, Alembic migration `0003_ai_trial`, and Docker candidate build and smoke tests passed.
