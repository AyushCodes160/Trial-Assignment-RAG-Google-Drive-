import json
import logging
import os
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

logger = logging.getLogger(__name__)

INDEX_PATH = "data/faiss_index/index.faiss"
META_PATH = "data/faiss_index/metadata.json"
DEFAULT_TOP_K = 5
EMBEDDING_DIM = 384                                     

def _ensure_dirs():
    Path(INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)

def _build_flat_index(dim: int) -> faiss.IndexFlatIP:
    return faiss.IndexFlatIP(dim)

class VectorStore:

    def __init__(self, embedding_dim: int = EMBEDDING_DIM):
        self.embedding_dim = embedding_dim
        self.index: Optional[faiss.Index] = None
        self.metadata: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
            try:
                self.index = faiss.read_index(INDEX_PATH)
                with open(META_PATH, "r") as f:
                    self.metadata = json.load(f)
                logger.info(
                    "Loaded FAISS index (%d vectors) from disk.", self.index.ntotal
                )
            except Exception as e:
                logger.error("Failed to load FAISS index: %s. Starting fresh.", e)
                self._reset()
        else:
            self._reset()

    def _reset(self):
        self.index = _build_flat_index(self.embedding_dim)
        self.metadata = []

    def save(self):
        _ensure_dirs()
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "w") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        logger.info("Saved FAISS index (%d vectors) to disk.", self.index.ntotal)

    def add(self, embeddings: np.ndarray, chunks: list[dict]) -> None:
        if len(embeddings) == 0:
            return
        embeddings = embeddings.astype(np.float32)
        self.index.add(embeddings)
        self.metadata.extend(chunks)
        logger.info("Added %d vectors. Total: %d.", len(embeddings), self.index.ntotal)

    def clear(self) -> None:
        self._reset()
        self.save()
        logger.info("Vector store cleared.")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = DEFAULT_TOP_K,
        filter_source: Optional[str] = None,
    ) -> list[dict]:
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty — no results.")
            return []

        query = query_embedding.reshape(1, -1).astype(np.float32)

        fetch_k = top_k * 4 if filter_source else top_k
        fetch_k = min(fetch_k, self.index.ntotal)

        scores, indices = self.index.search(query, fetch_k)
        scores = scores[0]
        indices = indices[0]

        results = []
        for score, idx in zip(scores, indices):
            if idx < 0 or idx >= len(self.metadata):
                continue
            chunk = dict(self.metadata[idx])
            chunk["score"] = float(score)

            if filter_source and chunk.get("source") != filter_source:
                continue
            results.append(chunk)
            if len(results) >= top_k:
                break

        return results

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal if self.index else 0

    def get_indexed_doc_ids(self) -> set[str]:
        return {m.get("doc_id", "") for m in self.metadata}

    def __repr__(self) -> str:
        return f"VectorStore(vectors={self.total_vectors}, dim={self.embedding_dim})"
