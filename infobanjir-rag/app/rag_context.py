import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .state_codes import STATE_NAME_TO_CODE, format_state, normalize_state_code


def build_summary_from_hits(hits: list[dict]) -> str:
    if not hits:
        return "No matching sources found in the local knowledge base."
    top_snippet = hits[0].get("text", "").strip()
    if not top_snippet:
        return "Based on retrieved sources, here are the most relevant findings."
    return f"Most relevant reading: {top_snippet}"


def infer_state_from_question(question: str, docs: list[dict]) -> str | None:
    q = question.lower()
    for name, code in STATE_NAME_TO_CODE.items():
        if re.search(rf"\b{re.escape(name)}\b", q):
            return code
    codes = {str(doc.get("state", "")).upper() for doc in docs if doc.get("state")}
    for code in codes:
        if code.lower() in q:
            return normalize_state_code(code)
    return None


def build_context(hits: list[dict]) -> str:
    lines = []
    for i, doc in enumerate(hits, start=1):
        title = doc.get("title", "")
        source = doc.get("source", "local")
        state_label = format_state(doc.get("state"))
        snippet = (doc.get("text") or "").strip().replace("\n", " ")
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        lines.append(f"[{i}] {title} ({source}) | State: {state_label}: {snippet}")
    return "\n".join(lines)


def parse_date_range(question: str) -> tuple[str | None, str | None]:
    q = question.lower()
    if "today" in q:
        today = datetime.now(timezone.utc).date().isoformat()
        return today, today

    between = re.search(r"between\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})", q)
    if between:
        return between.group(1), between.group(2)

    from_to = re.search(r"from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", q)
    if from_to:
        return from_to.group(1), from_to.group(2)

    single = re.search(r"(\d{4}-\d{2}-\d{2})", q)
    if single:
        date = single.group(1)
        return date, date

    return None, None
