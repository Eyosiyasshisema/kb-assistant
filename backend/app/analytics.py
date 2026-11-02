import numpy as np
from .embeddings import embed

def cluster_questions(rows: list[dict], threshold: float = 0.85) -> list[dict]:
    """Greedy clustering of similar questions. Tune the threshold by eyeballing results."""
    if not rows:
        return []
    vecs = embed([r["question"] for r in rows])
    clusters: list[dict] = []
    for r, v in zip(rows, vecs):
        for c in clusters:
            if float(np.dot(c["_vec"], v)) >= threshold:
                c["count"] += 1
                c["escalated"] += r["status"] == "escalated"
                break
        else:
            clusters.append({"question": r["question"], "count": 1,
                             "escalated": int(r["status"] == "escalated"), "_vec": v})
    for c in clusters:
        del c["_vec"]
    return sorted(clusters, key=lambda c: -c["count"])