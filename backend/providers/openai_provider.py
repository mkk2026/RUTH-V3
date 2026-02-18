"""OpenAI (GPT) provider implementation."""

import os
from typing import AsyncIterator, Optional

from .base import BaseProvider, GenerateResponse, StreamChunk, EmbeddingResponse


class OpenAIProvider(BaseProvider):
    """OpenAI GPT API provider.

    Requires the `openai` package: pip install openai
    """

    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        super().__init__(api_key=resolved_key, **kwargs)
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

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
        client = self._get_client()
        target_model = model or self.DEFAULT_MODEL

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        create_kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            create_kwargs["max_tokens"] = max_tokens

        response = await client.chat.completions.create(**create_kwargs)
        text = response.choices[0].message.content or ""

        return GenerateResponse(text=text, raw=response)

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
        client = self._get_client()
        target_model = model or self.DEFAULT_MODEL

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        create_kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            create_kwargs["max_tokens"] = max_tokens

        stream = await client.chat.completions.create(**create_kwargs)
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield StreamChunk(text=chunk.choices[0].delta.content)

        yield StreamChunk(is_done=True)

    async def embed(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        client = self._get_client()
        target_model = model or "text-embedding-3-small"
        response = await client.embeddings.create(
            model=target_model,
            input=text,
        )
        return EmbeddingResponse(
            embedding=response.data[0].embedding,
            raw=response,
        )
