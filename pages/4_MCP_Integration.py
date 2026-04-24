"""
MCP Server Management - Streamlit Page

Provides a UI for managing MCP server connections:
  - View registered MCP servers
  - Discover available tools from connected servers
  - Test tool execution
  - View the agent's MCP server endpoint info

This page demonstrates the interoperability layer that makes
enterprise agentic AI systems composable. In production, this
would be replaced by automated service discovery and orchestration.
"""

import streamlit as st
import asyncio
import json
from pathlib import Path

from src.mcp_tools import MCPClientManager, MCPServerConfig


def get_event_loop():
    """Get or create an event loop for async operations."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


st.set_page_config(page_title="MCP Integration", page_icon="🔌", layout="wide")
st.title("🔌 MCP Integration")
st.markdown(
    "Manage connections to external MCP (Model Context Protocol) servers. "
    "MCP is the standard for agent-to-tool communication in multi-agent "
    "enterprise AI systems."
)

# Initialize MCP manager in session state
if "mcp_manager" not in st.session_state:
    st.session_state.mcp_manager = MCPClientManager()
    # Load from config file if it exists
    config_path = Path("mcp_servers.json")
    if config_path.exists():
        st.session_state.mcp_manager.register_servers_from_config(str(config_path))

manager = st.session_state.mcp_manager

# --- MCP Server (our agent as a server) ---
st.header("🖥️ Agent as MCP Server")
st.markdown(
    "This agent exposes its knowledge base as an MCP server that other "
    "agents can connect to and query."
)

with st.expander("How to connect to this agent's MCP server"):
    st.code(
        '# Add to your MCP client configuration:\n'
        '{\n'
        '  "name": "ai-knowledge-agent",\n'
        '  "command": "python",\n'
        '  "args": ["-m", "src.mcp_server"],\n'
        '  "description": "Enterprise knowledge base with semantic search"\n'
        '}',
        language="json",
    )
    st.markdown(
        "**Tools exposed:**\n"
        "- `search_knowledge_base` - Semantic search across all ingested documents\n"
        "- `list_documents` - List all documents with chunk counts\n"
        "- `get_collection_stats` - Collection statistics"
    )

st.divider()

# --- MCP Client (connecting to external servers) ---
st.header("🔗 External MCP Connections")

# Show registered servers
if manager.servers:
    st.subheader("Registered Servers")
    for name, config in manager.servers.items():
        with st.expander(f"📡 {name} - {config.description or config.command}"):
            st.code(
                f"Command: {config.command}\n"
                f"Args: {' '.join(config.args)}\n"
                f"Description: {config.description}",
                language="text",
            )
else:
    st.info(
        "No MCP servers registered. Add servers via mcp_servers.json "
        "or use the form below."
    )

# Add new server
st.subheader("Add MCP Server")
with st.form("add_mcp_server"):
    col1, col2 = st.columns(2)
    with col1:
        server_name = st.text_input("Server Name", placeholder="e.g., filesystem")
        server_command = st.text_input("Command", placeholder="e.g., npx")
    with col2:
        server_args = st.text_input(
            "Arguments (comma-separated)",
            placeholder="e.g., -y,@modelcontextprotocol/server-filesystem,./docs",
        )
        server_desc = st.text_input("Description", placeholder="e.g., Local file access")
    
    if st.form_submit_button("Register Server"):
        if server_name and server_command:
            args = [a.strip() for a in server_args.split(",") if a.strip()]
            config = MCPServerConfig(
                name=server_name,
                command=server_command,
                args=args,
                description=server_desc,
            )
            manager.register_server(config)
            st.success(f"Registered server: {server_name}")
            st.rerun()
        else:
            st.warning("Server name and command are required.")

st.divider()

# Discover tools
st.subheader("Discovered Tools")

if st.button("🔍 Discover Tools from All Servers"):
    if not manager.servers:
        st.warning("No servers registered. Add a server first.")
    else:
        with st.spinner("Connecting to MCP servers and discovering tools..."):
            try:
                loop = get_event_loop()
                tools = loop.run_until_complete(manager.discover_tools())
                if tools:
                    st.success(f"Discovered {len(tools)} tools")
                    st.session_state.discovered_tools = True
                else:
                    st.warning(
                        "No tools discovered. Make sure the MCP servers "
                        "are running and accessible."
                    )
            except Exception as e:
                st.error(f"Discovery failed: {str(e)}")

# Show discovered tools
if manager._discovered_tools:
    for full_name, tool in manager._discovered_tools.items():
        with st.expander(f"🔧 {tool.name} (from {tool.server_name})"):
            st.markdown(f"**Description:** {tool.description}")
            if tool.input_schema.get("properties"):
                st.markdown("**Parameters:**")
                for param, info in tool.input_schema["properties"].items():
                    required = param in tool.input_schema.get("required", [])
                    req_badge = " *(required)*" if required else ""
                    st.markdown(
                        f"- `{param}`{req_badge}: {info.get('description', 'No description')}"
                    )

st.divider()

# Tool description for agent prompt
st.subheader("Agent Integration")
st.markdown(
    "The following text is injected into the agent's system prompt "
    "so it knows what external tools are available:"
)
st.code(manager.get_tools_description(), language="text")
