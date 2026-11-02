import { useEffect, useState } from "react";
import { api } from "./api";

type Review = { id: number; question: string; draft_answer: string | null; reason: string };

export default function ReviewQueue() {
  const [items, setItems] = useState<Review[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [err, setErr] = useState("");

  const load = () =>
    api<Review[]>("/reviews").then(setItems).catch(e => setErr(String(e)));
  useEffect(() => { load(); }, []);

  async function resolve(id: number, addToKb: boolean) {
    const answer = drafts[id] ?? items.find(i => i.id === id)?.draft_answer ?? "";
    try {
      await api(`/reviews/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ answer, add_to_kb: addToKb }),
      });
      load();
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div>
      <h2>Pending reviews ({items.length})</h2>
      {err && <p style={{ color: "crimson" }}>{err}</p>}
      {items.map(r => (
        <div key={r.id} style={{ border: "1px solid #ccc", background: "#fff", padding: 12, margin: "12px 0", borderRadius: 8 }}>
          <b>{r.question}</b> <small>({r.reason})</small>
          {r.draft_answer && <p><i>Model draft: {r.draft_answer}</i></p>}
          <textarea
            rows={3}
            style={{ width: "100%", boxSizing: "border-box" }}
            placeholder="Your answer…"
            value={drafts[r.id] ?? r.draft_answer ?? ""}
            onChange={e => setDrafts({ ...drafts, [r.id]: e.target.value })}
          />
          <button onClick={() => resolve(r.id, false)}>Resolve</button>{" "}
          <button onClick={() => resolve(r.id, true)}>Resolve + add to knowledge base</button>
        </div>
      ))}
    </div>
  );
}