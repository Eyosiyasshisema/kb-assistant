import hashlib, io, re
import httpx, trafilatura
from pypdf import PdfReader
from .db import pool
from .embeddings import embed

def extract_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(p.extract_text() or "" for p in reader.pages)
        return data.decode("utf-8", errors="ignore").replace("\r\n", "\n")

def fetch_url(url: str) -> tuple[str, str]:
    r = httpx.get(url, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "kb-assistant/0.1"})
    r.raise_for_status()
    meta = trafilatura.extract_metadata(r.text)
    title = meta.title if meta and meta.title else url
    return title, trafilatura.extract(r.text) or ""

def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):  
            cut = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if cut > start + size // 2:
                end = cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]

def store_document(title: str, source: str, source_type: str, text: str) -> dict:
    text = text.strip()
    if len(text) < 20:
        raise ValueError("No extractable text")
    h = hashlib.sha256(text.encode()).hexdigest()
    chunks = chunk_text(text)
    vectors = embed(chunks)
    with pool.connection() as conn:
        dup = conn.execute("SELECT id FROM documents WHERE content_hash=%s", (h,)).fetchone()
        if dup:
            return {"id": dup["id"], "duplicate": True}
        conn.execute("DELETE FROM documents WHERE source=%s", (source,))  # re-ingest replaces the old version
        doc = conn.execute(
            "INSERT INTO documents (title, source, source_type, content_hash) "
            "VALUES (%s,%s,%s,%s) RETURNING id", (title, source, source_type, h)).fetchone()
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, chunk_index, content, embedding) VALUES (%s,%s,%s,%s)",
                [(doc["id"], i, c, v) for i, (c, v) in enumerate(zip(chunks, vectors))])
    return {"id": doc["id"], "chunks": len(chunks), "duplicate": False}