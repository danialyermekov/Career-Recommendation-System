import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest

import database
import guest_sessions
from hashlib import sha256
import sqlalchemy as sa
import main
from conftest import TEST_PROFILE
from services.llm import LLMService


KEY = "test-only-secret-sentinel"
HEADERS = {"X-LLM-Provider": "gemini", "X-LLM-API-Key": KEY}
PAYLOAD = {"session_id": "test-session", "history": [], "message": "Career advice", "deep": False}
AI_PATHS = ["/chat", "/chat/stream", "/voice/transcribe"]



@pytest.fixture(autouse=True)
def owned_ai_session(client):
    guest_sessions.save('test-session', sha256(('a'*64).encode()).hexdigest(), {'context': 'Recommendation context'})

def post_ai(client, path, headers=None):
    if path == "/voice/transcribe":
        return client.post(path, content=b"test-audio", headers=headers)
    return client.post(path, json=PAYLOAD, headers=headers)


@pytest.mark.parametrize("path", AI_PATHS)
def test_missing_key_is_safe_even_with_environment_fallback(client, monkeypatch, path):
    monkeypatch.setenv("API_KEY", KEY)
    monkeypatch.setenv("GOOGLE_API_KEY", KEY)
    response = post_ai(client, path)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "key_missing"
    assert KEY not in response.text


@pytest.mark.parametrize("path", AI_PATHS)
def test_unsupported_provider_does_not_echo_headers(client, path):
    response = post_ai(client, path, {**HEADERS, "X-LLM-Provider": KEY})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "unsupported_provider"
    assert KEY not in response.text


