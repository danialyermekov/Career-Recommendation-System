<p align="center">
  <img src="assets/careerflow-logo.svg" alt="CareerFlow — wave symbol and wordmark" width="360">
</p>

<h1 align="center">CareerFlow</h1>

<p align="center">ML-powered career recommendations, skill-gap insights, and personalized learning roadmaps.</p>

<p align="center">
  <a href="https://careerflow.live">Website</a> ·
  <a href="https://careerflow.live/feedback">Feedback</a> ·
  <a href="mailto:contact@careerflow.live">Contact</a>
</p>

<p align="center">
  <a href="https://careerflow.live/about">About</a> ·
  <a href="https://careerflow.live/roadmap">Roadmap</a> ·
  <a href="https://careerflow.live/changelog">Changelog</a> ·
  <a href="https://careerflow.live/privacy">Privacy</a> ·
  <a href="https://careerflow.live/terms">Terms</a>
</p>

CareerFlow helps IT students explore a career direction. The application ranks seven IT careers using profile classification, skill similarity and historical market signals, explains the ranking, and builds a rule-based learning roadmap with courses. Try the **Guided Demo** on the [live website](https://careerflow.live) for an immediate recommendation and a guided results tour, or enter your own profile in guest mode. Sign in to save private history and learning progress.

**Status:** v1.1 public MVP, actively developed and deployed on Azure Container Apps. Google/GitHub OAuth and private history use Supabase Auth and PostgreSQL. The core ML recommendations and roadmap require no AI API key. The optional AI Advisor offers an enabled **Gemini Free Preview with up to three messages** on production, plus Claude/Gemini bring-your-own-key (BYOK) chat.

**Data scope:** Market signals come from historical 2023 job postings, not a live vacancy feed. The profile classifier is trained on synthetic educational data; scores are exploratory guidance, not predictions of career success. Dataset provenance and methodology are documented below.

**Repository:** [danialyermekov/careerflow](https://github.com/danialyermekov/careerflow). **Current maintainer:** [Danial Yermekov](#contact).

For configuration and safe local setup, see [Local Development](#local-development). The [backend README](backend/README.md) describes the API and services; the research READMEs linked under [Model Results](#model-results) describe the ML experiments. The production status above was checked on 9 October 2026.

## Contributors

The original project authors are:

| Name | GitHub |
| --- | --- |
| Danial Yermekov | https://github.com/danialyermekov |
| Nurbek Seiilbek | https://github.com/Nurbek399 |
| Turan Tastan | https://github.com/another-restless-student23 |

## What The System Does

The system helps students choose an IT career direction by combining:

- student profile classification with a CatBoost classifier;
- skill matching against profession profiles;
- historical labor-market demand and trend scoring;
- weighted final scoring across all supported professions;
- skill-gap analysis;
- personalized roadmaps with course recommendations;
- advanced course filtering by certificate, price, language, platform, and level;
- skill-level explainability with SHAP or fallback feature-importance logic;
- private recommendation history and roadmap progress in Supabase PostgreSQL;
- Google and GitHub OAuth through Supabase Auth, plus guest mode without sign-in;
- an interactive Guided Demo using the real recommendation pipeline, with temporary progress;
- a Gemini Free Preview with up to three messages, PostgreSQL quotas and server-side cost limits;
- optional Claude or Gemini AI Advisor chat with a user-provided session key;
- public About, Feedback, Roadmap and Changelog pages, with consent-based feedback moderation.

The app does not only return a single top profession. It shows all supported career tracks and lets the student compare scores, skill gaps, market signals, and roadmap requirements.

## Supported Career Tracks

- Business Analyst
- Cloud Engineer
- Data Analyst
- Data Engineer
- Data Scientist
- Machine Learning Engineer
- Software Engineer

## Main Features

### Recommendation Pipeline

The final recommendation score combines four signals:

```text
Final score =
  0.38 * normalized classifier/profile score
+ 0.35 * normalized skill-match score
+ 0.20 * normalized demand-trend score
+ 0.07 * normalized demand market-share score
```

These weights come from `backend/config.py`. In `backend/top_profession.py`, classifier values are divided by their sum; the other three signals are separately divided by their largest value across the scored careers. A zero denominator uses 1. The weighted sum is rounded to four decimal places, without a final normalization across careers. The frontend displays it as a match score out of 100, not a probability of career success. The breakdown uses these same normalized values; expandable details also show the raw API values.

Normalized user skills are sorted before vectorization because the saved TF-IDF vectorizer includes bigrams. This prevents Python set iteration order from changing scores between worker processes; the vectorizer and profession vectors are unchanged.

### Data and reviewer workflow

The landing-page **Guided Demo** immediately sends a fixed Computer Science profile through the real recommendation API and opens a five-step results tour; no manual form submission is required. It uses guest credentials even when the visitor is signed in, so demo results and progress remain temporary. The profile form separately offers an editable demo profile with GPA 3.2, Python/SQL/Pandas/Git/Excel and moderate self-ratings; this form still requires submission. Demo labels are browser-tab metadata; no history is fabricated. GPA is the only field the form requires users to enter; other API fields are populated with visible defaults.

Dataset provenance (source pages supplied by the project owner; upstream metadata checked on 2026-10-07):

| Source | Local use and derived artifacts | Upstream declared license |
|---|---|---|
| Luke Barousse’s [Data Jobs on Hugging Face](https://huggingface.co/datasets/lukebarousse/data_jobs) | Historical 2023 job postings. Demand and skill notebooks read `data/raw/data_jobs_norm.csv`; demand aggregation produces `ml/demand prediction/data/aggregated/weekly_vacancy_counts.csv`, identical to `backend/data/vacancy_data.csv`. Skill notebooks derive the TF-IDF vectorizer and profession vectors/profiles used for skill matching and roadmaps. | Apache 2.0 (`apache-2.0`), verified in the [upstream dataset card](https://huggingface.co/datasets/lukebarousse/data_jobs/raw/main/README.md). |
| hafsaatm’s [Career Path Recommendation on Kaggle](https://www.kaggle.com/datasets/hafsaatm/career-path-recommendation) | Synthetic profiles in `ml/classification/data/raw/career_multilabel_dataset.csv`, followed by local balancing, feature engineering and classifier training. The file has education/background fields, technical indicators, soft skills and three recommended-job labels; the current classifier targets `recommended_job_1`. | The [Kaggle metadata endpoint](https://www.kaggle.com/api/v1/datasets/view/hafsaatm/career-path-recommendation) reports `licenseName: "Unknown"`. License terms remain unverified; clarify them before broader reuse. |

The upstream Hugging Face card describes postings collected through Google from multiple sources; this project does not claim direct or complete coverage of LinkedIn, Glassdoor or any other platform. The Kaggle description explicitly identifies its profiles as synthetic educational/research data, not observed career outcomes. Upstream download revisions and checksums were not recorded, and the intermediate `data_jobs_norm.csv` files referenced by the notebooks are not checked in, so exact reproduction of the original imports remains unverified. These dataset declarations do not assign a license to CareerFlow itself.

The checked-in demand file `backend/data/vacancy_data.csv` contains 371 weekly career observations dated 2023-01-01 through 2023-12-31. The service maps the current calendar date to a 2023 week; these estimates are historical and do not represent live job availability. Trend is predicted volume divided by each career's historical weekly peak; market share is predicted volume divided by the total for the supported tracks, before ranking normalization.

The raw profile file contains 2,000 rows. The training preparation adds synthetic examples for missing Data Analyst and Data Engineer classes. The serving preprocessor uses study field, GPA, technical indicators, soft-skill ratings and derived features; it does not use age or gender. Synthetic-label classification is exploratory guidance and does not establish real career outcomes.

The course catalog contains 41,690 rows in `backend/data/all_courses.csv`, not a verified count of distinct, currently available courses. Price, availability and rating freshness are unverified. The public hero does not advertise this count. The roadmap uses normalized skill gaps, category limits and framework/language compatibility rules; progress counts user-marked learning steps.

Private application views use URL hashes (`#profile`, `#results/<session_id>`); public pages use clean paths such as `/about`, `/feedback`, `/roadmap` and `/changelog`, with prerendered HTML in the production build. OAuth returns to `/auth/callback`. A saved result can reload through the state API and belongs to its verified user. Guest results require a separate random credential and last at most two hours, ending earlier on a process restart or scale-to-zero. Guest history is never imported into an account automatically. Dataset licensing and infrastructure/privacy review remain separate concerns.

Backend services:

- `ClassifierService`: CatBoost model for profile-fit probabilities.
- `SkillMatcherService`: TF-IDF profession vectors and cosine similarity.
- `DemandService`: fits LightGBM on bundled historical data when the service is first initialized in a process, then caches weekly demand scores; it does not fetch live vacancies.
- `CourseFinderService`: roadmap course lookup from the course catalog.
- `LLMService`: optional Claude/Gemini chat and streaming; Gemini voice transcription.

### Course Filtering

The course catalog now uses:

```text
backend/data/all_courses.csv
```

The dataset includes course metadata such as:

- `platform`
- `difficulty`
- `certificate`
- `price`
- `rating`
- `number_of_reviews`
- `course_url`

The frontend provides filters for:

- certificate: with certificate, without certificate, all;
- price: free, paid, all;
- language: English, Russian, Kazakh, other available languages;
- platform: Coursera, Udemy, edX, Stepik, and other available platforms;
- level: Beginner, Intermediate, Advanced, Mixed, all.

Filters work together and update course lists without page reload. The same filtering logic is used in the recommended courses block and inside the roadmap. If no course matches the selected filters, the UI shows an empty-state message.

Some metadata is heuristic: the catalog has no language or currency column, and language/free-price handling can infer values from titles or providers. Filters do not verify the current course page, price, availability or certificate terms.

### Explainability

The app has two explanation layers:

- score-level explanation: profile match, skill match, market share, trend score;
- skill-level explanation: which skills increased or decreased the classifier confidence for the selected profession.

Skill-level explainability is implemented in `backend/services/classifier.py`:

1. It first tries CatBoost local SHAP values.
2. If SHAP cannot be computed for the runtime/model, it falls back to a model-aware feature-importance and counterfactual delta approach.

The frontend shows:

- bar chart of skill impact;
- top positive skills;
- top missing or negative skills;
- plain-language explanation for students.

When the user selects another profession, the explanation panel updates for that selected profession.

### PostgreSQL Persistence

The application uses Supabase PostgreSQL through SQLAlchemy Core, psycopg 3 and Alembic. Tables live in the private `careerflow` schema. A legacy SQLite file, if present locally, is only an input to the archival utility:

```text
backend/data/career_advisor.sqlite3
```

Schema changes run explicitly through Alembic after checking the database target; see [safe local migrations](#safe-local-migrations). Startup does not create or reset tables. UUID account IDs reference Supabase Auth users with cascading deletion. Application tables have RLS enabled and no browser-role permissions. The legacy SQLite file is ignored by Git and Docker context; application requests never read it or import its anonymous history into accounts. It is not a rollback database for v1.1.

Current tables:

| Table | Purpose |
| --- | --- |
| `users` | Verified Supabase Auth identity, display name, deletion status and timestamps |
| `recommendation_sessions` | Recommendation payloads, profile JSON, LLM context, progress JSON |
| `specialization_scores` | Final, classifier, skill, trend, market, vacancy scores per profession |
| `skill_gaps` | Full and missing skills by profession/category |
| `roadmap_items` | Roadmap tasks, order, completion state, related courses |
| `course_progress` | Per-course progress placeholders |
| `course_filter_preferences` | Saved filter state per recommendation session |
| `feedback` | Private submissions, publication consent, moderation status and origin |
| `feedback_votes` | Authenticated votes on published feature requests |
| `ai_trial_usage` | Preview allowance per guest cookie or authenticated identity |
| `ai_trial_budget` | Shared daily preview attempt budget |
| `ai_trial_ip` | Short-lived preview IP rate-limit counters |

Google/GitHub OAuth uses Supabase Auth and PKCE. The maintainer has manually confirmed both providers work on `careerflow.live` and that Google's OAuth app is in Production mode. Local sign-in separately requires the exact development callback URL in the development Supabase project's redirect allow-list; production success does not prove a local project's configuration. The backend verifies Bearer tokens through Supabase Auth and scopes every private session operation to the verified user. Feedback defaults to private and pending; only explicitly consented, approved reviews/features with maintainer-classified origin have a public listing. Feature votes require authentication.

### Visual Analytics

The results page includes:

- best match card;
- all-profession bars chart;
- multi-profession radar chart;
- skill-gap comparison;
- score circles;
- factor bars with tooltips;
- responsive desktop and mobile layouts.

### Learning Roadmap

Roadmap features:

- personalized skill-gap roadmap for the recommended profession;
- courses attached to missing skills;
- drag-and-drop category and skill ordering;
- checklist state for completed skills;
- completed steps section;
- roadmap progress bar;
- skill dependency tree with prerequisites and next recommended step;
- PostgreSQL persistence for signed-in users; temporary session-scoped memory for guests.

### AI Advisor

The AI Advisor is optional. No personal AI API key is required to use CareerFlow's recommendations, ML models, roadmap, resume parser, historical demand estimates, history, or progress. Signed-in users can save history and progress; guests use temporary session state.

#### Gemini Free Preview

Choose **Try with Gemini** to ask up to three questions about the current recommendation without supplying an API key. The preview is enabled on production: `/ai/preview` reported `available: true`, `total: 3` and model `gemini-3.5-flash-lite` during the 9 October 2026 audit. It requires consent, uses a server-managed Gemini key, and enforces PostgreSQL-backed quotas and daily cost limits. The allowance is tracked separately per guest cookie or verified account; it is not three messages per day or a verified per-person entitlement. Availability depends on remaining quota, the shared daily budget and provider status; core recommendations continue to work when the preview is unavailable.

Fresh local installations default to `GEMINI_DEMO_ENABLED=false`. When deliberately enabled, the preview uses `GEMINI_DEMO_API_KEY`, falling back to the legacy server-side `API_KEY` only for this preview. Neither key belongs in React variables or Docker build arguments. Preview conversations are not saved to recommendation history; the request sends a limited recommendation context. See [development configuration](#development-configuration) for the quota and model variables. Supported preview models are `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite` and `gemini-2.5-flash-lite`; other model IDs fail closed, with no Pro fallback.

#### Bring Your Own Key (Claude / Gemini)

For BYOK chat, open the AI assistant panel, select Claude / Anthropic or Gemini / Google, enter your API key, and choose **Use key**. Use **Remove key** to disable BYOK immediately. The following capabilities and credential-handling details apply to BYOK; the Free Preview is a separate, quota-limited text chat.

Features:

- grounded responses based on the current recommendation context;
- streaming responses;
- deep/thinking mode UI;
- voice transcription endpoint;
- speech playback in supported browsers;
- prompt-injection and off-topic guardrails;
- compact translucent floating button that does not block course browsing.

The password input is cleared after selecting **Use key**; the UI shows only the provider and a masked enabled state. Credentials live only in frontend module memory for the lifetime of the loaded React application. Client-side navigation keeps them available; a full refresh, reopening the page, or opening another tab starts without a key. **Remove key** clears them immediately. Credentials are never written to localStorage, sessionStorage, IndexedDB, cookies, chat messages, or recommendation/progress history. Loading this version removes the legacy `careerflow-llm-session` browser-storage entry without reading or restoring it.

Only `/chat`, `/chat/stream`, and `/voice/transcribe` receive `X-LLM-Provider` (`anthropic` or `gemini`) and `X-LLM-API-Key` headers. They are never URL/query/body fields. FastAPI validates headers without echoing their values, then passes them to the LLM service for that request. A small provider registry dispatches to per-call SDK clients, closed after completion; no credential-bearing backend singleton, session, cache, file, or database record is created. BYOK never falls back to server credentials, including `API_KEY`, `GEMINI_DEMO_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY` or `ANTHROPIC_API_KEY`.

The BYOK generation request checks the key; selecting **Use key** makes no provider call. Missing BYOK keys return HTTP 400, rejected credentials HTTP 401, rate limits HTTP 429, and unavailable providers HTTP 503. After an SSE stream starts, failures are safe JSON `type: "error"` events followed by one `[DONE]`. Invalid keys remain only in memory for the user to correct or remove. Removing/changing credentials aborts in-flight frontend AI requests.

Claude uses Anthropic Messages with `claude-sonnet-5-5`; deep mode uses adaptive thinking. Gemini retains the existing `google-genai` chat models and thought/text stream format. Audio transcription remains Gemini-only; Claude users can type or use browser speech playback. To add a provider, implement the same three provider methods, register it in `backend/services/llm.py`, and add its public metadata to `frontend/src/utils/llmSettings.js`.

Security limits: in-memory credentials do **not** protect against XSS or malicious browser extensions. Use HTTPS outside localhost. The key necessarily passes through CareerFlow's backend and the selected provider; provider-side processing and retention follow that provider's policies. BYOK errors are sanitized and SDK request/exception debug logging is suppressed. The separate preview error handler currently logs exception text, so its logs still require a privacy review; do not treat all provider failures as fully redacted. Keep reverse proxies, APM, analytics, and transport debug logging from recording `X-LLM-API-Key`, `x-api-key`, or `x-goog-api-key`. CORS permits the custom headers; it is not authentication. Supabase authentication and session ownership checks protect private results; basic request limits are process-local and require shared or edge limits before scaling.

### Resume / CV Parser

The backend can parse raw file bytes for:

- text-based PDF files;
- TXT files through supported text decoding.

It extracts:

- detected skills;
- possible current role;
- text preview.

Scanned image-only resumes require OCR, which is not implemented. DOCX is not supported by a dedicated document reader.

### Localization

The frontend supports:

- English;
- Russian;
- Kazakh.

Translations cover main UI, profession names, filters, roadmap, explanations, AI advisor texts, and PDF labels.

## System Architecture

```text
Student profile / uploaded resume
        |
        v
FastAPI backend
        |
        |-- CatBoost classifier -> profile probabilities + SHAP/fallback skill explanations
        |-- TF-IDF skill matcher -> profession skill similarity
        |-- LightGBM demand model -> trend and market-share scores
        |-- Roadmap engine -> skill gaps
        |-- Course finder -> filtered course metadata from all_courses.csv
        |-- Supabase PostgreSQL -> private history, scores, gaps, progress, filters, feedback
        |-- PyMuPDF parser -> resume skills and role extraction
        |-- Claude / Gemini LLM service -> optional BYOK advisor + Gemini Free Preview
        |
        v
React frontend
        |
        |-- profile form
        |-- all-profession visual analytics
        |-- SHAP/fallback skill impact UI
        |-- course filters
        |-- roadmap and dependency tree
        |-- AI advisor side panel
        |-- PDF export
```

## Tech Stack

| Layer | Tools |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Database | Supabase PostgreSQL, SQLAlchemy Core, Alembic, psycopg 3 |
| Authentication | Supabase Auth, Google/GitHub OAuth with PKCE |
| ML | CatBoost, LightGBM, scikit-learn, pandas, NumPy, joblib |
| Resume parsing | PyMuPDF |
| Frontend | React, Framer Motion, CSS Modules |
| AI advisor | Gemini Free Preview; optional Claude/Gemini BYOK via `anthropic` / `google-genai` |
| Testing | Pytest, React Scripts/Jest |
| Deployment | Azure Container Apps (production); Docker / Docker Compose (local) |

## Repository Structure

```text
careerflow/
├── .github/workflows/ci.yml              # Backend tests, frontend tests and build
├── assets/careerflow-logo.svg            # Official README logo
├── backend/
│   ├── data/
│   │   ├── all_courses.csv              # Course catalog; freshness/currency unverified
│   │   └── vacancy_data.csv             # Historical 2023 weekly demand observations
│   ├── models/                          # Serialized ML models and profiles
│   ├── migrations/                      # Versioned PostgreSQL schema changes
│   ├── services/
│   │   ├── classifier.py                # CatBoost scoring and SHAP/fallback explainability
│   │   ├── course_finder.py             # Course metadata and roadmap course lookup
│   │   ├── demand.py                    # Demand scoring
│   │   ├── llm.py                       # Claude/Gemini chat; Gemini voice transcription
│   │   ├── resume_parser.py             # Resume parser
│   │   └── skill_matcher.py             # Skill matching
│   ├── tests/                           # Backend tests
│   ├── database.py                      # Private PostgreSQL schema and persistence layer
│   ├── main.py                          # FastAPI routes
│   ├── roadmap.py                       # Roadmap generation
│   ├── schemas.py                       # Pydantic schemas
│   ├── .env.example                     # Backend configuration template, no secrets
│   ├── alembic.ini
│   ├── pyproject.toml                   # Backend dependencies
│   └── uv.lock                          # Locked backend environment
├── frontend/
│   ├── .env.example                     # Public API/Supabase build configuration
│   ├── public/
│   ├── scripts/                         # Public-page prerendering and branding tools
│   ├── package.json
│   ├── package-lock.json
│   └── src/
│       ├── components/
│       ├── context/
│       ├── pages/
│       ├── utils/api.js
│       └── i18n.js
├── ml/                                  # Research notebooks and model work
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start With Docker

Docker builds React and FastAPI into one image. First follow [development configuration](#development-configuration) and [safe local migrations](#safe-local-migrations) using a **separate, disposable development Supabase project**. Compose does not create a database. Never use production credentials for local setup or test commands.

From the repository root:

```bash
docker compose -p careerflow-local --env-file frontend/.env config --quiet
docker compose -p careerflow-local --env-file frontend/.env build app
docker compose -p careerflow-local --env-file frontend/.env up -d --no-build app
```

`--env-file frontend/.env` supplies Compose interpolation for the required `REACT_APP_SUPABASE_URL` and `REACT_APP_SUPABASE_PUBLISHABLE_KEY` **build arguments**. The separate `env_file: backend/.env` in Compose supplies backend runtime settings; it does not supply React build arguments. Rebuild after changing frontend values. Compose forces `REACT_APP_API_URL` to an empty string for same-origin requests.

Access the app at [http://localhost:8000](http://localhost:8000), [liveness](http://localhost:8000/health), [readiness](http://localhost:8000/ready) and [API docs](http://localhost:8000/docs). The Compose port mapping binds port 8000 on the host, so use a trusted development machine/network. Stop it from the repository root with:

```bash
docker compose -p careerflow-local --env-file frontend/.env down
```

For a loopback-only alternative on port 18002, stop Compose first and run its built image:

```bash
docker run --rm --name careerflow-local --env-file backend/.env --env-file frontend/.env -p 127.0.0.1:18002:8000 careerflow-local-app
```

Open [http://localhost:18002](http://localhost:18002); stop with `docker stop careerflow-local`. The explicit Compose project name makes the image name independent of the checkout directory or repository rename.

### Architecture and Runtime Notes

- **Single Container, Same-Origin:** The container uses a multi-stage build (`node:22-bookworm-slim` for React and `python:3.12-slim` for FastAPI). In production, `REACT_APP_API_URL` is intentionally empty so all API calls (`/recommend`, `/chat`, `/recommendation/...`) are made to the same origin without CORS overhead.
- **Reproducible Dependency Locking:** Frontend packages are installed strictly via `npm ci` matching `package-lock.json`. Backend dependencies are synchronized via `uv sync --locked --no-dev` using the committed `uv.lock`.
- **Durable Storage:** Supabase PostgreSQL survives container replacement. Migrations are a separate operation; no new PostgreSQL container or automatic database reset is used. Production migrations require a reviewed target, backup and release procedure.
- **Single Instance / Worker:** Guest state and basic IP rate limits are process-local. Keep 1 replica and 1 Uvicorn worker until a shared temporary-state/rate-limit store is introduced. Authenticated AI context is loaded from the owned PostgreSQL session.
- **Cloud Ingress (Azure Container Apps):** The container listens on internal port `8000` HTTP; Azure ingress handles public HTTPS for `careerflow.live`. The 9 October 2026 read-only check found single-revision mode, 0–1 replicas and ready image `careerflowacr.azurecr.io/careerflow:v1.1-73e220b`. Scale-to-zero can discard guest state. The image starts one Uvicorn worker with proxy-header support and access logs disabled; its wildcard forwarded-header trust assumes traffic arrives through the trusted ingress and needs review before exposing that server directly.
- **BYOK AI Security:** No LLM API keys are baked into the image. BYOK credentials stay in browser memory and travel only with explicit AI requests in secure headers. The optional free Gemini preview reads its separate backend-owned key from runtime environment, never from React configuration. No owner Anthropic key is required.

## Local Development

Use Python 3.11–3.13 (production/CI use 3.12), [uv](https://docs.astral.sh/uv/), and Node.js 22 with npm. Clone the current repository, or use an existing checkout:

```bash
git clone https://github.com/danialyermekov/careerflow.git
cd careerflow
```

### Development Configuration

Create `backend/.env` and `frontend/.env` from the respective [backend template](backend/.env.example) and [frontend template](frontend/.env.example) **only if those files do not already exist**. Fill them with your own development project settings; do not copy the production environment. A Supabase project is required because migrations reference `auth.users`; an empty standalone PostgreSQL database is not sufficient. Keep SSL enabled and URL-encode special characters in the database password.

| Variable | Location and purpose |
| --- | --- |
| `SUPABASE_URL` | Backend; development project's HTTPS URL |
| `DATABASE_URL` | Backend; that same project's PostgreSQL connection URL, with `sslmode=require` or stronger |
| `SUPABASE_PUBLISHABLE_KEY` | Backend; public key, or fallback from `REACT_APP_SUPABASE_PUBLISHABLE_KEY` / local frontend configuration |
| `SUPABASE_SECRET_KEY` | Optional server-only administrator key for self-service Auth identity deletion; legacy alias `SUPABASE_SERVICE_ROLE_KEY` is also accepted |
| `CORS_ORIGINS` | Backend; comma-separated origins, including `http://localhost:3000` for the separate dev server |
| `DEVELOPER_SUPABASE_USER_IDS` | Optional backend list of maintainer UUIDs for feedback origin classification |
| `REACT_APP_API_URL` | Frontend; `http://localhost:8000` for `npm start`, empty for the same-origin container build |
| `REACT_APP_SUPABASE_URL` | Frontend build; same development project's URL |
| `REACT_APP_SUPABASE_PUBLISHABLE_KEY` | Frontend build; public key only |
| `GEMINI_DEMO_ENABLED` | Backend; `false` by default, explicitly opt in for a development preview |
| `GEMINI_DEMO_API_KEY` / `API_KEY` | Backend only; dedicated preview key / legacy fallback, never BYOK credentials |
| `GEMINI_DEMO_MODEL` | Backend; `gemini-3.5-flash-lite` (default), `gemini-3.1-flash-lite` or `gemini-2.5-flash-lite` |
| `GEMINI_DEMO_FREE_MESSAGES` | Backend; default 3, allowed positive maximum 3 per preview identity |
| `GEMINI_DEMO_GLOBAL_DAILY_LIMIT` | Backend; default 100 shared preview attempts/day, not a per-user allowance |

Never put database passwords, administrator keys or AI keys in `REACT_APP_*` variables: React values are public in the build. Backend configuration loads `backend/.env` without overriding inherited environment variables; check the effective target before running migrations or starting the server. Neither `.env` file is committed.

For local OAuth, enable providers in your development Supabase project, configure their credentials there, and allow the exact callback `http://localhost:3000/auth/callback` (or `http://localhost:8000/auth/callback` for Compose). Add the matching `127.0.0.1` callback only if you use that origin. Google's Production status on the live project does not automatically configure a separate development project.

### Safe Local Migrations

Install locked dependencies first. `uv` reuses the existing project environment; manual activation or a second virtual environment is unnecessary:

```bash
cd backend
uv sync --locked --extra dev
```

Run this PowerShell example from `backend/`. Enter the project ref of your **disposable development project**, never the production ref. It checks the effective configuration (including inherited variables) against that ref before invoking Alembic, and does not print the connection string:

```powershell
$devProjectRef = Read-Host "Disposable development Supabase project ref"
@'
import re
import subprocess
import sys
from sqlalchemy.engine import make_url
from config import DATABASE_URL, SUPABASE_URL

ref = sys.argv[1].strip()
if not re.fullmatch(r"[a-z0-9]{20}", ref):
    raise SystemExit("Invalid development project ref; no migration was run.")
if SUPABASE_URL != f"https://{ref}.supabase.co":
    raise SystemExit("Supabase target mismatch; no migration was run.")
try:
    url = make_url(DATABASE_URL)
except Exception:
    raise SystemExit("Invalid database URL; no migration was run.") from None
direct = url.host == f"db.{ref}.supabase.co"
pooler = (url.host or "").endswith(".pooler.supabase.com") and url.username == f"postgres.{ref}"
if url.get_backend_name() != "postgresql" or not (direct or pooler):
    raise SystemExit("Database target mismatch; no migration was run.")
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
'@ | uv run --locked python - $devProjectRef
if ($LASTEXITCODE -ne 0) { throw "Migration failed; do not start the application." }
```

This is a development target check, not a production migration procedure. It depends on entering the correct development ref. If it fails, fix your development configuration; do not bypass it with a bare Alembic command.

### Backend

After successful development migrations, from `backend/`:

```bash
uv run --locked uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend URL:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

### Frontend

In another terminal:

```bash
cd frontend
npm ci
npm start
```

Frontend dev URL:

```text
http://localhost:3000
```

For local frontend + local backend, set `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:8000
```

Restart `npm start` after changing `.env`.

In Docker/production, the React build is served by FastAPI on port `8000`, so `REACT_APP_API_URL` is intentionally empty.

## API Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | GET | Backend health check |
| `/ready` | GET | Queries required tables and checks Auth configuration; does not compare the Alembic revision |
| `/recommend` | POST | Generates recommendation, scores, skill explanations, roadmap, courses, and session context |
| `/recommendation/history` | GET | Lists the authenticated user's private recommendation sessions |
| `/recommendation/history` | DELETE | Clears the authenticated user's private history |
| `/recommendation/{session_id}/state` | GET | Loads saved result, progress, and course filter preferences |
| `/recommendation/{session_id}/progress` | PUT | Saves roadmap checklist and drag-and-drop order |
| `/recommendation/{session_id}/course-filters` | PUT | Saves course filter preferences |
| `/parse-resume` | POST | Parses uploaded resume/CV bytes |
| `/courses/filter` | POST | Filters course recommendations |
| `/voice/transcribe` | POST | Transcribes short audio input via Gemini |
| `/ai/preview` | GET / POST | Server quota status / optional three-message Gemini preview |
| `/chat` | POST | Non-streaming BYOK AI advisor response |
| `/chat/stream` | POST | Streaming AI advisor response |
| `/account` | GET / DELETE | Verified account summary / account deletion (Auth deletion requires the server administrator key) |
| `/feedback` | POST | Submits private feedback with explicit publication consent options |
| `/api/feedback` | GET | Lists moderated, consented public feedback |
| `/api/feedback/{feedback_id}/vote` | PUT | Sets an authenticated feature-request vote |
| `/api/roadmap` | GET | Lists published feature requests tracked on the roadmap |
| `/` | GET | Serves the React build in Docker/production |

### Example Recommendation Request

```json
{
  "skills": ["python", "sql", "machine learning", "data analysis"],
  "field_of_study": "Computer Science",
  "gpa": 3.4,
  "python": 1,
  "java": 0,
  "c_cpp": 0,
  "sql": 1,
  "machine_learning": 1,
  "data_analysis": 1,
  "cloud_computing": 0,
  "cybersecurity": 0,
  "web_development": 0,
  "devops": 0,
  "networking": 0,
  "communication": 4,
  "leadership": 3,
  "problem_solving": 5,
  "teamwork": 4,
  "adaptability": 4,
  "lang": "en"
}
```

Requests to `/recommend` require either `Authorization: Bearer <Supabase access token>` or a cryptographically random, tab-scoped `X-Guest-Token` (32–128 alphanumeric characters). The frontend supplies these headers automatically. Private history and account endpoints always require authentication; session endpoints check both identity and ownership. Never supply `user_id` as authorization.

The response includes:

- `top_profession`
- `alternative_profession`
- `final_scores`
- `skill_scores`
- `classification_scores`
- `demand_scores`
- `skill_explanations`
- `roadmap_with_courses`
- `full_roadmap`
- `roadmaps_by_profession`
- `session_id`
- `context`

### Roadmap Progress Request

```json
{
  "doneSkills": ["libraries::pytorch"],
  "categoryOrder": ["programming", "libraries", "cloud"],
  "skillOrders": {
    "libraries": ["pytorch", "tensorflow"]
  },
  "selectedProfession": "Machine Learning Engineer"
}
```

### Course Filter Preferences Request

```json
{
  "filters": {
    "certificate": "with",
    "price": "paid",
    "language": "en",
    "platform": "Udemy",
    "level": "Beginner"
  }
}
```

### Resume Parser Request

The resume parser accepts raw file bytes. It does not require multipart upload.

PowerShell example:

```powershell
$path = Join-Path $PWD "resume.pdf" # Use your own local file.
Invoke-RestMethod `
  -Uri http://localhost:8000/parse-resume `
  -Method Post `
  -ContentType "application/pdf" `
  -Headers @{ "X-Filename" = [uri]::EscapeDataString((Split-Path $path -Leaf)) } `
  -InFile $path
```

Example response:

```json
{
  "filename": "resume.pdf",
  "skills": ["Python", "SQL", "MongoDB", "TensorFlow", "AWS", "Spark"],
  "role": "Data Scientist",
  "text_preview": "..."
}
```

## Testing

CI already exists in [.github/workflows/ci.yml](.github/workflows/ci.yml): backend tests (excluding the running-server recommendation tests), frontend tests and a production build run on pushes and pull requests. This workflow verifies code; it does not deploy Azure.

Backend unit/API tests, from a development environment:

```bash
cd backend
uv sync --locked --extra dev
uv run --locked --extra dev pytest --ignore=tests/test_recommendations.py
```

PostgreSQL integration tests are opt-in through `CAREERFLOW_TEST_POSTGRES`; they require an explicitly configured disposable database and must never target production. The complete suite also includes `test_recommendations.py`, which sends guest HTTP requests to a running backend at `http://localhost:8000` (overridable with `CAREERFLOW_TEST_API_URL`). Start a separate development backend before running these tests. The labeled recommendation cases are exploratory behavior checks, not a representative career-outcome benchmark.

Frontend production build:

```bash
cd frontend
npm ci
npm run build
```

Frontend tests:

```bash
cd frontend
npm test -- --watchAll=false
```

Current backend tests cover:

- recommendation response shape;
- scoring aggregation;
- all-profession score coverage;
- roadmap course output;
- chat context behavior;
- streaming chat;
- missing/unsupported credentials, safe HTTP/SSE errors, and CORS preflight;
- mocked Claude/Gemini SDK integration and credential-free recommendation persistence;
- language-aware course lookup;
- resume parser false-positive protection.

Frontend tests cover session-only key storage, saving/removal and masking, the actual assistant's no-key state, SSE errors, and credential headers on AI calls only. No real provider calls are made by these tests.

## Troubleshooting

### Docker build fails with `IncompleteRead`

This is usually a network interruption while downloading large Python wheels such as CatBoost, pandas, scikit-learn, or LightGBM.

Retry:

```bash
docker compose -p careerflow-local --env-file frontend/.env build app
docker compose -p careerflow-local --env-file frontend/.env up -d --no-build app
```

### `/recommend` returns `No module named 'catboost'`

The backend is running outside the environment where dependencies were installed.

Fix:

```powershell
cd backend
uv sync --locked --extra dev
uv run --locked uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or run Docker:

```bash
docker compose -p careerflow-local --env-file frontend/.env build app
docker compose -p careerflow-local --env-file frontend/.env up -d --no-build app
```

### Frontend cannot reach backend in local development

Check `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:8000
```

Restart `npm start`.

### Port 8000 is already in use

Stop the old container:

```bash
docker compose -p careerflow-local --env-file frontend/.env down
```

Or find the local process on Windows:

```powershell
Get-NetTCPConnection -LocalPort 8000
```

### AI chat does not answer

Choose **Try with Gemini** for the enabled production preview, subject to the three-message allowance and shared daily budget. Alternatively, save your Claude or Gemini API key in the assistant for the current loaded application session. If a provider rejects it, check the key, permissions and provider quota; the key remains in memory until you replace/remove it or reload the page. BYOK ignores server environment keys. A local preview is disabled by default. Other features continue to work without an AI key.

### Database schema and legacy SQLite

Use the [checked development migration example](#safe-local-migrations) with a disposable Supabase project. `/ready` queries required tables and checks Auth configuration, but does not compare the Alembic revision; `/health` alone does not prove database readiness. Do not delete/reset a production database. Legacy SQLite is only an archival source, not v1.1 persistence or a substitute for PostgreSQL backups. Production schema changes require a verified target, backup and reviewed release procedure.

### PDF parser misses text

The parser works best with text-based PDFs. Image-only scanned resumes need OCR, which is not included yet.

## Model Results

### Career Classification

Recorded experiment: **CatBoost (processed dataset)** in [classification_report_fixed.csv](ml/classification/results/classification_report_fixed.csv).

| Metric | Value |
| --- | ---: |
| Accuracy | 0.8440 |
| Macro F1 | 0.8094 |
| Weighted F1 | 0.8413 |

These are saved research results on the synthetic profile task, not a new audit run, end-to-end recommendation accuracy or a measure of career success. See the [classification methodology](ml/classification/README.md) and its notebooks for preparation, balancing and experiments. The CSV is the source for the values above.

### Demand Forecasting

Recorded experiment: **LightGBM with linear features** in [regression_report.csv](<ml/demand prediction/results/regression_report.csv>).

| Metric | Value |
| --- | ---: |
| MAE | 221.25 |
| WAPE | 0.1120 |
| R2 | 0.9442 |

See the [demand research methodology](<ml/demand prediction/README.md>) for temporal validation, feature engineering, errors and the two-week moving-average baseline (reported WAPE about 0.1085). The saved LightGBM WAPE above does not establish an improvement over that baseline. These are historical experiment metrics, not a fresh evaluation of the current serving process or live-market forecasting quality.

## Datasets

| Dataset | Purpose |
| --- | --- |
| `ml/classification/data/raw/career_multilabel_dataset.csv` | Initial synthetic student-profile data |
| `ml/classification/data/balanced/career_multilabel_dataset_balanced.csv` | Balanced classifier training data |
| `backend/data/vacancy_data.csv` | Historical 2023 weekly vacancy-demand observations |
| `backend/data/all_courses.csv` | Course recommendations with platform, difficulty, certificate and price metadata |

## Current Limitations

- Self-service Supabase Auth deletion requires the server-only Supabase administrator key, which was not configured in the audited Azure runtime; do not assume the full deletion flow is available.
- Guest state and basic request limits are process-local; use one worker/replica. Restart or scale-to-zero can end guest sessions before the two-hour TTL.
- Production Google/GitHub login is maintainer-confirmed; development callback allow-lists, infrastructure retention and provider-log handling need separate configuration/review.
- Course price values are numeric because the dataset does not include a currency column.
- Resume parsing does not include OCR for scanned PDFs or dedicated DOCX support.
- SHAP is attempted for the CatBoost classifier, but the code intentionally falls back to feature-importance/counterfactual explanations when SHAP is unavailable in the current runtime.
- Demand scoring fits LightGBM from packaged 2023 data and saved preprocessing/configuration; there is no live vacancy feed.
- The classifier uses synthetic labels and only seven careers. Its saved classification metrics do not validate the final weighted ranking on real student outcomes.

## Future Directions

The [public roadmap](https://careerflow.live/roadmap) is the source of truth for publicly tracked work. The following directions describe priorities and possible development, not release commitments or completed features:

- **CareerFlow v2.0:** frontend redesign and improved UX, selected by the maintainer as the next product priority; no release date is promised.
- **Recommendation quality:** improve models, ranking and validation with more representative data, including broader career coverage where evidence supports it.
- **Labor-market intelligence:** investigate fresher labor-market signals to reduce reliance on historical 2023 postings.
- **Personalized learning:** explore more adaptive roadmaps, skill-gap prioritization and better course recommendations.
- **Production reliability:** add monitoring and scalability improvements when usage justifies them, including shared temporary state and request limits before scaling beyond one replica.

## License

CareerFlow is a deployed public MVP operated as an **unincorporated project**, with research and portfolio origins. The repository currently has no project license file; public source availability does not grant an explicit open-source reuse license. No license is added or implied here. Dataset declarations in [Data and reviewer workflow](#data-and-reviewer-workflow) apply to their respective upstream sources and do not establish permission for all third-party data or assets. Clarify project and third-party rights before reuse or redistribution.

## Contact

CareerFlow is currently developed and maintained by **Danial Yermekov**. The original project authors are acknowledged in [Contributors](#contributors).

- **Email:** [contact@careerflow.live](mailto:contact@careerflow.live)
- **GitHub:** [danialyermekov](https://github.com/danialyermekov)
- **LinkedIn:** [Danial Yermekov](https://www.linkedin.com/in/danial-yermekov/)
