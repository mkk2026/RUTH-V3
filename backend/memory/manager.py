"""Central memory manager coordinating all three memory tiers."""

import os
from typing import Optional

from .episodic import EpisodicMemory
from .semantic import SemanticMemory
from .procedural import ProceduralMemory
from .extractor import MemoryExtractor


class MemoryManager:
    """Manages the three-tier memory system.

    Coordinates episodic, semantic, and procedural memory stores.
    Provides a unified interface for storing and retrieving memories,
    and automatic extraction from conversations.
    """

    def __init__(self, storage_path: str = "~/.ruth/memory", router=None, config: Optional[dict] = None):
        self.storage_path = os.path.expanduser(storage_path)
        self.router = router
        self.config = config or {}

        os.makedirs(self.storage_path, exist_ok=True)

        max_episodic = self.config.get("max_episodic_entries", 1000)
        max_semantic = self.config.get("max_semantic_entries", 5000)

        self.episodic = EpisodicMemory(self.storage_path, max_entries=max_episodic)
        self.semantic = SemanticMemory(self.storage_path, max_entries=max_semantic)
        self.procedural = ProceduralMemory(self.storage_path)
        self.extractor = MemoryExtractor(router=router)

        self._auto_extract = self.config.get("auto_extract", True)
        self._conversation_buffer = []
        self._buffer_max = 10  # Process after this many turns

        print(f"[MemoryManager] Initialized at {self.storage_path}")
        print(f"[MemoryManager] Counts: episodic={self.episodic.count}, semantic={self.semantic.count}, procedural={self.procedural.count}")

    def add_conversation_turn(self, sender: str, text: str):
        """Buffer a conversation turn for potential extraction.

        Call this for every chat message. When the buffer fills,
        automatic extraction runs.
        """
        self._conversation_buffer.append({"sender": sender, "text": text})

        if self._auto_extract and len(self._conversation_buffer) >= self._buffer_max:
            # Return the buffer for async processing (caller should await process_buffer())
            pass

    async def process_buffer(self):
        """Process buffered conversation turns to extract memories."""
        if not self._conversation_buffer:
            return

        conversation_text = "\n".join(
            f"[{turn['sender']}]: {turn['text']}"
            for turn in self._conversation_buffer
        )

        self._conversation_buffer.clear()

        extracted = await self.extractor.extract(conversation_text)

        # Store episodic summary
        if extracted["summary"]:
            embedding = await self._get_embedding(extracted["summary"])
            self.episodic.add(extracted["summary"], embedding=embedding)

        # Store semantic facts
        for fact in extracted["facts"]:
            embedding = await self._get_embedding(fact)
            self.semantic.add(fact, embedding=embedding)

        # Store procedural workflows
        for proc in extracted["procedures"]:
            embedding = await self._get_embedding(proc)
            self.procedural.add(proc, embedding=embedding)

        total = len(extracted["facts"]) + len(extracted["procedures"]) + (1 if extracted["summary"] else 0)
        if total > 0:
            print(f"[MemoryManager] Extracted {total} memories from conversation")

    async def get_relevant_context(self, query: str, top_k: int = 5) -> str:
        """Retrieve relevant memories for RAG context injection.

        Args:
            query: The current user query or conversation context
            top_k: Max results per memory tier

        Returns:
            Formatted string of relevant memories for context injection
        """
        query_embedding = await self._get_embedding(query)

        # Search all three tiers
        episodic_results = self.episodic.search(query, query_embedding=query_embedding, top_k=top_k)
        semantic_results = self.semantic.search(query, query_embedding=query_embedding, top_k=top_k)
        procedural_results = self.procedural.search(query, query_embedding=query_embedding, top_k=min(top_k, 3))

        context_parts = []

        if semantic_results:
            facts = [r["text"] for r in semantic_results]
            context_parts.append("Known facts about the user:\n" + "\n".join(f"- {f}" for f in facts))

        if episodic_results:
            episodes = [r["text"] for r in episodic_results]
            context_parts.append("Relevant past interactions:\n" + "\n".join(f"- {e}" for e in episodes))

        if procedural_results:
            procs = [r["text"] for r in procedural_results]
            context_parts.append("Relevant learned procedures:\n" + "\n".join(f"- {p}" for p in procs))

        if not context_parts:
            return ""

        return "\n\n".join(context_parts)

    async def _get_embedding(self, text: str) -> Optional[list]:
        """Generate an embedding for the given text using the configured provider."""
        if not self.router:
            return None
        try:
            provider = self.router.get_provider("embeddings")
            model = self.router.get_model("embeddings")
            result = await provider.embed(text, model=model)
            return result.embedding
        except Exception as e:
            print(f"[MemoryManager] Embedding failed: {e}")
            return None

    def get_stats(self) -> dict:
        """Return memory store statistics."""
        return {
            "episodic_count": self.episodic.count,
            "semantic_count": self.semantic.count,
            "procedural_count": self.procedural.count,
            "storage_path": self.storage_path,
            "auto_extract": self._auto_extract,
        }
