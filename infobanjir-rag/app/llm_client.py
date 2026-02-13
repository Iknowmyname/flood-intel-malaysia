from datetime import datetime, timezone

import time

import requests

from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_RETRIES, OLLAMA_TIMEOUT


def call_ollama(question: str, context: str) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    prompt = (
        "You are a helpful flood intelligence assistant. "
        "Answer the question using only the context. "
        "If the context is insufficient, say that clearly.\n"
        f"Today (UTC): {today}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    last_error = None
    for attempt in range(1, OLLAMA_RETRIES + 2):
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return (data.get("response") or "").strip()
        except Exception as exc:
            last_error = exc
            if attempt <= OLLAMA_RETRIES:
                time.sleep(0.5 * attempt)
                continue
            raise last_error


def check_ollama_health() -> bool:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        return True
    except Exception:
        return False
