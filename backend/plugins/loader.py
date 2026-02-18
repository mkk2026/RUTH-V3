"""Plugin discovery and loading system."""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Optional

from .base import BasePlugin, PluginContext
from .registry import PluginRegistry


class PluginLoader:
    """Discovers, validates, and loads plugins from configured directories.

    Scans for:
    1. Built-in plugins in backend/plugins/builtin/
    2. User plugins in ~/.ruth/plugins/
    3. Any additional directories from config
    """

    def __init__(self, registry: PluginRegistry, plugin_dirs: Optional[list[str]] = None):
        self.registry = registry

        # Default directories
        builtin_dir = os.path.join(os.path.dirname(__file__), "builtin")
        user_dir = os.path.expanduser("~/.ruth/plugins")

        self.plugin_dirs = [builtin_dir, user_dir]
        if plugin_dirs:
            for d in plugin_dirs:
                expanded = os.path.expanduser(d)
                if expanded not in self.plugin_dirs:
                    self.plugin_dirs.append(expanded)

    async def load_all(self, context: PluginContext, disabled: Optional[list[str]] = None):
        """Load all plugins from all configured directories.

        Args:
            context: Plugin context for initialization
            disabled: List of plugin names to skip
        """
        disabled_set = set(disabled or [])

        for plugin_dir in self.plugin_dirs:
            if not os.path.isdir(plugin_dir):
                os.makedirs(plugin_dir, exist_ok=True)
                continue

            await self._load_from_directory(plugin_dir, context, disabled_set)

    async def _load_from_directory(self, directory: str, context: PluginContext, disabled: set):
        """Load plugins from a single directory."""
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)

            # Single .py file plugin
            if item.endswith(".py") and not item.startswith("_"):
                plugin = self._load_module_plugin(item_path)
                if plugin and plugin.name not in disabled:
                    await self._register_plugin(plugin, context)

            # Directory plugin (must contain __init__.py or plugin.py)
            elif os.path.isdir(item_path):
                init_path = os.path.join(item_path, "__init__.py")
                plugin_path = os.path.join(item_path, "plugin.py")

                target = init_path if os.path.exists(init_path) else plugin_path
                if os.path.exists(target):
                    plugin = self._load_module_plugin(target)
                    if plugin and plugin.name not in disabled:
                        await self._register_plugin(plugin, context)

    def _load_module_plugin(self, filepath: str) -> Optional[BasePlugin]:
        """Load a plugin from a Python file."""
        try:
            module_name = Path(filepath).stem
            spec = importlib.util.spec_from_file_location(f"plugin_{module_name}", filepath)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for a Plugin class or create_plugin function
            if hasattr(module, "Plugin") and issubclass(module.Plugin, BasePlugin):
                return module.Plugin()
            elif hasattr(module, "create_plugin"):
                return module.create_plugin()

            return None

        except Exception as e:
            print(f"[PluginLoader] Error loading plugin from {filepath}: {e}")
            return None

    async def _register_plugin(self, plugin: BasePlugin, context: PluginContext):
        """Register a plugin and call its on_load hook."""
        try:
            await plugin.on_load(context)
            self.registry.register(plugin)
        except Exception as e:
            print(f"[PluginLoader] Error initializing plugin '{plugin.name}': {e}")

    async def load_single(self, filepath: str, context: PluginContext) -> Optional[BasePlugin]:
        """Load and register a single plugin file."""
        plugin = self._load_module_plugin(filepath)
        if plugin:
            await self._register_plugin(plugin, context)
        return plugin
