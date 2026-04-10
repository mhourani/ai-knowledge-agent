"""Vector store management using ChromaDB for the AI Knowledge Agent."""
import os
import chromadb
from typing import List, Optional

from langchain_core.documents import Document

from src.config import CHROMA_PERSIST_DIR, COLLECTION_NAME


def get_chroma_client():
    """
    Create a ChromaDB client that works in both local and containerized
    environments.
    
    - In local development: uses PersistentClient with a local directory,
      so data survives between runs without needing a separate service.
    - In containerized deployments (docker-compose, Kubernetes): uses
      HttpClient to connect to a separate ChromaDB service over HTTP,
      which is the standard production pattern.
    
    The mode is controlled by the CHROMA_HOST environment variable:
    - If set, connects to ChromaDB over HTTP at that host
    - If not set, falls back to local persistent mode
    """
    chroma_host = os.getenv("CHROMA_HOST")
    
    if chroma_host:
        # Production / containerized mode — connect to ChromaDB service
        chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
        print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}")
        return chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
        )
    else:
        # Local development mode — persistent on-disk storage
        return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    
def get_or_create_collection(client):
    """
    Get the existing collection or create a new one.
    
    We don't pass an embedding_function here because ChromaDB's
    default embedder (all-MiniLM-L6-v2) is applied automatically
    server-side when using HttpClient, and passing it explicitly
    causes serialization mismatches between client/server versions.
    """
    return client.get_or_create_collection(name=COLLECTION_NAME)


def ingest_documents(chunks: List[Document]) -> int:
    """
    Store document chunks in the vector database.
    
    Args:
        chunks: List of Document chunks from the loader.
        
    Returns:
        Number of chunks stored.
    """
    if not chunks:
        print("No chunks to ingest.")
        return 0

    client = get_chroma_client()
    collection = get_or_create_collection(client)

    # Prepare data for ChromaDB
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    documents = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    # Upsert into collection (add or update)
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"Ingested {len(chunks)} chunks into '{COLLECTION_NAME}' collection.")
    return len(chunks)


def search(query: str, n_results: int = 10) -> List[dict]:
    """
    Search the knowledge base for chunks relevant to the query.
    
    This is the core retrieval step in RAG — it finds the document
    chunks whose meaning is closest to the question being asked.
    
    Args:
        query: Natural language question or search query.
        n_results: Number of results to return.
        
    Returns:
        List of dicts with 'content', 'metadata', and 'distance' keys.
        Lower distance = more relevant.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    # Format results into a clean structure
    formatted = []
    for i in range(len(results["ids"][0])):
        formatted.append({
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })

    return formatted

def search_by_source(source: str, n_results: int = 20) -> List[dict]:
    """
    Retrieve all chunks from a specific source document.
    
    Useful when a question is about a specific document
    rather than a topic across documents.
    
    Args:
        source: Filename to filter by.
        n_results: Maximum results to return.
        
    Returns:
        List of dicts with 'content', 'metadata', and 'distance' keys.
    """
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    results = collection.get(
        where={"source": source},
        limit=n_results,
    )

    formatted = []
    for i in range(len(results["ids"])):
        formatted.append({
            "content": results["documents"][i],
            "metadata": results["metadatas"][i],
            "distance": 0.0,
        })

    return formatted

def reset_collection():
    """
    Delete and recreate the collection.
    
    Safe to call even if the collection doesn't exist yet — this makes
    it work reliably across fresh deployments (new containers, new
    Kubernetes pods) and existing databases.
    """
    client = get_chroma_client()
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        # Collection doesn't exist yet — that's fine, nothing to delete
        pass
    get_or_create_collection(client)
