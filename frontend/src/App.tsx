import { useState } from "react";
import Chat from "./chat";
import ReviewQueue from "./ReviewQueue";
import Analytics from "./Analytics";
import Documents from "./Documents";

const tabs = { Chat, Reviews: ReviewQueue, Analytics, Documents };
type Tab = keyof typeof tabs;

export default function App() {
  const [tab, setTab] = useState<Tab>("Chat");
  const [token, setToken] = useState(localStorage.getItem("adminToken") ?? "");
  const Page = tabs[tab];

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 16 }}>
            <header style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <img src="/favicon.svg" width={36} height={36} alt="" />
        <div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>KDB</div>
          <div style={{ fontSize: 12, color: "#666" }}>Knowledge base with an assist. Sources for every answer, humans for the hard ones.</div>
        </div>
      </header>
      <nav style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        {(Object.keys(tabs) as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)} disabled={t === tab}>{t}</button>
        ))}
        <input
          type="password"
          placeholder="Admin token"
          value={token}
          onChange={e => {
            setToken(e.target.value);
            localStorage.setItem("adminToken", e.target.value);
          }}
          style={{ marginLeft: "auto" }}
        />
      </nav>
      <Page />
    </div>
  );
}