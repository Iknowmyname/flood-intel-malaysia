import httpx

from .config import EXPRESS_BASE_URL


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


def build_docs_from_water(items: list[dict]) -> list[dict]:
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
