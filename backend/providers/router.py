"""Model router that directs requests to the appropriate provider based on task configuration."""

import os
from typing import Optional

from .base import BaseProvider
from .gemini import GeminiProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider


# Registry of available providers
PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}

# Default task-to-provider mapping
DEFAULT_MODEL_CONFIG = {
    "voice": {"provider": "gemini", "model": "models/gemini-2.5-flash-native-audio-preview-12-2025"},
    "cad": {"provider": "gemini", "model": "gemini-3-pro-preview"},
    "web_agent": {"provider": "gemini", "model": "gemini-2.5-computer-use-preview-10-2025"},
    "chat": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "embeddings": {"provider": "gemini", "model": "text-embedding-004"},
    "general": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "memory_extraction": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "skill_generation": {"provider": "gemini", "model": "gemini-2.5-flash"},
}


class ModelRouter:
    """Routes model requests to the configured provider for each task.

    Usage:
        router = ModelRouter(model_config=settings["model_config"], api_keys=api_keys)
        provider = router.get_provider("cad")
        response = await provider.generate("Design a phone stand", model=router.get_model("cad"))
    """

    def __init__(
        self,
        model_config: Optional[dict] = None,
        api_keys: Optional[dict] = None,
    ):
        self._model_config = {**DEFAULT_MODEL_CONFIG}
        if model_config:
            self._model_config.update(model_config)

        self._api_keys = api_keys or {}
        self._providers: dict[str, BaseProvider] = {}

    def _resolve_api_key(self, provider_name: str) -> Optional[str]:
        """Resolve API key from config, then environment variables."""
        key = self._api_keys.get(provider_name)
        if key:
            return key

        env_map = {
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
        }
        env_var = env_map.get(provider_name)
        if env_var:
            return os.getenv(env_var)
        return None

    def _get_or_create_provider(self, provider_name: str) -> BaseProvider:
        """Get a cached provider instance or create a new one."""
        if provider_name not in self._providers:
            provider_cls = PROVIDER_CLASSES.get(provider_name)
            if not provider_cls:
                raise ValueError(
                    f"Unknown provider: '{provider_name}'. "
                    f"Available: {list(PROVIDER_CLASSES.keys())}"
                )
            api_key = self._resolve_api_key(provider_name)
            self._providers[provider_name] = provider_cls(api_key=api_key)

        return self._providers[provider_name]

    def get_provider(self, task: str) -> BaseProvider:
        """Get the provider instance configured for the given task.

        Args:
            task: Task identifier (e.g., 'cad', 'chat', 'embeddings', 'web_agent')

        Returns:
            The configured BaseProvider instance
        """
        task_config = self._model_config.get(task, self._model_config.get("general"))
        if not task_config:
            raise ValueError(f"No provider configured for task: '{task}'")

        provider_name = task_config["provider"]
        return self._get_or_create_provider(provider_name)

    def get_model(self, task: str) -> str:
        """Get the model name configured for the given task."""
        task_config = self._model_config.get(task, self._model_config.get("general"))
        if not task_config:
            raise ValueError(f"No model configured for task: '{task}'")
        return task_config["model"]

    def get_task_config(self, task: str) -> dict:
        """Get the full task configuration (provider + model)."""
        return self._model_config.get(task, self._model_config.get("general", {}))

    def update_config(self, model_config: dict):
        """Update the model configuration at runtime."""
        self._model_config.update(model_config)

    def update_api_keys(self, api_keys: dict):
        """Update API keys and invalidate cached provider instances."""
        self._api_keys.update(api_keys)
        self._providers.clear()

    def list_tasks(self) -> dict:
        """Return current task-to-provider mapping."""
        return dict(self._model_config)

    def list_available_providers(self) -> list[str]:
        """Return names of available provider implementations."""
        return list(PROVIDER_CLASSES.keys())
