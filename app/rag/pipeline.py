import logging
import os
from typing import Optional

from app.embedding.embedder import embed_query
from app.search.vector_store import VectorStore

logger = logging.getLogger(__name__)

_vector_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

SYSTEM_PROMPT = (
    "You are a precise document assistant. "
    "Answer ONLY using the information provided in the context below. "
    "If the answer is not found in the context, respond with exactly: "
    "'Not found in documents.' "
    "Do not add any information from outside the context."
)

def _build_user_prompt(question: str, context_chunks: list[dict]) -> str:
    context_text = "\n\n---\n\n".join(
        [
            f"[Source: {c.get('file_name', 'Unknown')}]\n{c['chunk_text']}"
            for c in context_chunks
        ]
    )
    return (
        f"Context:\n{context_text}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

def _call_groq(prompt: str, system: str) -> str:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama3-8b-8192"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()

def _call_huggingface(prompt: str, system: str) -> str:
    import requests

    hf_token = os.environ.get("HF_API_TOKEN", "")
    model = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    full_prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{prompt} [/INST]"

    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 1024,
            "temperature": 0.1,
            "return_full_text": False,
        },
    }
    url = f"https://api-inference.huggingface.co/models/{model}"
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and data:
        return data[0].get("generated_text", "").strip()
    return str(data)

def _call_ollama(prompt: str, system: str) -> str:
    import requests

    model = os.getenv("OLLAMA_MODEL", "llama3")
    url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()

def _generate_answer(prompt: str, system: str) -> tuple[str, str]:

    if os.getenv("GROQ_API_KEY"):
        try:
            return _call_groq(prompt, system), "Groq (LLaMA-3)"
        except Exception as e:
            logger.warning("Groq failed: %s. Trying next backend…", e)

    if os.getenv("HF_API_TOKEN"):
        try:
            return _call_huggingface(prompt, system), "HuggingFace Inference"
        except Exception as e:
            logger.warning("HuggingFace failed: %s. Trying Ollama…", e)

    try:
        return _call_ollama(prompt, system), "Ollama (local)"
    except Exception as e:
        logger.error("All LLM backends failed. Last error: %s", e)
        return (
            "⚠️ No LLM backend is available. "
            "Please configure GROQ_API_KEY, HF_API_TOKEN, or start Ollama locally.",
            "None",
        )

def answer_question(
    question: str,
    top_k: int = 5,
    filter_source: Optional[str] = None,
) -> dict:
    store = get_vector_store()

    if store.total_vectors == 0:
        return {
            "answer": "⚠️ No documents have been indexed yet. Please sync Google Drive first.",
            "sources": [],
            "backend": "N/A",
            "context_used": 0,
        }

    query_emb = embed_query(question)

    chunks = store.search(query_emb, top_k=top_k, filter_source=filter_source)
    if not chunks:
        return {
            "answer": "Not found in documents. The indexed documents do not contain relevant information for this query.",
            "sources": [],
            "backend": "N/A",
            "context_used": 0,
        }

    prompt = _build_user_prompt(question, chunks)
    answer, backend = _generate_answer(prompt, SYSTEM_PROMPT)

    seen = set()
    unique_sources = []
    for c in chunks:
        key = (c.get("doc_id", ""), c.get("chunk_index", 0))
        if key not in seen:
            seen.add(key)
            unique_sources.append(c)

    return {
        "answer": answer,
        "sources": unique_sources,
        "backend": backend,
        "context_used": len(chunks),
    }

def index_documents(documents: list[dict]) -> int:
    from app.processing.parser import extract_text
    from app.processing.chunker import chunk_text
    from app.embedding.embedder import embed_texts

    store = get_vector_store()
    already_indexed = store.get_indexed_doc_ids()

    all_chunks = []
    for doc in documents:
        if doc["doc_id"] in already_indexed:
            logger.debug("Skipping already-indexed doc: %s", doc["file_name"])
            continue

        text = extract_text(doc["local_path"], doc.get("mime_type", ""))
        if not text:
            logger.warning("No text extracted from: %s", doc["file_name"])
            continue

        base_meta = {
            "doc_id": doc["doc_id"],
            "file_name": doc["file_name"],
            "source": doc.get("source", "gdrive"),
            "mime_type": doc.get("mime_type", ""),
        }
        chunks = chunk_text(text, metadata=base_meta)
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.info("No new chunks to index.")
        return 0

    texts = [c["chunk_text"] for c in all_chunks]
    embeddings = embed_texts(texts)
    store.add(embeddings, all_chunks)
    store.save()

    logger.info("Indexed %d new chunks across %d documents.", len(all_chunks), len(documents))
    return len(all_chunks)
