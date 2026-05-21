"""Scoring technique global — agrégation des composants SMC.

Score de 0 a 5.5 selon les critères du document 05-module-technique.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from data.compat import OHLCVData
from modules.technical.core import Trend, detect_swing_highs_lows, get_trend
from modules.technical.fvg import FairValueGap, fvg_ob_confluence
from modules.technical.liquidity import LiquidityPool, get_current_killzone
from modules.technical.ob import OBType, OrderBlock


@dataclass
class TechnicalSetup:
    """Un setup technique complet detecte par le module."""

    direction: str  # "LONG" | "SHORT"
    entry_zone: tuple[float, float]
    sl_zone: tuple[float, float]
    tp_zones: list[tuple[float, float]]
    ob: Optional[OrderBlock] = None
    fvgs: list[FairValueGap] = None
    liquidity_targets: list[LiquidityPool] = None
    score: float = 0.0
    grade: str = "F"  # F, D, C, B, A, A+
    timeframe: str = "M15"
    justification: str = ""


class TechnicalScorer:
    """Calcule le score technique d'un setup SMC."""

    MIN_SCORE_FOR_SIGNAL = 3.0
    A_PLUS_THRESHOLD = 4.0

    def __init__(self) -> None:
        self._scores: Dict[str, float] = {}

    def score_structure(
        self,
        h1_trend: Trend,
        h4_trend: Trend,
        direction: str,
    ) -> float:
        """Structure H1/H4 alignee avec le trade ? +1 si oui."""
        # Convertir direction en Trend
        target = Trend.BULLISH if direction == "LONG" else Trend.BEARISH

        h1_ok = h1_trend == target
        h4_ok = h4_trend == target

        if h1_ok and h4_ok:
            return 1.0
        if h1_ok:
            return 0.5
        return 0.0

    def score_bos(self, has_bos_in_direction: bool) -> float:
        """BOS M15 recent dans la direction du trade ? +1 si oui."""
        return 1.0 if has_bos_in_direction else 0.0

    def score_ob(self, ob: OrderBlock) -> float:
        """OB frais et de qualite ? +1 si oui."""
        if ob is None:
            return 0.0
        if ob.freshness.value == "FRESH":
            return 1.0
        if ob.freshness.value == "FIRST_TOUCH":
            return 0.7
        return 0.0

    def score_fvg(self, fvgs: list[FairValueGap], ob: OrderBlock) -> float:
        """FVG confluent avec l'OB ? +1 si oui."""
        if not fvgs or ob is None:
            return 0.0
        for fvg in fvgs:
            if fvg_ob_confluence(fvg, ob.ob_low, ob.ob_high):
                return 1.0
        return 0.0

    def score_liquidity(self, pools: list[LiquidityPool], direction: str) -> float:
        """Liquidite ciblee claire pour le TP ? +0.5 si oui."""
        if not pools:
            return 0.0
        # Au moins un pool dans la direction du trade
        if direction == "LONG":
            has_target = any(p.type in ("EQH", "PDH", "PWH", "PSYCH") for p in pools)
        else:
            has_target = any(p.type in ("EQL", "PDL", "PWL", "PSYCH") for p in pools)
        return 0.5 if has_target else 0.0

    def score_killzone(self) -> float:
        """Killzone active ? +0.5 si oui."""
        _, score = get_current_killzone()
        return 0.5 if score >= 2 else 0.0

    def calculate_total(
        self,
        direction: str,
        h1_trend: Trend,
        h4_trend: Trend,
        has_bos: bool,
        ob: Optional[OrderBlock],
        fvgs: list[FairValueGap],
        pools: list[LiquidityPool],
    ) -> tuple[float, str]:
        """Calcule le score total et la grade.

        Returns:
            (score, grade)
        """
        s = 0.0
        s += self.score_structure(h1_trend, h4_trend, direction)
        s += self.score_bos(has_bos)
        s += self.score_ob(ob)
        s += self.score_fvg(fvgs, ob)
        s += self.score_liquidity(pools, direction)
        s += self.score_killzone()

        grade = self._grade(s)
        return round(s, 2), grade

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 4.5:
            return "A+"
        if score >= 4.0:
            return "A"
        if score >= 3.5:
            return "B"
        if score >= 3.0:
            return "C"
        if score >= 2.0:
            return "D"
        return "F"


def build_setup(
    direction: str,
    ob: OrderBlock,
    data: OHLCVData,
    h1_trend: Trend,
    h4_trend: Trend,
    has_bos: bool,
    fvgs: list[FairValueGap],
    pools: list[LiquidityPool],
) -> Optional[TechnicalSetup]:
    """Construit un setup complet avec scoring.

    Returns:
        TechnicalSetup si le score >= 3.0, sinon None.
    """
    scorer = TechnicalScorer()
    score, grade = scorer.calculate_total(
        direction=direction,
        h1_trend=h1_trend,
        h4_trend=h4_trend,
        has_bos=has_bos,
        ob=ob,
        fvgs=fvgs,
        pools=pools,
    )

    if score < TechnicalScorer.MIN_SCORE_FOR_SIGNAL:
        logger.info(f"Setup {direction} rejete — score {score} < {TechnicalScorer.MIN_SCORE_FOR_SIGNAL}")
        return None

    # Zones SL/TP
    if direction == "LONG":
        sl_zone = (ob.ob_low * 0.999, ob.ob_low)  # sous le low de l'OB
        tp_zones = [(p.price, p.price + 2.0) for p in pools if p.price > ob.ob_high]
    else:
        sl_zone = (ob.ob_high, ob.ob_high * 1.001)  # au-dessus du high de l'OB
        tp_zones = [(p.price - 2.0, p.price) for p in pools if p.price < ob.ob_low]

    setup = TechnicalSetup(
        direction=direction,
        entry_zone=(ob.ob_low, ob.ob_high),
        sl_zone=sl_zone,
        tp_zones=tp_zones[:3],  # max 3 TP
        ob=ob,
        fvgs=fvgs,
        liquidity_targets=pools,
        score=score,
        grade=grade,
        timeframe=data.timeframe,
        justification=f"OB {ob.type.value} score={score} grade={grade}",
    )

    logger.success(
        f"Setup {direction} {grade} detecte — score={score} "
        f"OB@{ob.ob_low:.2f}-{ob.ob_high:.2f}"
    )
    return setup
