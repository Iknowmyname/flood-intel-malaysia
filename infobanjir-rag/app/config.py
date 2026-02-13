import os

EXPRESS_BASE_URL = os.getenv("EXPRESS_BASE_URL", "https://flood-monitoring-system.onrender.com")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "20"))
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

RAG_USE_LLM = True
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.25"))
