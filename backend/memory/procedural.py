"""Procedural memory -- stores learned workflows and skills."""

import time
import uuid
from typing import Optional

from .vector_store import VectorStore


class ProceduralMemory:
    """Stores learned workflows and step-by-step procedures.

    'To deploy user app: npm run build && scp dist/ server:/var/www'
    """

    def __init__(self, storage_path: str):
        self.store = VectorStore(storage_path, "procedural")

    def add(self, procedure: str, trigger: str = "", metadata: Optional[dict] = None, embedding: Optional[list] = None):
        """Store a learned procedure.

        Args:
            procedure: The steps/workflow description
            trigger: What triggers this procedure (e.g., 'deploy app', 'backup database')
        """
        doc_id = f"proc_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        meta = {
            "timestamp": time.time(),
            "type": "procedural",
            "trigger": trigger,
            **(metadata or {}),
        }
        self.store.add(doc_id, procedure, metadata=meta, embedding=embedding)

    def search(self, query: str = "", query_embedding: Optional[list] = None, top_k: int = 3) -> list[dict]:
        """Find relevant procedures."""
        return self.store.query(
            query_text=query,
            query_embedding=query_embedding,
            top_k=top_k,
            where={"type": "procedural"},
        )

    @property
    def count(self) -> int:
        return self.store.count()
