"""
AI Knowledge Agent - Web Interface

A professional web UI for the agentic RAG system powered by
LangGraph, ChromaDB, and Anthropic's Claude.
"""

import streamlit as st
import os
import time
from src.loader import load_documents, split_documents
from src.vectorstore import ingest_documents, search, reset_collection, get_chroma_client, get_or_create_collection
from src.agent import ConversationManager
from src.config import DOCS_DIR


# --- Page Configuration ---
st.set_page_config(
    page_title="AI Knowledge Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #888;
        margin-top: 0;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stat-number {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #666;
    }
    .source-tag {
        background: #e8f0fe;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.8rem;
        color: #1a73e8;
    }
</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
if "conversation" not in st.session_state:
    st.session_state.conversation = ConversationManager()
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- Helper Functions ---
def get_knowledge_base_stats():
    """Get stats about the current knowledge base."""
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        count = collection.count()
        return count
    except Exception:
        return 0


def get_document_list():
    """List documents in the docs folder."""
    if not os.path.exists(DOCS_DIR):
        return []
    supported = [".txt", ".pdf", ".md", ".docx", ".pptx", ".xlsx"]
    files = []
    for f in os.listdir(DOCS_DIR):
        ext = os.path.splitext(f)[1].lower()
        if ext in supported:
            size = os.path.getsize(os.path.join(DOCS_DIR, f))
            files.append({"name": f, "type": ext.upper().strip("."), "size": size})
    return files


# --- Sidebar ---
with st.sidebar:
    st.markdown("### 📚 Knowledge Base")

    chunk_count = get_knowledge_base_stats()
    doc_list = get_document_list()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Documents", len(doc_list))
    with col2:
        st.metric("Chunks", chunk_count)

    st.markdown("---")

    # Document Management
    st.markdown("#### Manage Documents")

    # File uploader
    uploaded_files = st.file_uploader(
        "Upload documents",
        accept_multiple_files=True,
        type=["txt", "pdf", "md", "docx", "pptx", "xlsx"],
        help="Supported: TXT, PDF, MD, DOCX, PPTX, XLSX",
    )

    if uploaded_files:
        os.makedirs(DOCS_DIR, exist_ok=True)
        for uploaded_file in uploaded_files:
            file_path = os.path.join(DOCS_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        st.success(f"Uploaded {len(uploaded_files)} file(s)")

    # Ingest button
    if st.button("🔄 Ingest Documents", use_container_width=True):
        with st.spinner("Loading and indexing documents..."):
            docs = load_documents()
            if docs:
                chunks = split_documents(docs)
                ingest_documents(chunks)
                st.success(f"Ingested {len(chunks)} chunks from {len(docs)} documents")
                st.rerun()
            else:
                st.warning("No documents found in docs/ folder")

    # Reset button
    if st.button("🗑️ Reset Knowledge Base", use_container_width=True):
        reset_collection()
        st.session_state.messages = []
        st.session_state.conversation = ConversationManager()
        st.success("Knowledge base reset")
        st.rerun()

    # Clear conversation
    if st.button("💬 Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation = ConversationManager()
        st.rerun()

    st.markdown("---")

    # Document list
    if doc_list:
        st.markdown("#### Current Documents")
        for doc in doc_list:
            size_kb = doc["size"] / 1024
            st.markdown(f"📄 **{doc['name']}** ({doc['type']}, {size_kb:.0f}KB)")
    else:
        st.info("No documents loaded yet. Upload files or add them to the docs/ folder.")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#888; font-size:0.8rem;'>"
        "Powered by LangGraph + ChromaDB + Claude<br>"
        "Built by Mark Hourani<br>"
        "<a href='https://github.com/mhourani/ai-knowledge-agent'>GitHub</a> | "
        "<a href='https://hourani.ai'>hourani.ai</a>"
        "</div>",
        unsafe_allow_html=True,
    )


# --- Main Content ---
st.markdown('<p class="main-header">🧠 AI Knowledge Agent</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Ask questions about your documents. '
    "The agent searches, evaluates, and synthesizes answers with citations.</p>",
    unsafe_allow_html=True,
)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about your knowledge base..."):
    # Check if knowledge base has content
    if get_knowledge_base_stats() == 0:
        st.warning("Your knowledge base is empty. Upload and ingest documents first using the sidebar.")
    else:
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching and reasoning..."):
                try:
                    response = st.session_state.conversation.ask(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
