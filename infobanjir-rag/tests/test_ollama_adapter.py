import pytest
import requests
from pydantic import ValidationError

from app.llm_adapters.ollama import OllamaAdapter
from app.llm_models import LlmPrompt


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text="fake error body"):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._payload


def make_adapter(retries=2):
    return OllamaAdapter(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
        timeout=120,
        keep_alive="10m",
        retries=retries,
    )


def make_prompt():
    return LlmPrompt(
        system_prompt="System instructions",
        user_prompt="What is the flood risk in Selangor?\nFlood risk context",
    )


def test_generate_calls_ollama_chat_and_maps_response(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout

        return FakeResponse(
            {
                "model": "llama3.2:3b",
                "message": {
                    "role": "assistant",
                    "content": " Flood risk is moderate. ",
                },
                "done": True,
                "total_duration": 7_500_000_000,
                "prompt_eval_count": 195,
                "eval_count": 80,
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    result = make_adapter().generate(make_prompt())

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout"] == 120
    assert captured["json"]["model"] == "llama3.2:3b"
    assert captured["json"]["stream"] is False
    assert captured["json"]["keep_alive"] == "10m"
    assert "format" not in captured["json"]

    assert captured["json"]["messages"][0]["role"] == "system"
    assert captured["json"]["messages"][1]["role"] == "user"
    assert "Flood risk context" in captured["json"]["messages"][1]["content"]
    assert "What is the flood risk in Selangor?" in captured["json"]["messages"][1]["content"]

    assert result.response == "Flood risk is moderate."
    assert result.input_tokens == 195
    assert result.output_tokens == 80
    assert result.provider_name == "ollama"
    assert result.llm_model == "llama3.2:3b"
    assert result.response_latency == 7500.0


def test_generate_adds_json_format_only_when_requested(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return FakeResponse(
            {
                "message": {
                    "role": "assistant",
                    "content": '{"tasks":[],"clarification":null}',
                }
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    make_adapter().generate(make_prompt(), json_mode=True)

    assert captured["json"]["format"] == "json"


def test_generate_uses_configured_model_when_response_model_missing(monkeypatch):
    def fake_post(url, json, timeout):
        return FakeResponse(
            {
                "message": {
                    "role": "assistant",
                    "content": "ok",
                },
                "total_duration": 1_000_000,
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    result = make_adapter().generate(make_prompt())

    assert result.llm_model == "llama3.2:3b"


def test_generate_retries_timeout_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_post(url, json, timeout):
        calls["count"] += 1

        if calls["count"] == 1:
            raise requests.Timeout("timed out")

        return FakeResponse(
            {
                "model": "llama3.2:3b",
                "message": {
                    "role": "assistant",
                    "content": "ok",
                },
                "total_duration": 1_000_000,
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    result = make_adapter(retries=1).generate(make_prompt())

    assert calls["count"] == 2
    assert result.response == "ok"


def test_generate_raises_timeout_after_retries_exhausted(monkeypatch):
    calls = {"count": 0}

    def fake_post(url, json, timeout):
        calls["count"] += 1
        raise requests.Timeout("timed out")

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    with pytest.raises(requests.Timeout):
        make_adapter(retries=2).generate(make_prompt())

    assert calls["count"] == 3


def test_generate_retries_connection_error_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_post(url, json, timeout):
        calls["count"] += 1

        if calls["count"] == 1:
            raise requests.ConnectionError("connection failed")

        return FakeResponse(
            {
                "model": "llama3.2:3b",
                "message": {
                    "role": "assistant",
                    "content": "ok",
                },
                "total_duration": 1_000_000,
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    result = make_adapter(retries=1).generate(make_prompt())

    assert calls["count"] == 2
    assert result.response == "ok"


def test_generate_retries_5xx_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_post(url, json, timeout):
        calls["count"] += 1

        if calls["count"] == 1:
            return FakeResponse(status_code=503)

        return FakeResponse(
            {
                "model": "llama3.2:3b",
                "message": {
                    "role": "assistant",
                    "content": "ok",
                },
                "total_duration": 1_000_000,
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    result = make_adapter(retries=1).generate(make_prompt())

    assert calls["count"] == 2
    assert result.response == "ok"


def test_generate_retries_429_then_succeeds(monkeypatch):
    calls = {"count": 0}

    def fake_post(url, json, timeout):
        calls["count"] += 1

        if calls["count"] == 1:
            return FakeResponse(status_code=429)

        return FakeResponse(
            {
                "model": "llama3.2:3b",
                "message": {
                    "role": "assistant",
                    "content": "ok",
                },
                "total_duration": 1_000_000,
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    result = make_adapter(retries=1).generate(make_prompt())

    assert calls["count"] == 2
    assert result.response == "ok"


def test_generate_does_not_retry_404(monkeypatch):
    calls = {"count": 0}

    def fake_post(url, json, timeout):
        calls["count"] += 1
        return FakeResponse(status_code=404)

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    with pytest.raises(requests.HTTPError):
        make_adapter(retries=2).generate(make_prompt())

    assert calls["count"] == 1


def test_generate_raises_validation_error_for_invalid_ollama_shape(monkeypatch):
    def fake_post(url, json, timeout):
        return FakeResponse(
            {
                "model": "llama3.2:3b",
                "message": {
                    "role": "assistant",
                },
            }
        )

    monkeypatch.setattr("app.llm_adapters.ollama.requests.post", fake_post)

    with pytest.raises(ValidationError):
        make_adapter(retries=0).generate(make_prompt())
