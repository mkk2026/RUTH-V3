"""Vector store abstraction for semantic memory search.

Uses ChromaDB when available, falls back to a simple in-memory cosine similarity search.
"""

import os
import json
import math
from typing import Optional
from pathlib import Path


class VectorStore:
    """Persistent vector store with semantic search.

    Attempts to use ChromaDB for production use.
    Falls back to a JSON-based store with brute-force cosine similarity if ChromaDB is unavailable.
    """

    def __init__(self, storage_path: str, collection_name: str):
        self.storage_path = os.path.expanduser(storage_path)
        self.collection_name = collection_name
        self._chroma_collection = None
        self._fallback_store: list[dict] = []
        self._fallback_path = os.path.join(self.storage_path, f"{collection_name}.json")
        self._use_chroma = False

        os.makedirs(self.storage_path, exist_ok=True)
        self._init_store()

    def _init_store(self):
        """Try ChromaDB, fall back to JSON."""
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.storage_path)
            self._chroma_collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._use_chroma = True
            print(f"[VectorStore] Using ChromaDB for '{self.collection_name}'")
        except ImportError:
            print(f"[VectorStore] ChromaDB not installed, using JSON fallback for '{self.collection_name}'")
            self._load_fallback()
        except Exception as e:
            print(f"[VectorStore] ChromaDB error: {e}, using JSON fallback")
            self._load_fallback()

    def _load_fallback(self):
        """Load the JSON fallback store."""
        if os.path.exists(self._fallback_path):
            try:
                with open(self._fallback_path, "r") as f:
                    self._fallback_store = json.load(f)
            except Exception:
                self._fallback_store = []

    def _save_fallback(self):
        """Save the JSON fallback store."""
        try:
            with open(self._fallback_path, "w") as f:
                json.dump(self._fallback_store, f)
        except Exception as e:
            print(f"[VectorStore] Error saving fallback: {e}")

    def add(self, doc_id: str, text: str, metadata: Optional[dict] = None, embedding: Optional[list] = None):
        """Add a document to the store."""
        meta = metadata or {}

        if self._use_chroma and self._chroma_collection is not None:
            kwargs = {
                "ids": [doc_id],
                "documents": [text],
                "metadatas": [meta],
            }
            if embedding:
                kwargs["embeddings"] = [embedding]
            self._chroma_collection.upsert(**kwargs)
        else:
            # Remove existing with same ID
            self._fallback_store = [d for d in self._fallback_store if d["id"] != doc_id]
            self._fallback_store.append({
                "id": doc_id,
                "text": text,
                "metadata": meta,
                "embedding": embedding or [],
            })
            self._save_fallback()

    def query(self, query_text: str = "", query_embedding: Optional[list] = None, top_k: int = 5, where: Optional[dict] = None) -> list[dict]:
        """Search for similar documents.

        Returns list of {id, text, metadata, distance}.
        """
        if self._use_chroma and self._chroma_collection is not None:
            kwargs = {"n_results": min(top_k, max(self._chroma_collection.count(), 1))}
            if query_embedding:
                kwargs["query_embeddings"] = [query_embedding]
            elif query_text:
                kwargs["query_texts"] = [query_text]
            else:
                return []
            if where:
                kwargs["where"] = where

            try:
                results = self._chroma_collection.query(**kwargs)
            except Exception as e:
                print(f"[VectorStore] Query error: {e}")
                return []

            docs = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    docs.append({
                        "id": doc_id,
                        "text": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })
            return docs

        # Fallback: brute-force cosine similarity
        if not query_embedding or not self._fallback_store:
            return self._fallback_store[:top_k]

        scored = []
        for doc in self._fallback_store:
            if not doc.get("embedding"):
                continue
            sim = self._cosine_similarity(query_embedding, doc["embedding"])
            scored.append({**doc, "distance": 1 - sim})

        scored.sort(key=lambda x: x["distance"])
        return scored[:top_k]

    def delete(self, doc_id: str):
        """Remove a document by ID."""
        if self._use_chroma and self._chroma_collection is not None:
            try:
                self._chroma_collection.delete(ids=[doc_id])
            except Exception:
                pass
        else:
            self._fallback_store = [d for d in self._fallback_store if d["id"] != doc_id]
            self._save_fallback()

    def count(self) -> int:
        """Return number of stored documents."""
        if self._use_chroma and self._chroma_collection is not None:
            return self._chroma_collection.count()
        return len(self._fallback_store)

    @staticmethod
    def _cosine_similarity(a: list, b: list) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
