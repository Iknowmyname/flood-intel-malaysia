from typing import List


def build_summary_from_hits(hits: list[dict]) -> str:
    if not hits:
        return "No matching sources found in the local knowledge base."
    top_snippet = hits[0].get("text", "").strip()
    if not top_snippet:
        return "Based on retrieved sources, here are the most relevant findings."
    return f"Most relevant reading: {top_snippet}"


def infer_state_from_question(question: str, docs: list[dict]) -> str | None:
    q = question.lower()
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


def format_state(state: str | None) -> str:
    if not state:
        return "Unknown"
    code = str(state).upper()
    name = _CODE_TO_STATE.get(code)
    if name:
        return f"{name} ({code})"
    return code


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
