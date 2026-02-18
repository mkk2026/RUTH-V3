"""Google Gemini provider implementation."""

import os
from typing import AsyncIterator, Optional

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    _GENAI_AVAILABLE = False

from .base import BaseProvider, GenerateResponse, StreamChunk, EmbeddingResponse


class GeminiProvider(BaseProvider):
    """Google Gemini API provider.

    Handles text generation, streaming with thinking, and embeddings.
    The Gemini Live Audio API is handled separately in ruth.py since it
    requires a persistent WebSocket session.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        super().__init__(api_key=resolved_key, **kwargs)
        self.client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=self.api_key,
        )

    @property
    def name(self) -> str:
        return "gemini"

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

        config_kwargs = {
            "temperature": temperature,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if max_tokens:
            config_kwargs["max_output_tokens"] = max_tokens
        if thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(include_thoughts=True)
        if tools:
            config_kwargs["tools"] = tools

        config = types.GenerateContentConfig(**config_kwargs)

        response = await self.client.aio.models.generate_content(
            model=target_model,
            contents=prompt,
            config=config,
        )

        text_parts = []
        thinking_parts = []

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if not part.text:
                    continue
                if part.thought:
                    thinking_parts.append(part.text)
                else:
                    text_parts.append(part.text)

        return GenerateResponse(
            text="".join(text_parts),
            thinking="".join(thinking_parts) if thinking_parts else None,
            raw=response,
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

        config_kwargs = {
            "temperature": temperature,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if max_tokens:
            config_kwargs["max_output_tokens"] = max_tokens
        if thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(include_thoughts=True)

        config = types.GenerateContentConfig(**config_kwargs)

        stream = await self.client.aio.models.generate_content_stream(
            model=target_model,
            contents=prompt,
            config=config,
        )

        async for chunk in stream:
            if not chunk.candidates:
                continue
            candidate = chunk.candidates[0]
            if not candidate.content or not candidate.content.parts:
                continue

            for part in candidate.content.parts:
                if not part.text:
                    continue
                if part.thought:
                    yield StreamChunk(thinking=part.text, is_thinking=True)
                else:
                    yield StreamChunk(text=part.text, is_thinking=False)

        yield StreamChunk(is_done=True)

    async def embed(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        **kwargs,
    ) -> EmbeddingResponse:
        target_model = model or "text-embedding-004"
        result = await self.client.aio.models.embed_content(
            model=target_model,
            content=text,
        )
        return EmbeddingResponse(
            embedding=list(result.embedding.values),
            raw=result,
        )
