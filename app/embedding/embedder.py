import hashlib
import logging
import os
import pickle
from pathlib import Path
from typing import Optional

os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_CACHE_DIR = "data/embedding_cache"
DEFAULT_BATCH_SIZE = 64
NORMALIZE_EMBEDDINGS = True

_model = None                  

def _get_model():
    global _model
    if _model is None:
        try:
            import torch
            if hasattr(torch.backends, "mps"):
                torch.backends.mps.enabled = False
        except Exception:
            pass
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s on CPU", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
        logger.info("Model loaded successfully.")
    return _model

def _chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def _cache_path(text_hash: str) -> str:
    return os.path.join(EMBEDDING_CACHE_DIR, f"{text_hash}.pkl")

def _load_cached_embedding(text_hash: str) -> Optional[np.ndarray]:
    path = _cache_path(text_hash)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

def _save_cached_embedding(text_hash: str, embedding: np.ndarray) -> None:
    Path(EMBEDDING_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    with open(_cache_path(text_hash), "wb") as f:
        pickle.dump(embedding, f)

def embed_texts(
    texts: list[str],
    batch_size: int = DEFAULT_BATCH_SIZE,
    use_cache: bool = True,
) -> np.ndarray:
    model = _get_model()
    embeddings = []
    uncached_indices = []
    uncached_texts = []

    placeholder = [None] * len(texts)
    if use_cache:
        for i, text in enumerate(texts):
            h = _chunk_hash(text)
            cached = _load_cached_embedding(h)
            if cached is not None:
                placeholder[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
    else:
        uncached_indices = list(range(len(texts)))
        uncached_texts = texts

    if uncached_texts:
        logger.info("Encoding %d new chunks (batch_size=%d)…", len(uncached_texts), batch_size)
        new_embeddings = model.encode(
            uncached_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
        )
        for idx, emb in zip(uncached_indices, new_embeddings):
            placeholder[idx] = emb
            if use_cache:
                _save_cached_embedding(_chunk_hash(texts[idx]), emb)

    result = np.array(placeholder, dtype=np.float32)
    logger.info("Embeddings ready: shape=%s", result.shape)
    return result

def embed_query(query: str) -> np.ndarray:
    model = _get_model()
    emb = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        show_progress_bar=False,
    )
    return emb[0].astype(np.float32)
