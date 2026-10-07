import pytest
from fastapi.testclient import TestClient

import main as app_main
import database


EXPECTED_PROFESSIONS = {
    "Business Analyst",
    "Cloud Engineer",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Software Engineer",
}


TEST_PROFILE = {
    "skills": ["python", "sql", "tensorflow", "pytorch", "aws"],
    "field_of_study": "Data Science",
    "gpa": 3.5,
    "python": 1,
    "java": 0,
    "c_cpp": 0,
    "sql": 1,
    "machine_learning": 1,
    "data_analysis": 1,
    "cloud_computing": 1,
    "cybersecurity": 0,
    "web_development": 0,
    "devops": 0,
    "networking": 0,
    "communication": 4,
    "leadership": 3,
    "problem_solving": 5,
    "teamwork": 4,
    "adaptability": 3,
    "lang": "en",
}


class DummySkillMatcher:
    def get_user_skills_ranked(self, skills):
        return [{"skill": skill, "canonical_skill": skill.lower(), "tfidf_weight": 0.0, "status": "verified"} for skill in skills]

    def get_scores(self, skills):
        has_ml = any(skill.lower() in {"pytorch", "tensorflow", "machine learning"} for skill in skills)
        return {
            "Business Analyst": 0.15,
            "Cloud Engineer": 0.35 if "aws" in {s.lower() for s in skills} else 0.12,
            "Data Analyst": 0.45,
            "Data Engineer": 0.40,
            "Data Scientist": 0.70 if has_ml else 0.30,
            "Machine Learning Engineer": 0.95 if has_ml else 0.25,
            "Software Engineer": 0.30,
        }


class DummyClassifier:
    def get_scores(self, profile):
        ml_signal = profile.get("machine_learning", 0)
        return {
            "Business Analyst": 0.05,
            "Cloud Engineer": 0.08,
            "Data Analyst": 0.10,
            "Data Engineer": 0.12,
            "Data Scientist": 0.18 if ml_signal else 0.12,
            "Machine Learning Engineer": 0.42 if ml_signal else 0.10,
            "Software Engineer": 0.05,
        }


class DummyDemand:
    def get_scores(self):
        return {
            "Business Analyst": {
                "trend_score": 0.30,
                "market_share": 0.10,
                "predicted_vacancies": 900,
            },
            "Cloud Engineer": {
                "trend_score": 0.28,
                "market_share": 0.08,
                "predicted_vacancies": 700,
            },
            "Data Analyst": {
                "trend_score": 0.50,
                "market_share": 0.16,
                "predicted_vacancies": 1500,
            },
            "Data Engineer": {
                "trend_score": 0.78,
                "market_share": 0.33,
                "predicted_vacancies": 4695,
            },
            "Data Scientist": {
                "trend_score": 0.42,
                "market_share": 0.11,
                "predicted_vacancies": 1100,
            },
            "Machine Learning Engineer": {
                "trend_score": 0.56,
                "market_share": 0.12,
                "predicted_vacancies": 2060,
            },
            "Software Engineer": {
                "trend_score": 0.35,
                "market_share": 0.10,
                "predicted_vacancies": 1300,
            },
        }


class DummyCourseFinder:
    def __init__(self):
        self.calls = []

    def get_roadmap_with_courses(self, profession, student_skills, lang="en"):
        self.calls.append(
            {
                "profession": profession,
                "student_skills": list(student_skills),
                "lang": lang,
            }
        )
        course_title = "PyTorch for Deep Learning" if lang == "en" else "PyTorch на практике"
        return (
            {
                "libraries": {
                    "pytorch": {
                        "courses": [
                            {
                                "title": course_title,
                                "platform": "Test Platform",
                                "rating": 4.8,
                                "reviews": 120,
                                "course_url": "https://example.com/course",
                            }
                        ]
                    }
                }
            },
            {"libraries": ["pytorch"]},
        )


class DummyLLM:
    def build_context(
        self,
        skills,
        skill_scores,
        classification_scores,
        demand_scores,
        roadmap_with_courses,
    ):
        return f"Context for skills: {', '.join(skills)}"

    def chat(self, context, history, message, *, provider, api_key):
        return f"Mock advisor response: {message}"

    def chat_stream(self, context, history, message, deep=False, *, provider, api_key):
        yield "Mock streamed advisor response"


@pytest.fixture
def mocked_services(monkeypatch):
    course_finder = DummyCourseFinder()
    monkeypatch.setattr(app_main, "skill_matcher", DummySkillMatcher())
    monkeypatch.setattr(app_main, "classifier", DummyClassifier())
    monkeypatch.setattr(app_main, "demand", DummyDemand())
    monkeypatch.setattr(app_main, "course_finder", course_finder)
    monkeypatch.setattr(app_main, "llm", DummyLLM())
    app_main.session_store.clear()
    return course_finder


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "career-test.sqlite3")
    database.init_db()


@pytest.fixture
def client(mocked_services, isolated_db):
    with TestClient(app_main.app) as test_client:
        yield test_client


@pytest.fixture
def recommendation_response(client):
    response = client.post("/recommend", json=TEST_PROFILE)
    assert response.status_code == 200, response.text
    return response.json()
