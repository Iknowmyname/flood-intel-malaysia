import logging
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .config import RAG_MIN_SCORE, RAG_TOP_K, RAG_USE_LLM
from .ingest import build_docs_from_rain, build_docs_from_water, fetch_express
from .llm_client import call_ollama, check_ollama_health
from .rag_context import build_context, build_summary_from_hits, infer_state_from_question
from .rag_store import ingest_documents, load_documents, retrieve_keyword, retrieve_semantic_from_docs


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


class RagExpressIngestRequest(BaseModel):
    state: str | None = None
    limit: int | None = 200
    replace: bool = True


@app.post("/rag/ingest-from-express", response_model=RagIngestResponse)
def rag_ingest_from_express(payload: RagExpressIngestRequest) -> RagIngestResponse:
    params = {}
    if payload.state:
        params["state"] = payload.state
    if payload.limit:
        params["limit"] = payload.limit

    rain_items = fetch_express("/api/readings/latest/rain", params)
    water_items = fetch_express("/api/readings/latest/water_level", params)

    docs = build_docs_from_rain(rain_items) + build_docs_from_water(water_items)
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

    hits: list[dict] = []
    if "today" in q:
        if state:
            documents = [doc for doc in documents if str(doc.get("state", "")).upper() == state]
        dates = []
        for doc in documents:
            recorded_at = doc.get("recorded_at")
            if isinstance(recorded_at, str) and recorded_at:
                dates.append(recorded_at[:10])
        if dates:
            latest = max(dates)
            documents = [
                doc for doc in documents
                if str(doc.get("recorded_at", ""))[:10] == latest
            ]
        hits = retrieve_semantic_from_docs(question, documents, RAG_TOP_K, min_score=RAG_MIN_SCORE)
        if not hits:
            hits = retrieve_keyword(question, top_k=RAG_TOP_K)
    else:
        if state:
            documents = [doc for doc in documents if str(doc.get("state", "")).upper() == state]
        hits = retrieve_semantic_from_docs(question, documents, RAG_TOP_K, min_score=RAG_MIN_SCORE)
        if not hits:
            hits = retrieve_keyword(question, top_k=RAG_TOP_K)

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
