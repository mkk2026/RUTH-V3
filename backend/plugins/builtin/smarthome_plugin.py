"""Built-in smart home (TP-Link Kasa) plugin."""

from plugins.base import BasePlugin, PluginContext, ToolDefinition


class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "smart_home"

    @property
    def description(self) -> str:
        return "TP-Link Kasa smart home device discovery and control"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="list_smart_devices",
                description="Lists all available smart home devices on the network.",
                parameters={"type": "OBJECT", "properties": {}},
                requires_confirmation=False,
            ),
            ToolDefinition(
                name="control_light",
                description="Controls a smart light device.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "target": {"type": "STRING", "description": "IP address of the device."},
                        "action": {"type": "STRING", "description": "'turn_on', 'turn_off', or 'set'."},
                        "brightness": {"type": "INTEGER", "description": "Optional brightness 0-100."},
                        "color": {"type": "STRING", "description": "Optional color name or 'warm'."},
                    },
                    "required": ["target", "action"],
                },
            ),
        ]

    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        # Smart home execution is handled inline in ruth.py due to device state management
        return {"result": f"_{tool_name}_dispatch", "_dispatch": tool_name, "_args": args}
