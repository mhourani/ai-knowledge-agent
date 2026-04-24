"""
MCP Server for the AI Knowledge Agent.

Exposes the knowledge base as an MCP (Model Context Protocol) server
that any MCP-compatible client can connect to and use as a tool.

MCP is the emerging standard for agent-to-tool communication. By
exposing our knowledge base as an MCP server, any agent in a
multi-agent ecosystem (Zora AI, Claude Desktop, custom agents) can
discover and use our document search capabilities through a
standardized interface.

This is the "interoperability layer" that makes agentic AI systems
composable. Instead of building custom integrations for every
consumer, we expose a standard interface once, and any MCP client
can use it.

Usage:
    # Start the MCP server
    python -m src.mcp_server

    # Or import and run programmatically
    from src.mcp_server import create_mcp_server
    server = create_mcp_server()
    server.run()
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
)

from src.vectorstore import (
    get_chroma_client,
    get_or_create_collection,
    search,
)

logger = logging.getLogger(__name__)


def create_mcp_server() -> Server:
    """
    Create an MCP server that exposes the knowledge base.

    Tools exposed:
      - search_knowledge_base: Semantic search across ingested documents
      - list_documents: List all documents in the knowledge base
      - get_collection_stats: Get statistics about the knowledge base
    """
    server = Server("ai-knowledge-agent")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Advertise available tools to MCP clients."""
        return [
            Tool(
                name="search_knowledge_base",
                description=(
                    "Search the enterprise knowledge base using semantic "
                    "similarity. Returns the most relevant document chunks "
                    "for a given query. Use this to find information across "
                    "all ingested documents including PDFs, Word docs, "
                    "spreadsheets, presentations, and text files."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query. Can be a question or keywords.",
                        },
                        "n_results": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5, max: 20).",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="list_documents",
                description=(
                    "List all documents currently in the knowledge base "
                    "with their chunk counts. Use this to understand what "
                    "information is available before searching."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_collection_stats",
                description=(
                    "Get statistics about the knowledge base including "
                    "total chunks, unique documents, and collection name."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls from MCP clients."""

        if name == "search_knowledge_base":
            return await _handle_search(arguments)
        elif name == "list_documents":
            return await _handle_list_documents()
        elif name == "get_collection_stats":
            return await _handle_stats()
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}",
            )]

    return server


async def _handle_search(arguments: dict) -> list[TextContent]:
    """Execute a knowledge base search."""
    query = arguments.get("query", "")
    n_results = min(arguments.get("n_results", 5), 20)

    if not query.strip():
        return [TextContent(
            type="text",
            text="Error: query cannot be empty.",
        )]

    try:
        results = search(query=query, n_results=n_results)

        formatted = []
        for i, r in enumerate(results):
            source = r.get("metadata", {}).get("source", "unknown")
            distance = r.get("distance", 0)
            relevance = 1 - distance
            content = r.get("content", "")
            formatted.append(
                f"[Result {i+1}] (relevance: {relevance:.2f}, source: {source})\n"
                f"{content}"
            )

        result_text = "\n\n".join(formatted) if formatted else "No results found."

        return [TextContent(
            type="text",
            text=result_text,
        )]

    except Exception as e:
        logger.error(f"Search error: {e}")
        return [TextContent(
            type="text",
            text=f"Search error: {str(e)}",
        )]


async def _handle_list_documents() -> list[TextContent]:
    """List all documents in the knowledge base."""
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        data = collection.get(limit=10000)

        sources = {}
        for meta in data["metadatas"]:
            source = meta.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        if not sources:
            return [TextContent(
                type="text",
                text="Knowledge base is empty. No documents have been ingested.",
            )]

        doc_list = "\n".join(
            f"  - {source}: {count} chunks"
            for source, count in sorted(sources.items())
        )

        return [TextContent(
            type="text",
            text=f"Documents in knowledge base ({len(sources)} files):\n{doc_list}",
        )]

    except Exception as e:
        logger.error(f"List documents error: {e}")
        return [TextContent(
            type="text",
            text=f"Error listing documents: {str(e)}",
        )]


async def _handle_stats() -> list[TextContent]:
    """Get collection statistics."""
    try:
        client = get_chroma_client()
        collection = get_or_create_collection(client)
        count = collection.count()
        data = collection.get(limit=10000)
        sources = set(m.get("source", "unknown") for m in data["metadatas"])

        stats = {
            "collection_name": "knowledge_base",
            "total_chunks": count,
            "unique_documents": len(sources),
        }

        return [TextContent(
            type="text",
            text=json.dumps(stats, indent=2),
        )]

    except Exception as e:
        logger.error(f"Stats error: {e}")
        return [TextContent(
            type="text",
            text=f"Error getting stats: {str(e)}",
        )]


async def main():
    """Run the MCP server over stdio."""
    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
