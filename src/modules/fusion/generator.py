"""Generation du Plan de Trade — niveaux techniques + sizing + validation risque.

Le bot calcule :
  - Zone d'entree (low/high de l'OB)
  - SL (derriere le wick de l'OB + buffer ATR × 0.5, min 15$, max 1% prix)
  - TP1/TP2/TP3 (liquidite, FVG oppose, trail)
  - R:R attendu
  - Sizing (lots) selon capital virtuel et % risque par grade
  - Validation risque (SL, R:R, drawdown, max trades, weekend gap)
  - Prix d'invalidation (cloture M5 sous/au-dessus de l'OB)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from core.config import Settings, load_settings
from modules.fusion.scoring import FusionScore
from modules.journal.database import JournalDatabase
from modules.risk.engine import RiskEngine
from modules.technical.fvg import FairValueGap
from modules.technical.liquidity import LiquidityPool, get_current_killzone
from modules.technical.ob import OrderBlock
from modules.technical.scorer import TechnicalSetup


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Sur XAU/USD, 1 pip standard = 0.01 (1 cent)
PIPS_PER_DOLLAR = 100.0

SIGNAL_EXPIRATION_MINUTES = 45  # 3 candles M15


# ---------------------------------------------------------------------------
# TradePlan
# ---------------------------------------------------------------------------

@dataclass
class TradePlan:
    """Plan de trade complet genere par le bot."""

    # Identifiants
    signal_id: str
    trade_id: Optional[str] = None  # TRADE-YYYYMMDD-NNN si execution
    pair: str = "XAUUSD"

    # Decision
    direction: str = "LONG"  # "LONG" | "SHORT"
    grade: str = "N/A"
    score_total: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    setup_type: str = ""

    # Zone d'entree
    entry_zone: Tuple[float, float] = (0.0, 0.0)  # (low, high)
    preferred_entry: float = 0.0

    # Stop Loss
    sl_price: float = 0.0
    sl_distance_dollars: float = 0.0
    sl_distance_pips: float = 0.0
    sl_distance_pct: float = 0.0

    # Take Profits
    tp1_price: Optional[float] = None
    tp1_distance_dollars: Optional[float] = None
    tp1_distance_pips: Optional[float] = None
    tp1_label: str = "Liquidity/FVG"
    tp1_ratio: Optional[str] = None
    tp1_allocation_pct: int = 50

    tp2_price: Optional[float] = None
    tp2_distance_dollars: Optional[float] = None
    tp2_distance_pips: Optional[float] = None
    tp2_label: str = "Structure H1"
    tp2_ratio: Optional[str] = None
    tp2_allocation_pct: int = 30

    tp3_price: Optional[float] = None
    tp3_distance_dollars: Optional[float] = None
    tp3_distance_pips: Optional[float] = None
    tp3_label: str = "Trail BE+"
    tp3_ratio: Optional[str] = None
    tp3_allocation_pct: int = 20

    # R:R
    rr_ratio: float = 0.0

    # Gestion
    invalidation_price: float = 0.0
    expiration_minutes: int = SIGNAL_EXPIRATION_MINUTES
    timestamp_generated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    valid_until: str = ""
    justification: str = ""

    # Sizing & Risque
    position_size_lots: Optional[float] = None
    risk_amount_dollars: Optional[float] = None
    risk_pct: Optional[float] = None

    # Contexte
    macro_context: Dict[str, Any] = field(default_factory=dict)
    technical_context: Dict[str, Any] = field(default_factory=dict)
    killzone: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# SignalGenerator
# ---------------------------------------------------------------------------

class SignalGenerator:
    """Genere un plan de trade valide a partir d'un setup technique."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db: Optional[JournalDatabase] = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.risk_engine = RiskEngine(settings=self.settings, db=db)

    def generate(
        self,
        setup: TechnicalSetup,
        fusion: FusionScore,
        pools: List[LiquidityPool],
        fvgs: List[FairValueGap],
        atr_value: Optional[float] = None,
    ) -> Optional[TradePlan]:
        """Genere le plan de trade complet.

        Args:
            setup: Setup technique detecte
            fusion: Score de fusion
            pools: Pools de liquidite detectes
            fvgs: FVGs detectes
            atr_value: Valeur ATR (optionnel) pour buffer SL

        Returns:
            TradePlan si le grade est A+ ou B, matrix autorisee, et risque OK.
            Sinon None avec raison loggee.
        """
        # Rejection stricte
        if fusion.grade in ("N/A", "C"):
            logger.info(f"Signal rejete — grade {fusion.grade} insuffisant")
            return None

        if not fusion.matrix_authorized:
            logger.info(f"Signal rejete — matrice: {fusion.matrix_reason}")
            return None

        direction = setup.direction
        ob = setup.ob
        if ob is None:
            logger.warning("Signal rejete — OB manquant dans le setup")
            return None

        # 1. Entree
        entry_zone = setup.entry_zone
        preferred_entry = (entry_zone[0] + entry_zone[1]) / 2

        # 2. Stop Loss (ATR-based si fourni)
        sl_price = self._calculate_sl(direction, ob, atr_value)
        sl_dist_dollars = abs(preferred_entry - sl_price)
        sl_dist_pips = sl_dist_dollars * PIPS_PER_DOLLAR
        sl_dist_pct = round(sl_dist_dollars / preferred_entry * 100, 3)

        # 3. Take Profits
        tp1, tp2, tp3 = self._calculate_tps(direction, preferred_entry, pools, fvgs, ob)

        # 4. R:R et ratios
        tp1_ratio = None
        tp2_ratio = None
        tp3_ratio = None
        rr = 0.0
        if tp1:
            tp1_dist = abs(tp1 - preferred_entry)
            if sl_dist_dollars > 0:
                rr = round(tp1_dist / sl_dist_dollars, 2)
                tp1_ratio = f"1:{rr:.1f}"
        if tp2 and sl_dist_dollars > 0:
            tp2_dist = abs(tp2 - preferred_entry)
            tp2_ratio = f"1:{round(tp2_dist / sl_dist_dollars, 1):.1f}"
        if tp3 and sl_dist_dollars > 0:
            tp3_dist = abs(tp3 - preferred_entry)
            tp3_ratio = f"1:{round(tp3_dist / sl_dist_dollars, 1):.1f}"

        # 5. Invalidation
        invalidation = self._calculate_invalidation(direction, ob)

        # 6. IDs et timing
        signal_id = self._generate_signal_id()
        now = datetime.now(timezone.utc)
        valid_until = (now + timedelta(minutes=SIGNAL_EXPIRATION_MINUTES)).isoformat()

        # 7. Contexte
        setup_type = self._build_setup_type(setup, fvgs)
        macro_ctx = self._build_macro_context(fusion)
        tech_ctx = self._build_technical_context(setup, pools, fvgs)
        killzone_name, _ = get_current_killzone()
        notes = self._build_notes(direction, ob, sl_price, invalidation, fusion)

        plan = TradePlan(
            signal_id=signal_id,
            pair="XAUUSD",
            direction=direction,
            grade=fusion.grade,
            score_total=fusion.total,
            score_breakdown={
                "macro": fusion.macro_component,
                "technical": fusion.technical_component,
                "timing": fusion.timing_component,
                "sentiment_adjustment": fusion.sentiment_adjustment,
            },
            setup_type=setup_type,
            entry_zone=entry_zone,
            preferred_entry=round(preferred_entry, 2),
            sl_price=round(sl_price, 2),
            sl_distance_dollars=round(sl_dist_dollars, 2),
            sl_distance_pips=round(sl_dist_pips, 1),
            sl_distance_pct=sl_dist_pct,
            tp1_price=round(tp1, 2) if tp1 else None,
            tp1_distance_dollars=round(abs(tp1 - preferred_entry), 2) if tp1 else None,
            tp1_distance_pips=round(abs(tp1 - preferred_entry) * PIPS_PER_DOLLAR, 1) if tp1 else None,
            tp1_ratio=tp1_ratio,
            tp1_allocation_pct=50,
            tp2_price=round(tp2, 2) if tp2 else None,
            tp2_distance_dollars=round(abs(tp2 - preferred_entry), 2) if tp2 else None,
            tp2_distance_pips=round(abs(tp2 - preferred_entry) * PIPS_PER_DOLLAR, 1) if tp2 else None,
            tp2_ratio=tp2_ratio,
            tp2_allocation_pct=30,
            tp3_price=round(tp3, 2) if tp3 else None,
            tp3_distance_dollars=round(abs(tp3 - preferred_entry), 2) if tp3 else None,
            tp3_distance_pips=round(abs(tp3 - preferred_entry) * PIPS_PER_DOLLAR, 1) if tp3 else None,
            tp3_ratio=tp3_ratio,
            tp3_allocation_pct=20,
            rr_ratio=rr,
            invalidation_price=round(invalidation, 2),
            expiration_minutes=SIGNAL_EXPIRATION_MINUTES,
            timestamp_generated=now.isoformat(),
            valid_until=valid_until,
            justification=fusion.justification,
            macro_context=macro_ctx,
            technical_context=tech_ctx,
            killzone=killzone_name,
            notes=notes,
        )

        # 8. Validation risque + sizing
        risk_result = self.risk_engine.check_trade(plan, grade=fusion.grade)
        if not risk_result.authorized:
            logger.warning(
                f"Signal rejete par RiskEngine — {risk_result.reason}"
            )
            return None

        # Ajouter sizing au plan
        if risk_result.sizing:
            plan.position_size_lots = risk_result.sizing.position_size_lots
            plan.risk_amount_dollars = risk_result.sizing.risk_amount_dollars
            plan.risk_pct = risk_result.sizing.risk_pct

        logger.success(
            f"Plan genere {signal_id} | {direction} {fusion.grade} | "
            f"Entry={plan.preferred_entry} | SL={plan.sl_price} ({plan.sl_distance_pips} pips) | "
            f"TP1={plan.tp1_price} | R:R={plan.rr_ratio} | "
            f"Size={plan.position_size_lots:.2f} lots | Risk={plan.risk_pct}% | "
            f"Valid until {valid_until}"
        )
        return plan

    # ------------------------------------------------------------------
    # Calculs techniques
    # ------------------------------------------------------------------

    def _calculate_sl(
        self,
        direction: str,
        ob: OrderBlock,
        atr_value: Optional[float] = None,
    ) -> float:
        """SL derriere le wick de l'OB + buffer technique.

        Si ATR fourni : buffer = max(sl_min_dollars, ATR × 0.5)
        Sinon : buffer = max(sl_min_dollars, max_sl_dist × 0.3)

        Min sl_min_dollars, max sl_max_pct_price du prix de l'OB.
        """
        price = (ob.ob_low + ob.ob_high) / 2
        max_sl_dist = price * (self.settings.trading.sl_max_pct_price / 100)

        if atr_value is not None:
            buffer = max(self.settings.trading.sl_min_dollars, atr_value * 0.5)
        else:
            buffer = max(self.settings.trading.sl_min_dollars, max_sl_dist * 0.3)

        if direction == "LONG":
            # Wick de l'OB = le plus bas de l'impulsion de creation
            wick_low = getattr(ob, "impulse_start", ob.ob_low)
            sl = min(wick_low, ob.ob_low) - buffer
        else:
            wick_high = getattr(ob, "impulse_end", ob.ob_high)
            sl = max(wick_high, ob.ob_high) + buffer

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

    @staticmethod
    def _generate_trade_id() -> str:
        """Genere un ID trade : TRADE-YYYYMMDD-NNN."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")
        counter = int((now.hour * 3600 + now.minute * 60 + now.second) / 10)
        return f"TRADE-{date_str}-{counter:03d}"

    # ------------------------------------------------------------------
    # Contexte & Notes
    # ------------------------------------------------------------------

    @staticmethod
    def _build_setup_type(setup: TechnicalSetup, fvgs: List[FairValueGap]) -> str:
        """Decrit le type de setup en texte."""
        ob_type = setup.ob.type.value if setup.ob else "Unknown"
        has_fvg = len(fvgs) > 0
        parts = [f"{ob_type} OB"]
        if has_fvg:
            parts.append("FVG confluent")
        return " + ".join(parts)

    @staticmethod
    def _build_macro_context(fusion: FusionScore) -> Dict[str, Any]:
        """Contexte macro pour le plan."""
        return {
            "score": fusion.macro_component,
            "justification": fusion.justification,
        }

    @staticmethod
    def _build_technical_context(
        setup: TechnicalSetup,
        pools: List[LiquidityPool],
        fvgs: List[FairValueGap],
    ) -> Dict[str, Any]:
        """Contexte technique pour le plan."""
        ob = setup.ob
        ctx: Dict[str, Any] = {
            "structure": f"{setup.direction} — grade {setup.grade}",
            "ob_zone": f"{ob.ob_low:.2f}-{ob.ob_high:.2f}" if ob else "",
            "fvg_zones": [f"{f.fvg_low:.2f}-{f.fvg_high:.2f}" for f in fvgs],
            "liquidity_targets": [
                f"{p.type}@{p.price:.2f}" for p in pools[:3]
            ],
        }
        return ctx

    @staticmethod
    def _build_notes(
        direction: str,
        ob: OrderBlock,
        sl_price: float,
        invalidation: float,
        fusion: FusionScore,
    ) -> str:
        """Genere les notes d'execution."""
        notes = [
            f"Attendre rejet M5 dans l'OB ({ob.ob_low:.2f}-{ob.ob_high:.2f}).",
            f"Ne pas entrer si cloture M5 sous {invalidation:.2f} (LONG) ou au-dessus (SHORT).",
            f"SL technique: {sl_price:.2f}.",
        ]
        if fusion.is_exception:
            notes.append("Exception active — verifier la liquidite avant execution.")
        if fusion.matrix_reason:
            notes.append(f"Matrix: {fusion.matrix_reason}")
        return " ".join(notes)


