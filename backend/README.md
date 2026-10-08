# CareerFlow API

A backend for ranking supported IT career directions from a student's profile, skills and historical market signals. Roadmaps use deterministic skill-gap rules; an optional LLM advisor helps discuss the results.

---

##  Key Features

*   **Intelligent Career Matching**: Uses a pre-trained **CatBoost** classifier to predict the best-fit profession based on the user's background, GPA, and domain knowledge (Python, C++, SQL, Machine Learning, etc.).
*   **Skill Assessment**: Ranks and matches users' skills against standard industry profiles.
*   **Market Demand Evaluation**: Uses **LightGBM** estimates from the checked-in 2023 weekly vacancy snapshot. These are historical market signals, not live job counts or current hiring growth.
*   **Personalized Roadmaps & Courses**: Automatically generates tailored learning roadmaps and curates course recommendations to cover skill gaps.
*   **LLM-Powered Interactive Chat**: Supports **Anthropic Claude and Google Gemini** with a user-provided session key to simulate an expert AI career advisor that provides natural-language guidance and answers questions in real-time, backed by the generated recommendation context.
*   **FastAPI Backend**: Built asynchronously on FastAPI, ensuring fast, robust, and scalable API endpoints.

---

##  Project Structure

```text
diploma/
├── data/                     # Datasets (courses_combined.csv # Combined of 4 courses dataset (only russian and english languages are left), 
vacancy_data.csv # weekly aggergation of data_jobs dataset)
├── models/                   # Serialized ML models, vectorizers, and JSON data
│   ├── classifier_model.joblib
│   ├── demand_model_params.json
│   ├── tfidf_vectorizer.joblib
│   └── ...                   # Preprocessors, taxonomy data, etc.
├── services/                 # Core domain services
│   ├── classifier.py         # Classifier ML model wrapper (CatBoost)
│   ├── course_finder.py      # Roadmap and course extraction logic
│   ├── demand.py             # Market demand computation (LightGBM)
│   ├── llm.py                # LLM context builder and chat handler (Claude/Gemini)
│   └── skill_matcher.py      # Skill comparison and scoring logic
├── tests/                    # Pytest test cases validating API limits & logic
│   ├── test_api.py
│   └── test_recommendations.py
├── utils/                    # Utility scripts (type checking, conversions)
├── config.py                 # Centralized configuration (Paths, Constants)
├── features.py               # Feature engineering logic for ML inference
├── main.py                   # FastAPI Application Entry Point
├── pyproject.toml            # Project dependencies and configurations
├── roadmap.py                # Roadmap generation algorithms
├── schemas.py                # Pydantic data models for API requests/responses
└── top_profession.py         # Final aggregation and weighting algorithm
```

---

##  Prerequisites & Dependencies

The project requires **Python 3.10+** (specifically tested with python >= 3.14 specified in `pyproject.toml`).

**Core Libraries:**
*   [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/) for building the REST API
*   [CatBoost](https://catboost.ai/) & [LightGBM](https://lightgbm.readthedocs.io/) for Machine Learning predictive modeling
*   [Scikit-learn](https://scikit-learn.org/) for NLP (TF-IDF) and preprocessing pipelines
*   [Google Gen AI SDK](https://github.com/googleapis/python-genai) and [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) for the optional LLM integrations
*   [Pandas](https://pandas.pydata.org/) for data manipulation and alignment

---

##  Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd diploma
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   Install required packages via standard tools or from `pyproject.toml`:
   ```bash
   pip install .
   ```

4. **Optional AI assistant:**
   No owner Anthropic key is required. BYOK ignores environment credentials; the separate optional Gemini preview uses only GEMINI_DEMO_API_KEY at backend runtime. See [preview configuration and quotas](../docs/guided-demo-ai-preview.md). In the frontend AI assistant panel, select Claude or Gemini, enter a key, and select **Use key** for the currently loaded page. **Remove key** disables AI immediately. The frontend keeps secrets only in memory until a full refresh or page close, never in browser storage, and sends `X-LLM-Provider` and `X-LLM-API-Key` exclusively to `/chat`, `/chat/stream`, and `/voice/transcribe`. The backend uses short-lived SDK clients and stores no keys in SQLite, session state, files, or globals. Voice transcription is Gemini-only. Missing credentials return 400; provider errors are sanitized, including SSE failures. See the root [README](../README.md#ai-advisor) for the full flow and security limits, including XSS and HTTPS.

---

##  Running the Application

**Start the Development Server:**
To run the FastAPI server, use Uvicorn running `main:app`.
```bash
uvicorn main:app --reload --port 8000
```
The interactive Swagger API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

**Running Tests:**
To ensure your endpoints and recommendation logic are working correctly, run the built-in Pytest suite:
```bash
pytest tests/ -v
```

---

##  API Endpoints

### `GET /health`
*   **Description**: Basic health check to confirm the service is live.
*   **Response**: `{"status": "ok"}`

### `POST /recommend`
*   **Description**: Evaluates a `StudentProfile` payload and returns the recommended IT profession, skill gap roadmap, course recommendations, and initiates an LLM session context.
*   **Payload Example**: Defines skills (e.g. `['Python', 'SQL']`), academic details (GPA, Field of Study), and quantified proficiencies across various IT branches.
*   **Response**: A detailed JSON object including `top_profession`, `final_scores`, skill analytics, course roadmaps, and a generated `session_id`.

### `POST /chat`
*   **Description**: Engage with the AI career advisor using a previously generated `session_id`. The advisor provides natural-language guidance informed by the student's exact learning gaps and recommended courses.
*   **Payload**: Requires the provider/key headers above, `session_id`, `history` (array of prior message objects), and the user's current `message`.

---

##  Under the Hood (Machine Learning)

*   **Classifier Service**: A trained CatBoost multi-class categorization model predicts the likelihood of various target IT professions (e.g., Data Engineer, Software Engineer, Cloud Analyst). It leverages a dedicated preprocessor to scale inputs like GPA, proficiency indicators, and categorical academic backgrounds.
*   **Demand Service**: Evaluates how hot the job market is for specific roles. Uses historical scrape data aligned with recent trends, modeled via a LightGBM regressor using Lasso-selected features.
*   **Skill Matcher & Course Finder**: Evaluates technical and soft-skill overlaps to compute a precise gap. Suggests course links specifically targeted at the missing skills for the optimal role.
