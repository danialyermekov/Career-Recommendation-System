# CareerFlow API

A backend for ranking supported IT career directions from a student's profile, skills and historical market signals. Roadmaps use deterministic skill-gap rules; an optional LLM advisor helps discuss the results.

---

##  Key Features

*   **Career Ranking**: Combines a pre-trained **CatBoost** profile classifier, TF-IDF skill similarity and historical demand signals across seven supported professions. The final match score is not a probability of career success.
*   **Skill Assessment**: Compares normalized user skills with profession profiles derived from the project's historical job-posting data.
*   **Market Demand Evaluation**: Uses **LightGBM** estimates from the checked-in 2023 weekly vacancy snapshot. These are historical market signals, not live job counts or current hiring growth.
*   **Personalized Roadmaps & Courses**: Automatically generates tailored learning roadmaps and curates course recommendations to cover skill gaps.
*   **Optional AI Advisor**: Production offers a three-message Gemini Free Preview; **Anthropic Claude and Google Gemini** BYOK chat use a user-provided key held in browser memory. Core recommendations require no AI key.
*   **Private Accounts and Guest Mode**: Supabase Auth verifies Google/GitHub OAuth identities; Supabase PostgreSQL stores private history and roadmap progress. Guest and Guided Demo results use temporary process-local state.
*   **Public Feedback**: Supports private submissions, consent-based moderation, published feature requests and authenticated voting.
*   **FastAPI Backend**: Provides validated API routes, health/readiness checks and same-origin React serving. Guest state and basic request limits currently require a single worker/replica.

---

##  Project Structure

```text
backend/
├── data/
│   ├── all_courses.csv       # Course catalog; freshness and currency unverified
│   └── vacancy_data.csv      # Historical 2023 weekly vacancy observations
├── models/                   # Serialized ML models, vectorizers, and JSON data
│   ├── classifier_model.joblib
│   ├── demand_model_params.json
│   ├── tfidf_vectorizer.joblib
│   └── ...                   # Preprocessors, taxonomy data, etc.
├── services/                 # Core domain services
│   ├── classifier.py         # Classifier ML model wrapper (CatBoost)
│   ├── course_finder.py      # Roadmap and course extraction logic
│   ├── demand.py             # Market demand computation (LightGBM)
│   ├── ai_trial.py           # Server-managed Gemini preview and PostgreSQL quotas
│   ├── llm.py                # LLM context builder and chat handler (Claude/Gemini)
│   ├── resume_parser.py      # Text-based PDF and TXT skill extraction
│   └── skill_matcher.py      # Skill comparison and scoring logic
├── tests/                    # Pytest test cases validating API limits & logic
│   ├── test_api.py
│   └── test_recommendations.py
├── utils/                    # Utility scripts (type checking, conversions)
├── config.py                 # Centralized configuration (Paths, Constants)
├── auth.py                   # Supabase token verification
├── database.py               # Private PostgreSQL schema and persistence
├── guest_sessions.py         # Temporary guest recommendations
├── migrations/               # Alembic schema revisions
├── alembic.ini
├── .env.example              # Backend configuration template
├── features.py               # Feature engineering logic for ML inference
├── main.py                   # FastAPI Application Entry Point
├── pyproject.toml            # Project dependencies and configurations
├── uv.lock                   # Locked backend dependencies
├── roadmap.py                # Roadmap generation algorithms
├── schemas.py                # Pydantic data models for API requests/responses
└── top_profession.py         # Final aggregation and weighting algorithm
```

---

##  Prerequisites & Dependencies

The backend requires **Python >=3.11,<3.14**, as specified in [pyproject.toml](pyproject.toml). Production and CI use Python 3.12. Use `uv` with the committed [uv.lock](uv.lock); the separate research modules have their own Python requirements.

