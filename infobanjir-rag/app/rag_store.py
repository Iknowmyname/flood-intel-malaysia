import json
from pathlib import Path
from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


DOCS_PATH = Path(__file__).resolve().parent.parent / "data" / "documents.json"

_DOCUMENTS_CACHE: list[dict] | None = None
_EMBED_MODEL: SentenceTransformer | None = None
_INDEX: faiss.Index | None = None
_INDEX_DOCS: list[dict] = []


def load_documents() -> list[dict]:
    global _DOCUMENTS_CACHE
    if _DOCUMENTS_CACHE is not None:
        return _DOCUMENTS_CACHE
    if not DOCS_PATH.exists():
        _DOCUMENTS_CACHE = []
        return _DOCUMENTS_CACHE
    with DOCS_PATH.open("r", encoding="utf-8") as handle:
        _DOCUMENTS_CACHE = json.load(handle)
    return _DOCUMENTS_CACHE


def ingest_documents(documents: list[dict], replace: bool = False) -> None:
    existing = load_documents()
    if replace:
        existing.clear()
    existing.extend(documents)
    build_index(existing)


def get_embedder() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


def embed_texts(texts: list[str]) -> np.ndarray:
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True)
    return np.array(vectors, dtype="float32")


def build_index_from_docs(documents: list[dict]) -> tuple[faiss.Index | None, list[dict]]:
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
    vectors = embed_texts(texts)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index, docs


def build_index(documents: list[dict]) -> None:
    global _INDEX, _INDEX_DOCS
    index, docs = build_index_from_docs(documents)
    _INDEX = index
    _INDEX_DOCS = docs


def ensure_index() -> None:
    if _INDEX is None:
        build_index(load_documents())


def retrieve_semantic_from_docs(question: str, documents: list[dict], top_k: int, min_score: float | None = None) -> list[dict]:
    index, docs = build_index_from_docs(documents)
    if index is None or not docs:
        return []
    qvec = embed_texts([question])
    k = min(top_k, len(docs))
    scores, idxs = index.search(qvec, k)
    hits = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        if min_score is not None and score < min_score:
            continue
        hits.append(docs[idx])
    return hits


def retrieve_semantic(question: str, top_k: int, state: str | None = None) -> list[dict]:
    if state:
        documents = load_documents()
        filtered = [doc for doc in documents if str(doc.get("state", "")).upper() == state]
        return retrieve_semantic_from_docs(question, filtered, top_k)

    ensure_index()
    if _INDEX is None or not _INDEX_DOCS:
        return []
    return retrieve_semantic_from_docs(question, _INDEX_DOCS, top_k)


def score_match(text: str, tokens: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for token in tokens if token and token in lowered)


def retrieve_keyword(question: str, top_k: int) -> list[dict]:
    tokens = [t.strip() for t in question.lower().split() if t.strip()]
    documents = load_documents()
    scored = []
    for doc in documents:
        score = score_match(doc.get("text", ""), tokens)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]
