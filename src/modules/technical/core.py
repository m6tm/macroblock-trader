"""Structure de marche — Swing Highs/Lows, BOS, CHoCH, tendance.

Smart Money Concepts (SMC) adapte a la volatilite de l'or.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from data.compat import OHLCVData


class Trend(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class SwingPoint:
    index: int
    timestamp: str
    price: float
    type: str  # "high" | "low"


@dataclass
class StructureEvent:
    type: str  # "BOS" | "CHoCH"
    direction: str  # "BULLISH" | "BEARISH"
    timestamp: str
    breakout_price: float
    broken_swing: SwingPoint
    confirming_index: int


def detect_swing_highs_lows(
    data: OHLCVData,
    lookback: int = 5,
) -> Tuple[List[SwingPoint], List[SwingPoint]]:
    """Detecte les swing highs et swing lows sur un jeu de candles.

    Un swing high est un sommet plus haut que les `lookback` candles
    a gauche et a droite. Inversement pour un swing low.
    """
    rows = data.rows()
    if len(rows) < 2 * lookback + 1:
        return [], []

    highs = [float(r["high"]) for r in rows]
    lows = [float(r["low"]) for r in rows]
    timestamps = [str(r["timestamp"]) for r in rows]

    swing_highs: List[SwingPoint] = []
    swing_lows: List[SwingPoint] = []

    for i in range(lookback, len(rows) - lookback):
        # Swing high
        if all(highs[i] > highs[i - k] for k in range(1, lookback + 1)) and all(
            highs[i] > highs[i + k] for k in range(1, lookback + 1)
        ):
            swing_highs.append(
                SwingPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=highs[i],
                    type="high",
                )
            )

        # Swing low
        if all(lows[i] < lows[i - k] for k in range(1, lookback + 1)) and all(
            lows[i] < lows[i + k] for k in range(1, lookback + 1)
        ):
            swing_lows.append(
                SwingPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=lows[i],
                    type="low",
                )
            )

    logger.debug(
        f"Swings detectes — highs={len(swing_highs)} lows={len(swing_lows)} "
        f"(lookback={lookback})"
    )
    return swing_highs, swing_lows


def _last_swing(
    swings: List[SwingPoint], before_index: int
) -> Optional[SwingPoint]:
    """Retourne le dernier swing avant l'index donne."""
    candidates = [s for s in swings if s.index < before_index]
    return candidates[-1] if candidates else None


def detect_bos_choch(
    data: OHLCVData,
    swing_highs: List[SwingPoint],
    swing_lows: List[SwingPoint],
) -> List[StructureEvent]:
    """Detecte les Breaks of Structure (BOS) et Changes of Character (CHoCH).

    Algorithme :
      - On parcourt les candles dans l'ordre chronologique
      - On maintient la tendance courante (BULLISH/BEARISH/NEUTRAL)
      - Si prix casse un swing high precedent en tendance haussiere → BOS BULLISH
      - Si prix casse un swing low precedent en tendance baissiere → BOS BEARISH
      - Si prix casse un swing low en tendance haussiere → CHoCH BEARISH (retournement)
      - Si prix casse un swing high en tendance baissiere → CHoCH BULLISH (retournement)
    """
    rows = data.rows()
    if not rows:
        return []

    events: List[StructureEvent] = []
    trend = Trend.NEUTRAL

    # Index des swings pour recherche rapide
    all_swings = sorted(swing_highs + swing_lows, key=lambda s: s.index)

    for i in range(1, len(rows)):
        high = float(rows[i]["high"])
        low = float(rows[i]["low"])

        # Derniers swings valides avant i
        last_high = _last_swing(swing_highs, i)
        last_low = _last_swing(swing_lows, i)

        if not last_high or not last_low:
            continue

        # BOS / CHoCH BULLISH — breakout d'un swing high
        if high > last_high.price:
            if trend == Trend.BULLISH:
                events.append(
                    StructureEvent(
                        type="BOS",
                        direction="BULLISH",
                        timestamp=str(rows[i]["timestamp"]),
                        breakout_price=high,
                        broken_swing=last_high,
                        confirming_index=i,
                    )
                )
            elif trend == Trend.BEARISH:
                events.append(
                    StructureEvent(
                        type="CHoCH",
                        direction="BULLISH",
                        timestamp=str(rows[i]["timestamp"]),
                        breakout_price=high,
                        broken_swing=last_high,
                        confirming_index=i,
                    )
                )
                trend = Trend.BULLISH
            else:
                # Premier signal — on initie la tendance
                trend = Trend.BULLISH

        # BOS / CHoCH BEARISH — breakdown d'un swing low
        if low < last_low.price:
            if trend == Trend.BEARISH:
                events.append(
                    StructureEvent(
                        type="BOS",
                        direction="BEARISH",
                        timestamp=str(rows[i]["timestamp"]),
                        breakout_price=low,
                        broken_swing=last_low,
                        confirming_index=i,
                    )
                )
            elif trend == Trend.BULLISH:
                events.append(
                    StructureEvent(
                        type="CHoCH",
                        direction="BEARISH",
                        timestamp=str(rows[i]["timestamp"]),
                        breakout_price=low,
                        broken_swing=last_low,
                        confirming_index=i,
                    )
                )
                trend = Trend.BEARISH
            else:
                trend = Trend.BEARISH

    logger.debug(f"Structure events detectes : {len(events)}")
    return events


def get_trend(
    data: OHLCVData,
    lookback: int = 5,
) -> Trend:
    """Determine la tendance dominante sur les derniers swings.

    - Si le dernier swing high est plus haut que l'avant-dernier
      ET le dernier swing low est plus haut → BULLISH
    - Inversement → BEARISH
    - Sinon → NEUTRAL
    """
    swing_highs, swing_lows = detect_swing_highs_lows(data, lookback)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return Trend.NEUTRAL

    # On regarde les 2 derniers swings de chaque cote
    last_hh = swing_highs[-1].price > swing_highs[-2].price
    last_lh = swing_lows[-1].price > swing_lows[-2].price

    last_ll = swing_lows[-1].price < swing_lows[-2].price
    last_hl = swing_highs[-1].price < swing_highs[-2].price

    if last_hh and last_lh:
        return Trend.BULLISH
    if last_ll and last_hl:
        return Trend.BEARISH
    return Trend.NEUTRAL


def get_trend_label(data: OHLCVData, lookback: int = 5) -> str:
    return get_trend(data, lookback).value
