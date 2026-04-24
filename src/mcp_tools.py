"""
MCP Client for the AI Knowledge Agent.

Enables the agent to connect to external MCP servers and use their
tools during its reasoning loop. This is the client-side complement
to mcp_server.py.

In a multi-agent enterprise environment (like Deloitte's Zora AI),
agents need to coordinate with external systems:
  - A finance agent connecting to an SAP MCP server
  - A supply chain agent connecting to an Oracle MCP server
  - A knowledge agent connecting to a document management MCP server

MCP provides the standardized protocol for this coordination.
Instead of building custom API integrations for each system, the
agent discovers available tools through MCP and uses them through
a uniform interface.

This module provides:
  1. MCPClientManager - manages connections to multiple MCP servers
  2. Tool discovery - automatically discovers what tools each server offers
  3. Tool execution - calls tools on remote servers and returns results
  4. Integration with the LangGraph agent - exposes MCP tools as agent capabilities
"""

import json
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an external MCP server."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class MCPTool:
    """A tool discovered from an MCP server."""
    server_name: str
    name: str
    description: str
    input_schema: dict
    
    @property
    def full_name(self) -> str:
        """Unique name combining server and tool name."""
        return f"{self.server_name}__{self.name}"


class MCPClientManager:
    """
    Manages connections to multiple MCP servers and provides
    a unified interface for tool discovery and execution.
    
    Usage:
        manager = MCPClientManager()
        manager.register_server(MCPServerConfig(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/docs"],
        ))
        
        # Discover tools
        tools = await manager.discover_tools()
        
        # Execute a tool
        result = await manager.call_tool("filesystem__read_file", {"path": "/docs/readme.md"})
    """
    
    def __init__(self):
        self.servers: dict[str, MCPServerConfig] = {}
        self._discovered_tools: dict[str, MCPTool] = {}
    
    def register_server(self, config: MCPServerConfig):
        """Register an MCP server for connection."""
        self.servers[config.name] = config
        logger.info(f"Registered MCP server: {config.name} ({config.command})")
    
    def register_servers_from_config(self, config_path: str):
        """
        Load server configurations from a JSON file.
        
        Expected format:
        {
            "servers": [
                {
                    "name": "filesystem",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/docs"],
                    "description": "Local filesystem access"
                }
            ]
        }
        """
        try:
            with open(config_path) as f:
                data = json.load(f)
            
            for server_data in data.get("servers", []):
                config = MCPServerConfig(
                    name=server_data["name"],
                    command=server_data["command"],
                    args=server_data.get("args", []),
                    env=server_data.get("env", {}),
                    description=server_data.get("description", ""),
                )
                self.register_server(config)
            
            logger.info(f"Loaded {len(self.servers)} MCP servers from {config_path}")
        
        except FileNotFoundError:
            logger.warning(f"MCP config file not found: {config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid MCP config JSON: {e}")
    
    async def discover_tools(self, server_name: Optional[str] = None) -> list[MCPTool]:
        """
        Connect to MCP servers and discover available tools.
        
        Args:
            server_name: If specified, only discover tools from this server.
                        If None, discover from all registered servers.
        
        Returns:
            List of discovered MCP tools.
        """
        servers_to_query = (
            {server_name: self.servers[server_name]}
            if server_name and server_name in self.servers
            else self.servers
        )
        
        discovered = []
        
        for name, config in servers_to_query.items():
            try:
                tools = await self._discover_server_tools(config)
                for tool in tools:
                    mcp_tool = MCPTool(
                        server_name=name,
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    )
                    self._discovered_tools[mcp_tool.full_name] = mcp_tool
                    discovered.append(mcp_tool)
                
                logger.info(f"Discovered {len(tools)} tools from {name}")
            
            except Exception as e:
                logger.error(f"Failed to discover tools from {name}: {e}")
        
        return discovered
    
    async def _discover_server_tools(self, config: MCPServerConfig) -> list:
        """Connect to a single server and list its tools."""
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env if config.env else None,
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.list_tools()
                return response.tools
    
    async def call_tool(self, tool_full_name: str, arguments: dict) -> str:
        """
        Execute a tool on its MCP server.
        
        Args:
            tool_full_name: The full tool name (server__tool_name).
            arguments: Tool arguments as a dictionary.
        
        Returns:
            Tool result as a string.
        """
        if tool_full_name not in self._discovered_tools:
            return f"Error: Unknown tool '{tool_full_name}'. Run discover_tools() first."
        
        tool = self._discovered_tools[tool_full_name]
        config = self.servers.get(tool.server_name)
        
        if not config:
            return f"Error: Server '{tool.server_name}' not registered."
        
        try:
            result = await self._execute_tool(config, tool.name, arguments)
            return result
        
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_full_name}, error: {e}")
            return f"Error executing {tool_full_name}: {str(e)}"
    
    async def _execute_tool(
        self, config: MCPServerConfig, tool_name: str, arguments: dict
    ) -> str:
        """Connect to server and execute a specific tool."""
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env if config.env else None,
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                
                # Extract text content from result
                text_parts = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        text_parts.append(content.text)
                
                return "\n".join(text_parts) if text_parts else "Tool returned no content."
    
    def get_tools_description(self) -> str:
        """
        Generate a text description of all discovered tools.
        
        This is used to inject tool awareness into the agent's
        system prompt so it knows what external capabilities
        are available.
        """
        if not self._discovered_tools:
            return "No external MCP tools available."
        
        descriptions = []
        for tool in self._discovered_tools.values():
            params = ""
            if tool.input_schema.get("properties"):
                param_list = []
                for param_name, param_info in tool.input_schema["properties"].items():
                    param_desc = param_info.get("description", "")
                    param_list.append(f"    - {param_name}: {param_desc}")
                params = "\n" + "\n".join(param_list)
            
            descriptions.append(
                f"  Tool: {tool.full_name}\n"
                f"  Server: {tool.server_name}\n"
                f"  Description: {tool.description}\n"
                f"  Parameters:{params}"
            )
        
        return "Available external tools via MCP:\n\n" + "\n\n".join(descriptions)
    
    def get_tool_names(self) -> list[str]:
        """Get list of all discovered tool names."""
        return list(self._discovered_tools.keys())


def get_default_mcp_manager() -> MCPClientManager:
    """
    Create an MCP client manager with default configuration.
    
    Loads server configs from mcp_servers.json if it exists,
    otherwise returns an empty manager.
    """
    manager = MCPClientManager()
    manager.register_servers_from_config("mcp_servers.json")
    return manager
