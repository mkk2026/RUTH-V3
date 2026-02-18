"""Abstract base class for all external service integrations."""

from abc import ABC, abstractmethod
from typing import Any


class BaseIntegration(ABC):
    """Base class for external service integrations.

    Each integration wraps an external service (Gmail, Calendar, etc.)
    and exposes its functionality as a set of tools that R.U.T.H. can invoke.

    Subclasses must implement:
        - name: Unique identifier for this integration
        - description: Human-readable summary
        - setup(): Async initialization (auth, connections)
        - teardown(): Async cleanup
    """

    def __init__(self):
        self._connected: bool = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this integration."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this integration provides."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether the integration is currently active and authenticated."""
        return self._connected

    @abstractmethod
    async def setup(self) -> None:
        """Initialize the integration -- authenticate, open connections, etc.

        Should set self._connected = True on success.
        """
        ...

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up resources -- close connections, revoke sessions.

        Should set self._connected = False.
        """
        ...

    def get_tools(self) -> list[dict]:
        """Return tool definitions this integration provides.

        Each tool dict follows the format:
            {
                "name": "tool_name",
                "description": "What this tool does",
                "parameters": {
                    "type": "object",
                    "properties": { ... },
                    "required": [ ... ]
                }
            }

        Override in subclasses to expose integration-specific tools.
        """
        return []

    async def execute(self, tool_name: str, args: dict) -> dict:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: The tool to execute (must be in get_tools())
            args: Arguments from the AI model

        Returns:
            Dict with at least a 'result' key

        Raises:
            ValueError: If tool_name is not recognized
        """
        tool_names = [t["name"] for t in self.get_tools()]
        if tool_name not in tool_names:
            raise ValueError(
                f"Integration '{self.name}' has no tool '{tool_name}'. "
                f"Available: {tool_names}"
            )
        raise NotImplementedError(
            f"Tool '{tool_name}' is declared but not implemented in '{self.name}'"
        )