**Core Libraries:**
*   [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/) for building the REST API
*   [CatBoost](https://catboost.ai/) & [LightGBM](https://lightgbm.readthedocs.io/) for Machine Learning predictive modeling
*   [Scikit-learn](https://scikit-learn.org/) for NLP (TF-IDF) and preprocessing pipelines
*   [Google Gen AI SDK](https://github.com/googleapis/python-genai) and [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) for the optional LLM integrations
*   [Pandas](https://pandas.pydata.org/) for data manipulation and alignment
*   SQLAlchemy Core, psycopg 3 and Alembic for Supabase PostgreSQL persistence and migrations

---

##  Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/danialyermekov/careerflow.git
   cd careerflow/backend
   ```

2. **Install locked dependencies:**
   ```bash
   uv sync --locked --extra dev
   ```
   `uv` reuses the project environment; manual activation is unnecessary.

3. **Configure a disposable development Supabase project and migrate it:**
   Follow [development configuration](../README.md#development-configuration) and the [checked migration example](../README.md#safe-local-migrations) in the root README. Create `.env` from [.env.example](.env.example) only if it does not already exist. `DATABASE_URL`, `SUPABASE_URL` and the public Auth key must refer to your development project, never production. Migrations reference `auth.users`; a bare PostgreSQL database is not sufficient. Startup does not create tables.

4. **Optional AI assistant:**
   Gemini Free Preview is enabled on production with up to three messages per preview identity; local installations default to disabled. Its server key is `GEMINI_DEMO_API_KEY`, with `API_KEY` as a legacy fallback **for Preview only**. BYOK never falls back to server keys, and no owner Anthropic key is required.

   In the frontend AI assistant panel, select Claude or Gemini, enter a key, and select **Use key** for the currently loaded page. **Remove key** disables BYOK immediately. The frontend keeps credentials only in memory until a full refresh or page close, and sends `X-LLM-Provider` and `X-LLM-API-Key` exclusively to `/chat`, `/chat/stream`, and `/voice/transcribe`. The backend uses short-lived SDK clients and does not persist BYOK keys. Voice transcription is Gemini-only. Missing BYOK credentials return 400; BYOK provider errors are sanitized, including SSE failures. Preview exception text is currently logged separately and still needs a privacy review. See [AI Advisor](../README.md#ai-advisor) for the full flow, quotas and security limits.

---

##  Running the Application

**Start the Development Server:**
To run the FastAPI server, use Uvicorn running `main:app`.
```bash
uv run --locked uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
The interactive Swagger API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

**Running Tests:**
From `backend/`, run unit/API tests without the separate running-server recommendation tests:
```bash
uv run --locked --extra dev pytest --ignore=tests/test_recommendations.py
```

`tests/test_recommendations.py` sends guest requests to a running development backend; `CAREERFLOW_TEST_API_URL` defaults to `http://localhost:8000`. PostgreSQL integration tests require explicit `CAREERFLOW_TEST_POSTGRES=1` and a disposable database. Never run these against production. See [Testing](../README.md#testing) for frontend and CI checks.

---

##  API Endpoints

### `GET /health`
*   **Description**: Basic health check to confirm the service is live.
*   **Response**: `{"status": "ok"}`

### `GET /ready`
*   **Description**: Queries required PostgreSQL tables and checks Supabase Auth configuration. It does not compare the Alembic revision.
*   **Response**: `{"status": "ready"}` when these checks succeed.

### `POST /recommend`
*   **Description**: Evaluates a `StudentProfile` payload and returns the recommended IT profession, skill gap roadmap, course recommendations, and initiates an LLM session context.
*   **Payload Example**: Defines skills (e.g. `['Python', 'SQL']`), academic details (GPA, Field of Study), and quantified proficiencies across various IT branches.
*   **Response**: A detailed JSON object including `top_profession`, `final_scores`, skill analytics, course roadmaps, and a generated `session_id`.
*   **Identity**: Requires a verified `Authorization: Bearer` token or a random `X-Guest-Token`; session operations enforce ownership. Private history requires authentication.

### `POST /chat`
*   **Description**: Engage with the AI career advisor using a previously generated `session_id`. The advisor provides natural-language guidance informed by the student's exact learning gaps and recommended courses.
*   **Payload**: Requires the provider/key headers above, `session_id`, `history` (array of prior message objects), and the user's current `message`.

### `GET /ai/preview` and `POST /ai/preview`
*   **Description**: Reads the server-managed Gemini allowance or submits a consented preview question about an owned recommendation. Guest and account allowances are tracked separately in PostgreSQL.

See the root [API endpoint table](../README.md#api-endpoints) for streaming, resume parsing, courses, history, progress, accounts, public feedback and roadmap routes.

---

##  Under the Hood (Machine Learning)

*   **Classifier Service**: A saved CatBoost model produces profile-fit scores for the [seven supported tracks](../README.md#supported-career-tracks), using study field, GPA, technical indicators, soft-skill ratings and derived features. Synthetic training labels do not validate real career outcomes.
*   **Demand Service**: Fits LightGBM at service initialization using bundled 2023 vacancy observations, saved preprocessing and selected features. Calendar dates are mapped to 2023 weeks and scores are cached; this is not a live market feed.
*   **Skill Matcher & Course Finder**: Uses TF-IDF/cosine skill similarity and deterministic gap/roadmap rules, then looks up courses in `data/all_courses.csv`. Language and some price handling are heuristic; price, availability and rating freshness are unverified.

The exact weighting formula, dataset provenance, saved experiment metrics and limitations are documented in the root [README](../README.md#recommendation-pipeline).
