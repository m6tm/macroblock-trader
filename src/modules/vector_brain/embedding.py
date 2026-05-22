"""Embedding engines — sentence-transformers primary, feature-based fallback."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np

# Optional sentence-transformers --------------------------------------------
try:
    from sentence_transformers import SentenceTransformer

    _ST_AVAILABLE = True
except Exception:  # pragma: no cover
    _ST_AVAILABLE = False


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------
class EmbeddingEngine(ABC):
    """Abstract embedding engine."""

    @property
    @abstractmethod
    def dim(self) -> int:
        """Dimensionality of produced vectors."""

    @abstractmethod
    def encode(self, text: str) -> np.ndarray:
        """Encode a single text into a vector."""

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts."""
        return np.stack([self.encode(t) for t in texts])


# ---------------------------------------------------------------------------
# Sentence-Transformers implementation
# ---------------------------------------------------------------------------
class SentenceTransformerEngine(EmbeddingEngine):
    """Lightweight sentence-transformers encoder (384 dims with all-MiniLM-L6-v2)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        if not _ST_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            )
        self._model = SentenceTransformer(model_name)
        self._dim_val: int = self._model.get_sentence_embedding_dimension()

    @property
    def dim(self) -> int:
        return self._dim_val

    def encode(self, text: str) -> np.ndarray:
        return self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        return self._model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True
        )


# ---------------------------------------------------------------------------
# Feature-based fallback (deterministic, no ML model required)
# ---------------------------------------------------------------------------
class FeatureEmbeddingEngine(EmbeddingEngine):
    """Deterministic feature encoder for trade-like structured data.

    Produces a normalised vector from key trade attributes.
    Ideal as fallback when sentence-transformers is unavailable.
    """

    _SETUP_TYPES = ["OB", "FVG", "OB+FVG", "BOS", "CHoCH", "LIQ", "OTHER"]
    _KILLZONES = [
        "LONDON_FIX_AM",
        "LONDON_FIX_PM",
        "NY_OPEN_COMEX",
        "LONDON_OPEN",
        "ASIA",
        "NY_CLOSE",
        "OTHER",
    ]

    @property
    def dim(self) -> int:
        # direction(1) + grade(1) + macro(1) + tech(1) + total(1) + rr(1)
        # + setup_onehot(7) + killzone_onehot(7) + sentiment(1) + xau_price(1)
        # + ob_freshness(1) + fvg_size(1) + liquidity_dist(1)
        return 25

    def encode(self, text: str) -> np.ndarray:
        # For text mode we parse the text as a trade dict first.
        # If called directly with raw text, we build a minimal vector.
        parsed = _parse_trade_text(text)
        return self._encode_dict(parsed)

    def encode_trade(self, trade: Dict[str, Any]) -> np.ndarray:
        """Encode a trade dictionary directly."""
        return self._encode_dict(trade)

    def _encode_dict(self, trade: Dict[str, Any]) -> np.ndarray:
        direction = 1.0 if trade.get("direction") == "LONG" else (-1.0 if trade.get("direction") == "SHORT" else 0.0)

        grade_map = {"A+": 1.0, "A": 0.85, "B": 0.5, "C": 0.25, "N/A": 0.0}
        grade = grade_map.get(trade.get("grade", "N/A"), 0.0)

        macro_score = _norm(trade.get("macro_score"), -5, 5)
        technical_score = _norm(trade.get("technical_score"), 0.0, 5.5)
        score_total = _norm(trade.get("score_total"), 0.0, 5.5)
        rr_expected = _norm(trade.get("rr_expected"), 0.0, 5.0)
        sentiment_score = _norm(trade.get("sentiment_score"), -5, 5)
        xau_price = _norm(trade.get("xauusd_price"), 1500.0, 3500.0)

        setup_vec = _onehot(trade.get("setup_type", "OTHER"), self._SETUP_TYPES)
        kz_vec = _onehot(trade.get("killzone", "OTHER"), self._KILLZONES)

        # Optional structural features (default 0.5 = neutral/unknown)
        ob_freshness = _norm(trade.get("ob_freshness"), 0, 10, default=0.5)
        fvg_size = _norm(trade.get("fvg_size"), 0, 50, default=0.5)
        liquidity_dist = _norm(trade.get("liquidity_dist"), 0, 200, default=0.5)

        vec = np.concatenate([
            np.array([direction, grade, macro_score, technical_score, score_total, rr_expected]),
            setup_vec,
            kz_vec,
            np.array([sentiment_score, xau_price, ob_freshness, fvg_size, liquidity_dist]),
        ]).astype(np.float32)

        # L2 normalise
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _norm(value: Any, vmin: float, vmax: float, default: float = 0.5) -> float:
    if value is None:
        return default
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v < vmin:
        return 0.0
    if v > vmax:
        return 1.0
    return (v - vmin) / (vmax - vmin)


def _onehot(value: Any, categories: List[str]) -> np.ndarray:
    vec = np.zeros(len(categories), dtype=np.float32)
    if value is None:
        return vec
    try:
        idx = categories.index(str(value))
        vec[idx] = 1.0
    except ValueError:
        # Unknown → map to last category (OTHER)
        vec[-1] = 1.0
    return vec


def _parse_trade_text(text: str) -> Dict[str, Any]:
    """Naive parser to extract key-value pairs from a descriptive trade text."""
    data: Dict[str, Any] = {}
    text_lower = text.lower()

    if "long" in text_lower:
        data["direction"] = "LONG"
    elif "short" in text_lower or "sell" in text_lower:
        data["direction"] = "SHORT"

    if "a+" in text_lower:
        data["grade"] = "A+"
    elif "grade b" in text_lower or "(b)" in text_lower:
        data["grade"] = "B"

    # Try to extract numbers after keywords
    import re

    m = re.search(r"macro score[:\s]+([+-]?\d+)", text_lower)
    if m:
        data["macro_score"] = int(m.group(1))
    m = re.search(r"technical score[:\s]+([\d.]+)", text_lower)
    if m:
        data["technical_score"] = float(m.group(1))
    m = re.search(r"score total[:\s]+([\d.]+)", text_lower)
    if m:
        data["score_total"] = float(m.group(1))
    m = re.search(r"rr[:\s]+([\d.]+)", text_lower)
    if m:
        data["rr_expected"] = float(m.group(1))

    for st in FeatureEmbeddingEngine._SETUP_TYPES:
        if st.lower() in text_lower:
            data["setup_type"] = st
            break

    for kz in FeatureEmbeddingEngine._KILLZONES:
        if kz.lower().replace("_", " ") in text_lower:
            data["killzone"] = kz
            break

    return data


def create_embedding_engine(
    model_name: Optional[str] = None,
    use_st_if_available: bool = True,
) -> EmbeddingEngine:
    """Factory: returns SentenceTransformerEngine if available, else FeatureEmbeddingEngine."""
    if use_st_if_available and _ST_AVAILABLE:
        return SentenceTransformerEngine(model_name or "sentence-transformers/all-MiniLM-L6-v2")
    return FeatureEmbeddingEngine()
