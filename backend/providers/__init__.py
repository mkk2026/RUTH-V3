"""
Model provider abstraction layer for R.U.T.H. V3.
Supports Gemini, Anthropic (Claude), OpenAI (GPT), and Ollama (local models).
"""

from .base import BaseProvider, GenerateResponse, StreamChunk, EmbeddingResponse
from .router import ModelRouter

__all__ = [
    "BaseProvider",
    "GenerateResponse",
    "StreamChunk",
    "EmbeddingResponse",
    "ModelRouter",
]
