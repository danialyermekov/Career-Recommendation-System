from pathlib import Path
import os
from dotenv import load_dotenv, dotenv_values

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env', override=False)
SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
# Local React configuration contains public values only; Compose passes this explicitly.
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY') or os.getenv('REACT_APP_SUPABASE_PUBLISHABLE_KEY') or dotenv_values(
    BASE_DIR.parent / 'frontend' / '.env'
).get('REACT_APP_SUPABASE_PUBLISHABLE_KEY', '')
SUPABASE_SECRET_KEY = os.getenv('SUPABASE_SECRET_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
DATABASE_URL = os.getenv('DATABASE_URL', '')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'https://careerflow.live,http://localhost:3000,http://127.0.0.1:3000').split(',')
DEVELOPER_USER_IDS = {value.strip() for value in os.getenv('DEVELOPER_SUPABASE_USER_IDS', '').split(',') if value.strip()}
MODELS_DIR = BASE_DIR / 'models'
DATA_DIR   = BASE_DIR / 'data'
DB_PATH    = DATA_DIR / 'career_advisor.sqlite3'

# Classifier
CLASSIFIER_PATH   = MODELS_DIR / 'classifier_model.joblib'
PREPROCESSOR_PATH_CLASSIFIER = MODELS_DIR / 'preprocessor_classifier.joblib'
PREPROCESSOR_PATH_DEMAND = MODELS_DIR / 'preprocessor_demand.joblib'
LASSO_FEATURES    = MODELS_DIR / 'lasso_features.json'
DEMAND_MODEL_PARAMS = MODELS_DIR / 'demand_model_params.json'

# Demand
VACANCY_DATA_PATH = DATA_DIR / 'vacancy_data.csv'

# Skill matcher
VECTORIZER_PATH        = MODELS_DIR / 'tfidf_vectorizer.joblib'
PROFESSION_VECTORS_PATH = MODELS_DIR / 'profession_vectors.joblib'
PROFESSION_NAMES_PATH  = MODELS_DIR / 'profession_names.joblib'

# Roadmap + courses
ROADMAP_PATH  = MODELS_DIR / 'profession_profiles.json'
COURSES_PATH  = DATA_DIR   / 'all_courses.csv'

# Courses from Roadmap
TOP_N_COURSES = 1


CLASS_NAMES = [
    'Business Analyst', 'Cloud Engineer', 'Data Analyst',
    'Data Engineer', 'Data Scientist', 'Machine Learning Engineer', 'Software Engineer'
]

# Scores for weighted scorer (top1 specialization)
CLASSIFIER_COEF = 0.38
SKILL_MATCHER_COEF = 0.35
DEMAND_MARKET_SHARE_COEF = 0.07
DEMAND_TREND_COEF = 0.20
