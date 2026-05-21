"""Generation du Plan de Trade — niveaux techniques sans sizing.

Le bot calcule :
  - Zone d'entree (low/high de l'OB)
  - SL (derriere le wick de l'OB, min 15$, max 1% prix)
  - TP1/TP2/TP3 (liquidite, FVG oppose, trail)
  - R:R attendu
  - Prix d'invalidation (cloture M5 sous/au-dessus de l'OB)

PAS de calcul de taille de position, PAS de % capital risque.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from core.config import Settings, load_settings
from modules.fusion.scoring import FusionScore
from modules.technical.fvg import FairValueGap
from modules.technical.liquidity import LiquidityPool
from modules.technical.ob import OrderBlock
from modules.technical.scorer import TechnicalSetup


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sur XAU/USD, 1 pip standard = 0.01 (1 cent)
PIPS_PER_DOLLAR = 100.0


# ---------------------------------------------------------------------------
# TradePlan
# ---------------------------------------------------------------------------

@dataclass
class TradePlan:
    """Plan de trade complet genere par le bot."""

    signal_id: str
    direction: str  # "LONG" | "SHORT"
    grade: str
    score_total: float
    score_breakdown: Dict[str, float]

    # Zone d'entree
    entry_zone: Tuple[float, float]  # (low, high)
    preferred_entry: float

    # Stop Loss
    sl_price: float
    sl_distance_dollars: float
    sl_distance_pips: float

    # Take Profits
    tp1_price: float
    tp1_distance_dollars: float
    tp1_distance_pips: float
    tp1_label: str = "Liquidity/FVG"

    tp2_price: Optional[float] = None
    tp2_distance_dollars: Optional[float] = None
    tp2_distance_pips: Optional[float] = None
    tp2_label: str = "Structure H1"

    tp3_price: Optional[float] = None
    tp3_distance_dollars: Optional[float] = None
    tp3_distance_pips: Optional[float] = None
    tp3_label: str = "Trail BE+"

    # R:R
    rr_ratio: float = 0.0

    # Gestion
    invalidation_price: float = 0.0
    expiration_minutes: int = 45  # 3 candles M15
    timestamp_generated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    justification: str = ""


# ---------------------------------------------------------------------------
# SignalGenerator
# ---------------------------------------------------------------------------

class SignalGenerator:
    """Genere un plan de trade pur a partir d'un setup technique valide."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or load_settings()

    def generate(
        self,
        setup: TechnicalSetup,
        fusion: FusionScore,
        pools: List[LiquidityPool],
        fvgs: List[FairValueGap],
    ) -> Optional[TradePlan]:
        """Genere le plan de trade complet.

        Returns:
            TradePlan si le grade est A+ ou B, sinon None.
        """
        if fusion.grade in ("N/A", "C"):
            logger.info(f"Signal rejete — grade {fusion.grade} insuffisant")
            return None

        direction = setup.direction
        ob = setup.ob
        if ob is None:
            logger.warning("Signal rejete — OB manquant dans le setup")
            return None

        # 1. Entree
        entry_zone = setup.entry_zone
        preferred_entry = (entry_zone[0] + entry_zone[1]) / 2

        # 2. Stop Loss
        sl_price = self._calculate_sl(direction, ob)
        sl_dist_dollars = abs(preferred_entry - sl_price)
        sl_dist_pips = sl_dist_dollars * PIPS_PER_DOLLAR

        # 3. Take Profits
        tp1, tp2, tp3 = self._calculate_tps(direction, preferred_entry, pools, fvgs, ob)

        # 4. R:R (base sur TP1)
        rr = 0.0
        if tp1:
            tp1_dist = abs(tp1 - preferred_entry)
            if sl_dist_dollars > 0:
                rr = round(tp1_dist / sl_dist_dollars, 2)

        # 5. Invalidation
        invalidation = self._calculate_invalidation(direction, ob)

        # 6. Signal ID
        signal_id = self._generate_signal_id()

        plan = TradePlan(
            signal_id=signal_id,
            direction=direction,
            grade=fusion.grade,
            score_total=fusion.total,
            score_breakdown={
                "macro": fusion.macro_component,
                "technical": fusion.technical_component,
                "timing": fusion.timing_component,
                "sentiment_adjustment": fusion.sentiment_adjustment,
            },
            entry_zone=entry_zone,
            preferred_entry=round(preferred_entry, 2),
            sl_price=round(sl_price, 2),
            sl_distance_dollars=round(sl_dist_dollars, 2),
            sl_distance_pips=round(sl_dist_pips, 1),
            tp1_price=round(tp1, 2) if tp1 else 0.0,
            tp1_distance_dollars=round(abs(tp1 - preferred_entry), 2) if tp1 else 0.0,
            tp1_distance_pips=round(abs(tp1 - preferred_entry) * PIPS_PER_DOLLAR, 1) if tp1 else 0.0,
            tp2_price=round(tp2, 2) if tp2 else None,
            tp2_distance_dollars=round(abs(tp2 - preferred_entry), 2) if tp2 else None,
            tp2_distance_pips=round(abs(tp2 - preferred_entry) * PIPS_PER_DOLLAR, 1) if tp2 else None,
            tp3_price=round(tp3, 2) if tp3 else None,
            tp3_distance_dollars=round(abs(tp3 - preferred_entry), 2) if tp3 else None,
            tp3_distance_pips=round(abs(tp3 - preferred_entry) * PIPS_PER_DOLLAR, 1) if tp3 else None,
            rr_ratio=rr,
            invalidation_price=round(invalidation, 2),
            justification=fusion.justification,
        )

        logger.success(
            f"Plan genere {signal_id} | {direction} {fusion.grade} | "
            f"Entry={plan.preferred_entry} | SL={plan.sl_price} ({plan.sl_distance_pips} pips) | "
            f"TP1={plan.tp1_price} | R:R={plan.rr_ratio}"
        )
        return plan

    # ------------------------------------------------------------------
    # Calculs techniques
    # ------------------------------------------------------------------

    def _calculate_sl(self, direction: str, ob: OrderBlock) -> float:
        """SL derriere le wick de l'OB + buffer technique.

        Min sl_min_dollars, max sl_max_pct_price du prix de l'OB.
        """
        price = (ob.ob_low + ob.ob_high) / 2
        max_sl_dist = price * (self.settings.trading.sl_max_pct_price / 100)
        buffer = max(self.settings.trading.sl_min_dollars, max_sl_dist * 0.3)

        if direction == "LONG":
            sl = ob.ob_low - buffer
        else:
            sl = ob.ob_high + buffer

        # Clamp pour ne pas depasser le max autorise
        actual_dist = abs(price - sl)
        if actual_dist > max_sl_dist:
            if direction == "LONG":
                sl = price - max_sl_dist
            else:
                sl = price + max_sl_dist

        return sl

    def _calculate_tps(
        self,
        direction: str,
        entry: float,
        pools: List[LiquidityPool],
        fvgs: List[FairValueGap],
        ob: OrderBlock,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Calcule les 3 niveaux de TP.

        TP1 : liquidite cible la plus proche ou FVG oppose.
        TP2 : liquidite plus lointaine ou structure opposee.
        TP3 : trailing (BE + 3x SL approximatif).
        """
        tp1: Optional[float] = None
        tp2: Optional[float] = None
        tp3: Optional[float] = None

        # --- TP1 : premier pool/FVG dans la direction ---
        candidates: List[float] = []
        for p in pools:
            if direction == "LONG" and p.price > entry:
                candidates.append(p.price)
            elif direction == "SHORT" and p.price < entry:
                candidates.append(p.price)

        for fvg in fvgs:
            if direction == "LONG" and fvg.fvg_high > entry:
                candidates.append(fvg.fvg_high)
            elif direction == "SHORT" and fvg.fvg_low < entry:
                candidates.append(fvg.fvg_low)

        # Trier par distance croissante
        if direction == "LONG":
            candidates.sort()
            candidates = [c for c in candidates if c > entry + 2.0]
        else:
            candidates.sort(reverse=True)
            candidates = [c for c in candidates if c < entry - 2.0]

        if len(candidates) >= 1:
            tp1 = candidates[0]
        if len(candidates) >= 2:
            tp2 = candidates[1]
        if len(candidates) >= 3:
            tp3 = candidates[2]

        # Fallback niveaux psychologiques si aucun pool/FVG
        if tp1 is None:
            if direction == "LONG":
                psy = ((int(entry) // 50) + 1) * 50
                if psy > entry + 2.0:
                    tp1 = float(psy)
            else:
                psy = ((int(entry) // 50)) * 50
                if psy < entry - 2.0:
                    tp1 = float(psy)

        # Fallback TP3 = trail approximatif si pas assez de cibles
        if tp3 is None and tp1 is not None:
            dist = abs(tp1 - entry)
            tp3 = entry + (dist * 2.5) if direction == "LONG" else entry - (dist * 2.5)

        return tp1, tp2, tp3

    @staticmethod
    def _calculate_invalidation(direction: str, ob: OrderBlock) -> float:
        """Prix d'invalidation : cloture M5 sous l'OB (LONG) ou au-dessus (SHORT)."""
        if direction == "LONG":
            return ob.ob_low
        return ob.ob_high

    @staticmethod
    def _generate_signal_id() -> str:
        """Genere un ID unique : SIG-YYYYMMDD-NNN."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")
        # Simple compteur base sur les secondes de la journee
        counter = int((now.hour * 3600 + now.minute * 60 + now.second) / 10)
        return f"SIG-{date_str}-{counter:03d}"
