import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 700
DEFAULT_CHUNK_OVERLAP = 100
CHUNK_SETTINGS = {\"size\": DEFAULT_CHUNK_SIZE, \"overlap\": DEFAULT_CHUNK_OVERLAP}

def _get_encoder():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except ImportError:
        logger.warning("tiktoken not installed; using whitespace token approximation.")
        return None

class _WhitespaceEncoder:

    @staticmethod
    def encode(text: str) -> list[str]:
        return text.split()

    @staticmethod
    def decode(tokens: list[str]) -> str:
        return " ".join(tokens)

def chunk_text(
    text: str,
    metadata: Optional[dict] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    if not text or not text.strip():
        return []

    metadata = metadata or {}
    enc = _get_encoder()

    if enc is not None:
        tokens = enc.encode(text)
        decode_fn = lambda toks: enc.decode(toks)
    else:
        fallback = _WhitespaceEncoder()
        tokens = fallback.encode(text)
        decode_fn = fallback.decode

    total_tokens = len(tokens)
    chunks = []
    start = 0
    chunk_index = 0

    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text_str = decode_fn(chunk_tokens)

        chunk_record = {
            **metadata,
            "chunk_text": chunk_text_str,
            "chunk_index": chunk_index,
            "token_count": len(chunk_tokens),
        }
        chunks.append(chunk_record)

        start += chunk_size - chunk_overlap
        chunk_index += 1

        if end == total_tokens:
            break

    logger.debug(
        "Chunked document '%s' into %d chunks (size=%d, overlap=%d).",
        metadata.get("file_name", "unknown"),
        len(chunks),
        chunk_size,
        chunk_overlap,
    )
    return chunks

def chunk_documents(
    documents: list[dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict]:
    all_chunks = []
    for doc in documents:
        text = doc.pop("text", "")
        chunks = chunk_text(text, metadata=doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        all_chunks.extend(chunks)
    return all_chunks
