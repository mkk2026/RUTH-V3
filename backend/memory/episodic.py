"""Episodic memory -- stores conversation summaries and event records."""

import time
import uuid
from typing import Optional

from .vector_store import VectorStore


class EpisodicMemory:
    """Stores timestamped conversation summaries and events.

    'Last Tuesday, user asked me to design a phone stand.'
    """

    def __init__(self, storage_path: str, max_entries: int = 1000):
        self.store = VectorStore(storage_path, "episodic")
        self.max_entries = max_entries

    def add(self, summary: str, metadata: Optional[dict] = None, embedding: Optional[list] = None):
        """Store a conversation summary."""
        doc_id = f"ep_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        meta = {
            "timestamp": time.time(),
            "type": "episodic",
            **(metadata or {}),
        }
        self.store.add(doc_id, summary, metadata=meta, embedding=embedding)

    def search(self, query: str = "", query_embedding: Optional[list] = None, top_k: int = 5) -> list[dict]:
        """Find relevant past conversations."""
        return self.store.query(
            query_text=query,
            query_embedding=query_embedding,
            top_k=top_k,
            where={"type": "episodic"},
        )

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Get most recent episodic memories (fallback, non-semantic)."""
        all_docs = self.store.query(query_text="", top_k=limit)
        return sorted(all_docs, key=lambda x: x.get("metadata", {}).get("timestamp", 0), reverse=True)[:limit]

    @property
    def count(self) -> int:
        return self.store.count()
