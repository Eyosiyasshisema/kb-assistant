from app import rag
from app.llm import Submission

HIT = [{"content": "Refunds within 30 days.", "document_id": 1, "title": "returns.md",
        "source": "returns.md", "score": 0.8}]

def run(monkeypatch, sub, hits=HIT):
    monkeypatch.setattr(rag, "retrieve", lambda q, k: hits)
    monkeypatch.setattr(rag, "ask_llm", lambda *a: (sub, {"in": 1, "out": 1}))
    return rag.answer_question("refund window?", prompt_version="v2")

def test_happy_path(monkeypatch):
    r = run(monkeypatch, Submission(answerable=True, answer="30 days", citations=[1], confidence=0.9))
    assert r["status"] == "answered"

def test_invalid_citation_escalates(monkeypatch):
    r = run(monkeypatch, Submission(answerable=True, answer="x", citations=[7], confidence=0.9))
    assert r["reason"] == "invalid_citation"

def test_no_citations_escalates(monkeypatch):
    r = run(monkeypatch, Submission(answerable=True, answer="x", citations=[], confidence=0.9))
    assert r["reason"] == "no_citations"

def test_low_confidence_escalates(monkeypatch):
    r = run(monkeypatch, Submission(answerable=True, answer="x", citations=[1], confidence=0.2))
    assert r["reason"] == "low_confidence"

def test_model_unsure_escalates(monkeypatch):
    r = run(monkeypatch, Submission(answerable=False, answer="", citations=[], confidence=0.9))
    assert r["reason"] == "model_unsure"

def test_garbage_llm_output_escalates(monkeypatch):
    assert run(monkeypatch, None)["reason"] == "llm_invalid_output"

def test_low_retrieval_skips_llm(monkeypatch):
    r = run(monkeypatch, None, hits=[{**HIT[0], "score": 0.1}])
    assert r["reason"] == "low_retrieval"