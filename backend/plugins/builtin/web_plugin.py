"""Built-in web browser automation plugin."""

from plugins.base import BasePlugin, PluginContext, ToolDefinition


class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "web_agent"

    @property
    def description(self) -> str:
        return "Web browser automation using Playwright and AI computer-use"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="run_web_agent",
                description="Opens a web browser and performs a task according to the prompt.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "prompt": {"type": "STRING", "description": "Detailed instructions for the web browser agent."},
                    },
                    "required": ["prompt"],
                },
            ),
        ]

    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        return {"result": f"_{tool_name}_dispatch", "_dispatch": tool_name, "_args": args}
