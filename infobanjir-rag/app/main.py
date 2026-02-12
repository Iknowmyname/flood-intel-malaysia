import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
import httpx
import numpy as np
from pydantic import BaseModel, Field
import requests
import logging
import faiss
from sentence_transformers import SentenceTransformer


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


DOCS_PATH = Path(__file__).resolve().parent.parent / "data" / "documents.json"
_DOCUMENTS_CACHE: list[dict] | None = None

# Embedding + vector index (in-memory)
_EMBED_MODEL: SentenceTransformer | None = None
_INDEX: faiss.Index | None = None
_INDEX_DOCS: list[dict] = []


# Source of truth for ingestion; override in deploy environments.
EXPRESS_BASE_URL = os.getenv("EXPRESS_BASE_URL", "https://flood-monitoring-system.onrender.com")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "20"))
RAG_USE_LLM = True
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))


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


def _get_embedder() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


def _embed_texts(texts: list[str]) -> np.ndarray:
    model = _get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return np.array(vectors, dtype="float32")


def _build_index_from_docs(documents: list[dict]) -> tuple[faiss.Index | None, list[dict]]:
    if not documents:
        return None, []
    texts = []
    docs = []
    for doc in documents:
        title = doc.get("title") or ""
        body = doc.get("text") or ""
        combined = (title + "\n" + body).strip()
        if not combined:
            continue
        texts.append(combined)
        docs.append(doc)
    if not texts:
        return None, []
    vectors = _embed_texts(texts)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index, docs


def _retrieve_semantic_from_docs(question: str, documents: list[dict], top_k: int) -> list[dict]:
    index, docs = _build_index_from_docs(documents)
    if index is None or not docs:
        return []
    qvec = _embed_texts([question])
    k = min(top_k, len(docs))
    scores, idxs = index.search(qvec, k)
    hits = []
    for idx in idxs[0]:
        if idx == -1:
            continue
        hits.append(docs[idx])
    return hits


def _build_index(documents: list[dict]) -> None:
    global _INDEX, _INDEX_DOCS
    index, docs = _build_index_from_docs(documents)
    _INDEX = index
    _INDEX_DOCS = docs


def _ensure_index() -> None:
    if _INDEX is None:
        documents = _load_documents()
        _build_index(documents)


def _retrieve_semantic(question: str, top_k: int = 3, state: str | None = None) -> list[dict]:
    if state:
        documents = _load_documents()
        filtered = [doc for doc in documents if str(doc.get("state", "")).upper() == state]
        hits = _retrieve_semantic_from_docs(question, filtered, top_k)
        if hits:
            return hits
        return _retrieve(question, top_k=top_k)

    _ensure_index()
    if _INDEX is None or not _INDEX_DOCS:
        return _retrieve(question, top_k=top_k)
    hits = _retrieve_semantic_from_docs(question, _INDEX_DOCS, top_k)
    if not hits:
        return _retrieve(question, top_k=top_k)
    return hits


def _build_context(hits: list[dict]) -> str:
    lines = []
    for i, doc in enumerate(hits, start=1):
        title = doc.get("title", "")
        source = doc.get("source", "local")
        state_label = _format_state(doc.get("state"))
        snippet = (doc.get("text") or "").strip().replace("\n", " ")
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        lines.append(f"[{i}] {title} ({source}) | State: {state_label}: {snippet}")
    return "\n".join(lines)


def _call_ollama(question: str, context: str) -> str:
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


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = p * (len(sorted_vals) - 1)
    low = int(idx)
    high = min(low + 1, len(sorted_vals) - 1)
    frac = idx - low
    return sorted_vals[low] + (sorted_vals[high] - sorted_vals[low]) * frac


def _infer_state_from_question(question: str, docs: list[dict]) -> str | None:
    q = question.lower()
    # Common Malaysia state name to code mapping alligned with express API codes
    name_to_code = {
        "selangor": "SEL",
        "kedah": "KED",
        "penang": "PNG",
        "pulau pinang": "PNG",
        "kelantan": "KTN",
        "johor": "JHR",
        "perak": "PRK",
        "pahang": "PHG",
        "terengganu": "TRG",
        "negeri sembilan": "NSN",
        "melaka": "MLK",
        "perlis": "PLS",
        "sabah": "SBH",
        "sarawak": "SWK",
        "kuala lumpur": "KUL",
        "putrajaya": "PTJ",
        "labuan": "LBN",
    }
    for name, code in name_to_code.items():
        if name in q:
            return code
    # Fallback: look for any state codes already present in docs.
    codes = {str(doc.get("state", "")).upper() for doc in docs if doc.get("state")}
    for code in codes:
        if code.lower() in q:
            return code
    return None


