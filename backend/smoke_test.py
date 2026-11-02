from app.ingest import store_document
from app.rag import answer_question

print(store_document(
    "test.md", "test.md", "file",
    "Refunds are accepted within 30 days of delivery if the item is unused. "
    "Shipping within Ethiopia takes 3 to 5 business days."))

for q in ["How long do I have to return something?", "Who won the 2014 World Cup?"]:
    r = answer_question(q)
    print("\nQ:", q, "\n->", r["status"], r["reason"], round(r["top_score"], 2), "\n  ", r["answer"])
    
from app.db import pool
pool.close()