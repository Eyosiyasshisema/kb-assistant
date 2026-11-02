# Knowledge Assistant with Citations and Human Review

A support assistant that answers questions **only from your own documents and web pages**, shows the **source for every answer**, and **hands uncertain questions to a human** instead of guessing. Every conversation is logged, and an analytics page shows the most common questions and the gaps in your documentation.

**Live demo:** https://kb-assistant-admin.onrender.com/
**Source code:** https://github.com/Eyosiyasshisema/kb-assistant

> The demo runs on free hosting. If it has been idle, the first request can take up to a minute while the server wakes up.

---

## Try it

1. Open the live demo and go to the **Chat** tab (it's public, no login needed).
2. Ask a question your documents answer. You'll get a short answer with a numbered citation. Click the citation to see the exact source passage.
3. Ask something the documents don't cover. The assistant won't invent an answer: it tells the user their question was passed to the team, and the question lands in the review queue.

The **Reviews**, **Analytics** and **Documents** tabs are the staff side of the product and are protected by an admin token. The sample knowledge base is for a fictional coffee roaster (see `backend/eval/corpus/`), so questions about shipping, returns, subscriptions, pricing, brewing and contact details will work well. To get view-only access to the admin tabs, contact me through GitHub.

---

## What it does

- **Answers with sources.** Every answer cites the passages it came from, and the UI shows the source text.
- **Refuses to guess.** If nothing relevant is found, or the model isn't confident, the question is escalated instead of answered.
- **Human review queue.** Escalated questions appear in an admin queue (with an optional Slack notification). A reviewer writes the answer and can add it to the knowledge base, so the same question is answered automatically next time.
- **Knowledge base management.** Upload PDF, Markdown or text files, or add a web page by URL.
- **Conversation logging and analytics.** Every question is stored with its status, confidence, latency and token usage. The analytics page shows top questions and "knowledge gaps" (questions that keep getting escalated).
- **Measured accuracy.** An evaluation harness scores the assistant on a set of answerable and unanswerable questions, and compares prompt versions.

### Why not just upload a file to ChatGPT, Claude or Gemini?

A general chatbot is great for one person asking about a few files. This project is for a **business** that needs the answers to be controlled and visible:

| Need | General chatbot with a file | This system |
|---|---|---|
| Users | One person, in their own account | Customers and staff, through the company's own site |
| Knowledge | A few files per chat | A persistent knowledge base, managed centrally |
| Trust | May answer from general knowledge or guess | Answers only from approved sources, always cited, escalates when unsure |
| Unknown questions | Often a plausible-sounding answer anyway | Routed to a human, whose answer improves the knowledge base |
| Visibility | None | Every conversation logged, with analytics on gaps |
| Proof it works | None | A repeatable evaluation with a hallucination metric |
| Data | Goes through a third-party chat product | Stays in the company's own database |

---

## How it works

```
question
   │
   ▼
embed the question (local model)
   │
   ▼
pgvector similarity search → top 5 passages
   │
   ├── best match below threshold? ──────────────► ESCALATE (LLM is never called)
   │
   ▼
LLM call → structured JSON output (validated)
   │
   ▼
guards:  valid output? valid citations? has citations?
         model says answerable? confidence high enough?
   │
   ├── any guard fails ──────────────────────────► ESCALATE → review queue (+ Slack)
   │                                                      │
   ▼                                                      ▼
ANSWER + citations                          human answers → optionally added to the knowledge base
   │
   ▼
every exchange is logged → analytics (top questions, knowledge gaps)
```

### How it fails (on purpose)

The model is never trusted blindly. Each failure has a defined behavior:

| Reason | What happens |
|---|---|
| `low_retrieval` | No relevant passage found. The LLM is skipped and the question is escalated. |
| `llm_invalid_output` | The model returned unusable output (or the provider failed) after retries. Escalated. |
| `invalid_citation` | The model cited a passage number that doesn't exist. Escalated. |
| `model_unsure` | The model reported it can't answer from the context. Escalated. |
| `no_citations` | An answer without sources is not allowed. Escalated. |
| `low_confidence` | The model's self-reported confidence is below the threshold. Escalated. |

Other resilience details:
- The LLM call retries on malformed output and on rate limits (with backoff).
- A Slack outage never breaks the user's answer (notifications run in the background and errors are caught).
- The prompt tells the model to treat retrieved text as untrusted data and ignore instructions inside it (basic prompt-injection defense for web-page sources).
- Re-ingesting a document replaces the old version, and identical content is de-duplicated by hash.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Database | PostgreSQL with pgvector (hosted on Supabase) |
| Embeddings | `BAAI/bge-small-en-v1.5` via fastembed, running locally (384 dimensions) |
| LLM | Google Gemini API (Flash model, configurable by environment variable) |
| Document parsing | pypdf (PDF), trafilatura (web pages) |
| Frontend | React, TypeScript, Vite |
| Hosting | Render (web service + static site) |
| Testing | pytest, plus a custom evaluation harness |

The LLM layer lives in a single file (`backend/app/llm.py`), so switching providers means changing one module.

---

## Project structure

```
kb-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py          API endpoints, auth, Slack notification
│   │   ├── rag.py           retrieval + guards (core logic)
│   │   ├── llm.py           LLM call with structured, validated output
│   │   ├── ingest.py        file/URL parsing, chunking, storage
│   │   ├── embeddings.py    local embedding model
│   │   ├── analytics.py     question clustering (top questions, gaps)
│   │   ├── db.py            Postgres connection pool
│   │   ├── config.py        settings from environment variables
│   │   └── prompts/         versioned system prompts (v1, v2, ...)
│   ├── eval/
│   │   ├── corpus/          sample knowledge base (fictional coffee roaster)
│   │   ├── questions.jsonl  evaluation questions
│   │   ├── ingest_corpus.py loads the sample documents
│   │   └── run_eval.py      evaluation runner
│   ├── tests/               unit tests for the guards and chunking
│   ├── schema.sql           database schema
│   ├── smoke_test.py        quick end-to-end check
│   └── requirements.txt
└── frontend/                React admin and chat UI
```

---

## API

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /health` | none | Health check (also queries the database) |
| `POST /api/chat` | none | Ask a question. Returns answer, status and citations. |
| `POST /api/documents` | admin | Upload a PDF, Markdown or text file |
| `POST /api/documents/url` | admin | Add a web page |
| `GET /api/documents` | admin | List documents |
| `GET /api/messages` | admin | Conversation log |
| `GET /api/reviews` | admin | Review queue (default: pending) |
| `POST /api/reviews/{id}/resolve` | admin | Answer an escalated question, optionally adding it to the knowledge base |
| `GET /api/analytics` | admin | Totals, top questions, knowledge gaps |

Interactive docs are available at `/docs` on the backend.

---

## Evaluation

Quality is measured, not assumed. `backend/eval/` contains:

- a sample knowledge base of 7 documents (a fictional coffee roaster);
- a question set with **answerable** questions (some phrased very differently from the source text, some needing facts from two documents) and **unanswerable** questions, including deliberate traps that sound covered but aren't;
- a runner that scores each prompt version on:
  - **retrieval hit rate:** did the right document reach the model?
  - **answered / cited correctly / answer correct:** for answerable questions;
  - **unanswerable questions escalated:** did it correctly refuse?
  - **wrongly answered:** unanswerable questions it answered anyway (the hallucination rate, the most important number).

The runner also prints a diagnosis for every failed question (retrieval miss, wrong citation, wrongly escalated, hallucinated answer), which is used to tune the prompt versions and the retrieval and confidence thresholds.

Run it from the `backend` folder:

```bash
python -m eval.ingest_corpus
python -m eval.run_eval v1 v2
```

Results are written to `backend/eval/results.md`, with per-question details in `backend/eval/details_<version>.json`. Set `QUESTIONS_FILE` to run a subset.

---

## Run it locally

**Requirements:** Python 3.12, Node.js 20+, a free [Supabase](https://supabase.com) project, and a free [Google AI Studio](https://aistudio.google.com) API key.

### 1. Database
1. Create a Supabase project.
2. Run `backend/schema.sql` in the Supabase SQL Editor (it enables the `vector` extension and creates the tables).
3. Copy the **Session pooler** connection string from the project's Connect dialog.

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash). On macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `backend/.env`:

```
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres
GEMINI_API_KEY=your-google-ai-studio-key
LLM_MODEL=gemini-3.5-flash
ADMIN_TOKEN=choose-a-secret-token
CORS_ORIGINS=http://localhost:5173
```

Start the API:

```bash
python -m uvicorn app.main:app --reload
```

Check `http://localhost:8000/health`, then run the quick end-to-end test:

```bash
python smoke_test.py
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`, type your admin token into the box at the top right, and upload a document in the **Documents** tab.

### 4. Tests
```bash
cd backend
python -m pytest
```

---

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | Postgres connection string (Supabase session pooler) | required |
| `GEMINI_API_KEY` | LLM API key | required |
| `LLM_MODEL` | Gemini model name | `gemini-3.5-flash` |
| `ADMIN_TOKEN` | Secret for admin endpoints | `change-me` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `http://localhost:5173` |
| `SLACK_WEBHOOK_URL` | Optional Slack incoming webhook for review alerts | empty (disabled) |
| `PROMPT_VERSION` | Which prompt file in `app/prompts/` to use | `v2` |
| `TOP_K` | Passages retrieved per question | `5` |
| `MIN_RETRIEVAL_SCORE` | Minimum similarity to attempt an answer | `0.5` |
| `MIN_CONFIDENCE` | Minimum model confidence to show an answer | `0.6` |

The two thresholds are tuned using the evaluation harness rather than guessed.

---

## Deployment (Render)

- **Backend:** Render Web Service, root directory `backend`. Build command installs `requirements.txt` and pre-downloads the embedding model; start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Health check path is `/health`. Set `PYTHON_VERSION=3.12.8` and the environment variables above.
- **Frontend:** Render Static Site, root directory `frontend`, build command `npm install && npm run build`, publish directory `dist`, with `VITE_API_URL` set to the backend's URL.
- **Database:** Supabase (free tier), reached through the session pooler so it works over IPv4.

---

## Limitations and production notes

This is a portfolio project, built to demonstrate the architecture. For a real client deployment I would add:

- **User accounts and roles** (for example Supabase Auth) instead of a single shared admin token.
- **Rate limiting and abuse protection** on the public chat endpoint.
- **A stronger evaluation loop:** larger question sets built from real conversations, and a model-based judge alongside the keyword checks.
- **Conversation memory** for follow-up questions (the current version answers each question independently).
- **Email or ticketing integration** for escalations, in addition to Slack.
- **Backups and monitoring** beyond the hosting defaults.

Free-tier notes: the demo's server sleeps when idle, and free LLM tiers may use submitted content to improve the provider's models, so only fictional sample data is used here. Never upload confidential documents to the public demo.

---

## Author

Built by Eyosiyas Shisema, a full-stack and ML engineer based in Addis Ababa, Ethiopia.
GitHub: [@Eyosiyasshisema](https://github.com/Eyosiyasshisema)