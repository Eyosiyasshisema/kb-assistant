import time
from .config import settings
from .db import pool
from .embeddings import embed
from .llm import ask_llm, load_prompt

FALLBACK = ("I'm not confident I can answer that accurately, so I've sent your "
            "question to our team. They'll follow up.")

def retrieve(question: str, k: int) -> list[dict]:
    qv = embed([question])[0]
    with pool.connection() as conn:
        return conn.execute(
            """SELECT c.content, d.id AS document_id, d.title, d.source,
                      1 - (c.embedding <=> %s) AS score
               FROM chunks c JOIN documents d ON d.id = c.document_id
               ORDER BY c.embedding <=> %s LIMIT %s""", (qv, qv, k)).fetchall()

def format_context(hits: list[dict]) -> str:
    return "\n\n".join(f"[{i}] (source: {h['title']})\n{h['content']}"
                       for i, h in enumerate(hits, 1))

def answer_question(question: str, prompt_version: str | None = None) -> dict:
    pv = prompt_version or settings.prompt_version
    t0 = time.perf_counter()
    hits = retrieve(question, settings.top_k)
    top = float(hits[0]["score"]) if hits else 0.0
    res = {"question": question, "prompt_version": pv, "top_score": top,
           "answer": None, "citations": [], "confidence": 0.0, "reason": None,
           "tokens_in": 0, "tokens_out": 0,
           "sources_retrieved": [h["title"] for h in hits]}

    def finish(status: str, reason: str | None = None) -> dict:
        res.update(status=status, reason=reason,
                   latency_ms=int((time.perf_counter() - t0) * 1000))
        return res

    if top < settings.min_retrieval_score:               # guard 1: nothing relevant found
        return finish("escalated", "low_retrieval")      # (skips the LLM call entirely)

    sub, usage = ask_llm(load_prompt(pv), format_context(hits), question)
    res["tokens_in"], res["tokens_out"] = usage["in"], usage["out"]

    if sub is None:                                      # guard 2: LLM failed or returned garbage twice
        return finish("escalated", "llm_invalid_output")
    res["answer"], res["confidence"] = sub.answer, sub.confidence

    if any(not 1 <= c <= len(hits) for c in sub.citations):   # guard 3: hallucinated citation
        return finish("escalated", "invalid_citation")
    if not sub.answerable:
        return finish("escalated", "model_unsure")
    if not sub.citations:                                # guard 4: uncited answers aren't allowed
        return finish("escalated", "no_citations")
    if sub.confidence < settings.min_confidence:         # guard 5: low self-reported confidence
        return finish("escalated", "low_confidence")

    res["citations"] = [
        {"n": c, "document_id": hits[c-1]["document_id"], "title": hits[c-1]["title"],
         "source": hits[c-1]["source"], "snippet": hits[c-1]["content"][:300]}
        for c in dict.fromkeys(sub.citations)]
    return finish("answered")