"""
Representativeness rationale
─────────────────────────────
Test profiles are drawn from three tiers:

  TIER 1 – Clear profiles (1 per profession, 7 total)
    Skill vectors constructed so that both the TF-IDF matcher AND the
    CatBoost classifier agree unambiguously.  A correct system must
    place the expected profession at top-1.

  TIER 2 – Borderline profiles (derived from confusion matrix, Section 4.4)
    The confusion matrix shows four dominant misclassification pairs:
      DE ↔ CE  (DevOps/cloud overlap)
      DE ↔ SE  (backend/pipeline overlap)
      DS ↔ MLE (ML-research vs ML-engineering)
      DS ↔ DA  (analytical skills shared)
    For each pair, one profile is designed so the expected profession
    sits at top-1 OR top-2.  These cases specifically test whether
    the weight combination can resolve genuinely ambiguous inputs.

  TIER 3 – Edge profiles (2 total)
    Low-GPA generalist and a high-GPA specialist with minimal hard skills.
    These probe robustness: the system must not collapse to a single
    profession for all weak profiles.

The full set covers all 7 professions at Tier 1, the 4 highest-confusion
pairs at Tier 2, and 2 robustness checks — 13 labeled cases in total.
The expected_top2 flag marks cases where top-2 membership is
acceptable, matching the accept criterion in test_top_profession_matches_expected.
"""

import httpx
import pytest

BASE_URL = "http://localhost:8000"

