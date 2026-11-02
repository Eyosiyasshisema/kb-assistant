import json, os, sys, time
from pathlib import Path
from app.db import pool
from app.rag import answer_question

SLEEP_SECONDS = 5   # stays under free-tier requests-per-minute limits
QUESTIONS = Path(os.getenv("QUESTIONS_FILE", "eval/questions.jsonl"))

def norm(s: str | None) -> str:
    return (s or "").lower().replace(",", "")

def evaluate(version: str):
    rows = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    m = dict(ans_total=0, unans_total=0, hit=0, answered=0, cited=0, correct=0,
             escalated_ok=0, hallucinated=0)
    details, ans_scores, unans_scores = [], [], []
    for q in rows:
        r = answer_question(q["question"], prompt_version=version)
        answered = r["status"] == "answered"
        d = {"question": q["question"], "answerable": q["answerable"], "status": r["status"],
             "reason": r["reason"], "top_score": round(r["top_score"], 3), "answer": r["answer"],
             "cited": [c["title"] for c in r["citations"]], "problems": []}
        if q["answerable"]:
            m["ans_total"] += 1
            ans_scores.append(r["top_score"])
            exp = set(q["expected_sources"])
            if exp & set(r["sources_retrieved"]):
                m["hit"] += 1
            else:
                d["problems"].append("retrieval_miss")
            if answered:
                m["answered"] += 1
                if exp & {c["title"] for c in r["citations"]}:
                    m["cited"] += 1
                else:
                    d["problems"].append("wrong_citation")
                if all(norm(s) in norm(r["answer"]) for s in q["must_contain"]):
                    m["correct"] += 1
                else:
                    d["problems"].append("answer_missing_fact")
            else:
                d["problems"].append(f"wrongly_escalated:{r['reason']}")
        else:
            m["unans_total"] += 1
            unans_scores.append(r["top_score"])
            if answered:
                m["hallucinated"] += 1
                d["problems"].append("answered_unanswerable")
            else:
                m["escalated_ok"] += 1
        details.append(d)
        time.sleep(SLEEP_SECONDS)
    m["min_score_answerable"] = round(min(ans_scores), 3) if ans_scores else None
    m["max_score_unanswerable"] = round(max(unans_scores), 3) if unans_scores else None
    return m, details

if __name__ == "__main__":
    versions = sys.argv[1:] or ["v1", "v2"]
    lines = ["| prompt | retrieval hit@5 | answered | cited correctly | answer correct | unanswerable escalated | wrongly answered |",
             "|---|---|---|---|---|---|---|"]
    for v in versions:
        m, details = evaluate(v)
        Path(f"eval/details_{v}.json").write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
        a, u = m["ans_total"], m["unans_total"]
        lines.append(f"| {v} | {m['hit']}/{a} | {m['answered']}/{a} | {m['cited']}/{m['answered'] or 1} | "
                     f"{m['correct']}/{m['answered'] or 1} | {m['escalated_ok']}/{u} | {m['hallucinated']}/{u} |")
        print(f"\n=== {v}: problems ===")
        for d in details:
            if d["problems"]:
                print(f"- {d['question']}\n    {d['problems']} score={d['top_score']} answer={d['answer']}")
        print(f"retrieval score: lowest on answerable = {m['min_score_answerable']}, "
              f"highest on unanswerable = {m['max_score_unanswerable']}")
    out = "\n".join(lines)
    print("\n" + out)
    Path("eval/results.md").write_text(out, encoding="utf-8")
    pool.close()