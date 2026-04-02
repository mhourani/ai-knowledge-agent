"""Vector store management using ChromaDB for the AI Knowledge Agent."""

import chromadb
from typing import List, Optional

from langchain_core.documents import Document

from src.config import CHROMA_PERSIST_DIR, COLLECTION_NAME


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Create a persistent ChromaDB client.
    
    Data is stored locally in the .chroma directory so it
    survives between runs — you don't re-ingest every time.
    """
    return chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_or_create_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """
    Get existing collection or create a new one.
    
    Uses ChromaDB's built-in embedding function (all-MiniLM-L6-v2)
    which runs locally — no API calls needed for embeddings.
    """
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Enterprise AI Knowledge Base"},
    )


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


def reset_collection() -> None:
    """Delete and recreate the collection. Useful for re-ingesting."""
    client = get_chroma_client()
    client.delete_collection(name=COLLECTION_NAME)
    print(f"Collection '{COLLECTION_NAME}' has been reset.")
