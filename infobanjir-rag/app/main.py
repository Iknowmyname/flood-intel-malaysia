import logging
import threading
import time
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .config import (
    AUTO_INGEST_ON_STARTUP,
    AUTO_INGEST_REFRESH_SECONDS,
    EXPRESS_DEFAULT_LIMIT,
    RAG_MIN_SCORE,
    RAG_TOP_K,
    RAG_USE_LLM,
)
from .ingest import ingest_from_express
from .llm_client import call_ollama, check_ollama_health
from .rag_context import build_context, build_summary_from_hits, infer_state_from_question, parse_date_range
from .rag_store import get_stats, ingest_documents, load_documents, retrieve_keyword, retrieve_semantic


app = FastAPI(title="HydroIntel MY RAG", version="0.1.0")
log = logging.getLogger("infobanjir_rag")


class RagAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class RagCitation(BaseModel):
    source: str
    snippet: str


class RagAskResponse(BaseModel):
    answer: str
    citations: List[RagCitation]
    confidence: float
    request_id: str
    timestamp: str


class RagDocument(BaseModel):
    id: str
    title: str
    source: str
    text: str


class RagIngestRequest(BaseModel):
    documents: List[RagDocument] = Field(default_factory=list)


class RagIngestResponse(BaseModel):
    ingested: int
    total: int
    source: str


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "infobanjir-rag",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/llm")
def health_llm() -> dict:
    return {
        "status": "ok" if check_ollama_health() else "unavailable",
        "service": "ollama",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/rag/stats")
def rag_stats() -> dict:
    stats = get_stats()
    stats["timestamp"] = datetime.now(timezone.utc).isoformat()
    return stats


@app.get("/rag/stats/by-state")
def rag_stats_by_state() -> dict:
    documents = load_documents()
    counts = {}
    latest_dates = {}
    for doc in documents:
        state = str(doc.get("state", "Unknown")).upper()
        counts[state] = counts.get(state, 0) + 1
        recorded_date = str(doc.get("recorded_date") or "")
        if recorded_date:
            prev = latest_dates.get(state)
            if prev is None or recorded_date > prev:
                latest_dates[state] = recorded_date
    return {
        "counts": counts,
        "latest_dates": latest_dates,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class RagExpressIngestRequest(BaseModel):
    state: str | None = None
    limit: int | None = None
    replace: bool = True


@app.post("/rag/ingest-from-express", response_model=RagIngestResponse)
def rag_ingest_from_express(payload: RagExpressIngestRequest) -> RagIngestResponse:
    docs = ingest_from_express(state=payload.state, limit=payload.limit)
    ingest_documents(docs, replace=payload.replace)
    return RagIngestResponse(ingested=len(docs), total=len(load_documents()), source="express")


@app.post("/rag/ingest", response_model=RagIngestResponse)
def rag_ingest(payload: RagIngestRequest) -> RagIngestResponse:
    docs = [doc.model_dump() for doc in payload.documents]
    ingest_documents(docs, replace=False)
    return RagIngestResponse(ingested=len(docs), total=len(load_documents()), source="manual")


@app.post("/rag/ask", response_model=RagAskResponse)
def rag_ask(payload: RagAskRequest) -> RagAskResponse:
    documents = load_documents()
    question = payload.question or ""
    q = question.lower()
    state = infer_state_from_question(question, documents)
    date_from, date_to = parse_date_range(question)

    hits: list[dict] = []
    hits = retrieve_semantic(
        question,
        top_k=RAG_TOP_K,
        state=state,
        date_from=date_from,
        date_to=date_to,
        min_score=RAG_MIN_SCORE,
    )
    if not hits:
        hits = retrieve_keyword(
            question,
            top_k=RAG_TOP_K,
            state=state,
            date_from=date_from,
            date_to=date_to,
        )

    if hits:
        context = build_context(hits)
        if RAG_USE_LLM:
            try:
                answer = call_ollama(question, context)
                confidence = 0.55
            except Exception:
                log.exception("LLM call failed; falling back to summary")
                answer = "LLM unavailable; " + build_summary_from_hits(hits)
                confidence = 0.35
        else:
            answer = build_summary_from_hits(hits)
            confidence = 0.35
    else:
        answer = "No matching sources found in the local knowledge base."
        confidence = 0.1

    citations = [
        RagCitation(
            source=doc.get("source", "local"),
            snippet=(doc.get("text", "")[:200]),
        )
        for doc in hits
    ]

    return RagAskResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        request_id="stub",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _auto_ingest_loop() -> None:
    while True:
        success = True
        message = "ok"
        ingested = 0
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            docs = ingest_from_express(state=None, limit=EXPRESS_DEFAULT_LIMIT)
            ingest_documents(docs, replace=True)
            ingested = len(docs)
            log.info("Auto-ingest refreshed %s documents", ingested)
        except Exception:
            log.exception("Auto-ingest failed")
            success = False
            message = "failed"
        _set_ingest_status(
            success=success,
            ingested=ingested,
            message=message,
            started_at=started_at,
        )
        time.sleep(AUTO_INGEST_REFRESH_SECONDS)


@app.on_event("startup")
def startup_ingest() -> None:
    if not AUTO_INGEST_ON_STARTUP:
        return
    thread = threading.Thread(target=_auto_ingest_loop, daemon=True)
    thread.start()


_INGEST_STATUS = {
    "last_success": None,
    "last_failure": None,
    "last_ingested": 0,
    "last_message": "never_run",
    "last_started_at": None,
}


def _set_ingest_status(success: bool, ingested: int, message: str, started_at: str) -> None:
    if success:
        _INGEST_STATUS["last_success"] = datetime.now(timezone.utc).isoformat()
    else:
        _INGEST_STATUS["last_failure"] = datetime.now(timezone.utc).isoformat()
    _INGEST_STATUS["last_ingested"] = ingested
    _INGEST_STATUS["last_message"] = message
    _INGEST_STATUS["last_started_at"] = started_at


@app.get("/rag/ingest/status")
def rag_ingest_status() -> dict:
    return {
        **_INGEST_STATUS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
