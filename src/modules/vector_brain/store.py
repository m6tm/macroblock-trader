"""Vector store implementations — ChromaDB primary, Numpy fallback."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Optional ChromaDB ----------------------------------------------------------
try:
    import chromadb
    from chromadb.config import Settings

    _CHROMADB_AVAILABLE = True
except Exception:  # pragma: no cover
    _CHROMADB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class VectorRecord:
    """A single vector + metadata pair."""

    trade_id: str
    vector: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of a k-NN query."""

    trade_id: str
    similarity: float
    metadata: Dict[str, Any]


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------
class VectorStore(ABC):
    """Abstract vector database."""

    @abstractmethod
    def add(self, record: VectorRecord) -> None:
        """Add or overwrite a vector record."""

    @abstractmethod
    def get(self, trade_id: str) -> Optional[VectorRecord]:
        """Retrieve a single record by trade_id."""

    @abstractmethod
    def query(
        self,
        vector: np.ndarray,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """k-NN search with optional metadata filters."""

    @abstractmethod
    def update_metadata(self, trade_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for an existing record."""

    @abstractmethod
    def count(self) -> int:
        """Total number of vectors stored."""

    @abstractmethod
    def delete(self, trade_id: str) -> bool:
        """Delete a record."""


# ---------------------------------------------------------------------------
# ChromaDB implementation
# ---------------------------------------------------------------------------
class ChromaVectorStore(VectorStore):
    """ChromaDB-backed vector store."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str = "gold_memory",
    ) -> None:
        if not _CHROMADB_AVAILABLE:
            raise RuntimeError(
                "ChromaDB is not installed. Install it with: pip install chromadb"
            )

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, record: VectorRecord) -> None:
        vector_list = record.vector.tolist()
        self._collection.upsert(
            ids=[record.trade_id],
            embeddings=[vector_list],
            metadatas=[record.metadata],
        )

    def get(self, trade_id: str) -> Optional[VectorRecord]:
        try:
            result = self._collection.get(ids=[trade_id], include=["embeddings", "metadatas"])
            if not result["ids"]:
                return None
            vec = np.array(result["embeddings"][0], dtype=np.float32)
            meta = result["metadatas"][0] if result["metadatas"] else {}
            return VectorRecord(trade_id=trade_id, vector=vec, metadata=meta)
        except Exception:
            return None

    def query(
        self,
        vector: np.ndarray,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        kwargs: Dict[str, Any] = {
            "query_embeddings": [vector.tolist()],
            "n_results": n_results,
            "include": ["distances", "metadatas"],
        }
        if filters:
            kwargs["where"] = filters

        result = self._collection.query(**kwargs)
        if not result["ids"] or not result["ids"][0]:
            return []

        out: List[RetrievalResult] = []
        for tid, dist, meta in zip(
            result["ids"][0],
            result["distances"][0],
            result["metadatas"][0],
        ):
            # Chroma cosine distance = 1 - cosine_similarity
            similarity = max(0.0, 1.0 - float(dist))
            out.append(RetrievalResult(trade_id=tid, similarity=similarity, metadata=meta))
        return out

    def update_metadata(self, trade_id: str, metadata: Dict[str, Any]) -> bool:
        try:
            self._collection.update(ids=[trade_id], metadatas=[metadata])
            return True
        except Exception:
            return False

    def count(self) -> int:
        return self._collection.count()

    def delete(self, trade_id: str) -> bool:
        try:
            self._collection.delete(ids=[trade_id])
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Numpy fallback implementation (pure Python, no external vector DB)
# ---------------------------------------------------------------------------
class NumpyVectorStore(VectorStore):
    """In-memory vector store backed by NumPy with optional JSON persistence.

    Used as fallback when ChromaDB is unavailable (e.g. Termux / restricted env).
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._vectors: Dict[str, np.ndarray] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load()

    # ------------------------------------------------------------------ persistence
    def _load(self) -> None:
        with open(self._persist_path, "r", encoding="utf-8") as fh:  # type: ignore[arg-type]
            raw = fh.read().strip()
            if not raw:
                return
            data = json.loads(raw)
        for item in data:
            self._vectors[item["id"]] = np.array(item["vector"], dtype=np.float32)
            self._metadata[item["id"]] = item.get("metadata", {})

    def persist(self) -> None:
        if not self._persist_path:
            return
        Path(self._persist_path).parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "id": tid,
                "vector": self._vectors[tid].tolist(),
                "metadata": self._metadata.get(tid, {}),
            }
            for tid in self._vectors
        ]
        with open(self._persist_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)

    # ------------------------------------------------------------------ VectorStore API
    def add(self, record: VectorRecord) -> None:
        self._vectors[record.trade_id] = record.vector.astype(np.float32)
        self._metadata[record.trade_id] = dict(record.metadata)
        self.persist()

    def get(self, trade_id: str) -> Optional[VectorRecord]:
        vec = self._vectors.get(trade_id)
        if vec is None:
            return None
        return VectorRecord(
            trade_id=trade_id,
            vector=vec.copy(),
            metadata=dict(self._metadata.get(trade_id, {})),
        )

    def query(
        self,
        vector: np.ndarray,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        if not self._vectors:
            return []

        vec = vector.astype(np.float32)
        # Cosine similarity against all stored vectors
        ids = list(self._vectors.keys())
        mat = np.stack([self._vectors[tid] for tid in ids])

        # Normalise query and matrix
        vec_norm = vec / (np.linalg.norm(vec) + 1e-9)
        mat_norm = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
        similarities = mat_norm @ vec_norm

        # Build results with optional filter
        results: List[RetrievalResult] = []
        for tid, sim in zip(ids, similarities):
            meta = self._metadata.get(tid, {})
            if filters and not _match_filter(meta, filters):
                continue
            results.append(RetrievalResult(trade_id=tid, similarity=float(sim), metadata=meta))

        # Sort descending by similarity
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:n_results]

    def update_metadata(self, trade_id: str, metadata: Dict[str, Any]) -> bool:
        if trade_id not in self._vectors:
            return False
        self._metadata[trade_id].update(metadata)
        self.persist()
        return True

    def count(self) -> int:
        return len(self._vectors)

    def delete(self, trade_id: str) -> bool:
        if trade_id not in self._vectors:
            return False
        del self._vectors[trade_id]
        self._metadata.pop(trade_id, None)
        self.persist()
        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _match_filter(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Simple flat filter matching (AND logic)."""
    for key, expected in filters.items():
        actual = metadata.get(key)
        if isinstance(expected, dict):
            # Minimal Chroma-like operator support: $eq, $ne, $gt, $gte, $lt, $lte
            op, val = next(iter(expected.items()))
            if op == "$eq" and actual != val:
                return False
            if op == "$ne" and actual == val:
                return False
            if op == "$gt" and not (actual is not None and actual > val):
                return False
            if op == "$gte" and not (actual is not None and actual >= val):
                return False
            if op == "$lt" and not (actual is not None and actual < val):
                return False
            if op == "$lte" and not (actual is not None and actual <= val):
                return False
        else:
            if actual != expected:
                return False
    return True


def create_vector_store(
    persist_dir: str = "./data/chroma_db/",
    collection_name: str = "gold_memory",
    use_chroma_if_available: bool = True,
) -> VectorStore:
    """Factory: returns ChromaVectorStore if available, else NumpyVectorStore."""
    if use_chroma_if_available and _CHROMADB_AVAILABLE:
        return ChromaVectorStore(persist_dir=persist_dir, collection_name=collection_name)
    # Fallback: JSON-backed numpy store
    persist_path = os.path.join(persist_dir, "numpy_fallback.json")
    return NumpyVectorStore(persist_path=persist_path)
