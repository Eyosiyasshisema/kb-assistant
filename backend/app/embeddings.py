import numpy as np
from fastembed import TextEmbedding
from .config import settings

_model = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=settings.model_cache)  

def embed(texts: list[str]) -> list[np.ndarray]:
    return [np.asarray(v, dtype=np.float32) for v in _model.embed(texts)]