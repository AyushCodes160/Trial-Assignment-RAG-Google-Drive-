# 🗂️ DriveChat — Personal ChatGPT over Google Drive

> **A production-grade RAG system that turns your Google Drive into a searchable AI knowledge base — using 100% free, open-source tools.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)](https://streamlit.io)
[![FAISS](https://img.shields.io/badge/Vector%20Store-FAISS-orange)](https://github.com/facebookresearch/faiss)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ✨ Features

| Feature | Details |
|---|---|
| **Google Drive Sync** | PDFs, Google Docs (exported as PDF), and TXT files via Service Account |
| **Incremental Sync** | Skips files already indexed — only re-embeds changed documents |
| **Smart Chunking** | 700-token chunks with 100-token overlap (tiktoken `cl100k_base`) |
| **Local Embeddings** | `all-MiniLM-L6-v2` via SentenceTransformers — completely free |
| **Embedding Cache** | Per-chunk disk cache prevents redundant re-encoding across restarts |
| **FAISS Vector Store** | Cosine-similarity search with persistent index and metadata sidecar |
| **Multi-LLM Support** | Groq (LLaMA-3) → HuggingFace Inference → Ollama (automatic fallback) |
| **Grounded Answers** | LLM is strictly prompted to answer only from document context |
| **Rich UI** | Dark glassmorphism Streamlit UI with source citations and chunk previews |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit UI                      │
│  ┌──────────────┐  ┌────────────────────────────┐  │
│  │  Sync Drive  │  │    Ask a Question           │  │
│  └──────┬───────┘  └──────────┬─────────────────┘  │
└─────────┼────────────────────┼────────────────────┘
          ▼                    ▼
  ┌───────────────┐    ┌───────────────────┐
  │ GDrive        │    │  RAG Pipeline     │
  │ Connector     │    │  (pipeline.py)    │
  └──────┬────────┘    └──┬────────────────┘
         │               │
         ▼               ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  Parser      │  │  Embedder    │  │  VectorStore │
  │  (PDF/TXT)   │  │  (MiniLM)    │  │  (FAISS)     │
  └──────────────┘  └──────────────┘  └──────────────┘
         │               │
         ▼               ▼
  ┌──────────────────────────────────────┐
  │           Chunker (tiktoken)         │
  └──────────────────────────────────────┘
```

---

## 📁 Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── connectors/
│   │   ├── __init__.py
│   │   └── gdrive.py          # Google Drive API connector
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── parser.py          # PDF/TXT text extractor
│   │   └── chunker.py         # Token-aware chunker
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── embedder.py        # SentenceTransformers (MiniLM)
│   ├── search/
│   │   ├── __init__.py
│   │   └── vector_store.py    # FAISS index + metadata
│   └── rag/
│       ├── __init__.py
│       └── pipeline.py        # End-to-end RAG orchestrator
├── streamlit_app.py            # Main Streamlit UI
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & install dependencies

```bash
git clone <your-repo-url>
cd Trial-Assignment-RAG-Google-Drive-

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 2. Configure Google Drive access

**Step A — Create a Service Account:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Drive API** (APIs & Services → Enable APIs)
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
5. Download the JSON key file → save as `service_account.json` in the project root

**Step B — Share your Drive folder with the service account:**
- Copy the service account's email (ends in `@...gserviceaccount.com`)
- In Google Drive, right-click your folder → **Share** → paste the email → **Viewer**

### 3. Configure your LLM backend

Copy `.env.example` to `.env` and fill in at least one LLM:

```bash
cp .env.example .env
```

**Option A — Groq (recommended, free):**
```
GROQ_API_KEY=gsk_...
```
Get a free key at [console.groq.com](https://console.groq.com)

**Option B — HuggingFace Inference API:**
```
HF_API_TOKEN=hf_...
```
Get a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

**Option C — Ollama (fully local):**
```bash
# Install from https://ollama.com
ollama pull llama3
# No env vars needed
```

### 4. Launch the app

```bash
streamlit run streamlit_app.py
```

Open [http://localhost:8502](http://localhost:8502) in your browser.

> **Note**: Port may be `8502` if `8501` is already in use on your machine.

### 5. Sync and chat

1. Enter your service account path and optional folder ID in the sidebar
2. Click **▶ Sync Drive** — files will be downloaded, chunked, and indexed
3. Ask questions in the chat input — answers come with source citations!

---

## 🧩 Tech Stack

| Component | Technology |
|---|---|
| UI | Streamlit |
| Google Drive | `google-api-python-client` (Service Account) |
| PDF Extraction | PyMuPDF (fitz) + pdfplumber fallback |
| Tokenisation | tiktoken (`cl100k_base`) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers) |
| Vector Store | FAISS (IndexFlatIP — cosine similarity) |
| LLM (Option 1) | Groq free API — LLaMA-3-8b |
| LLM (Option 2) | HuggingFace Inference — Mistral-7B |
| LLM (Option 3) | Ollama local — Llama3 |
| Config | python-dotenv |

---

## 🤖 LLM Prompt Strategy

The system prompt enforces document-grounded answers:

```
"You are a precise document assistant.
Answer ONLY using the information provided in the context below.
If the answer is not found in the context, respond with exactly:
'Not found in documents.'
Do not add any information from outside the context."
```

---

## 🔄 Incremental Sync

The system tracks which files have been indexed using a local JSON metadata cache (`data/metadata_cache.json`). On subsequent syncs:
- Files with unchanged `modifiedTime` → skipped (no re-download)
- Documents already in FAISS (by `doc_id`) → not re-embedded
- Only new/changed files are processed

---

## 📊 Data Storage

All data is stored locally under `data/` (gitignored):

```
data/
├── downloaded_files/    # Raw files from Drive
├── embedding_cache/     # Per-chunk embedding pickle files
├── faiss_index/
│   ├── index.faiss      # FAISS binary index
│   └── metadata.json    # Chunk metadata sidecar
└── metadata_cache.json  # Drive sync state
```

---

## ⚡ Production Considerations

- **Scale**: For >100k chunks, replace `IndexFlatIP` with `IndexIVFFlat` (see FAISS docs)
- **Security**: Never commit `service_account.json` or `.env`
- **Deployment**: Works on Streamlit Community Cloud — mount credentials as secrets
- **Performance**: Embedding cache eliminates redundant computation on restarts

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
