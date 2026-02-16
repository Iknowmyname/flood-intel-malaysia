from app.rag_context import build_context, build_summary_from_hits, format_state, infer_state_from_question


def test_format_state_known_code():
    assert format_state("SEL") == "Selangor (SEL)"


def test_infer_state_from_question():
    docs = [{"state": "SEL"}]
    assert infer_state_from_question("Flood risk in Selangor", docs) == "SEL"


def test_build_context_includes_state():
    hits = [
        {
            "title": "Rainfall reading Station A",
            "source": "express",
            "state": "SEL",
            "text": "Rainfall reading at Station A in Klang, SEL recorded at 2026-02-12.",
        }
    ]
    context = build_context(hits)
    assert "State: Selangor (SEL)" in context


def test_build_summary_from_flood_risk_hits():
    hits = [
        {
            "type": "flood_risk",
            "state": "SEL",
            "value": 68.2,
            "recorded_at": "2026-02-16T08:00:00Z",
        }
    ]
    summary = build_summary_from_hits(hits)
    assert "heuristic" in summary.lower()
    assert "Selangor (SEL)" in summary
    assert "68.2/100" in summary
