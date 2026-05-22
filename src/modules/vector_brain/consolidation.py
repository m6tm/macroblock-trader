"""Weekly consolidation — clustering and insight generation."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np

from modules.vector_brain.store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class WeeklyInsight:
    """A single insight from weekly consolidation."""

    category: str  # e.g. "setup", "killzone", "grade"
    key: str       # e.g. "OB+FVG"
    win_rate: float
    trade_count: int
    avg_pnl: float
    message: str


def weekly_clustering(
    store: VectorStore,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group all vectors by setup_type and killzone for pattern analysis.

    Returns a dict of clusters with raw metadata records.
    """
    # NumpyVectorStore does not expose list-all; Chroma does via get()
    # We support both by probing the store.
    records: List[Dict[str, Any]] = []

    if hasattr(store, "_collection"):
        # ChromaDB — fetch all
        try:
            result = store._collection.get(include=["metadatas"])  # type: ignore[attr-defined]
            for tid, meta in zip(result["ids"], result["metadatas"]):
                rec = dict(meta)
                rec["trade_id"] = tid
                records.append(rec)
        except Exception as exc:
            logger.warning(f"Chroma weekly fetch failed: {exc}")
    elif hasattr(store, "_metadata"):
        # NumpyVectorStore
        for tid, meta in store._metadata.items():  # type: ignore[attr-defined]
            rec = dict(meta)
            rec["trade_id"] = tid
            records.append(rec)

    clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        setup = rec.get("setup_type") or "UNKNOWN"
        kz = rec.get("killzone") or "UNKNOWN"
        clusters[f"setup:{setup}"].append(rec)
        clusters[f"killzone:{kz}"].append(rec)
        clusters["all"].append(rec)
    return dict(clusters)


def generate_weekly_insights(
    clusters: Dict[str, List[Dict[str, Any]]],
    min_trades: int = 3,
) -> List[WeeklyInsight]:
    """Generate human-readable insights from weekly clusters.

    Filters to clusters with at least ``min_trades`` entries.
    """
    insights: List[WeeklyInsight] = []

    for cluster_key, records in clusters.items():
        if len(records) < min_trades:
            continue

        cat, key = cluster_key.split(":", 1) if ":" in cluster_key else ("all", cluster_key)
        wins = losses = bes = 0
        pnls: List[float] = []

        for rec in records:
            status = (rec.get("status_virtual") or "").upper()
            if status in ("WIN", "CLOSED_WIN"):
                wins += 1
            elif status in ("LOSS", "CLOSED_LOSS"):
                losses += 1
            elif status in ("BE", "BREAKEVEN", "CLOSED_BE"):
                bes += 1

            pnl = rec.get("pnl_real_dollars") or rec.get("pnl_virtual_dollars")
            if pnl is not None:
                pnls.append(float(pnl))

        total = wins + losses + bes
        wr = wins / total if total else 0.0
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

        if wr >= 0.75 and avg_pnl > 0:
            msg = f"{key}: Tres fort — {wr*100:.0f}% WR, P&L moyen +{avg_pnl:.1f}$"
        elif wr <= 0.40 and avg_pnl < 0:
            msg = f"{key}: Faible — {wr*100:.0f}% WR, P&L moyen {avg_pnl:.1f}$"
        elif avg_pnl > 0:
            msg = f"{key}: Positif — {wr*100:.0f}% WR, P&L moyen +{avg_pnl:.1f}$"
        else:
            msg = f"{key}: Mixte — {wr*100:.0f}% WR, P&L moyen {avg_pnl:.1f}$"

        insights.append(
            WeeklyInsight(
                category=cat,
                key=key,
                win_rate=wr,
                trade_count=total,
                avg_pnl=avg_pnl,
                message=msg,
            )
        )

    # Sort by absolute avg P&L descending
    insights.sort(key=lambda i: abs(i.avg_pnl), reverse=True)
    return insights


def best_and_worst_setups(
    insights: List[WeeklyInsight],
) -> Tuple[Optional[WeeklyInsight], Optional[WeeklyInsight]]:
    """Return the best and worst setup insights."""
    setup_insights = [i for i in insights if i.category == "setup"]
    if not setup_insights:
        return None, None
    best = max(setup_insights, key=lambda i: i.avg_pnl)
    worst = min(setup_insights, key=lambda i: i.avg_pnl)
    return best, worst
