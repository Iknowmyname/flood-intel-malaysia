import app.rag_store as store


def test_retrieve_keyword_finds_match():
    store._DOCUMENTS_CACHE = [
        {"text": "Rainfall reading in Selangor with 5 mm."},
        {"text": "Water level reading in Johor."},
    ]
    hits = store.retrieve_keyword("rainfall selangor", top_k=3)
    assert hits
    assert "Rainfall" in hits[0]["text"]
