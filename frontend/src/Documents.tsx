import { useEffect, useState, type ChangeEvent } from "react";
import { api } from "./api";

type Doc = { id: number; title: string; source_type: string; chunks: number };

export default function Documents() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [url, setUrl] = useState("");
  const [msg, setMsg] = useState("");

  const load = () => api<Doc[]>("/documents").then(setDocs).catch(e => setMsg(String(e)));
  useEffect(() => { load(); }, []);

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    try {
      await api("/documents", { method: "POST", body: fd });
      setMsg("Uploaded ✔");
      load();
    } catch (err) {
      setMsg(String(err));
    }
  }

  async function addUrl() {
    try {
      await api("/documents/url", { method: "POST", body: JSON.stringify({ url }) });
      setUrl("");
      setMsg("Page added ✔");
      load();
    } catch (err) {
      setMsg(String(err));
    }
  }

  return (
    <div>
      <h2>Knowledge base</h2>
      <p><input type="file" accept=".pdf,.md,.txt" onChange={upload} /></p>
      <p>
        <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://…" style={{ width: "60%" }} />{" "}
        <button onClick={addUrl}>Add web page</button>
      </p>
      <p>{msg}</p>
      <ul>
        {docs.map(d => (
          <li key={d.id}>{d.title} ({d.source_type}, {d.chunks} chunks)</li>
        ))}
      </ul>
    </div>
  );
}