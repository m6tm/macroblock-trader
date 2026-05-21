"""Detection des pools de liquidite et gestion des killzones.

Equal Highs/Lows, niveaux psychologiques, previous session levels.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from data.compat import OHLCVData


@dataclass
class LiquidityPool:
    type: str  # "EQH" | "EQL" | "PSYCH" | "PDH" | "PDL" | "PWH" | "PWL"
    price: float
    label: str
    strength: float = 1.0  # 1.0 = faible, 3.0 = fort


def detect_equal_highs(
    data: OHLCVData,
    tolerance: float = 0.15,
    min_candles_between: int = 5,
) -> List[LiquidityPool]:
    """Detecte les Equal Highs (EQH) — deux sommets approximativement egaux.

    Args:
        tolerance: Ecart maxi en dollars entre les deux sommets (0.15$ pour l'or)
        min_candles_between: Nombre minimum de candles entre les deux sommets
    """
    rows = data.rows()
    pools: List[LiquidityPool] = []

    for i in range(len(rows)):
        for j in range(i + min_candles_between, len(rows)):
            hi = float(rows[i]["high"])
            hj = float(rows[j]["high"])
            if abs(hi - hj) <= tolerance:
                pools.append(
                    LiquidityPool(
                        type="EQH",
                        price=max(hi, hj),
                        label=f"EQH@{max(hi, hj):.2f}",
                        strength=2.0,
                    )
                )

    logger.debug(f"Equal Highs detectes : {len(pools)}")
    return pools


def detect_equal_lows(
    data: OHLCVData,
    tolerance: float = 0.15,
    min_candles_between: int = 5,
) -> List[LiquidityPool]:
    """Detecte les Equal Lows (EQL) — deux creux approximativement egaux."""
    rows = data.rows()
    pools: List[LiquidityPool] = []

    for i in range(len(rows)):
        for j in range(i + min_candles_between, len(rows)):
            li = float(rows[i]["low"])
            lj = float(rows[j]["low"])
            if abs(li - lj) <= tolerance:
                pools.append(
                    LiquidityPool(
                        type="EQL",
                        price=min(li, lj),
                        label=f"EQL@{min(li, lj):.2f}",
                        strength=2.0,
                    )
                )

    logger.debug(f"Equal Lows detectes : {len(pools)}")
    return pools


def detect_psychological_levels(
    current_price: float,
    range_around: float = 100.0,
    step: float = 50.0,
) -> List[LiquidityPool]:
    """Genere les niveaux psychologiques proches du prix actuel.

    Exemple pour l'or : 4500, 4550, 4600... (pas 100 car l'or bouge vite)
    """
    pools: List[LiquidityPool] = []
    base = int(current_price / step) * step

    for level in range(int(base - range_around), int(base + range_around) + 1, int(step)):
        if level <= 0:
            continue
        distance = abs(current_price - level)
        strength = 3.0 if distance < 20 else 2.0
        pools.append(
            LiquidityPool(
                type="PSYCH",
                price=float(level),
                label=f"PSYCH@{level}",
                strength=strength,
            )
        )

    return pools


def detect_previous_session_levels(data: OHLCVData) -> List[LiquidityPool]:
    """Detecte le Previous Day High/Low et Previous Week High/Low.

    Retourne les 4 niveaux s'ils sont disponibles dans les donnees.
    """
    rows = data.rows()
    if not rows:
        return []

    # Day high/low — on suppose que les donnees couvrent au moins 24h
    day_high = max(float(r["high"]) for r in rows)
    day_low = min(float(r["low"]) for r in rows)

    pools = [
        LiquidityPool(type="PDH", price=day_high, label=f"PDH@{day_high:.2f}", strength=2.5),
        LiquidityPool(type="PDL", price=day_low, label=f"PDL@{day_low:.2f}", strength=2.5),
    ]

    # Week high/low — approximes si on a assez de donnees
    if len(rows) >= 100:  # ~1 semaine en M15
        week_slice = rows[-100:]
        week_high = max(float(r["high"]) for r in week_slice)
        week_low = min(float(r["low"]) for r in week_slice)
        pools.extend(
            [
                LiquidityPool(type="PWH", price=week_high, label=f"PWH@{week_high:.2f}", strength=3.0),
                LiquidityPool(type="PWL", price=week_low, label=f"PWL@{week_low:.2f}", strength=3.0),
            ]
        )

    return pools


# ------------------------------------------------------------------
# Killzones
# ------------------------------------------------------------------

KILLZONES = {
    "asia": (time(0, 0), time(8, 0), 0),
    "london_open": (time(8, 0), time(9, 0), 1),
    "london_fix_am": (time(10, 0), time(11, 0), 2),
    "ny_open_comex": (time(13, 20), time(14, 30), 2),
    "london_fix_pm": (time(15, 0), time(16, 0), 2),
    "london_close": (time(16, 0), time(17, 0), 1),
    "ny_close": (time(21, 0), time(22, 0), 0),
}


def get_current_killzone(dt: Optional[datetime] = None) -> Tuple[str, int]:
    """Retourne la killzone active et son score de timing.

    Args:
        dt: Datetime UTC. Si None, utilise l'heure actuelle.

    Returns:
        Tuple (nom_killzone, score). ("none", 0) si hors killzone.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    current_t = dt.time()
    for name, (start, end, score) in KILLZONES.items():
        if start <= current_t <= end:
            return name, score
    return "none", 0


def is_killzone_active(
    preferred: List[str],
    dt: Optional[datetime] = None,
) -> bool:
    """Vérifie si on est dans une des killzones preferentielles."""
    name, _ = get_current_killzone(dt)
    return name in preferred