@pytest.mark.parametrize("path", AI_PATHS)
def test_invalid_key_format_does_not_echo_header(client, path):
    response = post_ai(client, path, {**HEADERS, "X-LLM-API-Key": f"{KEY} invalid"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "key_invalid"
    assert KEY not in response.text


@pytest.mark.parametrize("provider", ["gemini", "anthropic"])
@pytest.mark.parametrize("path", ["/chat", "/chat/stream"])
def test_route_forwards_request_credentials_and_normalized_history(client, monkeypatch, provider, path):
    service = Mock()
    service.chat.return_value = "Answer"
    service.chat_stream.return_value = iter([json.dumps({"type": "text", "content": "Answer"})])
    monkeypatch.setattr(main, "llm", service)
    guest_sessions.save('test-session', sha256(('a'*64).encode()).hexdigest(), {'context': 'Recommendation context'})
    history = [{"role": "assistant", "content": "Previous answer"}]
    response = client.post(path, json={**PAYLOAD, "history": history}, headers={**HEADERS, "X-LLM-Provider": provider})
    assert response.status_code == 200
    call = (service.chat_stream if path.endswith("stream") else service.chat).call_args.kwargs
    assert call["provider"] == provider
    assert call["api_key"] == KEY
    assert call["history"] == history
    assert call["context"] == "Recommendation context"
    assert KEY not in response.text
    assert KEY not in repr(guest_sessions.sessions)


@pytest.fixture
def sdk_clients(monkeypatch):
    import anthropic
    from google import genai

    google_factory = MagicMock()
    claude_factory = MagicMock()
    monkeypatch.setattr(genai, "Client", google_factory)
    monkeypatch.setattr(anthropic, "Anthropic", claude_factory)
    return google_factory, claude_factory


def test_gemini_sdk_chat_stream_and_transcription_are_preserved(sdk_clients):
    factory, _ = sdk_clients
    sdk = factory.return_value.__enter__.return_value
    sdk.models.generate_content.return_value.text = "Gemini answer"
    sdk.models.generate_content_stream.return_value = [SimpleNamespace(candidates=[SimpleNamespace(
        content=SimpleNamespace(parts=[SimpleNamespace(text="thinking", thought=True), SimpleNamespace(text="answer", thought=False)]),
    )])]
    service = LLMService()
    history = [{"role": "assistant", "content": "Previous reply"}]
    assert service.chat("Context", history, "Question", provider="gemini", api_key=KEY) == "Gemini answer"
    request = sdk.models.generate_content.call_args.kwargs
    assert request["contents"][0].role == "model"
    assert request["contents"][0].parts[0].text == "Previous reply"
    assert request["contents"][-1].parts[0].text == "Context:\nContext\n\nQuestion: Question"
    chunks = list(service.chat_stream("Context", history, "Question", deep=True, provider="gemini", api_key=KEY))
    assert [json.loads(c)["type"] for c in chunks] == ["thought", "text"]
    assert sdk.models.generate_content_stream.call_args.kwargs["model"] == "gemini-2.5-pro"
    assert service.transcribe_audio(b"audio", "audio/wav", "ru", provider="gemini", api_key=KEY) == "Gemini answer"
    assert sdk.models.generate_content.call_args.kwargs["contents"][0].parts[1].inline_data.data == b"audio"
    assert factory.call_args.kwargs["api_key"] == KEY
    assert factory.call_args.kwargs["vertexai"] is False
    assert factory.return_value.__exit__.call_count == 3
    assert KEY not in repr(vars(service))


def test_claude_sdk_chat_and_thinking_stream(sdk_clients):
    _, factory = sdk_clients
    sdk = factory.return_value.__enter__.return_value
    sdk.messages.create.return_value.content = [SimpleNamespace(type="text", text="Claude answer")]
    sdk.messages.stream.return_value.__enter__.return_value = [
        SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(type="thinking_delta", thinking="Thinking")),
        SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(type="text_delta", text="Answer")),
    ]
    service = LLMService()
    history = [{"role": "user", "content": "Previous question"}]
    assert service.chat("Context", history, "Question", provider="anthropic", api_key=KEY) == "Claude answer"
    request = sdk.messages.create.call_args.kwargs
    assert request["system"] == service.system_prompt
    assert request["messages"][0] == history[0]
    assert request["messages"][-1]["content"] == "Context:\nContext\n\nQuestion: Question"
    chunks = list(service.chat_stream("Context", history, "Question", deep=True, provider="anthropic", api_key=KEY))
    assert [json.loads(c)["type"] for c in chunks] == ["thought", "text"]
    assert sdk.messages.stream.call_args.kwargs["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert sdk.messages.create.call_args.kwargs["thinking"] == {"type": "between_tools"}
    assert factory.call_args.kwargs["api_key"] == KEY
    assert factory.call_args.kwargs["base_url"] == "https://api.anthropic.com"
    assert factory.return_value.__exit__.call_count == 2
    assert sdk.messages.stream.return_value.__exit__.called
    assert KEY not in repr(vars(service))


@pytest.mark.parametrize("provider,path", [("gemini", p) for p in AI_PATHS] + [("anthropic", "/chat"), ("anthropic", "/chat/stream")])
@pytest.mark.parametrize("status,code", [(401, "key_rejected"), (403, "key_rejected"), (429, "rate_limited"), (503, "provider_unavailable")])
def test_sdk_errors_are_sanitized_in_http_sse_and_logs(client, monkeypatch, sdk_clients, caplog, provider, path, status, code):
    from anthropic import APIStatusError
    from google.genai.errors import APIError

    if provider == "gemini":
        error = APIError(status, {"error": {"message": KEY, "code": status}})
        sdk = sdk_clients[0].return_value.__enter__.return_value
        sdk.models.generate_content.side_effect = error
        sdk.models.generate_content_stream.side_effect = error
    else:
        error = APIStatusError(KEY, response=httpx.Response(status, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")), body={"secret": KEY})
        sdk = sdk_clients[1].return_value.__enter__.return_value
        sdk.messages.create.side_effect = error
        sdk.messages.stream.side_effect = error
    monkeypatch.setattr(main, "llm", LLMService())
    response = post_ai(client, path, {**HEADERS, "X-LLM-Provider": provider})
    if path.endswith("stream"):
        assert response.status_code == 200
        assert f'"code": "{code}"' in response.text
        assert response.text.count("data: [DONE]") == 1
    else:
        assert response.status_code == (401 if status == 403 else status)
        assert response.json()["detail"]["code"] == code
    assert KEY not in response.text
    assert KEY not in caplog.text


def test_claude_audio_is_explicitly_unsupported(client, monkeypatch):
    monkeypatch.setattr(main, "llm", LLMService())
    response = post_ai(client, "/voice/transcribe", {**HEADERS, "X-LLM-Provider": "anthropic"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "voice_unsupported"


def test_non_ai_requests_and_serialized_history_exclude_key(client, monkeypatch, sdk_clients):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(main, "llm", LLMService())
    result = client.post("/recommend", json=TEST_PROFILE)
    assert result.status_code == 200
    assert not sdk_clients[0].called and not sdk_clients[1].called
    session = result.json()["session_id"]
    sdk_clients[0].return_value.__enter__.return_value.models.generate_content.return_value.text = "Career advice"
    assert client.post("/chat", json={**PAYLOAD, "session_id": session}, headers=HEADERS).status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/recommendation/history").status_code == 401
    assert client.get(f"/recommendation/{session}/state").status_code == 200
    assert client.put(f"/recommendation/{session}/progress", json={"doneSkills": []}).status_code == 200
    assert client.put(f"/recommendation/{session}/course-filters", json={"filters": {}}).status_code == 200
    assert client.post("/parse-resume", content=b"Python and SQL", headers={"X-Filename": "resume.txt"}).status_code == 200
    with database.get_connection() as connection:
        assert connection.scalar(sa.select(sa.func.count()).select_from(database.sessions)) == 0
    assert KEY not in repr(guest_sessions.sessions)


def test_cors_allows_ai_headers_without_credentials(client):
    response = client.options("/chat/stream", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-llm-provider,x-llm-api-key",
    })
    assert response.status_code == 200
    assert "x-llm-api-key" in response.headers["access-control-allow-headers"].lower()


def test_midstream_failure_preserves_text_then_sends_safe_error_and_one_done(client, monkeypatch):
    def stream(**kwargs):
        yield json.dumps({"type": "text", "content": "First chunk"})
        raise RuntimeError(KEY)

    service = Mock()
    service.chat_stream.side_effect = stream
    monkeypatch.setattr(main, "llm", service)
    response = client.post("/chat/stream", json=PAYLOAD, headers=HEADERS)
    assert "First chunk" in response.text
    assert '"type": "error"' in response.text
    assert '"code": "provider_unavailable"' in response.text
    assert response.text.count("data: [DONE]") == 1
    assert KEY not in response.text


def test_gemini_invalid_key_reason_is_recognized_without_echoing_metadata(client, monkeypatch, sdk_clients):
    from google.genai.errors import APIError

    sdk = sdk_clients[0].return_value.__enter__.return_value
    sdk.models.generate_content.side_effect = APIError(400, {"error": {
        "message": KEY, "details": [{"reason": "API_KEY_INVALID", "metadata": {"key": KEY}}],
    }})
    monkeypatch.setattr(main, "llm", LLMService())
    response = client.post("/chat", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "key_rejected"
    assert KEY not in response.text
