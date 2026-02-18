"""Central registry for managing integration lifecycle and dispatch."""

from typing import Optional

from .base import BaseIntegration


class IntegrationRegistry:
    """Manages all loaded integrations and dispatches tool calls.

    Similar to PluginRegistry but focused on external service integrations
    that require authentication, network connections, and lifecycle management.
    """

    def __init__(self):
        self._integrations: dict[str, BaseIntegration] = {}

    def register(self, integration: BaseIntegration) -> None:
        """Register an integration by its name.

        Args:
            integration: An instance of a BaseIntegration subclass.
        """
        if integration.name in self._integrations:
            print(
                f"[IntegrationRegistry] Warning: overwriting integration "
                f"'{integration.name}'"
            )
        self._integrations[integration.name] = integration
        print(
            f"[IntegrationRegistry] Registered '{integration.name}' "
            f"({len(integration.get_tools())} tools)"
        )

    def unregister(self, name: str) -> None:
        """Remove an integration by name.

        Args:
            name: The integration's unique name.
        """
        if name not in self._integrations:
            print(f"[IntegrationRegistry] '{name}' not found, nothing to unregister")
            return
        del self._integrations[name]
        print(f"[IntegrationRegistry] Unregistered '{name}'")

    def get(self, name: str) -> Optional[BaseIntegration]:
        """Retrieve a registered integration by name."""
        return self._integrations.get(name)

    def list_all(self) -> list[dict]:
        """Return summary info for every registered integration."""
        return [
            {
                "name": integ.name,
                "description": integ.description,
                "connected": integ.is_connected,
                "tools": [t["name"] for t in integ.get_tools()],
            }
            for integ in self._integrations.values()
        ]

    async def setup_all(self) -> dict[str, bool]:
        """Initialize every registered integration.

        Returns:
            Dict mapping integration name to success boolean.
        """
        results: dict[str, bool] = {}
        for name, integ in self._integrations.items():
            try:
                await integ.setup()
                results[name] = True
                print(f"[IntegrationRegistry] '{name}' setup OK")
            except Exception as e:
                results[name] = False
                print(f"[IntegrationRegistry] '{name}' setup failed: {e}")
        return results

    async def teardown_all(self) -> None:
        """Tear down every registered integration."""
        for name, integ in self._integrations.items():
            try:
                await integ.teardown()
                print(f"[IntegrationRegistry] '{name}' teardown OK")
            except Exception as e:
                print(f"[IntegrationRegistry] '{name}' teardown error: {e}")

    async def execute(
        self, integration_name: str, tool_name: str, args: dict
    ) -> dict:
        """Dispatch a tool call to the correct integration.

        Args:
            integration_name: Which integration owns the tool.
            tool_name: The tool to execute.
            args: Arguments from the AI model.

        Returns:
            Dict with 'result' key on success, or error information.
        """
        integ = self._integrations.get(integration_name)
        if integ is None:
            return {"result": f"Integration '{integration_name}' not found"}

        if not integ.is_connected:
            return {
                "result": f"Integration '{integration_name}' is not connected. "
                f"Call setup() first."
            }

        try:
            return await integ.execute(tool_name, args)
        except Exception as e:
            print(
                f"[IntegrationRegistry] Error in '{integration_name}.{tool_name}': {e}"
            )
            return {"result": f"Integration error: {e}"}

    def get_all_tool_declarations(self) -> list[dict]:
        """Return tool definitions from all connected integrations.

        Useful for building the combined tool list sent to the AI model.
        """
        declarations: list[dict] = []
        for integ in self._integrations.values():
            if integ.is_connected:
                declarations.extend(integ.get_tools())
        return declarations
