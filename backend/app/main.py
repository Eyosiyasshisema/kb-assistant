import logging, secrets
import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
from .analytics import cluster_questions
from .config import settings
from .db import pool
from .ingest import extract_text, fetch_url, store_document
from .rag import FALLBACK, answer_question

log = logging.getLogger("kb")
app = FastAPI(title="Knowledge Assistant")
app.add_middleware(CORSMiddleware,
                   allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])

def require_admin(x_admin_token: str = Header(default="")):
    if not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Unauthorized")
admin = [Depends(require_admin)]

@app.get("/health")
def health():
    with pool.connection() as conn:       
        conn.execute("SELECT 1")
    return {"ok": True}

class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    conversation_id: str | None = None

def notify_slack(message_id: int, question: str, reason: str):
    if not settings.slack_webhook_url:
        return
    try:   
        httpx.post(settings.slack_webhook_url, timeout=5,
                   json={"text": f":sos: Needs review #{message_id} ({reason}): {question}"})
    except Exception:
        log.exception("slack notification failed")

def save_message(res: dict, conversation_id: str | None) -> tuple[int, str]:
    with pool.connection() as conn:
        if conversation_id:
            ok = conn.execute("SELECT 1 FROM conversations WHERE id=%s", (conversation_id,)).fetchone()
            conversation_id = conversation_id if ok else None
        if not conversation_id:
            conversation_id = str(conn.execute(
                "INSERT INTO conversations DEFAULT VALUES RETURNING id").fetchone()["id"])
        msg = conn.execute(
            """INSERT INTO messages (conversation_id, question, answer, status, reason, confidence,
               top_score, citations, prompt_version, latency_ms, tokens_in, tokens_out)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (conversation_id, res["question"], res["answer"], res["status"], res["reason"],
             res["confidence"], res["top_score"], Jsonb(res["citations"]), res["prompt_version"],
             res["latency_ms"], res["tokens_in"], res["tokens_out"])).fetchone()
        if res["status"] == "escalated":
            conn.execute("INSERT INTO reviews (message_id) VALUES (%s)", (msg["id"],))
    return msg["id"], conversation_id

@app.post("/api/chat")
def chat(body: ChatIn, bg: BackgroundTasks):
    res = answer_question(body.question)
    msg_id, conv_id = save_message(res, body.conversation_id)
    if res["status"] == "escalated":
        bg.add_task(notify_slack, msg_id, body.question, res["reason"])
    return {"message_id": msg_id, "conversation_id": conv_id, "status": res["status"],
            "answer": res["answer"] if res["status"] == "answered" else FALLBACK,
            "citations": res["citations"]}

@app.post("/api/documents", dependencies=admin)
async def upload(file: UploadFile = File(...)):
    text = extract_text(file.filename, await file.read())
    try:
        return store_document(file.filename, file.filename, "file", text)
    except ValueError as e:
        raise HTTPException(422, str(e))

class UrlIn(BaseModel):
    url: str

@app.post("/api/documents/url", dependencies=admin)
def add_url(body: UrlIn):
    title, text = fetch_url(body.url)
    try:
        return store_document(title, body.url, "url", text)
    except ValueError as e:
        raise HTTPException(422, str(e))

@app.get("/api/documents", dependencies=admin)
def list_documents():
    with pool.connection() as conn:
        return conn.execute("""SELECT d.id, d.title, d.source, d.source_type, d.created_at,
            (SELECT count(*) FROM chunks c WHERE c.document_id = d.id) AS chunks
            FROM documents d ORDER BY d.created_at DESC""").fetchall()

@app.get("/api/messages", dependencies=admin)
def list_messages(limit: int = 100):
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM messages ORDER BY id DESC LIMIT %s", (limit,)).fetchall()

@app.get("/api/reviews", dependencies=admin)
def list_reviews(status: str = "pending"):
    with pool.connection() as conn:
        return conn.execute("""SELECT r.id, r.status, r.created_at, m.question,
            m.answer AS draft_answer, m.reason, m.citations
            FROM reviews r JOIN messages m ON m.id = r.message_id
            WHERE r.status = %s ORDER BY r.id""", (status,)).fetchall()

class ResolveIn(BaseModel):
    answer: str = Field(min_length=3)
    add_to_kb: bool = False

@app.post("/api/reviews/{review_id}/resolve", dependencies=admin)
def resolve(review_id: int, body: ResolveIn):
    with pool.connection() as conn:
        row = conn.execute("""UPDATE reviews SET status='resolved', reviewer_answer=%s, resolved_at=now()
            WHERE id=%s AND status='pending' RETURNING message_id""",
            (body.answer, review_id)).fetchone()
        if not row:
            raise HTTPException(404, "Review not found or already resolved")
        q = conn.execute("SELECT question FROM messages WHERE id=%s",
                         (row["message_id"],)).fetchone()["question"]
    if body.add_to_kb: 
        store_document(f"FAQ: {q[:80]}", f"review:{review_id}", "faq", f"Q: {q}\nA: {body.answer}")
    return {"ok": True}

@app.get("/api/analytics", dependencies=admin)
def analytics():
    with pool.connection() as conn:
        totals = conn.execute("""SELECT count(*) AS total,
            count(*) FILTER (WHERE status='escalated') AS escalated,
            coalesce(avg(latency_ms),0)::int AS avg_latency_ms,
            coalesce(sum(tokens_in),0) AS tokens_in, coalesce(sum(tokens_out),0) AS tokens_out
            FROM messages WHERE created_at > now() - interval '30 days'""").fetchone()
        rows = conn.execute("""SELECT question, status FROM messages
            WHERE created_at > now() - interval '30 days'""").fetchall()
    clusters = cluster_questions(rows)
    gaps = sorted([c for c in clusters if c["escalated"]], key=lambda c: -c["escalated"])
    return {"totals": totals, "top_questions": clusters[:10], "gaps": gaps[:10]}