"""Retrieval engine — k-NN search with result analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from modules.vector_brain.store import RetrievalResult, VectorStore


@dataclass
class SimilarTradeAnalysis:
    """Aggregated analysis of similar trades."""

    trade_ids: List[str]
    similarities: List[float]
    win_rate: float
    avg_pnl_virtual: float
    avg_pnl_real: float
    avg_similarity: float
    avg_rr_realized: float
    win_count: int
    loss_count: int
    be_count: int


def find_similar_trades(
    store: VectorStore,
    vector: np.ndarray,
    n: int = 5,
    min_feedback_status: Optional[str] = "SUBMITTED",
    only_user_executed: bool = True,
) -> List[RetrievalResult]:
    """Query the vector store for the k most similar trades.

    Filters by default to trades with user feedback and real execution
    so that the analysis is grounded in validated experience.
    """
    filters: Dict[str, Any] = {}
    if only_user_executed:
        filters["user_executed"] = True
    if min_feedback_status:
        filters["user_feedback_status"] = min_feedback_status

    return store.query(vector=vector, n_results=n, filters=filters or None)


def analyze_similar_trades(results: List[RetrievalResult]) -> SimilarTradeAnalysis:
    """Aggregate metrics from a list of retrieval results."""
    if not results:
        return SimilarTradeAnalysis(
            trade_ids=[],
            similarities=[],
            win_rate=0.0,
            avg_pnl_virtual=0.0,
            avg_pnl_real=0.0,
            avg_similarity=0.0,
            avg_rr_realized=0.0,
            win_count=0,
            loss_count=0,
            be_count=0,
        )

    tids: List[str] = []
    sims: List[float] = []
    wins = losses = bes = 0
    pnls_virtual: List[float] = []
    pnls_real: List[float] = []
    rr_realized: List[float] = []

    for r in results:
        tids.append(r.trade_id)
        sims.append(r.similarity)

        status = (r.metadata.get("status_virtual") or "").upper()
        if status in ("WIN", "CLOSED_WIN"):
            wins += 1
        elif status in ("LOSS", "CLOSED_LOSS"):
            losses += 1
        elif status in ("BE", "BREAKEVEN", "CLOSED_BE"):
            bes += 1

        pnl_v = r.metadata.get("pnl_virtual_dollars")
        if pnl_v is not None:
            pnls_virtual.append(float(pnl_v))
        pnl_r = r.metadata.get("pnl_real_dollars")
        if pnl_r is not None:
            pnls_real.append(float(pnl_r))
        rr = r.metadata.get("rr_realized")
        if rr is not None:
            rr_realized.append(float(rr))

    total = wins + losses + bes
    win_rate = wins / total if total > 0 else 0.0

    return SimilarTradeAnalysis(
        trade_ids=tids,
        similarities=sims,
        win_rate=win_rate,
        avg_pnl_virtual=_safe_mean(pnls_virtual),
        avg_pnl_real=_safe_mean(pnls_real),
        avg_similarity=_safe_mean(sims),
        avg_rr_realized=_safe_mean(rr_realized),
        win_count=wins,
        loss_count=losses,
        be_count=bes,
    )


def _safe_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0
