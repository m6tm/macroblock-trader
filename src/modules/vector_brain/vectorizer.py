"""Trade vectorization — SQLite → embedding → vector store."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from modules.vector_brain.embedding import EmbeddingEngine, FeatureEmbeddingEngine
from modules.vector_brain.store import VectorRecord, VectorStore

logger = logging.getLogger(__name__)


def build_trade_text(trade: Dict[str, Any]) -> str:
    """Generate a rich semantic description of a trade for embedding."""
    direction = trade.get("direction", "UNKNOWN")
    grade = trade.get("grade", "N/A")
    setup = trade.get("setup_type", "unknown")
    killzone = trade.get("killzone", "unknown")
    macro_score = trade.get("macro_score", 0)
    technical_score = trade.get("technical_score", 0.0)
    score_total = trade.get("score_total", 0.0)
    rr = trade.get("rr_expected", 0.0)
    entry = trade.get("entry_price_actual") or trade.get("entry_price_virtual")
    sl = trade.get("sl_price")
    tp1 = trade.get("tp1_price")

    lines = [
        f"Context: Gold trade {direction} with grade {grade}.",
        f"Setup: {setup} on M15 with confluent factors.",
        f"Killzone: {killzone} active.",
        f"Macro score: {macro_score} for gold.",
        f"Technical score: {technical_score} out of 5.5.",
        f"Total score: {score_total}.",
    ]
    if entry is not None and sl is not None:
        lines.append(f"Entry: {entry:.2f}, SL: {sl:.2f}, RR: 1 to {rr:.2f}.")
    if tp1 is not None:
        lines.append(f"Take profit 1: {tp1:.2f}.")

    return " ".join(lines)


def vectorize_trade(
    store: VectorStore,
    engine: EmbeddingEngine,
    trade: Dict[str, Any],
) -> Optional[VectorRecord]:
    """Embed a trade and persist it to the vector store.

    Returns the created VectorRecord or None on failure.
    """
    trade_id = trade.get("trade_id")
    if not trade_id:
        logger.warning("Cannot vectorize trade without trade_id")
        return None

    # Build metadata subset for ChromaDB / numpy store
    metadata: Dict[str, Any] = {
        "trade_id": trade_id,
        "signal_id": trade.get("signal_id"),
        "direction": trade.get("direction"),
        "grade": trade.get("grade"),
        "setup_type": trade.get("setup_type"),
        "killzone": trade.get("killzone"),
        "macro_score": trade.get("macro_score"),
        "technical_score": trade.get("technical_score"),
        "score_total": trade.get("score_total"),
        "rr_expected": trade.get("rr_expected"),
        "status_virtual": trade.get("status_virtual"),
        "pnl_virtual_dollars": trade.get("pnl_virtual_dollars"),
        "pnl_real_dollars": trade.get("pnl_real_dollars"),
        "user_executed": trade.get("user_executed", False),
        "user_feedback_status": trade.get("user_feedback_status"),
        "created_at": trade.get("created_at"),
    }
    # Clean None values for stores that dislike them (Chroma metadata)
    metadata = {k: v for k, v in metadata.items() if v is not None}

    # Encode
    if isinstance(engine, FeatureEmbeddingEngine):
        vector = engine.encode_trade(trade)
    else:
        text = build_trade_text(trade)
        vector = engine.encode(text)

    record = VectorRecord(trade_id=trade_id, vector=vector, metadata=metadata)
    store.add(record)
    logger.info(f"Trade {trade_id} vectorized — {len(vector)} dims")
    return record


def update_trade_vector_metadata(
    store: VectorStore,
    trade_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """Update metadata of an existing trade vector (e.g. after feedback)."""
    ok = store.update_metadata(trade_id, metadata)
    if ok:
        logger.info(f"Vector metadata updated for {trade_id}")
    else:
        logger.warning(f"Failed to update vector metadata for {trade_id}")
    return ok
