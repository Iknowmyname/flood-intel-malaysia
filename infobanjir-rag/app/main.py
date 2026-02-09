import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import FastAPI
import httpx
from pydantic import BaseModel, Field


app = FastAPI(title="HydroIntel MY RAG", version="0.1.0")


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


DOCS_PATH = Path(__file__).resolve().parent.parent / "data" / "documents.json"
_DOCUMENTS_CACHE: list[dict] | None = None


# Source of truth for ingestion; override in deploy environments.
EXPRESS_BASE_URL = os.getenv("EXPRESS_BASE_URL", "https://flood-monitoring-system.onrender.com")


def _load_documents() -> list[dict]:
    global _DOCUMENTS_CACHE
    if _DOCUMENTS_CACHE is not None:
        return _DOCUMENTS_CACHE
    if not DOCS_PATH.exists():
        _DOCUMENTS_CACHE = []
        return _DOCUMENTS_CACHE
    # Seed cache from disk on first load; subsequent ingests stay in memory.
    with DOCS_PATH.open("r", encoding="utf-8") as handle:
        _DOCUMENTS_CACHE = json.load(handle)
    return _DOCUMENTS_CACHE


def _score_match(text: str, tokens: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for token in tokens if token and token in lowered)


def _retrieve(question: str, top_k: int = 3) -> list[dict]:
    # MVP keyword match; replace with embeddings + vector search later.
    tokens = [t.strip() for t in question.lower().split() if t.strip()]
    documents = _load_documents()
    scored = []
    for doc in documents:
        score = _score_match(doc.get("text", ""), tokens)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def _build_summary_from_hits(hits: list[dict]) -> str:
    if not hits:
        return "No matching sources found in the local knowledge base."
    top_snippet = hits[0].get("text", "").strip()
    if not top_snippet:
        return "Based on retrieved sources, here are the most relevant findings."
    return f"Most relevant reading: {top_snippet}"


class RagExpressIngestRequest(BaseModel):
    state: str | None = None
    limit: int | None = 200
    replace: bool = True


def _fetch_express(path: str, params: dict) -> list[dict]:
    url = f"{EXPRESS_BASE_URL}{path}"
    with httpx.Client(timeout=10) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    return payload.get("items", [])


def _build_docs_from_rain(items: list[dict]) -> list[dict]:
    docs = []
    for item in items:
        docs.append(
            {
                "id": f"rain-{item.get('station_id', 'unknown')}-{item.get('recorded_at', 'na')}",
                "title": f"Rainfall reading {item.get('station_name', 'Unknown')}",
                "source": item.get("source", "express"),
                "text": (
                    f"Rainfall reading at {item.get('station_name', 'Unknown')} "
                    f"in {item.get('district', 'Unknown')}, {item.get('state', 'Unknown')} "
                    f"recorded at {item.get('recorded_at', 'Unknown')} "
                    f"with {item.get('rain_mm', 'Unknown')} mm."
                ),
            }
        )
    return docs


def _build_docs_from_water(items: list[dict]) -> list[dict]:
    docs = []
    for item in items:
        docs.append(
            {
                "id": f"water-{item.get('station_id', 'unknown')}-{item.get('recorded_at', 'na')}",
                "title": f"Water level reading {item.get('station_name', 'Unknown')}",
                "source": item.get("source", "express"),
                "text": (
                    f"Water level reading at {item.get('station_name', 'Unknown')} "
                    f"in {item.get('district', 'Unknown')}, {item.get('state', 'Unknown')} "
                    f"recorded at {item.get('recorded_at', 'Unknown')} "
                    f"with {item.get('river_level_m', 'Unknown')} m."
                ),
            }
        )
    return docs


@app.post("/rag/ingest-from-express", response_model=RagIngestResponse)
def rag_ingest_from_express(payload: RagExpressIngestRequest) -> RagIngestResponse:
    # Manual ingestion endpoint for MVP; schedule this in production.
    params = {}
    if payload.state:
        params["state"] = payload.state
    if payload.limit:
        params["limit"] = payload.limit

    rain_items = _fetch_express("/api/readings/latest/rain", params)
    water_items = _fetch_express("/api/readings/latest/water_level", params)

    docs = _build_docs_from_rain(rain_items) + _build_docs_from_water(water_items)
    documents = _load_documents()
    if payload.replace:
        documents.clear()
    documents.extend(docs)
    return RagIngestResponse(ingested=len(docs), total=len(documents), source="express")


@app.post("/rag/ingest", response_model=RagIngestResponse)
def rag_ingest(payload: RagIngestRequest) -> RagIngestResponse:
    documents = _load_documents()
    added = 0
    for doc in payload.documents:
        documents.append(doc.model_dump())
        added += 1
    return RagIngestResponse(ingested=added, total=len(documents), source="manual")


@app.post("/rag/ask", response_model=RagAskResponse)
def rag_ask(payload: RagAskRequest) -> RagAskResponse:
    # Free-only MVP: keyword-based retrieval from local JSON docs.
    hits = _retrieve(payload.question, top_k=3)
    if hits:
        answer = _build_summary_from_hits(hits)
        citations = [
            RagCitation(
                source=doc.get("source", "local"),
                snippet=doc.get("text", "")[:200],
            )
            for doc in hits
        ]
        confidence = 0.35
    else:
        answer = "No matching sources found in the local knowledge base."
        citations = []
        confidence = 0.1
    return RagAskResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        request_id="stub",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
