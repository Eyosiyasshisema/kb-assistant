import { useEffect, useState } from "react";
import { api } from "./api";

type Cluster = { question: string; count: number; escalated: number };
type Data = {
  totals: { total: number; escalated: number; avg_latency_ms: number; tokens_in: number; tokens_out: number };
  top_questions: Cluster[];
  gaps: Cluster[];
};

function Table({ rows }: { rows: Cluster[] }) {
  return (
    <table>
      <thead><tr><th>Question</th><th>Asked</th><th>Escalated</th></tr></thead>
      <tbody>
        {rows.map((c, i) => (
          <tr key={i}><td>{c.question}</td><td>{c.count}</td><td>{c.escalated}</td></tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Analytics() {
  const [d, setD] = useState<Data | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api<Data>("/analytics").then(setD).catch(e => setErr(String(e)));
  }, []);

  if (err) return <p style={{ color: "crimson" }}>{err}</p>;
  if (!d) return <p>Loading…</p>;
  const t = d.totals;
  const rate = t.total ? Math.round((t.escalated / t.total) * 100) : 0;

  return (
    <div>
      <p>
        Questions (30 days): <b>{t.total}</b> · Escalated: <b>{rate}%</b> ·
        Avg latency: <b>{t.avg_latency_ms} ms</b> · Tokens: <b>{t.tokens_in + t.tokens_out}</b>
      </p>
      <h3>Top questions</h3>
      <Table rows={d.top_questions} />
      <h3>Knowledge gaps (most escalated)</h3>
      <Table rows={d.gaps} />
    </div>
  );
}