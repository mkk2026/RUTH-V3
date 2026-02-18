"""Central plugin registry -- manages plugin lifecycle and tool dispatch."""

from typing import Optional

from .base import BasePlugin, PluginContext, ToolDefinition


class PluginRegistry:
    """Manages all loaded plugins and their tools.

    Provides a single dispatch point for tool execution:
        registry.execute(tool_name, args, context)
    instead of the massive if/elif chain in ruth.py.
    """

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._tool_map: dict[str, str] = {}  # tool_name -> plugin_name
        self._tool_defs: dict[str, ToolDefinition] = {}

    def register(self, plugin: BasePlugin):
        """Register a plugin and index its tools."""
        if plugin.name in self._plugins:
            print(f"[PluginRegistry] Warning: Overwriting plugin '{plugin.name}'")

        self._plugins[plugin.name] = plugin

        for tool in plugin.get_tools():
            if tool.name in self._tool_map:
                existing = self._tool_map[tool.name]
                print(f"[PluginRegistry] Warning: Tool '{tool.name}' already registered by '{existing}', overwriting with '{plugin.name}'")

            self._tool_map[tool.name] = plugin.name
            self._tool_defs[tool.name] = tool

        print(f"[PluginRegistry] Registered plugin '{plugin.name}' with {len(plugin.get_tools())} tools")

    def unregister(self, plugin_name: str):
        """Remove a plugin and its tools from the registry."""
        if plugin_name not in self._plugins:
            return

        plugin = self._plugins[plugin_name]
        for tool in plugin.get_tools():
            self._tool_map.pop(tool.name, None)
            self._tool_defs.pop(tool.name, None)

        del self._plugins[plugin_name]
        print(f"[PluginRegistry] Unregistered plugin '{plugin_name}'")

    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        """Execute a tool by dispatching to its owning plugin.

        Args:
            tool_name: The tool to execute
            args: Arguments from the AI model
            context: Shared execution context

        Returns:
            Dict with 'result' key, or error information
        """
        plugin_name = self._tool_map.get(tool_name)
        if not plugin_name:
            return {"result": f"Unknown tool: '{tool_name}'"}

        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return {"result": f"Plugin '{plugin_name}' not found"}

        if not plugin.enabled:
            return {"result": f"Plugin '{plugin_name}' is disabled"}

        try:
            return await plugin.execute(tool_name, args, context)
        except Exception as e:
            print(f"[PluginRegistry] Error executing '{tool_name}': {e}")
            return {"result": f"Tool error: {str(e)}"}

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tool_map

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name."""
        return self._tool_defs.get(tool_name)

    def list_tools(self) -> list[ToolDefinition]:
        """Return all registered tool definitions."""
        return list(self._tool_defs.values())

    def list_plugins(self) -> list[dict]:
        """Return info about all registered plugins."""
        result = []
        for p in self._plugins.values():
            result.append({
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "author": p.author,
                "enabled": p.enabled,
                "tools": [t.name for t in p.get_tools()],
            })
        return result

    def get_tool_declarations(self) -> list[dict]:
        """Return tool definitions in Gemini function_declarations format.

        This replaces the hardcoded tools_list in tools.py.
        """
        declarations = []
        for tool in self._tool_defs.values():
            declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            })
        return declarations

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)
