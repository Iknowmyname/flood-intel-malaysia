import httpx

from .config import EXPRESS_BASE_URL, EXPRESS_DEFAULT_LIMIT
from .state_codes import CANONICAL_STATE_CODES, normalize_state_code, to_upstream_state_code


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


def _safe_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _risk_level(score: float) -> str:
    if score >= 65.0:
        return "High"
    if score >= 35.0:
        return "Moderate"
    return "Low"


def build_docs_from_flood_risk(rain_items: list[dict], water_items: list[dict]) -> list[dict]:
    by_state: dict[str, dict[str, object]] = {}

    for item in rain_items:
        state = normalize_state_code(item.get("state")) or "Unknown"
        row = by_state.setdefault(
            state,
            {
                "max_rain": None,
                "max_rain_station": "Unknown station",
                "max_water": None,
                "max_water_station": "Unknown station",
                "latest_recorded_at": "",
            },
        )
        rain = _safe_float(item.get("rain_mm"))
        if rain is not None and (row["max_rain"] is None or rain > row["max_rain"]):
            row["max_rain"] = rain
            row["max_rain_station"] = item.get("station_name") or "Unknown station"
        recorded_at = str(item.get("recorded_at") or "")
        if recorded_at and recorded_at > row["latest_recorded_at"]:
            row["latest_recorded_at"] = recorded_at

    for item in water_items:
        state = normalize_state_code(item.get("state")) or "Unknown"
        row = by_state.setdefault(
            state,
            {
                "max_rain": None,
                "max_rain_station": "Unknown station",
                "max_water": None,
                "max_water_station": "Unknown station",
                "latest_recorded_at": "",
            },
        )
        water = _safe_float(item.get("river_level_m"))
        if water is not None and (row["max_water"] is None or water > row["max_water"]):
            row["max_water"] = water
            row["max_water_station"] = item.get("station_name") or "Unknown station"
        recorded_at = str(item.get("recorded_at") or "")
        if recorded_at and recorded_at > row["latest_recorded_at"]:
            row["latest_recorded_at"] = recorded_at

    all_rain_values = [_safe_float(item.get("rain_mm")) for item in rain_items]
    all_water_values = [_safe_float(item.get("river_level_m")) for item in water_items]
    max_rain_global = max((v for v in all_rain_values if v is not None), default=0.0)
    max_water_global = max((v for v in all_water_values if v is not None), default=0.0)

    docs = []
    for state, row in by_state.items():
        max_rain = row["max_rain"]
        max_water = row["max_water"]

        rain_norm = 0.0 if max_rain is None or max_rain_global <= 0 else max_rain / max_rain_global
        water_norm = 0.0 if max_water is None or max_water_global <= 0 else max_water / max_water_global

        score = round((0.5 * rain_norm + 0.5 * water_norm) * 100.0, 1)
        risk_level = _risk_level(score)
        recorded_at = str(row["latest_recorded_at"] or "Unknown time")
        recorded_date = recorded_at[:10] if len(recorded_at) >= 10 else "na"
        rain_label = "n/a" if max_rain is None else f"{max_rain:.2f} mm"
        water_label = "n/a" if max_water is None else f"{max_water:.2f} m"

        docs.append(
            {
                "id": f"risk-{state}-{recorded_date}",
                "title": f"Heuristic flood risk summary for {state}",
                "source": "derived_heuristic",
                "type": "flood_risk",
                "state": state,
                "recorded_at": recorded_at,
                "value": score,
                "text": (
                    f"Flood risk in {state} is assessed as {risk_level} "
                    f"(score {score}/100) based on latest available readings. "
                    f"Highest recent rainfall: {rain_label} at {row['max_rain_station']}. "
                    f"Highest recent river level: {water_label} at {row['max_water_station']}. "
                    "This is a heuristic estimate from observed rainfall and river levels, "
                    "not an official warning classification."
                ),
            }
        )

    return docs


def ingest_from_express(state: str | None = None, limit: int | None = None) -> list[dict]:
    limit = limit if limit is not None else EXPRESS_DEFAULT_LIMIT

    if state:
        upstream_state = to_upstream_state_code(state)
        params = {"state": upstream_state, "limit": limit}
        rain_items = fetch_express("/api/readings/latest/rain", params)
        water_items = fetch_express("/api/readings/latest/water_level", params)
        risk_docs = build_docs_from_flood_risk(rain_items, water_items)
        return build_docs_from_rain(rain_items) + build_docs_from_water(water_items) + risk_docs

    # No state specified: pull for every state to maximize coverage.
    all_docs = {}
    all_rain_items = []
    all_water_items = []
    for code in CANONICAL_STATE_CODES:
        upstream_state = to_upstream_state_code(code)
        params = {"state": upstream_state, "limit": limit}
        rain_items = fetch_express("/api/readings/latest/rain", params)
        water_items = fetch_express("/api/readings/latest/water_level", params)
        all_rain_items.extend(rain_items)
        all_water_items.extend(water_items)
        for doc in build_docs_from_rain(rain_items) + build_docs_from_water(water_items):
            doc_id = doc.get("id")
            if doc_id:
                all_docs[doc_id] = doc
    for doc in build_docs_from_flood_risk(all_rain_items, all_water_items):
        doc_id = doc.get("id")
        if doc_id:
            all_docs[doc_id] = doc
    return list(all_docs.values())