_CODE_TO_STATE = {
    "SEL": "Selangor",
    "KED": "Kedah",
    "PNG": "Penang",
    "KTN": "Kelantan",
    "JHR": "Johor",
    "PRK": "Perak",
    "PHG": "Pahang",
    "TRG": "Terengganu",
    "NSN": "Negeri Sembilan",
    "MLK": "Melaka",
    "PLS": "Perlis",
    "SBH": "Sabah",
    "SWK": "Sarawak",
    "KUL": "Kuala Lumpur",
    "PTJ": "Putrajaya",
    "LBN": "Labuan",
}


def _format_state(state: str | None) -> str:
    if not state:
        return "Unknown"
    code = str(state).upper()
    name = _CODE_TO_STATE.get(code)
    if name:
        return f"{name} ({code})"
    return code


def _extract_values(docs: list[dict], doc_type: str, state: str | None) -> list[float]:
    values = []
    for doc in docs:
        if doc.get("type") != doc_type:
            continue
        if state and str(doc.get("state", "")).upper() != state:
            continue
        value = doc.get("value")
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _classify_rainfall_intensity(mm: float) -> str:
    if mm <= 10:
        return "Light"
    if mm <= 30:
        return "Moderate"
    if mm <= 60:
        return "Heavy"
    return "Very Heavy"


def _water_level_risk(values: list[float]) -> str:
    if not values:
        return "Unknown"
    p70 = _percentile(values, 0.7)
    p90 = _percentile(values, 0.9)
    max_val = max(values)
    if p90 is not None and max_val >= p90:
        return "High"
    if p70 is not None and max_val >= p70:
        return "Elevated"
    return "Normal"


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
                "type": "rainfall",
                "state": item.get("state", "Unknown"),
                "recorded_at": item.get("recorded_at"),
                "value": item.get("rain_mm"),
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
                "type": "water_level",
                "state": item.get("state", "Unknown"),
                "recorded_at": item.get("recorded_at"),
                "value": item.get("river_level_m"),
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
    _build_index(documents)
    return RagIngestResponse(ingested=len(docs), total=len(documents), source="express")


@app.post("/rag/ingest", response_model=RagIngestResponse)
def rag_ingest(payload: RagIngestRequest) -> RagIngestResponse:
    documents = _load_documents()
    added = 0
    for doc in payload.documents:
        documents.append(doc.model_dump())
        added += 1
    _build_index(documents)
    return RagIngestResponse(ingested=added, total=len(documents), source="manual")


@app.post("/rag/ask", response_model=RagAskResponse)
def rag_ask(payload: RagAskRequest) -> RagAskResponse:
    # Baseline ask function for early RAG testing
    docs = _load_documents()
    question = payload.question or ""
    q = question.lower()
    state = _infer_state_from_question(question, docs)

    wants_rain = "rain" in q or "rainfall" in q
    wants_water = "water level" in q or "river level" in q
    wants_average = "average" in q or "mean" in q
    wants_risk = "risk" in q or "possibility" in q or "flood" in q
    wants_opinion = "what do you think" in q or "status" in q

    answer = ""
    citations = []
    confidence = 0.4

    if "today" in q:
        documents = _load_documents()
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
        hits = _retrieve_semantic_from_docs(question, documents, RAG_TOP_K)
        if not hits:
            hits = _retrieve(question, top_k=RAG_TOP_K)
    else:
        hits = _retrieve_semantic(question, top_k=RAG_TOP_K, state=state)
    if hits:
        context = _build_context(hits)
        if RAG_USE_LLM:
            try:
                answer = _call_ollama(question, context)
                confidence = 0.55
            except Exception:
                log.exception("LLM call failed; falling back to summary")
                answer = _build_summary_from_hits(hits)
                confidence = 0.35
        else:
            answer = _build_summary_from_hits(hits)
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
