"""Built-in filesystem operations plugin."""

import os

from plugins.base import BasePlugin, PluginContext, ToolDefinition


class Plugin(BasePlugin):
    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "File read, write, and directory operations within projects"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="write_file",
                description="Writes content to a file at the specified path. Overwrites if exists.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "The path of the file to write to."},
                        "content": {"type": "STRING", "description": "The content to write to the file."},
                    },
                    "required": ["path", "content"],
                },
            ),
            ToolDefinition(
                name="read_file",
                description="Reads the content of a file.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "The path of the file to read."},
                    },
                    "required": ["path"],
                },
            ),
            ToolDefinition(
                name="read_directory",
                description="Lists the contents of a directory.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "path": {"type": "STRING", "description": "The path of the directory to list."},
                    },
                    "required": ["path"],
                },
            ),
        ]

    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        if tool_name == "write_file":
            return await self._write_file(args, context)
        elif tool_name == "read_file":
            return await self._read_file(args, context)
        elif tool_name == "read_directory":
            return await self._read_directory(args, context)
        return {"result": f"Unknown tool: {tool_name}"}

    async def _write_file(self, args: dict, context: PluginContext) -> dict:
        path = args["path"]
        content = args["content"]

        if context.project_manager:
            current_project_path = context.project_manager.get_current_project_path()
            if not os.path.isabs(path):
                final_path = current_project_path / path
            else:
                final_path = current_project_path / os.path.basename(path)
        else:
            final_path = path

        try:
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, "w", encoding="utf-8") as f:
                f.write(content)
            project_name = context.project_manager.current_project if context.project_manager else "unknown"
            return {"result": f"File '{os.path.basename(str(final_path))}' written to project '{project_name}'."}
        except Exception as e:
            return {"result": f"Failed to write file '{path}': {str(e)}"}

    def _resolve_path(self, path: str, context: PluginContext) -> str:
        """Resolve relative paths against the current project directory."""
        if context.project_manager and not os.path.isabs(path):
            return str(context.project_manager.get_current_project_path() / path)
        return path

    async def _read_file(self, args: dict, context: PluginContext) -> dict:
        path = self._resolve_path(args["path"], context)
        try:
            if not os.path.exists(path):
                return {"result": f"File '{args['path']}' does not exist."}
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"result": f"Content of '{args['path']}':\n{content}"}
        except Exception as e:
            return {"result": f"Failed to read file '{args['path']}': {str(e)}"}

    async def _read_directory(self, args: dict, context: PluginContext) -> dict:
        path = self._resolve_path(args["path"], context)
        try:
            if not os.path.exists(path):
                return {"result": f"Directory '{args['path']}' does not exist."}
            items = os.listdir(path)
            return {"result": f"Contents of '{args['path']}': {', '.join(items)}"}
        except Exception as e:
            return {"result": f"Failed to read directory '{args['path']}': {str(e)}"}
