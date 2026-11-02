import { useState } from "react";
import { api } from "./api";

type Citation = { n: number; title: string; snippet: string };
type Msg = { role: "user" | "bot"; text: string; status?: string; citations?: Citation[] };

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [conv, setConv] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send() {
    const question = input.trim();
    if (!question || busy) return;
    setInput(""); setBusy(true);
    setMsgs(m => [...m, { role: "user", text: question }]);
    try {
      const r = await api<any>("/chat", {
        method: "POST",
        body: JSON.stringify({ question, conversation_id: conv }),
      });
      setConv(r.conversation_id);
      setMsgs(m => [...m, { role: "bot", text: r.answer, status: r.status, citations: r.citations }]);
    } catch {
      setMsgs(m => [...m, { role: "bot", text: "Something went wrong. Please try again." }]);
    } finally { setBusy(false); }
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      {msgs.map((m, i) => (
        <div key={i} style={{ margin: "12px 0", textAlign: m.role === "user" ? "right" : "left" }}>
          <div>{m.text}</div>
          {m.status === "escalated" && <small>⏳ Sent to a team member for review</small>}
          {m.citations?.map(c => (
            <details key={c.n}><summary>[{c.n}] {c.title}</summary><p>{c.snippet}…</p></details>
          ))}
        </div>
      ))}
      <input value={input} onChange={e => setInput(e.target.value)}
             onKeyDown={e => e.key === "Enter" && send()} placeholder="Ask a question…"
             style={{ width: "80%" }} />
      <button onClick={send} disabled={busy}>{busy ? "…" : "Send"}</button>
    </div>
  );
}