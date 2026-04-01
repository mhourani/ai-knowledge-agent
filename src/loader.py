"""Document loader and text splitter for the AI Knowledge Agent."""

import os
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
)

from src.config import DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, SUPPORTED_EXTENSIONS


# Map file extensions to their loader class
LOADER_MAP = {
    ".txt": TextLoader,
    ".pdf": PyPDFLoader,
    ".md": UnstructuredMarkdownLoader,
}


def load_documents(docs_dir: str = DOCS_DIR) -> List[Document]:
    """
    Load all supported documents from the specified directory.
    
    Args:
        docs_dir: Path to the directory containing documents.
        
    Returns:
        List of Document objects with content and metadata.
    """
    documents = []

    if not os.path.exists(docs_dir):
        print(f"Documents directory '{docs_dir}' not found. Creating it.")
        os.makedirs(docs_dir)
        return documents

    for filename in os.listdir(docs_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            print(f"Skipping unsupported file: {filename}")
            continue

        filepath = os.path.join(docs_dir, filename)
        loader_class = LOADER_MAP.get(ext)

        if loader_class is None:
            continue

        try:
            loader = loader_class(filepath)
            loaded = loader.load()
            # Add the source filename to metadata
            for doc in loaded:
                doc.metadata["source"] = filename
            documents.extend(loaded)
            print(f"Loaded: {filename} ({len(loaded)} pages/sections)")
        except Exception as e:
            print(f"Error loading {filename}: {e}")

    print(f"\nTotal documents loaded: {len(documents)}")
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """
    Split documents into smaller chunks for vector storage.
    
    Uses RecursiveCharacterTextSplitter which tries to split on
    natural boundaries (paragraphs, sentences) before resorting
    to character-level splits.
    
    Args:
        documents: List of Document objects to split.
        
    Returns:
        List of smaller Document chunks with preserved metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")
    return chunks