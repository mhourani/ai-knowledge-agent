"""Configuration settings for the AI Knowledge Agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# LLM Settings
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

# Vector Store Settings
CHROMA_PERSIST_DIR = ".chroma"
COLLECTION_NAME = "knowledge_base"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Document Settings
DOCS_DIR = "docs"
SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".md"]
