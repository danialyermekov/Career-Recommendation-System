# Career Recommendation System

Full-stack AI career guidance system for students. The application recommends IT career tracks, compares all supported professions, explains recommendation factors down to individual skills, builds a personalized learning roadmap with filtered course recommendations, stores user progress in SQLite, parses resumes, exports a PDF report, and includes an optional AI advisor.

## Authors

| Name | GitHub |
| --- | --- |
| Danial Yermekov | https://github.com/danialyermekov |
| Nurbek Seiilbek | https://github.com/Nurbek399 |
| Turan Tastan | https://github.com/another-restless-student23 |

## What The System Does

The system helps students choose an IT career direction by combining:

- student profile classification with a CatBoost classifier;
- skill matching against profession profiles;
- labor-market demand and trend scoring;
- weighted final scoring across all supported professions;
- skill-gap analysis;
- personalized roadmaps with course recommendations;
- advanced course filtering by certificate, price, language, platform, and level;
- skill-level explainability with SHAP or fallback feature-importance logic;
- persistent recommendation history and roadmap progress in SQLite;
- optional Gemini-powered AI advisor chat.

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
  0.40 * classifier/profile score
+ 0.40 * skill-match score
+ 0.15 * demand-trend score
+ 0.05 * demand market-share score
```

Backend services:

- `ClassifierService`: CatBoost model for profile-fit probabilities.
- `SkillMatcherService`: TF-IDF profession vectors and cosine similarity.
- `DemandService`: LightGBM-based demand and vacancy trend scoring.
- `CourseFinderService`: roadmap course lookup from the course catalog.
- `LLMService`: optional Gemini chat, streaming, and voice transcription.

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

### SQLite Persistence

The project uses local SQLite storage:

```text
backend/data/career_advisor.sqlite3
```

The database is initialized automatically on backend startup. It is ignored by git and Docker build context.

Current tables:

| Table | Purpose |
| --- | --- |
| `users` | Local/demo user record, ready for future authentication |
| `recommendation_sessions` | Recommendation payloads, profile JSON, LLM context, progress JSON |
| `specialization_scores` | Final, classifier, skill, trend, market, vacancy scores per profession |
| `skill_gaps` | Full and missing skills by profession/category |
| `roadmap_items` | Roadmap tasks, order, completion state, related courses |
| `course_progress` | Per-course progress placeholders |
| `course_filter_preferences` | Saved filter state per recommendation session |

There is no full authentication yet. Data is saved for a demo user (`demo`) so the architecture can later be extended to real user accounts.

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
- persistence through SQLite with localStorage fallback.

### AI Advisor

The AI advisor is optional and uses Gemini when `API_KEY` is provided.

Features:

- grounded responses based on the current recommendation context;
- streaming responses;
- deep/thinking mode UI;
- voice transcription endpoint;
- speech playback in supported browsers;
- prompt-injection and off-topic guardrails;
- compact translucent floating button that does not block course browsing.

Without `API_KEY`, the recommendation pipeline still works, but chat endpoints return a configuration error.

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
        |-- SQLite database -> history, scores, gaps, roadmap progress, filter preferences
        |-- PyMuPDF parser -> resume skills and role extraction
        |-- Gemini LLM service -> optional AI advisor
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
| Database | SQLite, lightweight custom data-access layer |
| ML | CatBoost, LightGBM, scikit-learn, pandas, NumPy, joblib |
| Resume parsing | PyMuPDF |
| Frontend | React, Framer Motion, CSS Modules |
| AI advisor | Google Gemini via `google-genai` |
| Testing | Pytest, React Scripts/Jest |
| Deployment | Docker, Docker Compose |

## Repository Structure

```text
Career-Recommendation-System/
├── backend/
│   ├── data/
│   │   ├── all_courses.csv              # Course catalog with prices
│   │   ├── vacancy_data.csv             # Demand dataset
│   │   └── career_advisor.sqlite3       # Local runtime DB, gitignored
│   ├── models/                          # Serialized ML models and profiles
│   ├── services/
│   │   ├── classifier.py                # CatBoost scoring and SHAP/fallback explainability
│   │   ├── course_finder.py             # Course metadata and roadmap course lookup
│   │   ├── demand.py                    # Demand scoring
│   │   ├── llm.py                       # Gemini chat and voice transcription
│   │   ├── resume_parser.py             # Resume parser
│   │   └── skill_matcher.py             # Skill matching
│   ├── tests/                           # Backend tests
│   ├── database.py                      # SQLite schema and persistence layer
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

Docker is the recommended way to run the whole app because the ML dependencies are heavy.

From the project root:

```bash
docker compose up --build
```

Open the app:

```text
http://localhost:8000
```

Open API docs:

```text
http://localhost:8000/docs
```

Optional Gemini AI advisor:

```bash
API_KEY=your_google_gemini_api_key docker compose up --build
```

Windows PowerShell:

```powershell
$env:API_KEY="your_google_gemini_api_key"
docker compose up --build
```

Or create a root `.env` file:

```env
API_KEY=your_google_gemini_api_key
```

Then run:

```bash
docker compose up --build
```

Stop containers:

```bash
docker compose down
```

If the build fails with `IncompleteRead` during `pip install`, retry the build. The Dockerfile uses pip retries and longer timeouts, but large ML wheels can still fail on unstable network connections:

```bash
docker compose build --no-cache
docker compose up
```

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
| `/recommendation/history` | GET | Lists saved demo-user recommendation sessions |
| `/recommendation/history` | DELETE | Clears saved demo-user history |
| `/recommendation/{session_id}/state` | GET | Loads saved result, progress, and course filter preferences |
| `/recommendation/{session_id}/progress` | PUT | Saves roadmap checklist and drag-and-drop order |
| `/recommendation/{session_id}/course-filters` | PUT | Saves course filter preferences |
| `/parse-resume` | POST | Parses uploaded resume/CV bytes |
| `/voice/transcribe` | POST | Transcribes short audio input via Gemini |
| `/chat` | POST | Non-streaming AI advisor response |
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
  },
  "user_id": "demo"
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
pip install -e ".[dev]"
python -m pytest
```

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
- language-aware course lookup;
- resume parser false-positive protection.

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
docker compose up --build
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

The AI advisor requires:

```env
API_KEY=your_google_gemini_api_key
```

Recommendation generation, course filters, roadmap, and charts work without this key.

### SQLite database should be reset

Stop the backend and delete:

```text
backend/data/career_advisor.sqlite3
```

The schema will be recreated on the next backend startup.

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

- Authentication is not implemented yet; persistence currently uses a demo user.
- SQLite is local and intended for demo/development deployment.
- Course price values are numeric because the dataset does not include a currency column.
- Resume parsing does not include OCR for scanned PDFs.
- SHAP is attempted for the CatBoost classifier, but the code intentionally falls back to feature-importance/counterfactual explanations when SHAP is unavailable in the current runtime.
- Demand forecasting uses packaged data and model artifacts, not a live vacancy feed.

## Future Improvements

- Add authentication and per-user profiles.
- Add migrations with Alembic if the schema grows.
- Add OCR for scanned resumes.
- Add course currency/source normalization.
- Connect demand forecasting to live vacancy data.
- Add CI for backend tests and frontend build.
- Add model registry and dataset versioning with MLflow or DVC.

## License

This repository is intended for academic and portfolio demonstration purposes. Add an explicit license before public reuse or distribution.
