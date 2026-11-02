from app.ingest import chunk_text

def test_long_text_is_split_without_empty_chunks():
    chunks = chunk_text("This is a sentence. " * 200)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)

def test_short_text_is_one_chunk():
    assert len(chunk_text("Short text.")) == 1