"""Built-in CAD generation plugin."""

from plugins.base import BasePlugin, PluginContext, ToolDefinition


class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "cad"

    @property
    def description(self) -> str:
        return "3D CAD model generation and iteration using build123d"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="generate_cad",
                description="Generates a 3D CAD model based on a prompt.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "prompt": {"type": "STRING", "description": "The description of the object to generate."},
                    },
                    "required": ["prompt"],
                },
            ),
            ToolDefinition(
                name="iterate_cad",
                description="Modifies or iterates on the current CAD design based on user feedback.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "prompt": {"type": "STRING", "description": "The changes or modifications to apply."},
                    },
                    "required": ["prompt"],
                },
            ),
        ]

    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        # CAD execution is handled as a background task in ruth.py
        # The plugin returns a dispatch marker that ruth.py intercepts
        return {"result": f"_{tool_name}_dispatch", "_dispatch": tool_name, "_args": args}
