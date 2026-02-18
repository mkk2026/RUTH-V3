"""Built-in 3D printing plugin."""

from plugins.base import BasePlugin, PluginContext, ToolDefinition


class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "printing"

    @property
    def description(self) -> str:
        return "3D printer discovery, slicing, and print job management"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="discover_printers",
                description="Discovers 3D printers on the local network.",
                parameters={"type": "OBJECT", "properties": {}},
                requires_confirmation=False,
            ),
            ToolDefinition(
                name="print_stl",
                description="Prints an STL file to a 3D printer. Handles slicing and upload.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "stl_path": {"type": "STRING", "description": "Path to STL file, or 'current' for the most recent."},
                        "printer": {"type": "STRING", "description": "Printer name or IP address."},
                        "profile": {"type": "STRING", "description": "Optional slicer profile name."},
                    },
                    "required": ["stl_path", "printer"],
                },
            ),
            ToolDefinition(
                name="get_print_status",
                description="Gets current status of a 3D printer including progress and temperatures.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "printer": {"type": "STRING", "description": "Printer name or IP address."},
                    },
                    "required": ["printer"],
                },
                requires_confirmation=False,
            ),
        ]

    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        return {"result": f"_{tool_name}_dispatch", "_dispatch": tool_name, "_args": args}
