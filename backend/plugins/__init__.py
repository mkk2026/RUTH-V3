"""
Dynamic plugin/skill system for R.U.T.H. V3.
Plugins register tools that the AI can invoke. Supports built-in and user-created plugins.
"""

from .base import BasePlugin, PluginContext, ToolDefinition
from .registry import PluginRegistry
from .loader import PluginLoader

__all__ = [
    "BasePlugin",
    "PluginContext",
    "ToolDefinition",
    "PluginRegistry",
    "PluginLoader",
]
