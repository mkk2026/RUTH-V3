"""Abstract base class for all model providers."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional
from dataclasses import dataclass, field


@dataclass
class GenerateResponse:
    """Standardized response from a model provider."""
    text: str
    thinking: Optional[str] = None
    tool_calls: list = field(default_factory=list)
    raw: Any = None


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""
    text: str = ""
    thinking: str = ""
    is_thinking: bool = False
    is_done: bool = False


@dataclass
class EmbeddingResponse:
    """Response from an embedding request."""
    embedding: list = field(default_factory=list)
    raw: Any = None


class BaseProvider(ABC):
    """Abstract base class for all model providers.

    Each provider must implement generate() and stream().
    Embedding support is optional.
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'gemini', 'anthropic', 'openai', 'ollama')."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None,
        thinking: bool = False,
        **kwargs,
    ) -> GenerateResponse:
        """Generate a complete response from the model."""
        ...

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        thinking: bool = False,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from the model."""
        ...

    async def embed(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        """Generate embeddings. Not all providers support this."""
        raise NotImplementedError(f"{self.name} does not support embeddings")
