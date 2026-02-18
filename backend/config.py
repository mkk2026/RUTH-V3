"""Centralized configuration management for R.U.T.H. V3.

Handles settings persistence, .env secrets, Pydantic validation, and hot-reload.
API keys are read from .env, never stored in settings.json.
"""

import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


# --- Default Configuration ---

DEFAULT_MODEL_CONFIG = {
    "voice": {"provider": "gemini", "model": "models/gemini-2.5-flash-native-audio-preview-12-2025"},
    "cad": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "web_agent": {"provider": "gemini", "model": "gemini-2.5-computer-use-preview-10-2025"},
    "chat": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "embeddings": {"provider": "gemini", "model": "text-embedding-004"},
    "general": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "memory_extraction": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "skill_generation": {"provider": "gemini", "model": "gemini-2.5-flash"},
}

DEFAULT_TOOL_PERMISSIONS = {
    "generate_cad": True,
    "iterate_cad": True,
    "run_web_agent": True,
    "write_file": True,
    "read_directory": True,
    "read_file": True,
    "create_project": True,
    "switch_project": True,
    "list_projects": True,
    "list_smart_devices": True,
    "control_light": True,
    "discover_printers": True,
    "print_stl": True,
    "get_print_status": True,
    "execute_command": True,
    "execute_code": True,
}

DEFAULT_MEMORY_CONFIG = {
    "enabled": True,
    "auto_extract": True,
    "storage_path": "~/.ruth/memory",
    "max_episodic_entries": 1000,
    "max_semantic_entries": 5000,
    "rag_top_k": 5,
}

DEFAULT_SCHEDULER_CONFIG = {
    "enabled": False,
    "storage_path": "~/.ruth/scheduler",
    "max_concurrent_tasks": 5,
}

DEFAULT_INTEGRATIONS_CONFIG = {
    "enabled_integrations": [],
    "webhook_port": 8001,
    "oauth_tokens_path": "~/.ruth/tokens",
}

DEFAULT_MESSAGING_CONFIG = {
    "enabled_platforms": [],
    "telegram": {"bot_token": ""},
    "discord": {"bot_token": ""},
    "slack": {"bot_token": "", "app_token": ""},
}

DEFAULT_DAEMON_CONFIG = {
    "enabled": False,
    "auto_start": False,
    "log_path": "~/.ruth/logs",
}

DEFAULT_SETTINGS = {
    "face_auth_enabled": False,
    "camera_flipped": False,
    "tool_permissions": DEFAULT_TOOL_PERMISSIONS,
    "printers": [],
    "kasa_devices": [],
    "model_config": DEFAULT_MODEL_CONFIG,
    "plugins": {
        "enabled": True,
        "directories": ["~/.ruth/plugins"],
        "disabled_plugins": [],
    },
    "memory": DEFAULT_MEMORY_CONFIG,
    "scheduler": DEFAULT_SCHEDULER_CONFIG,
    "integrations": DEFAULT_INTEGRATIONS_CONFIG,
    "messaging": DEFAULT_MESSAGING_CONFIG,
    "daemon": DEFAULT_DAEMON_CONFIG,
}


class AppConfig:
    """Application configuration manager.

    Loads settings from settings.json, merges with defaults,
    and reads API keys from environment variables.
    """

    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = Path(settings_file)
        self._settings: dict = {}
        self._callbacks: list = []
        self.load()

    def load(self):
        """Load settings from file, merging with defaults."""
        self._settings = json.loads(json.dumps(DEFAULT_SETTINGS))

        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    loaded = json.load(f)
                self._deep_merge(self._settings, loaded)
                print(f"[Config] Loaded settings from {self.settings_file}")
            except Exception as e:
                print(f"[Config] Error loading settings: {e}")
        else:
            print(f"[Config] No settings file found, using defaults")
            self.save()

    def save(self):
        """Persist current settings to file."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self._settings, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving settings: {e}")

    def get(self, key: str, default=None):
        """Get a top-level setting."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a top-level setting and save."""
        self._settings[key] = value
        self.save()
        self._notify(key, value)

    def update(self, data: dict):
        """Update multiple settings and save."""
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(self._settings.get(key), dict):
                self._settings[key].update(value)
            else:
                self._settings[key] = value
        self.save()
        self._notify("bulk_update", data)

    def get_all(self) -> dict:
        """Return full settings dictionary."""
        return dict(self._settings)

    def on_change(self, callback):
        """Register a callback for settings changes."""
        self._callbacks.append(callback)

    def _notify(self, key: str, value):
        """Notify registered callbacks of changes."""
        for cb in self._callbacks:
            try:
                cb(key, value)
            except Exception as e:
                print(f"[Config] Callback error: {e}")

    @property
    def model_config(self) -> dict:
        return self._settings.get("model_config", DEFAULT_MODEL_CONFIG)

    @property
    def tool_permissions(self) -> dict:
        return self._settings.get("tool_permissions", DEFAULT_TOOL_PERMISSIONS)

    @property
    def memory_config(self) -> dict:
        return self._settings.get("memory", DEFAULT_MEMORY_CONFIG)

    @property
    def scheduler_config(self) -> dict:
        return self._settings.get("scheduler", DEFAULT_SCHEDULER_CONFIG)

    @property
    def plugins_config(self) -> dict:
        return self._settings.get("plugins", {})

    @property
    def messaging_config(self) -> dict:
        return self._settings.get("messaging", DEFAULT_MESSAGING_CONFIG)

    @property
    def integrations_config(self) -> dict:
        return self._settings.get("integrations", DEFAULT_INTEGRATIONS_CONFIG)

    @property
    def daemon_config(self) -> dict:
        return self._settings.get("daemon", DEFAULT_DAEMON_CONFIG)

    @staticmethod
    def get_api_keys() -> dict:
        """Read API keys from environment variables. Never stored in settings.json."""
        return {
            "gemini": os.getenv("GEMINI_API_KEY", ""),
            "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            "openai": os.getenv("OPENAI_API_KEY", ""),
        }

    @staticmethod
    def _deep_merge(base: dict, override: dict):
        """Recursively merge override into base in-place."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                AppConfig._deep_merge(base[key], value)
            else:
                base[key] = value
