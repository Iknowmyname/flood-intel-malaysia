import pytest
from app.llm_models import LlmResponse


class FakeOllamaAdapter:
    created_with = None
    generate_called_with = None

    def __init__(self, base_url, model, timeout, keep_alive, retries):
        FakeOllamaAdapter.created_with = {
            "base_url": base_url,
            "model": model,
            "timeout": timeout,
            "keep_alive": keep_alive,
            "retries": retries,
        }

    def generate(self, question: str, context: str) -> LlmResponse:
        FakeOllamaAdapter.generate_called_with = {
            "question": question,
            "context": context,
        }

        return LlmResponse(
            response="fake answer",
            input_tokens=10,
            output_tokens=5,
            provider_name="ollama",
            llm_model="fake-model",
            response_latency=123.4,
        )


def test_call_llm_uses_ollama_adapter(monkeypatch):
    from app import llm_client

    monkeypatch.setattr(llm_client, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(llm_client, "OLLAMA_BASE_URL", "http://test-ollama")
    monkeypatch.setattr(llm_client, "OLLAMA_MODEL", "test-model")
    monkeypatch.setattr(llm_client, "OLLAMA_TIMEOUT", 9.0)
    monkeypatch.setattr(llm_client, "OLLAMA_RETRIES", 3)
    monkeypatch.setattr(llm_client, "OllamaAdapter", FakeOllamaAdapter)

    result = llm_client.call_llm("What is the flood risk?", "Context text")

    assert result.response == "fake answer"

    assert FakeOllamaAdapter.created_with == {
        "base_url": "http://test-ollama",
        "model": "test-model",
        "timeout": 9.0,
        "keep_alive": "10m",
        "retries": 3,
    }

    assert FakeOllamaAdapter.generate_called_with == {
        "question": "What is the flood risk?",
        "context": "Context text",
    }


def test_call_llm_rejects_unsupported_provider(monkeypatch):
    from app import llm_client

    monkeypatch.setattr(llm_client, "LLM_PROVIDER", "unsupported")

    with pytest.raises(RuntimeError, match="Unsupported LLM provider"):
        llm_client.call_llm("question", "context")