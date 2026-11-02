CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  source TEXT NOT NULL,
  source_type TEXT NOT NULL,            -- 'file' | 'url' | 'faq'
  content_hash TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chunks (
  id SERIAL PRIMARY KEY,
  document_id INT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(384) NOT NULL
);
CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
  id SERIAL PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id),
  question TEXT NOT NULL,
  answer TEXT,                          -- model draft, kept even when escalated
  status TEXT NOT NULL,                 -- 'answered' | 'escalated'
  reason TEXT,                          -- why it was escalated
  confidence REAL,
  top_score REAL,
  citations JSONB DEFAULT '[]',
  prompt_version TEXT,
  latency_ms INT,
  tokens_in INT, tokens_out INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reviews (
  id SERIAL PRIMARY KEY,
  message_id INT NOT NULL REFERENCES messages(id),
  status TEXT NOT NULL DEFAULT 'pending',   -- 'pending' | 'resolved'
  reviewer_answer TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

-- Supabase exposes public tables through its own API. Turning on RLS (with no
-- policies) blocks that; your backend connects as the owner role and is unaffected.
ALTER TABLE documents     ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks        ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages      ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews       ENABLE ROW LEVEL SECURITY;