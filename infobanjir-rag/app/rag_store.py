from typing import List, Optional

from . import config  # ensures telemetry env vars are set before chromadb import

# Chroma telemetry can be noisy or incompatible with local posthog versions.
# Force-disable capture to avoid runtime noise.
try:
    import posthog  # type: ignore

    def _noop(*_args, **_kwargs):
        return None

    posthog.capture = _noop
    posthog.flush = _noop
except Exception:
    pass

import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from .config import CHROMA_COLLECTION, CHROMA_PERSIST_DIR
from .state_codes import get_state_synonyms


_DOCUMENTS_CACHE: list[dict] | None = None
_EMBED_MODEL: SentenceTransformer | None = None
_CHROMA_CLIENT: Optional[chromadb.api.ClientAPI] = None
_CHROMA_COLLECTION: Optional[Collection] = None


def _build_where_clause(
    state: str | None = None,
    doc_type: str | None = None,
    recorded_date: str | None = None,
) -> dict | None:
    clauses: list[dict] = []
    if state:
        clauses.append({"state": {"$in": get_state_synonyms(state)}})
    if doc_type:
        clauses.append({"type": doc_type})
    if recorded_date:
        clauses.append({"recorded_date": recorded_date})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _get_collection() -> Collection:
    global _CHROMA_CLIENT, _CHROMA_COLLECTION
    if _CHROMA_CLIENT is None:
        _CHROMA_CLIENT = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    if _CHROMA_COLLECTION is None:
        _CHROMA_COLLECTION = _CHROMA_CLIENT.get_or_create_collection(
            name=CHROMA_COLLECTION
        )
    return _CHROMA_COLLECTION


def load_documents() -> list[dict]:
    global _DOCUMENTS_CACHE
    if _DOCUMENTS_CACHE is not None:
        return _DOCUMENTS_CACHE
    collection = _get_collection()
    payload = collection.get(include=["documents", "metadatas"])
    docs = []
    for text, meta, doc_id in zip(
        payload.get("documents", []),
        payload.get("metadatas", []),
        payload.get("ids", []),
    ):
        doc = dict(meta or {})
        doc["id"] = doc_id
        doc["text"] = text
        state = doc.get("state")
        if state:
            doc["state"] = str(state).upper()
        docs.append(doc)
    _DOCUMENTS_CACHE = docs
    return _DOCUMENTS_CACHE


def ingest_documents(documents: list[dict], replace: bool = False) -> None:
    collection = _get_collection()
    if replace:
        existing = collection.get(include=["documents"])
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        _reset_cache()

    ids = []
    texts = []
    metas = []
    for doc in documents:
        doc_id = str(doc.get("id"))
        if not doc_id:
            continue
        ids.append(doc_id)
        texts.append(doc.get("text", ""))
        recorded_at = doc.get("recorded_at") or ""
        recorded_date = recorded_at[:10] if isinstance(recorded_at, str) else ""
        metas.append(
            {
                "title": doc.get("title"),
                "source": doc.get("source"),
                "type": doc.get("type"),
                "state": doc.get("state"),
                "recorded_at": recorded_at,
                "recorded_date": recorded_date,
                "value": doc.get("value"),
            }
        )

    if ids:
        embeddings = embed_texts(texts)
        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metas,
            embeddings=embeddings,
        )

    _reset_cache()


def _reset_cache() -> None:
    global _DOCUMENTS_CACHE
    _DOCUMENTS_CACHE = None


def get_embedder() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def retrieve_semantic(
    question: str,
    top_k: int,
    state: str | None = None,
    doc_type: str | None = None,
    recorded_date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_score: float | None = None,
) -> list[dict]:
    collection = _get_collection()
    where = _build_where_clause(
        state=state,
        doc_type=doc_type,
        recorded_date=recorded_date,
    )
    candidate_k = top_k * 5 if (date_from or date_to) else top_k
    qvec = embed_texts([question])
    result = collection.query(
        query_embeddings=qvec,
        n_results=candidate_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    distances = (result.get("distances") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    texts = (result.get("documents") or [[]])[0]
    for distance, meta, text in zip(distances, metas, texts):
        score = 1.0 - float(distance)
        if min_score is not None and score < min_score:
            continue
        doc = dict(meta or {})
        doc["text"] = text
        if date_from or date_to:
            doc_date = str(doc.get("recorded_date") or "")
            if date_from and doc_date < date_from:
                continue
            if date_to and doc_date > date_to:
                continue
        hits.append(doc)
        if len(hits) >= top_k:
            break
    return hits


def score_match(text: str, tokens: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for token in tokens if token and token in lowered)


def retrieve_keyword(
    question: str,
    top_k: int,
    state: str | None = None,
    doc_type: str | None = None,
    recorded_date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    tokens = [t.strip() for t in question.lower().split() if t.strip()]
    documents = load_documents()
    scored = []
    for doc in documents:
        if state and str(doc.get("state", "")).upper() not in get_state_synonyms(state):
            continue
        if doc_type and str(doc.get("type", "")).lower() != doc_type.lower():
            continue
        if recorded_date and str(doc.get("recorded_date", "")) != recorded_date:
            continue
        doc_date = str(doc.get("recorded_date") or "")
        if date_from and doc_date < date_from:
            continue
        if date_to and doc_date > date_to:
            continue
        score = score_match(doc.get("text", ""), tokens)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def get_stats() -> dict:
    collection = _get_collection()
    payload = collection.get(include=["documents"])
    total = len(payload.get("documents", []))
    return {
        "total_documents": total,
        "collection": CHROMA_COLLECTION,
        "persist_dir": CHROMA_PERSIST_DIR,
    }
