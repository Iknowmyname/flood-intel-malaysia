import logging

from .prompt_builder import build_prompt, build_plan_prompt
from .llm_adapters.ollama import OllamaAdapter
from .llm_models import LlmResponse
from .planner_models import QueryPlan
from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_RETRIES, OLLAMA_TIMEOUT, LLM_PROVIDER


log = logging.getLogger(__name__)


def create_adapter() -> OllamaAdapter:

    if LLM_PROVIDER == "ollama":
        log.info(f"Model used : ollama")
        return OllamaAdapter(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            timeout=OLLAMA_TIMEOUT,
            keep_alive="10m",
            retries=OLLAMA_RETRIES
        )
    
    raise RuntimeError(f"Unsupported LLM provider: {LLM_PROVIDER}")

    
def call_llm(question: str, context: str) -> LlmResponse:

    prompt = build_prompt(question, context)
    return create_adapter().generate(prompt)
       


def plan_query(question: str) -> QueryPlan:
    prompt = build_plan_prompt(question)
    response = create_adapter().generate(prompt, json_mode=True)
    return QueryPlan.model_validate_json(response.response)






