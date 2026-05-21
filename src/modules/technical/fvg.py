"""Detection des Fair Value Gaps (FVG) — Smart Money Concepts.

Bullish FVG : Low(N+2) > High(N)
Bearish FVG : High(N+2) < Low(N)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from loguru import logger

from data.compat import OHLCVData


class FVGType(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


@dataclass
class FairValueGap:
    type: FVGType
    index: int  # Index de la candle N (debut du gap)
    timestamp: str
    fvg_low: float
    fvg_high: float
    gap_size: float
    mitigated: bool = False

    def zone(self) -> Tuple[float, float]:
        return (self.fvg_low, self.fvg_high)


def detect_bullish_fvg(data: OHLCVData) -> List[FairValueGap]:
    """Detecte les FVG bullish : Low(N+2) > High(N)."""
    rows = data.rows()
    if len(rows) < 3:
        return []

    fvgs: List[FairValueGap] = []
    for i in range(len(rows) - 2):
        high_n = float(rows[i]["high"])
        low_n2 = float(rows[i + 2]["low"])

        if low_n2 > high_n:
            gap_size = low_n2 - high_n
            fvgs.append(
                FairValueGap(
                    type=FVGType.BULLISH,
                    index=i,
                    timestamp=str(rows[i]["timestamp"]),
                    fvg_low=high_n,
                    fvg_high=low_n2,
                    gap_size=gap_size,
                )
            )

    logger.debug(f"Bullish FVG detectes : {len(fvgs)}")
    return fvgs


def detect_bearish_fvg(data: OHLCVData) -> List[FairValueGap]:
    """Detecte les FVG bearish : High(N+2) < Low(N)."""
    rows = data.rows()
    if len(rows) < 3:
        return []

    fvgs: List[FairValueGap] = []
    for i in range(len(rows) - 2):
        low_n = float(rows[i]["low"])
        high_n2 = float(rows[i + 2]["high"])

        if high_n2 < low_n:
            gap_size = low_n - high_n2
            fvgs.append(
                FairValueGap(
                    type=FVGType.BEARISH,
                    index=i,
                    timestamp=str(rows[i]["timestamp"]),
                    fvg_low=high_n2,
                    fvg_high=low_n,
                    gap_size=gap_size,
                )
            )

    logger.debug(f"Bearish FVG detectes : {len(fvgs)}")
    return fvgs


def check_fvg_mitigation(
    fvgs: List[FairValueGap],
    data: OHLCVData,
) -> List[FairValueGap]:
    """Verifie si un FVG a ete comble par le prix subsequent."""
    rows = data.rows()
    for fvg in fvgs:
        if fvg.index >= len(rows) - 1:
            continue
        for j in range(fvg.index + 3, len(rows)):
            low_j = float(rows[j]["low"])
            high_j = float(rows[j]["high"])
            # Mitigation = le prix entre dans la zone du FVG
            if low_j <= fvg.fvg_high and high_j >= fvg.fvg_low:
                fvg.mitigated = True
                break
    return fvgs


def fvg_ob_confluence(
    fvg: FairValueGap,
    ob_low: float,
    ob_high: float,
    max_distance: float = 5.0,
) -> bool:
    """Verifie si un FVG est confluent avec un Order Block.

    Args:
        max_distance: Distance maxi entre les zones en dollars (defaut 5$ pour l'or)

    Returns:
        True si les zones se chevauchent ou sont proches.
    """
    fvg_low, fvg_high = fvg.zone()

    # Chevauchement direct
    if not (fvg_high < ob_low or fvg_low > ob_high):
        return True

    # Proximite
    if fvg_high < ob_low:
        return (ob_low - fvg_high) <= max_distance
    else:
        return (fvg_low - ob_high) <= max_distance
