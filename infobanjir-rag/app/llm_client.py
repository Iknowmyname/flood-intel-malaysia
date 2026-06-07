import requests
import logging
import time

from datetime import datetime, timezone
from typing import Callable

from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_RETRIES, OLLAMA_TIMEOUT, LLM_PROVIDER


log = logging.getLogger("infobanjir_rag")


LlmProvider = Callable[[str, str], str]

SYSTEM_PROMPT = (
    "You are a helpful flood intelligence assistant.\n"
    "Answer the question using only the context.\n"
    "If the context is insufficient, say that clearly.\n"
)

def build_prompt(question: str, context: str) -> str:

    today = datetime.now(timezone.utc).date().isoformat()

    return (
        f"{SYSTEM_PROMPT}"
        f"Today (UTC): {today}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )


def log_llm_metrics(model: str, data: dict):
    log.info(
        "ollama.generate model=%s total_ms=%.2f load_ms=%.2f prompt_eval_ms=%.2f eval_ms=%.2f prompt_tokens=%s output_tokens=%s",
        model,
        data.get("total_duration", 0) / 1_000_000,
        data.get("load_duration", 0) / 1_000_000,
        data.get("prompt_eval_duration", 0) / 1_000_000,
        data.get("eval_duration", 0) / 1_000_000,
        data.get("prompt_eval_count"),
        data.get("eval_count"),
    )


def call_ollama(question: str, context: str) -> str:

    prompt = build_prompt(question, context)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "num_predict": 80,
            "temperature": 0.2,
        },
    }

    for attempt in range(1, OLLAMA_RETRIES + 2):
        try:

            start = time.perf_counter()

            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )

            duration_ms = (time.perf_counter() - start) * 1000
            log.info(
                "ollama.request completed duration_ms=%.2f",
                duration_ms,
            )

            response.raise_for_status()
            data = response.json()

            log_llm_metrics(OLLAMA_MODEL, data)

            return (data.get("response") or "").strip()
        
        except Exception as exc:
            if attempt <= OLLAMA_RETRIES:
                time.sleep(0.5 * attempt)
                continue
            raise exc



LLM_PROVIDERS: dict[str, LlmProvider] = {
    "ollama": call_ollama,
}


    
def call_llm(question: str, context: str) -> str:

    try:
        provider = LLM_PROVIDERS[LLM_PROVIDER]
    except KeyError:
        raise RuntimeError("Unsupported provider value")
    
    return provider(question, context)
       

def check_ollama_health() -> bool:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        return True
    except Exception:
        return False

