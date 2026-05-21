"""Runner de validation Phase 5 — Moteur Fusion & Signal.

Usage : python -m src.modules.fusion.runner
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loguru import logger

from core.logger import setup_logging
from modules.fusion.scoring import FusionScorer
from modules.fusion.generator import SignalGenerator
from modules.macro.scorer import MacroScore, MacroScorer
from modules.macro.core import MacroSnapshot
from modules.sentiment.scorer import SentimentScore
from modules.technical.liquidity import LiquidityPool
from modules.technical.ob import OBType, OrderBlock, OBFreshness
from modules.technical.scorer import TechnicalSetup


def _make_mock_setup(direction: str = "LONG", score: float = 4.5) -> TechnicalSetup:
    """Cree un setup technique fictif pour la demo."""
    ob = OrderBlock(
        type=OBType.BULLISH if direction == "LONG" else OBType.BEARISH,
        index=10,
        timestamp="2024-01-01T10:00:00Z",
        ob_low=2340.0,
        ob_high=2342.0,
        impulse_start=2338.0,
        impulse_end=2345.0,
        freshness=OBFreshness.FRESH,
    )
    return TechnicalSetup(
        direction=direction,
        entry_zone=(2340.0, 2342.0),
        sl_zone=(2338.0, 2339.0) if direction == "LONG" else (2343.0, 2344.0),
        tp_zones=[(2346.0, 2347.0), (2350.0, 2351.0)],
        ob=ob,
        score=score,
        grade="A+" if score >= 4.5 else "B",
    )


def _make_mock_macro(score: float = 2.0) -> MacroScore:
    return MacroScore(
        total=score,
        grade="POUSSEE HAUSSIERE",
        dxy_component=0.3,
        yields_component=0.2,
        fed_component=0.1,
        risk_component=0.0,
        inflation_component=0.1,
        justification="Macro mock",
    )


def _make_mock_sentiment(score: float = 0.0) -> SentimentScore:
    return SentimentScore(
        total=score,
        grade="NEUTRE",
        cot_signal=0.0,
        retail_signal=0.0,
        fear_greed_signal=0.0,
        justification="Sentiment mock",
    )


def main() -> int:
    setup_logging()
    logger.info("=" * 60)
    logger.info("🧠 VALIDATION PHASE 5 — MOTEUR FUSION & SIGNAL")
    logger.info("=" * 60)

    scorer = FusionScorer()
    generator = SignalGenerator()

    # 1. Setup A+ aligne macro
    logger.info("→ Test 1 : Setup A+ + Macro haussier + Timing parfait")
    setup = _make_mock_setup(direction="LONG", score=5.0)
    macro = _make_mock_macro(score=2.5)
    sentiment = _make_mock_sentiment(score=1.0)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0, sentiment=sentiment)
    logger.info(f"   Fusion: {fusion.total} | Grade: {fusion.grade}")
    assert fusion.grade == "A+", f"Attendu A+, got {fusion.grade}"

    # 2. Setup B neutre macro
    logger.info("→ Test 2 : Setup B + Macro neutre + Timing moyen")
    setup2 = _make_mock_setup(direction="LONG", score=4.0)
    macro2 = _make_mock_macro(score=1.0)
    fusion2 = scorer.calculate_total(macro2, setup2, timing_score=2.0)
    logger.info(f"   Fusion: {fusion2.total} | Grade: {fusion2.grade}")
    assert fusion2.grade == "B", f"Attendu B, got {fusion2.grade}"

    # 3. Signal rejete
    logger.info("→ Test 3 : Setup faible + Macro contre")
    setup3 = _make_mock_setup(direction="SHORT", score=2.0)
    macro3 = _make_mock_macro(score=-2.0)  # baissier
    fusion3 = scorer.calculate_total(macro3, setup3, timing_score=0.0)
    logger.info(f"   Fusion: {fusion3.total} | Grade: {fusion3.grade}")
    assert fusion3.grade == "N/A"

    # 4. Exception sentiment contre-trend
    logger.info("→ Test 4 : Exception sentiment (contre-trend)")
    setup4 = _make_mock_setup(direction="SHORT", score=5.0)
    macro4 = _make_mock_macro(score=2.5)  # haussier
    sentiment4 = _make_mock_sentiment(score=-2.0)  # extreme greed → favorise short
    fusion4 = scorer.calculate_total(macro4, setup4, timing_score=2.0, sentiment=sentiment4)
    logger.info(f"   Fusion: {fusion4.total} | Grade: {fusion4.grade} | Exception={fusion4.is_exception}")
    assert fusion4.is_exception is True

    # 5. Generation plan de trade
    logger.info("→ Test 5 : Generation plan de trade (sans sizing)")
    demo_pools = [
        LiquidityPool(type="PSYCH", price=2375.0, label="niveau 2375", strength=2.0),
        LiquidityPool(type="PDH", price=2390.0, label="prev day high", strength=2.5),
    ]
    plan = generator.generate(setup, fusion, pools=demo_pools, fvgs=[])
    assert plan is not None
    logger.info(f"   Signal ID: {plan.signal_id}")
    logger.info(f"   Direction: {plan.direction} | Grade: {plan.grade}")
    logger.info(f"   Entry: {plan.preferred_entry} (zone {plan.entry_zone})")
    logger.info(f"   SL: {plan.sl_price} (${plan.sl_distance_dollars} / {plan.sl_distance_pips} pips)")
    logger.info(f"   TP1: {plan.tp1_price} (${plan.tp1_distance_dollars} / {plan.tp1_distance_pips} pips)")
    if plan.tp2_price:
        logger.info(f"   TP2: {plan.tp2_price} (${plan.tp2_distance_dollars} / {plan.tp2_distance_pips} pips)")
    if plan.tp3_price:
        logger.info(f"   TP3: {plan.tp3_price} (${plan.tp3_distance_dollars} / {plan.tp3_distance_pips} pips)")
    logger.info(f"   R:R = 1:{plan.rr_ratio}")
    logger.info(f"   Invalidation: {plan.invalidation_price}")
    logger.info(f"   Expiration: {plan.expiration_minutes} min")
    assert plan.rr_ratio >= 2.0, f"R:R trop faible: {plan.rr_ratio}"

    # 6. Verification absence sizing
    logger.info("→ Test 6 : Verification absence sizing/position")
    assert not hasattr(plan, "position_size"), "Le plan ne doit PAS contenir de sizing"
    assert not hasattr(plan, "risk_pct"), "Le plan ne doit PAS contenir de % risque"
    logger.info("   ✅ Pas de sizing — OK")

    # Bilan
    logger.info("=" * 60)
    logger.info("📊 BILAN PHASE 5")
    logger.info("   Score A+ : ✅")
    logger.info("   Score B  : ✅")
    logger.info("   Rejet N/A : ✅")
    logger.info("   Exception sentiment : ✅")
    logger.info("   Plan de trade (SL/TP pips, sans sizing) : ✅")
    logger.info("=" * 60)
    logger.success("✅ Phase 5 VALIDE")

    return 0


if __name__ == "__main__":
    sys.exit(main())
