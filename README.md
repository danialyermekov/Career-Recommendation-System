<p align="center">
  <img src="docs/assets/careerflow-logo.svg" alt="CareerFlow — wave symbol and wordmark" width="360">
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

CareerFlow helps IT students choose a career direction. The application ranks supported IT careers using profile classification, skill similarity and historical market signals, explains the ranking, and builds a rule-based learning roadmap with courses. The core recommendations and roadmap run through the ML pipeline without an AI API key. The optional AI Advisor offers a three-message Gemini Free Preview when enabled by the maintainer, plus Claude/Gemini bring-your-own-key (BYOK) chat.

**Status:** v1.1 public MVP, actively developed and deployed on Azure Container Apps. The project started in 2026, with the public MVP launch on 7 October 2026. Google/GitHub OAuth and private history use Supabase Auth and PostgreSQL; guest mode provides temporary recommendations without signing in.

**Data scope:** Market signals come from historical 2023 job postings, not a live vacancy feed. The profile classifier is trained on synthetic educational data; scores are exploratory guidance, not predictions of career success. Dataset provenance and methodology are documented below.

**Repository:** [danialyermekov/Career-Recommendation-System](https://github.com/danialyermekov/careerflow).

For the guided demo, Gemini preview configuration, quota limits and manual release gates, see [guided-demo-ai-preview.md](docs/guided-demo-ai-preview.md).
For v1.1 configuration, safe migration, release gates and rollback, see [deployment-v1.1.md](docs/deployment-v1.1.md).
For public pages, consent-based feedback, voting, exact moderation commands and verified changelog sources, see [public-product-pages.md](docs/public-product-pages.md).
For prerendered public HTML, technical SEO and owner steps for DNS verification/indexing, see [google-search-console.md](docs/google-search-console.md).

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

Use **Use demo profile** on the landing page or profile form to load an editable Computer Science student with GPA 3.2, Python/SQL/Pandas/Git/Excel and moderate self-ratings. Submit it through the normal recommendation API. Demo labels are browser-tab metadata; no history is fabricated. GPA is the only field the form requires users to enter; other API fields are populated with visible defaults.

Dataset provenance (source pages supplied by the project owner; upstream metadata checked on 2026-10-07):

| Source | Local use and derived artifacts | Upstream declared license |
|---|---|---|
| Luke Barousse’s [Data Jobs on Hugging Face](https://huggingface.co/datasets/lukebarousse/data_jobs) | Historical 2023 job postings. Demand and skill notebooks read `data/raw/data_jobs_norm.csv`; demand aggregation produces `ml/demand prediction/data/aggregated/weekly_vacancy_counts.csv`, identical to `backend/data/vacancy_data.csv`. Skill notebooks derive the TF-IDF vectorizer and profession vectors/profiles used for skill matching and roadmaps. | Apache 2.0 (`apache-2.0`), verified in the [upstream dataset card](https://huggingface.co/datasets/lukebarousse/data_jobs/raw/main/README.md). |
| hafsaatm’s [Career Path Recommendation on Kaggle](https://www.kaggle.com/datasets/hafsaatm/career-path-recommendation) | Synthetic profiles in `ml/classification/data/raw/career_multilabel_dataset.csv`, followed by local balancing, feature engineering and classifier training. The file has education/background fields, technical indicators, soft skills and three recommended-job labels; the current classifier targets `recommended_job_1`. | The [Kaggle metadata endpoint](https://www.kaggle.com/api/v1/datasets/view/hafsaatm/career-path-recommendation) reports `licenseName: "Unknown"`. License terms remain unverified; clarify them before broader reuse. |

The upstream Hugging Face card describes postings collected through Google from multiple sources; this project does not claim direct or complete coverage of LinkedIn, Glassdoor or any other platform. The Kaggle description explicitly identifies its profiles as synthetic educational/research data, not observed career outcomes. Upstream download revisions and checksums were not recorded, and the intermediate `data_jobs_norm.csv` files referenced by the notebooks are not checked in, so exact reproduction of the original imports remains unverified. These dataset declarations do not assign a license to CareerFlow itself.

The checked-in demand file `backend/data/vacancy_data.csv` contains 371 weekly career observations dated 2023-01-01 through 2023-12-31. The service maps the current calendar date to a 2023 week; these estimates are historical and do not represent live job availability. Trend is predicted volume divided by each career's historical weekly peak; market share is predicted volume divided by the total for the supported tracks, before ranking normalization.

The raw profile file contains 2,000 rows. The training preparation adds synthetic examples for missing Data Analyst and Data Engineer classes. The serving preprocessor uses study field, GPA, technical indicators, soft-skill ratings and derived features; it does not use age or gender. Synthetic-label classification is exploratory guidance and does not establish real career outcomes.

The course catalog contains 41,690 rows in `backend/data/all_courses.csv`, not a verified count of distinct, currently available courses. Price, availability and rating freshness are unverified. The public hero does not advertise this count. The roadmap uses normalized skill gaps, category limits and framework/language compatibility rules; progress counts user-marked learning steps.

Navigation uses URL hashes (`#profile`, `#results/<session_id>`) without adding a router. A saved result can reload through the existing state API. Supabase Auth provides Google/GitHub sign-in. Each saved result belongs to its verified user; guest results require a separate random credential and expire after two hours or a server restart. Guest history is never imported into an account automatically. Dataset licensing and the documented infrastructure/privacy review items remain separate release concerns.

Backend services:

- `ClassifierService`: CatBoost model for profile-fit probabilities.
- `SkillMatcherService`: TF-IDF profession vectors and cosine similarity.
- `DemandService`: LightGBM-based demand and vacancy trend scoring.
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

The project uses the existing Supabase PostgreSQL database through SQLAlchemy Core, psycopg 3 and Alembic. Tables live in the private `careerflow` schema. The previous SQLite file is retained only for a read-only archival migration:

```text
backend/data/career_advisor.sqlite3
```

Schema changes run explicitly with `uv run alembic upgrade head`; startup does not create or reset tables. UUID account IDs reference Supabase Auth users with cascading deletion. Application tables have RLS enabled and no browser-role permissions. The legacy SQLite file remains ignored by Git and Docker context; it is not imported into new accounts.

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

Google/GitHub OAuth uses Supabase Auth and PKCE. The backend verifies Bearer tokens through Supabase Auth and scopes every private session operation to the verified user. Feedback defaults to private and pending; only explicitly consented, approved reviews/features with maintainer-classified origin have a public listing. Feature votes require authentication. See [deployment and migration instructions](docs/deployment-v1.1.md) and the [moderation workflow](docs/public-product-pages.md).

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

Choose **Try with Gemini** to ask up to three questions about the current recommendation without supplying an API key. The preview requires consent and maintainer activation, uses a server-managed Gemini key, and enforces PostgreSQL-backed quotas and daily cost limits. Availability depends on the remaining quota and provider status; core recommendations continue to work when the preview is unavailable. See [preview configuration and limits](docs/guided-demo-ai-preview.md).

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

Only `/chat`, `/chat/stream`, and `/voice/transcribe` receive `X-LLM-Provider` (`anthropic` or `gemini`) and `X-LLM-API-Key` headers. They are never URL/query/body fields. FastAPI validates headers without echoing their values, then passes them to the LLM service for that request. A small provider registry dispatches to per-call SDK clients, closed after completion; no credential-bearing backend singleton, session, cache, file, or database record is created. Environment keys (`API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`) are not application fallbacks.

The BYOK generation request checks the key; selecting **Use key** makes no provider call. Missing BYOK keys return HTTP 400, rejected credentials HTTP 401, rate limits HTTP 429, and unavailable providers HTTP 503. After an SSE stream starts, failures are safe JSON `type: "error"` events followed by one `[DONE]`. Invalid keys remain only in memory for the user to correct or remove. Removing/changing credentials aborts in-flight frontend AI requests.

Claude uses Anthropic Messages with `claude-sonnet-5-5`; deep mode uses adaptive thinking. Gemini retains the existing `google-genai` chat models and thought/text stream format. Audio transcription remains Gemini-only; Claude users can type or use browser speech playback. To add a provider, implement the same three provider methods, register it in `backend/services/llm.py`, and add its public metadata to `frontend/src/utils/llmSettings.js`.

Security limits: in-memory credentials do **not** protect against XSS or malicious browser extensions. Use HTTPS outside localhost. The key necessarily passes through CareerFlow's backend and the selected provider; provider-side processing and retention follow that provider's policies. Application code does not log credentials or raw provider exceptions, and suppresses SDK request/exception debug logging. Keep reverse proxies, APM, analytics, and transport debug logging from recording `X-LLM-API-Key`, `x-api-key`, or `x-goog-api-key`. CORS already permits the custom headers; it is not authentication. Supabase authentication and session ownership checks protect private results; basic request limits are process-local and require shared or edge limits before scaling.

### Resume / CV Parser

The backend can parse raw file bytes for:

- text-based PDF files;
- TXT files;
- document-like files with extractable text.

It extracts:

- detected skills;
- possible current role;
- text preview.

Scanned image-only resumes require OCR and are not fully supported yet.

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
Career-Recommendation-System/
├── backend/
│   ├── data/
│   │   ├── all_courses.csv              # Course catalog with prices
│   │   ├── vacancy_data.csv             # Demand dataset
│   │   └── career_advisor.sqlite3       # Legacy archive source, gitignored
│   ├── models/                          # Serialized ML models and profiles
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
│   └── pyproject.toml                   # Backend dependencies
├── frontend/
│   ├── public/
│   ├── package.json
│   └── src/
│       ├── components/
│       ├── context/
│       ├── pages/
│       ├── utils/api.js
│       └── i18n.js
├── ml/                                  # Research notebooks and model work
├── scripts/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start With Docker

Configure both `.env` files from their examples first. React Supabase values are build-time arguments, not runtime-only settings. Apply Alembic migrations before starting the app. For production updates, preserve the previous image and database backups and follow the [deployment and rollback checks](docs/deployment-v1.1.md).

Docker is the recommended way to run the whole app because the ML dependencies are heavy and pre-compiled in a two-stage reproducible build.

### Production Container Build & Run

1. Build the production image:

```bash
docker compose --env-file frontend/.env build app
docker compose --env-file frontend/.env run --rm --no-deps app alembic upgrade head
```

2. Run the single container (example using local port `18002` or `8000`):

```bash
docker run --rm --name careerflow-local --env-file backend/.env --env-file frontend/.env -p 127.0.0.1:18002:8000 career-recommendation-system-app
```

3. Access the endpoints:
- Application UI: [http://localhost:18002/](http://localhost:18002/)
- Healthcheck: [http://localhost:18002/health](http://localhost:18002/health)
- API documentation: [http://localhost:18002/docs](http://localhost:18002/docs)

4. Stop the container:

```bash
docker stop careerflow-local
```

### Quick Start With Docker Compose

Alternatively, use Docker Compose to run on port `8000`:

```bash
docker compose --env-file frontend/.env build app
docker compose --env-file frontend/.env run --rm --no-deps app alembic upgrade head
docker compose --env-file frontend/.env up -d --no-build app
```

Access the app at [http://localhost:8000](http://localhost:8000) and API docs at [http://localhost:8000/docs](http://localhost:8000/docs). Stop containers with:

```bash
docker compose down
```

### Architecture and Runtime Notes

- **Single Container, Same-Origin:** The container uses a multi-stage build (`node:22-bookworm-slim` for React and `python:3.12-slim` for FastAPI). In production, `REACT_APP_API_URL` is intentionally empty so all API calls (`/recommend`, `/chat`, `/recommendation/...`) are made to the same origin without CORS overhead.
- **Reproducible Dependency Locking:** Frontend packages are installed strictly via `npm ci` matching `package-lock.json`. Backend dependencies are synchronized via `uv sync --locked --no-dev` using the committed `uv.lock`.
- **Durable Storage:** Supabase PostgreSQL survives container replacement. Apply Alembic migrations before promotion; no new PostgreSQL container or automatic database reset is used.
- **Single Instance / Worker:** Guest state and basic IP rate limits are process-local. Keep 1 replica and 1 Uvicorn worker until a shared temporary-state/rate-limit store is introduced. Authenticated AI context is loaded from the owned PostgreSQL session.
- **Cloud Ingress (Azure Container Apps):** The container listens on internal port `8000` HTTP. In production deployment, external HTTPS termination and TLS certificates are handled by the cloud ingress controller.
- **BYOK AI Security:** No LLM API keys are baked into the image. BYOK credentials stay in browser memory and travel only with explicit AI requests in secure headers. The optional free Gemini preview reads its separate backend-owned key from runtime environment, never from React configuration. No owner Anthropic key is required.

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

macOS / Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
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
npm install
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
| `/recommend` | POST | Generates recommendation, scores, skill explanations, roadmap, courses, and session context |
| `/recommendation/history` | GET | Lists the authenticated user's private recommendation sessions |
| `/recommendation/history` | DELETE | Clears the authenticated user's private history |
| `/recommendation/{session_id}/state` | GET | Loads saved result, progress, and course filter preferences |
| `/recommendation/{session_id}/progress` | PUT | Saves roadmap checklist and drag-and-drop order |
| `/recommendation/{session_id}/course-filters` | PUT | Saves course filter preferences |
| `/parse-resume` | POST | Parses uploaded resume/CV bytes |
| `/voice/transcribe` | POST | Transcribes short audio input via Gemini |
| `/ai/preview` | GET / POST | Server quota status / optional three-message Gemini preview |
| `/chat` | POST | Non-streaming BYOK AI advisor response |
| `/chat/stream` | POST | Streaming AI advisor response |
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
$path = "C:\Users\Администратор\Downloads\resume.pdf"
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

Backend tests:

```bash
cd backend
uv run --extra dev pytest tests/test_api.py tests/test_course_finder.py tests/test_llm.py
```

The complete suite (`uv run --extra dev pytest`) also includes `test_recommendations.py`, which sends HTTP requests to a running backend at `http://localhost:8000`. Run that server with a disposable database when validating recommendation persistence.

Frontend production build:

```bash
cd frontend
npm install
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
docker compose build --no-cache
docker compose up
```

### `/recommend` returns `No module named 'catboost'`

The backend is running outside the environment where dependencies were installed.

Fix:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or run Docker:

```bash
docker compose --env-file frontend/.env build app
docker compose --env-file frontend/.env run --rm --no-deps app alembic upgrade head
docker compose --env-file frontend/.env up -d --no-build app
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
docker compose down
```

Or find the local process on Windows:

```powershell
Get-NetTCPConnection -LocalPort 8000
```

### AI chat does not answer

Open the AI assistant panel and save your Claude or Gemini API key for the current tab session. If a provider rejects it, check the key, permissions, and provider quota; the key is kept until you replace or remove it. BYOK ignores server environment keys. Alternatively, choose **Try with Gemini** for the limited server-managed preview when enabled. Other features continue to work without a key.

### Database schema and legacy SQLite

Apply versioned schema changes with `uv run alembic upgrade head`. Do not delete/reset a production database. Legacy SQLite is retained for private archival backup and rollback; shared anonymous data is never reassigned to newly registered users. See [deployment-v1.1.md](docs/deployment-v1.1.md) for backup, migration, rollback and account-deletion operations.

### PDF parser misses text

The parser works best with text-based PDFs. Image-only scanned resumes need OCR, which is not included yet.

## Model Results

### Career Classification

Best model: CatBoost on processed dataset.

| Metric | Value |
| --- | ---: |
| Accuracy | 0.8440 |
| Macro F1 | 0.8094 |
| Weighted F1 | 0.8413 |

### Demand Forecasting

Best representative model: LightGBM with selected features.

| Metric | Value |
| --- | ---: |
| MAE | 221.25 |
| WAPE | 0.1120 |
| R2 | 0.9442 |

## Datasets

| Dataset | Purpose |
| --- | --- |
| `ml/classification/data/raw/career_multilabel_dataset.csv` | Initial student-profile data |
| `ml/classification/data/balanced/career_multilabel_dataset_balanced.csv` | Balanced classifier training data |
| `backend/data/vacancy_data.csv` | Weekly vacancy-demand forecasting |
| `backend/data/all_courses.csv` | Course recommendations with platform, difficulty, certificate and price metadata |

## Current Limitations

- Self-service Supabase Auth deletion requires the server-only Supabase administrator key.
- Guest state and abuse limits are process-local; use one worker/replica.
- External OAuth redirects, Google Testing allow-list and infrastructure retention settings require owner review.
- Course price values are numeric because the dataset does not include a currency column.
- Resume parsing does not include OCR for scanned PDFs.
- SHAP is attempted for the CatBoost classifier, but the code intentionally falls back to feature-importance/counterfactual explanations when SHAP is unavailable in the current runtime.
- Demand forecasting uses packaged data and model artifacts, not a live vacancy feed.

## Future Improvements

- Add OCR for scanned resumes.
- Add course currency/source normalization.
- Connect demand forecasting to live vacancy data.
- Add CI for backend tests and frontend build.
- Add model registry and dataset versioning with MLflow or DVC.

## License

This repository is intended for academic and portfolio demonstration purposes. Add an explicit license before public reuse or distribution.

## Contact

CareerFlow is currently developed and maintained by **Danial Yermekov**. The original project authors are acknowledged in [Contributors](#contributors).

- **Email:** [contact@careerflow.live](mailto:contact@careerflow.live)
- **GitHub:** [danialyermekov](https://github.com/danialyermekov)
- **LinkedIn:** [Danial Yermekov](https://www.linkedin.com/in/danial-yermekov/)
