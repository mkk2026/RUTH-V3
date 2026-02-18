"""Anthropic (Claude) provider implementation."""

import os
from typing import AsyncIterator, Optional

from .base import BaseProvider, GenerateResponse, StreamChunk


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider.

    Requires the `anthropic` package: pip install anthropic
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        super().__init__(api_key=resolved_key, **kwargs)
        self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "anthropic package required. Install with: pip install anthropic"
                )
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
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

        messages = [{"role": "user", "content": prompt}]
        create_kwargs = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens or 8192,
            "temperature": temperature,
        }
        if system_instruction:
            create_kwargs["system"] = system_instruction

        if thinking:
            create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 4096}

        response = await client.messages.create(**create_kwargs)

        text_parts = []
        thinking_parts = []

        for block in response.content:
            if block.type == "thinking":
                thinking_parts.append(block.thinking)
            elif block.type == "text":
                text_parts.append(block.text)

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
        client = self._get_client()
        target_model = model or self.DEFAULT_MODEL

        messages = [{"role": "user", "content": prompt}]
        create_kwargs = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens or 8192,
            "temperature": temperature,
        }
        if system_instruction:
            create_kwargs["system"] = system_instruction

        if thinking:
            create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 4096}

        async with client.messages.stream(**create_kwargs) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "thinking"):
                            yield StreamChunk(thinking=delta.thinking, is_thinking=True)
                        elif hasattr(delta, "text"):
                            yield StreamChunk(text=delta.text, is_thinking=False)

        yield StreamChunk(is_done=True)
