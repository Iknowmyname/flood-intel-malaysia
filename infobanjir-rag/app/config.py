import os

# Default runtime settings for local development (no env vars required).
os.environ.setdefault("CHROMA_TELEMETRY", "false")
os.environ.setdefault("CHROMA_ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("POSTHOG_DISABLED", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

EXPRESS_BASE_URL = os.getenv("EXPRESS_BASE_URL", "https://flood-monitoring-system.onrender.com")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

RAG_USE_LLM = True
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.1"))

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "readings")

AUTO_INGEST_ON_STARTUP = os.getenv("AUTO_INGEST_ON_STARTUP", "true").lower() in ("1", "true", "yes")
AUTO_INGEST_REFRESH_SECONDS = int(os.getenv("AUTO_INGEST_REFRESH_SECONDS", "600"))
EXPRESS_DEFAULT_LIMIT = int(os.getenv("EXPRESS_DEFAULT_LIMIT", "1000"))