# ─────────────────────────────────────────────
# TIER 1 — Clear profiles (one per profession)
# ─────────────────────────────────────────────
CLEAR_PROFILES = [
    (
        {
            "skills": ["python", "pandas", "scikit-learn", "machine learning",
                        "deep learning", "pytorch", "tensorflow", "mlops"],
            "field_of_study": "Data Science",
            "gpa": 3.8,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 0,
            "machine_learning": 1, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Machine Learning Engineer",
        False,
    ),
    (
        {
            "skills": ["sql", "excel", "power bi", "tableau", "statistics",
                        "data visualization", "google analytics"],
            "field_of_study": "Data Science",
            "gpa": 3.5,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 0, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 1,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Data Analyst",
        False,
    ),
    (
        {
            "skills": ["python", "spark", "airflow", "kafka", "postgresql",
                        "etl", "data warehouse", "dbt", "hadoop"],
            "field_of_study": "Computer Science",
            "gpa": 3.6,
            "python": 1, "java": 1, "c_cpp": 0, "sql": 1,
            "machine_learning": 0, "data_analysis": 0, "cloud_computing": 1,
            "cybersecurity": 0, "web_development": 0, "devops": 1,
            "networking": 0, "communication": 0, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Data Engineer",
        False,
    ),
    (
        {
            "skills": ["requirements gathering", "bpmn", "jira", "confluence",
                        "sql", "excel", "uml", "stakeholder management"],
            "field_of_study": "Data Science",
            "gpa": 3.3,
            "python": 0, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 0, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 1,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Business Analyst",
        False,
    ),
    (
        {
            "skills": ["aws", "terraform", "docker", "kubernetes", "ci/cd",
                        "linux", "networking", "ansible"],
            "field_of_study": "Computer Science",
            "gpa": 3.4,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 0,
            "machine_learning": 0, "data_analysis": 0, "cloud_computing": 1,
            "cybersecurity": 0, "web_development": 0, "devops": 1,
            "networking": 1, "communication": 0, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Cloud Engineer",
        False,
    ),
    (
        {
            "skills": ["python", "statistics", "r", "hypothesis testing",
                        "feature engineering", "xgboost", "research", "bayesian"],
            "field_of_study": "AI",
            "gpa": 3.9,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 1, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Data Scientist",
        False,
    ),
    (
        {
            "skills": ["java", "spring boot", "react", "rest api", "git",
                        "design patterns", "unit testing", "agile"],
            "field_of_study": "Software Engineering",
            "gpa": 3.4,
            "python": 0, "java": 1, "c_cpp": 1, "sql": 1,
            "machine_learning": 0, "data_analysis": 0, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 1, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Software Engineer",
        False,
    ),
]

# ─────────────────────────────────────────────────────────────────
# TIER 2 — Borderline profiles (confusion-matrix-derived pairs)
#   expected_top2=True means top-1 OR top-2 is acceptable
# ─────────────────────────────────────────────────────────────────
BORDERLINE_PROFILES = [
    # DE ↔ CE: pipeline-heavy but strong cloud
    (
        {
            "skills": ["python", "spark", "airflow", "aws", "s3", "glue",
                        "postgresql", "etl", "terraform"],
            "field_of_study": "Computer Science",
            "gpa": 3.4,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 0, "data_analysis": 0, "cloud_computing": 1,
            "cybersecurity": 0, "web_development": 0, "devops": 1,
            "networking": 0, "communication": 0, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Data Engineer",
        True,
    ),
    # DE ↔ SE: backend dev who writes data pipelines
    (
        {
            "skills": ["python", "java", "postgresql", "rest api",
                        "kafka", "rabbitmq", "docker", "git"],
            "field_of_study": "Software Engineering",
            "gpa": 3.3,
            "python": 1, "java": 1, "c_cpp": 0, "sql": 1,
            "machine_learning": 0, "data_analysis": 0, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 1,
            "networking": 0, "communication": 0, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Data Engineer",
        True,
    ),
    # DS ↔ MLE: strong ML but also writes production code
    (
        {
            "skills": ["python", "pytorch", "scikit-learn", "mlflow",
                        "docker", "fastapi", "feature engineering", "statistics"],
            "field_of_study": "Data Science",
            "gpa": 3.7,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 1, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 1,
            "networking": 0, "communication": 0, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Machine Learning Engineer",
        True,
    ),
    # DS ↔ DA: good analyst who does some ML
    (
        {
            "skills": ["python", "pandas", "sql", "tableau",
                        "scikit-learn", "statistics", "ab testing"],
            "field_of_study": "Data Science",
            "gpa": 3.5,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 1, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Data Scientist",
        True,
    ),
    # BA ↔ DA: business-heavy analyst, low coding
    (
        {
            "skills": ["excel", "sql", "power bi", "stakeholder management",
                        "process mapping", "jira", "reporting"],
            "field_of_study": "Business Administration",
            "gpa": 3.2,
            "python": 0, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 0, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 1,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Business Analyst",
        True,
    ),
]

# ─────────────────────────────────────────────
# TIER 3 — Edge / robustness profiles
# ─────────────────────────────────────────────
EDGE_PROFILES = [
    # Low-GPA generalist: system should still pick SOMETHING reasonable
    (
        {
            "skills": ["python", "sql", "excel"],
            "field_of_study": "Computer Science",
            "gpa": 2.4,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 1,
            "machine_learning": 0, "data_analysis": 1, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 1, "leadership": 0,
            "problem_solving": 1, "teamwork": 1, "adaptability": 1,
        },
        "Data Analyst",
        True,
    ),
    # High-GPA AI specialist with no hard-skill checkboxes
    (
        {
            "skills": ["pytorch", "transformers", "nlp", "paper implementation",
                        "research", "latex", "python"],
            "field_of_study": "AI",
            "gpa": 4.0,
            "python": 1, "java": 0, "c_cpp": 0, "sql": 0,
            "machine_learning": 1, "data_analysis": 0, "cloud_computing": 0,
            "cybersecurity": 0, "web_development": 0, "devops": 0,
            "networking": 0, "communication": 0, "leadership": 0,
            "problem_solving": 1, "teamwork": 0, "adaptability": 1,
        },
        "Data Scientist",
        True,
    ),
]

ALL_LABELED_PROFILES = CLEAR_PROFILES + BORDERLINE_PROFILES + EDGE_PROFILES


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

@pytest.mark.parametrize("profile, expected, top2_ok", ALL_LABELED_PROFILES)
def test_top_profession_matches_expected(profile, expected, top2_ok):
    r = httpx.post(f"{BASE_URL}/recommend", json=profile, timeout=30)
    assert r.status_code == 200, f"API error: {r.text}"

    data   = r.json()
    top    = data["top_profession"]
    alt    = data.get("alternative_profession", "")
    scores = data.get("final_scores", {})

    if top2_ok:
        assert expected in (top, alt), (
            f"\nProfile skills : {profile['skills']}"
            f"\nExpected       : {expected}  (top-2 accepted)"
            f"\nReceived top-1 : {top}"
            f"\nReceived top-2 : {alt}"
            f"\nFinal scores   : {scores}"
        )
    else:
        assert top == expected, (
            f"\nProfile skills : {profile['skills']}"
            f"\nExpected top-1 : {expected}"
            f"\nReceived top-1 : {top}"
            f"\nReceived top-2 : {alt}"
            f"\nFinal scores   : {scores}"
        )


def test_response_has_all_required_fields():
    """Smoke test: verify response schema on a minimal profile."""
    profile = CLEAR_PROFILES[0][0]
    r = httpx.post(f"{BASE_URL}/recommend", json=profile, timeout=30)
    assert r.status_code == 200
    data = r.json()
    for field in ["top_profession", "alternative_profession",
                  "final_scores", "skill_scores",
                  "classification_scores", "demand_scores",
                  "roadmap_with_courses", "full_roadmap"]:
        assert field in data, f"Missing field: {field}"


def test_all_professions_appear_in_scores():
    """All 7 supported professions must appear in final_scores."""
    expected_profs = {
        "Business Analyst", "Cloud Engineer", "Data Analyst",
        "Data Engineer", "Data Scientist",
        "Machine Learning Engineer", "Software Engineer",
    }
    profile = CLEAR_PROFILES[0][0]
    r = httpx.post(f"{BASE_URL}/recommend", json=profile, timeout=30)
    data = r.json()
    returned = set(data["final_scores"].keys())
    assert expected_profs == returned, f"Score keys mismatch: {returned ^ expected_profs}"


def test_scores_sum_sanity():
    """Final scores must all be in [0, 1] (post min-max normalization)."""
    profile = CLEAR_PROFILES[2][0]
    r = httpx.post(f"{BASE_URL}/recommend", json=profile, timeout=30)
    data = r.json()
    for prof, score in data["final_scores"].items():
        assert 0.0 <= score <= 1.0, f"{prof} score {score} outside [0,1]"


def test_roadmap_lists_missing_skills():
    """Roadmap should contain at least one missing skill for a non-expert profile."""
    profile = {
        "skills": ["python"],
        "field_of_study": "Data Science",
        "gpa": 3.0,
        "python": 1, "java": 0, "c_cpp": 0, "sql": 0,
        "machine_learning": 0, "data_analysis": 0, "cloud_computing": 0,
        "cybersecurity": 0, "web_development": 0, "devops": 0,
        "networking": 0, "communication": 1, "leadership": 0,
        "problem_solving": 1, "teamwork": 1, "adaptability": 1,
    }
    r = httpx.post(f"{BASE_URL}/recommend", json=profile, timeout=30)
    data = r.json()
    roadmap = data.get("roadmap_with_courses", {})
    total_missing = sum(len(v) for v in roadmap.values())
    assert total_missing > 0, "Expected missing skills for a minimal-skill profile"