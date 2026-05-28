from pathlib import Path

BASE_DIR = Path(__file__).parent
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
TOP_N_COURSES = 5


CLASS_NAMES = [
    'Business Analyst', 'Cloud Engineer', 'Data Analyst',
    'Data Engineer', 'Data Scientist', 'Machine Learning Engineer', 'Software Engineer'
]

# Scores for weighted scorer (top1 specialization)
CLASSIFIER_COEF = 0.4
SKILL_MATCHER_COEF = 0.4
DEMAND_MARKET_SHARE_COEF = 0.05
DEMAND_TREND_COEF = 0.15
