import logging


from .llm_adapters.ollama import OllamaAdapter
from .llm_models import LlmResponse
from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_RETRIES, OLLAMA_TIMEOUT, LLM_PROVIDER


log = logging.getLogger(__name__)

    
def call_llm(question: str, context: str) -> LlmResponse:

    if LLM_PROVIDER == "ollama":
        log.info("Creation of OllamaAdapter object")
        adapter = OllamaAdapter(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            timeout=OLLAMA_TIMEOUT,
            keep_alive="10m",
            retries=OLLAMA_RETRIES
        )

        return adapter.generate(question, context)
    
    raise RuntimeError(f"Unsupported LLM provider: {LLM_PROVIDER}")
       






