"""
Multimodal document processing for the AI Knowledge Agent.

Uses Claude's vision capabilities to extract text and descriptions
from images, making visual content searchable in the knowledge base.
"""

import os
import base64
import anthropic
from typing import List
from pathlib import Path

from langchain_core.documents import Document
from src.config import ANTHROPIC_API_KEY, MODEL_NAME

# Supported image formats
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".webp"]

# Max image size for Claude API (20MB)
MAX_IMAGE_SIZE = 20 * 1024 * 1024


def get_image_media_type(filepath: str) -> str:
    """Map file extension to media type for the Claude API."""
    ext = os.path.splitext(filepath)[1].lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(ext, "image/png")


def encode_image(filepath: str) -> str:
    """Read an image file and return its base64 encoding."""
    with open(filepath, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analyze_image(filepath: str) -> str:
    """
    Use Claude's vision to analyze an image and extract
    a detailed text description.
    
    This handles:
    - Scanned documents (OCR-like extraction)
    - Architecture diagrams (component and flow description)
    - Whiteboard photos (content transcription)
    - Screenshots (UI and content description)
    - Charts and graphs (data interpretation)
    - General images (detailed description)
    
    Args:
        filepath: Path to the image file.
        
    Returns:
        Text description of the image content.
    """
    file_size = os.path.getsize(filepath)
    if file_size > MAX_IMAGE_SIZE:
        return f"[Image too large to process: {file_size / 1024 / 1024:.1f}MB, max {MAX_IMAGE_SIZE / 1024 / 1024}MB]"

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    image_data = encode_image(filepath)
    media_type = get_image_media_type(filepath)
    filename = os.path.basename(filepath)

    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analyze this image thoroughly and extract ALL information from it. "
                            "Follow these rules based on what you see:\n\n"
                            "- If it's a DOCUMENT or SCANNED TEXT: Extract all text exactly as written, "
                            "preserving structure, headings, and formatting.\n"
                            "- If it's an ARCHITECTURE DIAGRAM: Describe every component, connection, "
                            "data flow, and technology mentioned. List all labels.\n"
                            "- If it's a WHITEBOARD: Transcribe all text, diagrams, and annotations.\n"
                            "- If it's a CHART or GRAPH: Describe the type, axes, data points, "
                            "trends, and any labels or legends.\n"
                            "- If it's a SCREENSHOT: Describe the application, UI elements, and "
                            "any visible text or data.\n"
                            "- If it's a PHOTO: Provide a detailed description of the scene, "
                            "objects, text, and context.\n\n"
                            "Be comprehensive. Every piece of text and visual information matters "
                            "because this description will be used for search and retrieval."
                        ),
                    },
                ],
            }
        ],
    )

    return message.content[0].text


def load_images(docs_dir: str) -> List[Document]:
    """
    Load all supported images from a directory, analyze them with
    Claude's vision, and return as searchable Documents.
    
    Args:
        docs_dir: Path to directory containing images.
        
    Returns:
        List of Document objects with image descriptions as content.
    """
    documents = []

    if not os.path.exists(docs_dir):
        return documents

    for filename in os.listdir(docs_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue

        filepath = os.path.join(docs_dir, filename)

        try:
            print(f"Analyzing image: {filename}...")
            description = analyze_image(filepath)

            doc = Document(
                page_content=f"[Image: {filename}]\n\n{description}",
                metadata={
                    "source": filename,
                    "type": "image",
                    "format": ext.strip("."),
                },
            )
            documents.append(doc)
            print(f"  Extracted {len(description)} characters of description")
        except Exception as e:
            print(f"Error analyzing {filename}: {e}")

    return documents