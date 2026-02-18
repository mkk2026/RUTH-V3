"""Built-in project management plugin."""

from plugins.base import BasePlugin, PluginContext, ToolDefinition


class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "projects"

    @property
    def description(self) -> str:
        return "Project creation, switching, and listing"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="create_project",
                description="Creates a new project folder to organize files.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "description": "The name of the new project."},
                    },
                    "required": ["name"],
                },
            ),
            ToolDefinition(
                name="switch_project",
                description="Switches the current active project context.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "description": "The name of the project to switch to."},
                    },
                    "required": ["name"],
                },
            ),
            ToolDefinition(
                name="list_projects",
                description="Lists all available projects.",
                parameters={
                    "type": "OBJECT",
                    "properties": {},
                },
                requires_confirmation=False,
            ),
        ]

    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        pm = context.project_manager
        if not pm:
            return {"result": "Project manager not available."}

        if tool_name == "create_project":
            name = args["name"]
            success, msg = pm.create_project(name)
            if success:
                pm.switch_project(name)
                msg += f" Switched to '{name}'."
            return {"result": msg}

        elif tool_name == "switch_project":
            name = args["name"]
            success, msg = pm.switch_project(name)
            if success and context.session:
                ctx = pm.get_project_context()
                try:
                    await context.session.send(
                        input=f"System Notification: {msg}\n\n{ctx}",
                        end_of_turn=False,
                    )
                except Exception:
                    pass
            return {"result": msg}

        elif tool_name == "list_projects":
            projects = pm.list_projects()
            return {"result": f"Available projects: {', '.join(projects)}"}

        return {"result": f"Unknown tool: {tool_name}"}
