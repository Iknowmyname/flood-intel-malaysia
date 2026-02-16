STATE_NAME_TO_CODE = {
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

# Express/publicinfobanjir codes -> canonical codes
STATE_CODE_ALIASES = {
    "KDH": "KED",
    "KEL": "KTN",
    "SRK": "SWK",
    "SAB": "SBH",
    "WLH": "KUL",  # Wilayah Persekutuan Kuala Lumpur
    "WLP": "LBN",  # Wilayah Persekutuan Labuan
}

STATE_CODE_SYNONYMS = {
    "KED": ["KED", "KDH"],
    "KTN": ["KTN", "KEL"],
    "SWK": ["SWK", "SRK"],
    "SBH": ["SBH", "SAB"],
    "KUL": ["KUL", "WLH"],
    "LBN": ["LBN", "WLP"],
}

CODE_TO_STATE = {
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

CANONICAL_STATE_CODES = sorted(CODE_TO_STATE.keys())


def normalize_state_code(raw: str | None) -> str | None:
    if not raw:
        return None
    code = str(raw).upper()
    return STATE_CODE_ALIASES.get(code, code)


def get_state_synonyms(code: str | None) -> list[str]:
    if not code:
        return []
    canon = normalize_state_code(code)
    return STATE_CODE_SYNONYMS.get(canon, [canon])


def format_state(code: str | None) -> str:
    if not code:
        return "Unknown"
    canon = normalize_state_code(code)
    name = CODE_TO_STATE.get(canon)
    if name:
        return f"{name} ({canon})"
    return canon
