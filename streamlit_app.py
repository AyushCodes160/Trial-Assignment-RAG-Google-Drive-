import logging
import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="DriveChat — Personal AI over Google Drive",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Root variables ── */
    :root {
        --bg-primary: #0d1117;
        --bg-secondary: #161b22;
        --bg-card: rgba(22, 27, 34, 0.85);
        --accent: #7c3aed;
        --accent-light: #a78bfa;
        --accent-glow: rgba(124, 58, 237, 0.25);
        --text-primary: #e6edf3;
        --text-secondary: #8b949e;
        --border: rgba(255,255,255,0.08);
        --success: #3fb950;
        --warning: #d29922;
        --error: #f85149;
        --radius: 12px;
    }

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background: var(--bg-primary);
        color: var(--text-primary);
    }

    .stApp { background: var(--bg-primary); }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }

    /* ── Header gradient strip ── */
    .header-strip {
        background: linear-gradient(135deg, #7c3aed 0%, #2563eb 50%, #0891b2 100%);
        padding: 2rem 2.5rem;
        border-radius: var(--radius);
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .header-strip::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse at 70% 50%, rgba(255,255,255,0.07) 0%, transparent 70%);
    }
    .header-strip h1 {
        font-size: 2rem;
        font-weight: 700;
        color: #fff;
        margin: 0 0 0.25rem 0;
        letter-spacing: -0.5px;
    }
    .header-strip p {
        color: rgba(255,255,255,0.75);
        font-size: 0.95rem;
        margin: 0;
    }

    /* ── Metric cards ── */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1.2rem 1.4rem;
        text-align: center;
        backdrop-filter: blur(12px);
        transition: box-shadow 0.2s ease;
    }
    .metric-card:hover { box-shadow: 0 0 16px var(--accent-glow); }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--accent-light);
    }
    .metric-label {
        font-size: 0.78rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* ── Chat messages ── */
    .chat-bubble {
        padding: 1rem 1.25rem;
        border-radius: var(--radius);
        margin: 0.5rem 0;
        line-height: 1.65;
        font-size: 0.95rem;
        animation: fadeIn 0.3s ease;
    }
    .chat-user {
        background: linear-gradient(135deg, rgba(124,58,237,0.2), rgba(37,99,235,0.2));
        border: 1px solid rgba(124,58,237,0.3);
        border-left: 3px solid var(--accent);
    }
    .chat-assistant {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-left: 3px solid var(--success);
    }
    .chat-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
        color: var(--text-secondary);
    }

    /* ── Source pills ── */
    .source-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(124,58,237,0.15);
        border: 1px solid rgba(124,58,237,0.35);
        border-radius: 999px;
        padding: 0.2rem 0.7rem;
        font-size: 0.78rem;
        color: var(--accent-light);
        margin: 0.2rem 0.2rem 0.2rem 0;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent), #2563eb) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.5rem !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        transition: opacity 0.2s ease, transform 0.1s ease !important;
    }
    .stButton > button:hover { opacity: 0.9; transform: translateY(-1px); }
    .stButton > button:active { transform: translateY(0); }

    /* ── Input ── */
    .stTextInput > div > div > input,
    .stTextArea textarea {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px var(--accent-glow) !important;
    }

    /* ── Status banners ── */
    .status-success {
        background: rgba(63,185,80,0.12);
        border: 1px solid rgba(63,185,80,0.35);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: var(--success);
        font-size: 0.9rem;
    }
    .status-error {
        background: rgba(248,81,73,0.12);
        border: 1px solid rgba(248,81,73,0.35);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: var(--error);
        font-size: 0.9rem;
    }
    .status-warning {
        background: rgba(210,153,34,0.12);
        border: 1px solid rgba(210,153,34,0.35);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: var(--warning);
        font-size: 0.9rem;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* ── Divider ── */
    hr { border-color: var(--border) !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 999px; }
    </style>
    """,
    unsafe_allow_html=True,
)

def _init_state():
    defaults = {
        "chat_history": [],
        "total_vectors": 0,
        "indexed_files": 0,
        "last_sync_time": None,
        "llm_backend": "—",
        "app_mode": "Drive",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

with st.sidebar:
    app_mode = st.session_state.get("app_mode", "Drive")
    mode_titles = {
        "Drive": ("🗂️ DriveChat", "Personal AI over Google Drive"),
        "GitHub": ("🐙 GitChat", "Personal AI over GitHub Repos"),
        "Web": ("🌐 WebChat", "Personal AI over Web Links"),
        "Upload": ("📄 DocChat", "Personal AI over Local Documents"),
    }
    title, subtitle = mode_titles.get(app_mode, mode_titles["Drive"])
    
    st.markdown(
        f"<div style='font-size:1.4rem;font-weight:700;color:#a78bfa;margin-bottom:0.5rem'>{title}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.82rem;color:#8b949e;margin-bottom:1.5rem'>{subtitle}</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("### ⚙️ Configuration")
    sa_path = st.text_input(
        "Service Account JSON Path",
        value=os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "service_account.json"),
        help="Path to your Google Service Account credentials JSON file.",
        key="sa_path_input",
    )
    folder_id = st.text_input(
        "Google Drive Folder ID (optional)",
        value=os.getenv("GDRIVE_FOLDER_ID", ""),
        help="Leave blank to search all accessible Drive files.",
        key="folder_id_input",
    )
    top_k = st.slider(
        "Context chunks (top-k)", min_value=1, max_value=10, value=5, key="top_k_slider"
    )

    st.divider()

    st.markdown("### 📥 Add Knowledge")
    selected_tab = st.radio("Select Source", ["Drive", "GitHub", "Web", "Upload"], horizontal=True, label_visibility="collapsed", key="app_mode")
    
    if selected_tab == "Drive":
        do_sync_drive = st.button("▶ Sync Drive", use_container_width=True)
    else:
        do_sync_drive = False
        
    if selected_tab == "GitHub":
        repo_url_input = st.text_input("GitHub Repo URL", placeholder="https://github.com/...")
        do_sync_git = st.button("▶ Clone & Sync", use_container_width=True)
    else:
        do_sync_git = False
        
    if selected_tab == "Web":
        web_url_input = st.text_input("Web Page URL", placeholder="https://...")
        do_sync_web = st.button("▶ Scrape Link", use_container_width=True)
    else:
        do_sync_web = False
        
    if selected_tab == "Upload":
        uploaded_docs = st.file_uploader("Upload Files", accept_multiple_files=True, type=["pdf", "txt", "docx"])
        do_sync_file = st.button("▶ Process Files", use_container_width=True)
    else:
        do_sync_file = False
        
    st.markdown("<br>", unsafe_allow_html=True)
    do_clear = st.button("🗑 Clear All Knowledge", use_container_width=True)

    sync_status_placeholder = st.empty()

    st.divider()
    st.markdown("### 📊 Index Stats")
    stat_col1, stat_col2 = st.columns(2)
    with stat_col1:
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{st.session_state.total_vectors:,}</div>"
            f"<div class='metric-label'>Vectors</div></div>",
            unsafe_allow_html=True,
        )
    with stat_col2:
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{st.session_state.indexed_files}</div>"
            f"<div class='metric-label'>Files</div></div>",
            unsafe_allow_html=True,
        )

    if st.session_state.last_sync_time:
        st.caption(f"Last sync: {st.session_state.last_sync_time}")

    st.divider()
    st.markdown(
        f"<div style='font-size:0.78rem;color:#8b949e'>LLM: <b style='color:#a78bfa'>{st.session_state.llm_backend}</b></div>",
        unsafe_allow_html=True,
    )
    st.caption("Built with ❤️ · Streamlit + FAISS + SentenceTransformers + Groq")

if do_clear:
    import json
    from app.rag.pipeline import get_vector_store
    store = get_vector_store()
    store.clear()
    if os.path.exists("data/metadata_cache.json"):
        os.remove("data/metadata_cache.json")
    st.session_state.total_vectors = 0
    st.session_state.indexed_files = 0
    st.session_state.chat_history = []
    sync_status_placeholder.markdown(
        "<div class='status-warning'>⚠️ Knowledge base cleared.</div>",
        unsafe_allow_html=True,
    )

if do_sync_drive or do_sync_git or do_sync_web or do_sync_file:
    progress_bar = st.sidebar.progress(0, text="Initializing...")
    progress_text = st.sidebar.empty()

    def _progress_cb(current, total, name, skipped=False):
        pct = int(current / total * 100) if total > 0 else 0
        label = f"{'⏭ Skipping' if skipped else '⬇ Processing'}: {name[:40]}"
        progress_bar.progress(pct / 100, text=label)
        progress_text.caption(f"{current}/{total} processed")

    try:
        from app.rag.pipeline import index_documents, get_vector_store
        new_docs = []
        new_chunks = 0
        
        with st.sidebar:
            with st.spinner("Fetching data..."):
                if selected_tab == "Drive" and do_sync_drive:
                    if not os.path.exists(sa_path) and "GOOGLE_SERVICE_ACCOUNT_JSON" not in st.secrets:
                        raise ValueError(f"Service account file not found: {sa_path}")
                    from app.connectors.gdrive import sync_google_drive, get_all_cached_files
                    sync_google_drive(sa_path, folder_id=folder_id or None, progress_callback=_progress_cb)
                    new_docs = get_all_cached_files()
                    
                elif do_sync_git:
                    from app.connectors.github import sync_github_repo
                    new_docs = sync_github_repo(repo_url_input, progress_callback=_progress_cb)
                    
                elif do_sync_web:
                    from app.connectors.web import sync_web_link
                    new_docs = sync_web_link(web_url_input, progress_callback=_progress_cb)
                    
                elif do_sync_file:
                    from app.connectors.upload import sync_uploaded_files
                    new_docs = sync_uploaded_files(uploaded_docs, progress_callback=_progress_cb)

        progress_bar.empty()
        progress_text.empty()

        if new_docs:
            with st.sidebar:
                with st.spinner("Indexing documents..."):
                    new_chunks = index_documents(new_docs)

        store = get_vector_store()
        st.session_state.total_vectors = store.total_vectors
        st.session_state.indexed_files = len(store.get_indexed_doc_ids())
        st.session_state.last_sync_time = time.strftime("%H:%M:%S")

        if new_chunks > 0:
            sync_status_placeholder.markdown(
                f"<div class='status-success'>✅ Added {len(new_docs)} source(s) → "
                f"{new_chunks:,} new chunks indexed.</div>",
                unsafe_allow_html=True,
            )
        else:
            sync_status_placeholder.markdown(
                "<div class='status-warning'>✓ Source processed but no new text was indexed.</div>",
                unsafe_allow_html=True,
            )

    except Exception as exc:
        progress_bar.empty()
        progress_text.empty()
        sync_status_placeholder.markdown(
            f"<div class='status-error'>❌ Sync failed: {exc}</div>",
            unsafe_allow_html=True,
        )

mode_descriptions = {
    "Drive": "Your Personal AI Assistant — powered by your Google Drive documents",
    "GitHub": "Your Personal AI Assistant — powered by your GitHub repositories",
    "Web": "Your Personal AI Assistant — powered by Web Links",
    "Upload": "Your Personal AI Assistant — powered by Local Documents",
}
main_title = st.session_state.get("app_mode", "Drive")
title_icon = {"Drive": "🗂️ DriveChat", "GitHub": "🐙 GitChat", "Web": "🌐 WebChat", "Upload": "📄 DocChat"}[main_title]

st.markdown(
    f"""
    <div class="header-strip">
        <h1>{title_icon}</h1>
        <p>{mode_descriptions[main_title]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

from app.rag.pipeline import get_vector_store as _gvs

_store = _gvs()
st.session_state.total_vectors = _store.total_vectors
st.session_state.indexed_files = len(_store.get_indexed_doc_ids())

if _store.total_vectors == 0:
    st.markdown(
        """
        <div class='status-warning'>
        👈 <strong>Get started:</strong> Enter your Service Account JSON path in the sidebar, then click <strong>Sync Drive</strong>
        to index your documents. Once indexed, ask anything below!
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='chat-bubble chat-user'>"
            f"<div class='chat-label'>🙋 You</div>{msg['content']}</div>",
            unsafe_allow_html=True,
        )
    else:
        answer_html = msg["content"].replace("\n", "<br>")
        
        mode_titles = {
            "Drive": "🗂️ DriveChat", "GitHub": "🐙 GitChat", 
            "Web": "🌐 WebChat", "Upload": "📄 DocChat"
        }
        bot_name = mode_titles.get(st.session_state.get("app_mode", "Drive"), "🤖 AI").split()[1]
        
        st.markdown(
            f"<div class='chat-bubble chat-assistant'>"
            f"<div class='chat-label'>🤖 {bot_name}</div>{answer_html}</div>",
            unsafe_allow_html=True,
        )

        if msg.get("sources"):
            source_pills = "".join(
                [
                    f"<span class='source-pill'>📄 {s.get('file_name', 'Unknown')}"
                    f" <span style='opacity:0.5'>chunk {s.get('chunk_index',0)}</span>"
                    f" <span style='opacity:0.4'>({s.get('score',0):.2f})</span></span>"
                    for s in msg["sources"]
                ]
            )
            st.markdown(
                f"<div style='margin-top:0.5rem;margin-bottom:0.5rem'>"
                f"<span style='font-size:0.78rem;color:#8b949e;margin-right:0.5rem'>📌 Sources:</span>"
                f"{source_pills}</div>",
                unsafe_allow_html=True,
            )
            with st.expander("🔍 View source excerpts", expanded=False):
                for i, src in enumerate(msg["sources"]):
                    st.markdown(
                        f"**[{i+1}] {src.get('file_name','Unknown')}** "
                        f"— chunk {src.get('chunk_index',0)} "
                        f"(score: {src.get('score',0):.3f})"
                    )
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.04);border-left:3px solid #7c3aed;"
                        f"padding:0.75rem;border-radius:0 8px 8px 0;font-size:0.88rem;"
                        f"color:#c9d1d9;line-height:1.6;margin-bottom:0.75rem'>"
                        f"{src['chunk_text'][:600]}{'…' if len(src['chunk_text']) > 600 else ''}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        if msg.get("backend"):
            st.caption(f"⚡ Backend: {msg['backend']} · {msg.get('context_used',0)} context chunk(s)")

st.markdown("<br>", unsafe_allow_html=True)

with st.form("chat_form", clear_on_submit=True):
    question_col, btn_col = st.columns([5, 1])
    with question_col:
        user_input = st.text_input(
            "Ask a question about your documents…",
            placeholder="e.g. Summarise the key points from the uploaded documents…",
            label_visibility="collapsed",
            key="question_input",
        )
    with btn_col:
        submitted = st.form_submit_button("Send →", use_container_width=True)

if submitted and user_input.strip():
    st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})

    with st.spinner("Thinking…"):
        from app.rag.pipeline import answer_question
        result = answer_question(
            user_input.strip(),
            top_k=st.session_state.get("top_k_slider", 5),
            chat_history=st.session_state.chat_history
        )

    st.session_state.llm_backend = result.get("backend", "—")
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
            "backend": result.get("backend", ""),
            "context_used": result.get("context_used", 0),
        }
    )
    st.rerun()

if st.session_state.chat_history:
    if st.button("🗑 Clear Chat", key="clear_chat_btn"):
        st.session_state.chat_history = []
        st.rerun()
