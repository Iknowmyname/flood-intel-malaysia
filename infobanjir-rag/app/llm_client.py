from datetime import datetime, timezone

import requests

from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


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
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return (data.get("response") or "").strip()
