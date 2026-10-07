from conftest import EXPECTED_PROFESSIONS, TEST_PROFILE


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommend_endpoint_returns_complete_payload(recommendation_response):
    expected_keys = {
        "top_profession",
        "session_id",
        "alternative_profession",
        "final_scores",
        "skill_scores",
        "classification_scores",
        "demand_scores",
        "roadmap_with_courses",
        "full_roadmap",
        "context",
    }

    assert expected_keys <= set(recommendation_response)
    assert recommendation_response["top_profession"] == "Machine Learning Engineer"
    assert recommendation_response["alternative_profession"]
    assert recommendation_response["session_id"]


def test_recommend_scores_cover_all_supported_professions(recommendation_response):
    assert set(recommendation_response["skill_scores"]) == EXPECTED_PROFESSIONS
    assert set(recommendation_response["classification_scores"]) == EXPECTED_PROFESSIONS
    assert set(recommendation_response["demand_scores"]) == EXPECTED_PROFESSIONS
    assert set(recommendation_response["final_scores"]) == EXPECTED_PROFESSIONS


def test_final_scores_are_sorted_descending(recommendation_response):
    scores = list(recommendation_response["final_scores"].values())

    assert scores == sorted(scores, reverse=True)


def test_demand_scores_are_bounded_and_have_vacancy_counts(recommendation_response):
    for scores in recommendation_response["demand_scores"].values():
        assert 0 <= scores["trend_score"] <= 1
        assert 0 <= scores["market_share"] <= 1
        assert scores["predicted_vacancies"] >= 0


def test_roadmap_contains_course_recommendations(recommendation_response):
    roadmap = recommendation_response["roadmap_with_courses"]

    assert "libraries" in roadmap
    assert "pytorch" in roadmap["libraries"]
    assert roadmap["libraries"]["pytorch"]["courses"][0]["title"] == "PyTorch for Deep Learning"


def test_chat_uses_stored_recommendation_context(client, recommendation_response):
    response = client.post(
        "/chat",
        headers={"X-LLM-Provider": "gemini", "X-LLM-API-Key": "test-session-key"},
        json={
            "session_id": recommendation_response["session_id"],
            "history": [],
            "message": "What should I learn first?",
            "deep": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Mock advisor response: What should I learn first?"


def test_chat_stream_returns_server_sent_events(client, recommendation_response):
    response = client.post(
        "/chat/stream",
        headers={"X-LLM-Provider": "gemini", "X-LLM-API-Key": "test-session-key"},
        json={
            "session_id": recommendation_response["session_id"],
            "history": [],
            "message": "Stream answer",
            "deep": False,
        },
    )

    assert response.status_code == 200
    assert "data: Mock streamed advisor response" in response.text
    assert "data: [DONE]" in response.text


def test_recommend_passes_language_to_course_finder(client, mocked_services):
    profile = {**TEST_PROFILE, "lang": "kk"}

    response = client.post("/recommend", json=profile)

    assert response.status_code == 200
    assert mocked_services.calls[-1]["lang"] == "kk"


def test_recommend_rejects_invalid_payload(client):
    profile = dict(TEST_PROFILE)
    profile.pop("gpa")

    response = client.post("/recommend", json=profile)

    assert response.status_code == 422


def test_resume_parser_avoids_short_token_false_positives(client):
    response = client.post(
        "/parse-resume",
        content=(
            "I want to go into data science. I work with Python, SQL, MongoDB, "
            "and TensorFlow. The phrase go forward should not be treated as a Go skill."
        ).encode("utf-8"),
        headers={
            "content-type": "text/plain",
            "x-filename": "resume.txt",
        },
    )

    assert response.status_code == 200
    skills = response.json()["skills"]
    assert "Python" in skills
    assert "SQL" in skills
    assert "MongoDB" in skills
    assert "TensorFlow" in skills
    assert "Go" not in skills
    assert "R" not in skills
