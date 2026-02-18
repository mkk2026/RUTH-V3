"""Semantic memory -- stores facts, preferences, and knowledge about the user."""

import time
import uuid
from typing import Optional

from .vector_store import VectorStore


class SemanticMemory:
    """Persistent facts and preferences that persist across sessions.

    'User prefers metric units.'
    'User owns an Ender 3 V3 printer.'
    """

    def __init__(self, storage_path: str, max_entries: int = 5000):
        self.store = VectorStore(storage_path, "semantic")
        self.max_entries = max_entries

    def add(self, fact: str, category: str = "general", metadata: Optional[dict] = None, embedding: Optional[list] = None):
        """Store a fact or preference."""
        doc_id = f"sem_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        meta = {
            "timestamp": time.time(),
            "type": "semantic",
            "category": category,
            **(metadata or {}),
        }
        self.store.add(doc_id, fact, metadata=meta, embedding=embedding)

    def search(self, query: str = "", query_embedding: Optional[list] = None, top_k: int = 5, category: Optional[str] = None) -> list[dict]:
        """Find relevant facts."""
        where = {"type": "semantic"}
        if category:
            where["category"] = category
        return self.store.query(
            query_text=query,
            query_embedding=query_embedding,
            top_k=top_k,
            where=where,
        )

    def update(self, doc_id: str, new_fact: str, embedding: Optional[list] = None):
        """Update an existing fact."""
        self.store.delete(doc_id)
        self.store.add(doc_id, new_fact, embedding=embedding)

    def delete(self, doc_id: str):
        """Remove a fact."""
        self.store.delete(doc_id)

    @property
    def count(self) -> int:
        return self.store.count()