# ---------------------------------------------------------------------------
# SignalInvalidator
# ---------------------------------------------------------------------------

class SignalInvalidator:
    """Surveille les signaux actifs et detecte les invalidations."""

    @staticmethod
    def check_invalidation_long(plan: TradePlan, current_price: float) -> bool:
        """Cloture M5 sous l'OB → signal long invalide."""
        if plan.direction != "LONG":
            return False
        # On considere que le prix actuel est une cloture M5
        return current_price < plan.invalidation_price

    @staticmethod
    def check_invalidation_short(plan: TradePlan, current_price: float) -> bool:
        """Cloture M5 au-dessus de l'OB → signal short invalide."""
        if plan.direction != "SHORT":
            return False
        return current_price > plan.invalidation_price

    @staticmethod
    def check_expiration(plan: TradePlan, current_time: Optional[datetime] = None) -> bool:
        """Verifie si le signal a expire (45 min par defaut)."""
        if not plan.valid_until:
            return False
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        try:
            valid = datetime.fromisoformat(plan.valid_until.replace("Z", "+00:00"))
            return current_time > valid
        except ValueError:
            return False

    @staticmethod
    def check_macro_invalidation(plan: TradePlan, active_locks: List[str]) -> bool:
        """Si un macro lock est actif, le signal est invalide/suspendu."""
        if not active_locks:
            return False
        # Tout lock active invalide le signal en attente
        return len(active_locks) > 0
