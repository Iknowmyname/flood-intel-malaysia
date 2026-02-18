import httpx

from .config import EXPRESS_BASE_URL, EXPRESS_DEFAULT_LIMIT
from .state_codes import CANONICAL_STATE_CODES, normalize_state_code


def fetch_express(path: str, params: dict) -> list[dict]:
    url = f"{EXPRESS_BASE_URL}{path}"
    with httpx.Client(timeout=10) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    return payload.get("items", [])


def build_docs_from_rain(items: list[dict]) -> list[dict]:
    docs = []
    for item in items:
        state = normalize_state_code(item.get("state")) or "Unknown"
        docs.append(
            {
                "id": f"rain-{item.get('station_id', 'unknown')}-{item.get('recorded_at', 'na')}",
                "title": f"Rainfall reading {item.get('station_name', 'Unknown')}",
                "source": item.get("source", "express"),
                "type": "rainfall",
                "state": state,
                "recorded_at": item.get("recorded_at"),
                "value": item.get("rain_mm"),
                "text": (
                    f"Rainfall reading at {item.get('station_name', 'Unknown')} "
                    f"in {item.get('district', 'Unknown')}, {state} "
                    f"recorded at {item.get('recorded_at', 'Unknown')} "
                    f"with {item.get('rain_mm', 'Unknown')} mm."
                ),
            }
        )
    return docs


def build_docs_from_water(items: list[dict]) -> list[dict]:
    docs = []
    for item in items:
        state = normalize_state_code(item.get("state")) or "Unknown"
        docs.append(
            {
                "id": f"water-{item.get('station_id', 'unknown')}-{item.get('recorded_at', 'na')}",
                "title": f"Water level reading {item.get('station_name', 'Unknown')}",
                "source": item.get("source", "express"),
                "type": "water_level",
                "state": state,
                "recorded_at": item.get("recorded_at"),
                "value": item.get("river_level_m"),
                "text": (
                    f"Water level reading at {item.get('station_name', 'Unknown')} "
                    f"in {item.get('district', 'Unknown')}, {state} "
                    f"recorded at {item.get('recorded_at', 'Unknown')} "
                    f"with {item.get('river_level_m', 'Unknown')} m."
                ),
            }
        )
    return docs
def ingest_from_express(state: str | None = None, limit: int | None = None) -> list[dict]:
    limit = limit if limit is not None else EXPRESS_DEFAULT_LIMIT

    if state:
        params = {"state": state, "limit": limit}
        rain_items = fetch_express("/api/readings/latest/rain", params)
        water_items = fetch_express("/api/readings/latest/water_level", params)
        return build_docs_from_rain(rain_items) + build_docs_from_water(water_items)

    # No state specified: pull for every state to maximize coverage.
    all_docs = {}
    for code in CANONICAL_STATE_CODES:
        params = {"state": code, "limit": limit}
        rain_items = fetch_express("/api/readings/latest/rain", params)
        water_items = fetch_express("/api/readings/latest/water_level", params)
        for doc in build_docs_from_rain(rain_items) + build_docs_from_water(water_items):
            doc_id = doc.get("id")
            if doc_id:
                all_docs[doc_id] = doc
    return list(all_docs.values())
