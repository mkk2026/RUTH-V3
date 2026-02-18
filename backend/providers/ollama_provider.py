"""Ollama (local models) provider implementation."""

import os
import json
from typing import AsyncIterator, Optional

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    _AIOHTTP_AVAILABLE = False

from .base import BaseProvider, GenerateResponse, StreamChunk, EmbeddingResponse


class OllamaProvider(BaseProvider):
    """Ollama local model provider.

    Communicates with a running Ollama server via HTTP API.
    No additional packages needed beyond aiohttp (already a project dependency).
    """

    DEFAULT_MODEL = "llama3.1"
    DEFAULT_EMBED_MODEL = "nomic-embed-text"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.base_url = kwargs.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def name(self) -> str:
        return "ollama"

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
        target_model = model or self.DEFAULT_MODEL

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_instruction:
            payload["system"] = system_instruction
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
            ) as resp:
                data = await resp.json()

        return GenerateResponse(
            text=data.get("response", ""),
            raw=data,
        )

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
        target_model = model or self.DEFAULT_MODEL

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if system_instruction:
            payload["system"] = system_instruction
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
            ) as resp:
                async for line in resp.content:
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue

                    text = data.get("response", "")
                    if text:
                        yield StreamChunk(text=text)

                    if data.get("done", False):
                        break

        yield StreamChunk(is_done=True)

    async def embed(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        target_model = model or self.DEFAULT_EMBED_MODEL

        payload = {
            "model": target_model,
            "input": text,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/embed",
                json=payload,
            ) as resp:
                data = await resp.json()

        embeddings = data.get("embeddings", [[]])
        return EmbeddingResponse(
            embedding=embeddings[0] if embeddings else [],
            raw=data,
        )
