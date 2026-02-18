"""MCP (Model Context Protocol) client manager for R.U.T.H. V3.

Allows Ruth to connect to external MCP-compatible tool servers and use
their tools dynamically. Supports stdio and HTTP transports.
"""

import asyncio
import json
import os
import subprocess
from typing import Any, Dict, List, Optional


class MCPClientManager:
    """Manages connections to multiple MCP servers.

    Each connection discovers available tools via the MCP protocol
    and makes them executable through Ruth's tool system.
    """

    def __init__(self):
        self._connections: Dict[str, dict] = {}

    async def connect(self, name: str, command: str = "", url: str = "") -> str:
        """Connect to an MCP server via stdio or HTTP transport.

        Args:
            name: Identifier for this connection.
            command: For stdio transport, the command to start the server.
            url: For HTTP transport, the server URL.

        Returns:
            Status message describing the connection result.
        """
        if name in self._connections:
            return f"Already connected to MCP server '{name}'. Disconnect first to reconnect."

        try:
            mcp_available = True
            try:
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client
            except ImportError:
                mcp_available = False

            if not mcp_available:
                # Fallback: manage as a subprocess with JSON-RPC over stdio
                return await self._connect_subprocess(name, command, url)

            if command:
                return await self._connect_stdio_mcp(name, command)
            elif url:
                return await self._connect_http_mcp(name, url)
            else:
                return "Error: Provide either 'command' (stdio) or 'url' (HTTP) to connect."

        except Exception as e:
            return f"MCP connection error: {e}"

    async def _connect_subprocess(self, name: str, command: str, url: str) -> str:
        """Fallback connection using raw subprocess stdio JSON-RPC."""
        if not command:
            return "Error: HTTP transport requires the 'mcp' library. Install: pip install mcp"

        try:
            parts = command.split()
            proc = await asyncio.create_subprocess_exec(
                *parts,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send JSON-RPC initialize request
            init_request = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "ruth", "version": "3.0"},
                }
            }) + "\n"

            proc.stdin.write(init_request.encode())
            await proc.stdin.drain()

            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=10)
                response = json.loads(response_line.decode())
            except (asyncio.TimeoutError, json.JSONDecodeError):
                proc.terminate()
                return f"MCP server '{name}' did not respond to initialize. Check the command."

            # Send tools/list request
            list_request = json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }) + "\n"

            proc.stdin.write(list_request.encode())
            await proc.stdin.drain()

            try:
                tools_line = await asyncio.wait_for(proc.stdout.readline(), timeout=10)
                tools_response = json.loads(tools_line.decode())
                tools = tools_response.get("result", {}).get("tools", [])
            except (asyncio.TimeoutError, json.JSONDecodeError):
                tools = []

            self._connections[name] = {
                "type": "subprocess",
                "process": proc,
                "command": command,
                "tools": tools,
                "request_id": 3,
            }

            tool_names = [t.get("name", "?") for t in tools]
            return f"Connected to MCP server '{name}' ({len(tools)} tools: {', '.join(tool_names)})"

        except FileNotFoundError:
            return f"Error: Command not found: {parts[0]}. Make sure it's installed."
        except Exception as e:
            return f"Error starting MCP server '{name}': {e}"

    async def _connect_stdio_mcp(self, name: str, command: str) -> str:
        """Connect using the mcp library's stdio transport."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            parts = command.split()
            server_params = StdioServerParameters(command=parts[0], args=parts[1:])

            transport = stdio_client(server_params)
            read_stream, write_stream = await transport.__aenter__()
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            tools_result = await session.list_tools()
            tools = [{"name": t.name, "description": t.description} for t in tools_result.tools]

            self._connections[name] = {
                "type": "mcp_stdio",
                "session": session,
                "transport": transport,
                "tools": tools,
            }

            tool_names = [t["name"] for t in tools]
            return f"Connected to MCP server '{name}' ({len(tools)} tools: {', '.join(tool_names)})"
        except Exception as e:
            return f"MCP stdio connection error: {e}"

    async def _connect_http_mcp(self, name: str, url: str) -> str:
        """Connect using HTTP/SSE transport."""
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            transport = sse_client(url)
            read_stream, write_stream = await transport.__aenter__()
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            tools_result = await session.list_tools()
            tools = [{"name": t.name, "description": t.description} for t in tools_result.tools]

            self._connections[name] = {
                "type": "mcp_http",
                "session": session,
                "transport": transport,
                "url": url,
                "tools": tools,
            }

            tool_names = [t["name"] for t in tools]
            return f"Connected to MCP server '{name}' ({len(tools)} tools: {', '.join(tool_names)})"
        except Exception as e:
            return f"MCP HTTP connection error: {e}"

    async def disconnect(self, name: str) -> str:
        """Disconnect from an MCP server."""
        if name not in self._connections:
            return f"No connection named '{name}' found."

        conn = self._connections.pop(name)
        try:
            conn_type = conn.get("type", "")
            if conn_type == "subprocess":
                proc = conn.get("process")
                if proc and proc.returncode is None:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        proc.kill()
            elif conn_type in ("mcp_stdio", "mcp_http"):
                session = conn.get("session")
                transport = conn.get("transport")
                if session:
                    await session.__aexit__(None, None, None)
                if transport:
                    await transport.__aexit__(None, None, None)
        except Exception as e:
            print(f"[MCP] Error disconnecting '{name}': {e}")

        return f"Disconnected from MCP server '{name}'."

    async def list_all_tools(self) -> str:
        """List tools from all connected MCP servers."""
        if not self._connections:
            return "No MCP servers connected."

        lines = []
        for name, conn in self._connections.items():
            tools = conn.get("tools", [])
            lines.append(f"\nServer: {name} ({len(tools)} tools)")
            for tool in tools:
                t_name = tool.get("name", "?")
                t_desc = tool.get("description", "")[:100]
                lines.append(f"  - {t_name}: {t_desc}")
        return "\n".join(lines)

    async def execute_tool(self, server_name: str, tool_name: str, arguments: dict = None) -> str:
        """Execute a tool on a connected MCP server."""
        if server_name not in self._connections:
            return f"No connection named '{server_name}'. Use mcp_connect first."

        conn = self._connections[server_name]
        arguments = arguments or {}

        try:
            conn_type = conn.get("type", "")

            if conn_type == "subprocess":
                return await self._execute_subprocess(conn, tool_name, arguments)
            elif conn_type in ("mcp_stdio", "mcp_http"):
                session = conn["session"]
                result = await session.call_tool(tool_name, arguments)
                content_parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        content_parts.append(block.text)
                    else:
                        content_parts.append(str(block))
                return "\n".join(content_parts) if content_parts else "Tool executed (no output)."
            else:
                return f"Unknown connection type: {conn_type}"
        except Exception as e:
            return f"MCP tool execution error: {e}"

    async def _execute_subprocess(self, conn: dict, tool_name: str, arguments: dict) -> str:
        """Execute a tool via JSON-RPC subprocess."""
        proc = conn.get("process")
        if not proc or proc.returncode is not None:
            return "Error: MCP server process is no longer running."

        request_id = conn.get("request_id", 3)
        conn["request_id"] = request_id + 1

        request = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }) + "\n"

        try:
            proc.stdin.write(request.encode())
            await proc.stdin.drain()

            response_line = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
            response = json.loads(response_line.decode())

            if "error" in response:
                return f"MCP error: {response['error'].get('message', 'unknown')}"

            result = response.get("result", {})
            content = result.get("content", [])
            parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
                else:
                    parts.append(str(block))
            return "\n".join(parts) if parts else "Tool executed (no output)."
        except asyncio.TimeoutError:
            return "MCP tool execution timed out (30s)."
        except Exception as e:
            return f"MCP subprocess execution error: {e}"

    async def shutdown(self):
        """Disconnect all servers on shutdown."""
        for name in list(self._connections.keys()):
            await self.disconnect(name)
