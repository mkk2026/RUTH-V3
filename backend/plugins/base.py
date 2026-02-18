"""Base classes for the plugin system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ToolDefinition:
    """Definition of a tool that can be called by the AI."""
    name: str
    description: str
    parameters: dict
    handler: Optional[Callable] = None
    requires_confirmation: bool = True
    is_async: bool = True


@dataclass
class PluginContext:
    """Context object passed to plugins during execution.

    Provides access to shared services without tight coupling.
    """
    router: Any = None           # ModelRouter instance
    project_manager: Any = None  # ProjectManager instance
    config: Any = None           # AppConfig instance
    emit: Optional[Callable] = None  # Socket.IO emit function
    session: Any = None          # Gemini Live session (for sending notifications)


class BasePlugin(ABC):
    """Abstract base class for all plugins.

    Plugins must implement:
        - name: Unique plugin identifier
        - description: What the plugin does
        - get_tools(): Returns list of ToolDefinition
        - execute(tool_name, args, context): Runs a tool
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def author(self) -> str:
        return "core-brim-tech"

    @property
    def enabled(self) -> bool:
        return getattr(self, '_enabled', True)

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return tool definitions this plugin provides."""
        ...

    @abstractmethod
    async def execute(self, tool_name: str, args: dict, context: PluginContext) -> dict:
        """Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments from the AI model
            context: Shared context with access to services

        Returns:
            Dict with at least a 'result' key containing the response text
        """
        ...

    async def on_load(self, context: PluginContext):
        """Called when the plugin is loaded. Override for initialization."""
        pass

    async def on_unload(self):
        """Called when the plugin is unloaded. Override for cleanup."""
        pass
