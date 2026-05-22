"""Scoring adjustment based on vector brain retrieval results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from modules.vector_brain.retrieval import SimilarTradeAnalysis


class VectorDbMode:
    PASSIVE = "PASSIVE"
    LIGHT = "LIGHT"
    FULL = "FULL"


@dataclass
class AdjustmentResult:
    """Result of a vector-brain adjustment."""

    adjustment: float
    mode: str
    reason: Optional[str] = None
    similar_trade_count: int = 0
    win_rate_similar: float = 0.0
    avg_pnl_similar: float = 0.0


def get_vector_db_mode(trades_count: int) -> str:
    """Determine activation mode based on historical trade volume.

    - < 30 trades  → PASSIVE (observation only)
    - 30–100       → LIGHT   (±0.1 max)
    - 100+         → FULL    (±0.3 max)
    """
    if trades_count < 30:
        return VectorDbMode.PASSIVE
    if trades_count <= 100:
        return VectorDbMode.LIGHT
    return VectorDbMode.FULL


def calculate_adjustment(
    analysis: SimilarTradeAnalysis,
    mode: str = VectorDbMode.FULL,
) -> AdjustmentResult:
    """Compute a score adjustment from similar-trade statistics.

    Rules (from spec 16.5.4):
      PASSIVE → 0 always
      LIGHT   → ±0.1 max
      FULL    → ±0.3 max, +0.1 intermediate
    """
    if mode == VectorDbMode.PASSIVE or analysis.trade_ids == []:
        return AdjustmentResult(
            adjustment=0.0,
            mode=mode,
            reason=None,
            similar_trade_count=len(analysis.trade_ids),
            win_rate_similar=analysis.win_rate,
            avg_pnl_similar=analysis.avg_pnl_real,
        )

    wr = analysis.win_rate
    avg_pnl = analysis.avg_pnl_real if analysis.avg_pnl_real != 0 else analysis.avg_pnl_virtual

    if mode == VectorDbMode.LIGHT:
        if wr >= 0.80 and avg_pnl > 0:
            adj = +0.1
            reason = "Trades similaires historiquement très performants"
        elif wr <= 0.40 and avg_pnl < 0:
            adj = -0.1
            reason = "Trades similaires historiquement perdants — prudence"
        else:
            adj = 0.0
            reason = None
    else:  # FULL
        if wr >= 0.80 and avg_pnl > 0:
            adj = +0.2
            reason = "Trades similaires historiquement tres performants"
        elif wr <= 0.40 and avg_pnl < 0:
            adj = -0.3
            reason = "Trades similaires historiquement perdants — prudence"
        elif wr >= 0.60 and avg_pnl > 0:
            adj = +0.1
            reason = "Trades similaires legerement favorables"
        else:
            adj = 0.0
            reason = None

    return AdjustmentResult(
        adjustment=adj,
        mode=mode,
        reason=reason,
        similar_trade_count=len(analysis.trade_ids),
        win_rate_similar=wr,
        avg_pnl_similar=avg_pnl,
    )
