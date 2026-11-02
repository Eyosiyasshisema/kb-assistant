from pathlib import Path
from app.db import pool
from app.ingest import store_document

for p in sorted(Path("eval/corpus").glob("*.md")):
    text = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    print(p.name, store_document(p.name, p.name, "file", text))
pool.close()