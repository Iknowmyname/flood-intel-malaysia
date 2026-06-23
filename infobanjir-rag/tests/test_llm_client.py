import pytest
from pydantic import ValidationError

from app.llm_models import LlmPrompt, LlmResponse
from app.planner_models import Metric, Operation, QueryPlan, TimeType


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

    def generate(
        self,
        prompt: LlmPrompt,
        json_mode: bool = False,
    ) -> LlmResponse:
        FakeOllamaAdapter.generate_called_with = {
            "prompt": prompt,
            "json_mode": json_mode,
        }

        response = (
            """
            {
                "tasks": [
                    {
                        "operation": "get_highest_reading",
                        "location": {
                            "state": "Selangor",
                            "district": null,
                            "station": null
                        },
                        "metric": "rainfall",
                        "time": {
                            "type": "current",
                            "start_time": null,
                            "end_time": null,
                            "duration": null
                        }
                    }
                ],
                "clarification": null
            }
            """
            if json_mode
            else "fake answer"
        )

        return LlmResponse(
            response=response,
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

    call = FakeOllamaAdapter.generate_called_with
    assert call["json_mode"] is False
    assert call["prompt"].system_prompt
    assert "What is the flood risk?" in call["prompt"].user_prompt
    assert "Context text" in call["prompt"].user_prompt


def test_call_llm_rejects_unsupported_provider(monkeypatch):
    from app import llm_client

    monkeypatch.setattr(llm_client, "LLM_PROVIDER", "unsupported")

    with pytest.raises(RuntimeError, match="Unsupported LLM provider"):
        llm_client.call_llm("question", "context")


def test_plan_query_uses_json_mode_and_returns_query_plan(monkeypatch):
    from app import llm_client

    monkeypatch.setattr(llm_client, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(llm_client, "OllamaAdapter", FakeOllamaAdapter)

    plan = llm_client.plan_query("What is the highest rainfall in Selangor?")

    assert isinstance(plan, QueryPlan)
    assert plan.clarification is None
    assert len(plan.tasks) == 1
    assert plan.tasks[0].operation is Operation.GET_HIGHEST_READING
    assert plan.tasks[0].location.state == "Selangor"
    assert plan.tasks[0].metric is Metric.RAINFALL
    assert plan.tasks[0].time.type is TimeType.CURRENT

    call = FakeOllamaAdapter.generate_called_with
    assert call["json_mode"] is True
    assert call["prompt"].user_prompt == (
        "What is the highest rainfall in Selangor?"
    )


def test_plan_query_rejects_invalid_planner_output(monkeypatch):
    from app import llm_client

    class InvalidPlannerAdapter(FakeOllamaAdapter):
        def generate(
            self,
            prompt: LlmPrompt,
            json_mode: bool = False,
        ) -> LlmResponse:
            return LlmResponse(
                response='{"tasks":[{"operation":"unknown_operation"}]}',
                input_tokens=1,
                output_tokens=1,
                provider_name="ollama",
                llm_model="fake-model",
                response_latency=1.0,
            )

    monkeypatch.setattr(llm_client, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(llm_client, "OllamaAdapter", InvalidPlannerAdapter)

    with pytest.raises(ValidationError):
        llm_client.plan_query("Do something unsupported")
