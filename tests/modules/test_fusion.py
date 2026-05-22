"""Tests de validation Phase 5 — Moteur Fusion & Signal."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from modules.fusion.scoring import FusionScorer, FusionScore
from modules.fusion.generator import SignalGenerator, TradePlan, SignalInvalidator
from modules.macro.scorer import MacroScore
from modules.sentiment.scorer import SentimentScore
from modules.technical.ob import OBType, OrderBlock, OBFreshness
from modules.technical.scorer import TechnicalSetup


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_setup(direction: str = "LONG", score: float = 4.5) -> TechnicalSetup:
    ob = OrderBlock(
        type=OBType.BULLISH if direction == "LONG" else OBType.BEARISH,
        index=10,
        timestamp="2024-01-01T10:00:00Z",
        ob_low=2340.0,
        ob_high=2342.0,
        impulse_start=2339.5,  # wick proche pour R:R favorable en test
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


def _make_macro(total: float = 2.0) -> MacroScore:
    return MacroScore(
        total=total,
        grade="HAUSSIER",
        dxy_component=0.3,
        yields_component=0.2,
        fed_component=0.1,
        risk_component=0.0,
        inflation_component=0.1,
        justification="mock",
    )


def _make_sentiment(total: float = 0.0) -> SentimentScore:
    return SentimentScore(
        total=total,
        grade="NEUTRE",
        cot_signal=0.0,
        retail_signal=0.0,
        fear_greed_signal=0.0,
        justification="mock",
    )


def _make_pools(direction: str = "LONG") -> list:
    """Cree des pools de liquidite fictifs pour les tests."""
    from modules.technical.liquidity import LiquidityPool
    if direction == "LONG":
        return [
            LiquidityPool(type="PSYCH", price=2375.0, label="niveau 2375", strength=2.0),
            LiquidityPool(type="PDH", price=2390.0, label="prev day high", strength=2.5),
        ]
    return [
        LiquidityPool(type="PSYCH", price=2280.0, label="niveau 2280", strength=2.0),
        LiquidityPool(type="PDL", price=2260.0, label="prev day low", strength=2.5),
    ]


# ------------------------------------------------------------------
# Tests Scoring
# ------------------------------------------------------------------

def test_fusion_a_plus() -> None:
    scorer = FusionScorer()
    setup = _make_setup(score=5.0)
    macro = _make_macro(total=2.5)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0)
    assert fusion.total >= 3.5
    assert fusion.grade == "A+"
    assert fusion.matrix_authorized is True


def test_fusion_b() -> None:
    scorer = FusionScorer()
    setup = _make_setup(score=4.0)
    macro = _make_macro(total=1.0)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0)
    assert 2.5 <= fusion.total < 3.5
    assert fusion.grade == "B"


def test_fusion_rejected() -> None:
    scorer = FusionScorer()
    setup = _make_setup(direction="SHORT", score=2.0)
    macro = _make_macro(total=-2.0)  # baissier
    fusion = scorer.calculate_total(macro, setup, timing_score=0.0)
    assert fusion.grade == "N/A"
    assert fusion.matrix_authorized is False


def test_fusion_sentiment_exception_short() -> None:
    """Macro haussier + tech exceptionnel + greed extreme → exception short."""
    scorer = FusionScorer()
    setup = _make_setup(direction="SHORT", score=5.0)
    macro = _make_macro(total=2.5)
    sentiment = _make_sentiment(total=-2.0)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0, sentiment=sentiment)
    assert fusion.is_exception is True
    assert fusion.sentiment_adjustment == 0.5


def test_fusion_sentiment_exception_long() -> None:
    """Macro baissier + tech exceptionnel + fear extreme → exception long."""
    scorer = FusionScorer()
    setup = _make_setup(direction="LONG", score=5.0)
    macro = _make_macro(total=-2.5)
    sentiment = _make_sentiment(total=2.0)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0, sentiment=sentiment)
    assert fusion.is_exception is True
    assert fusion.sentiment_adjustment == 0.5


def test_fusion_no_exception_neutral() -> None:
    scorer = FusionScorer()
    setup = _make_setup(score=5.0)
    macro = _make_macro(total=2.5)
    sentiment = _make_sentiment(total=0.0)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0, sentiment=sentiment)
    assert fusion.is_exception is False
    assert fusion.sentiment_adjustment == 0.0


# ------------------------------------------------------------------
# Tests Matrice Macro × Technique
# ------------------------------------------------------------------

def test_matrix_a_plus_aligned() -> None:
    """A+ + Macro aligned → A+ autorise."""
    scorer = FusionScorer()
    setup = _make_setup(direction="LONG", score=5.0)
    macro = _make_macro(total=2.5)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0)
    assert fusion.matrix_authorized is True
    assert "A+ + Macro aligned" in fusion.matrix_reason


def test_matrix_a_plus_neutral_exception() -> None:
    """A+ + Macro neutre + Timing 2 → B autorise (exception)."""
    scorer = FusionScorer()
    setup = _make_setup(direction="LONG", score=5.0)
    macro = _make_macro(total=0.0)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0)
    assert fusion.matrix_authorized is True
    assert fusion.is_exception is True
    assert "macro neutre" in fusion.matrix_reason.lower() or "exception" in fusion.matrix_reason.lower()


def test_matrix_a_plus_against_rejected() -> None:
    """A+ + Macro contre → REJET."""
    scorer = FusionScorer()
    setup = _make_setup(direction="LONG", score=5.0)
    macro = _make_macro(total=-2.5)  # baissier, contre le LONG
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0)
    assert fusion.matrix_authorized is False
    assert "Macro contre" in fusion.matrix_reason


def test_matrix_b_neutral_rejected() -> None:
    """B + Macro neutre → REJET."""
    scorer = FusionScorer()
    setup = _make_setup(direction="LONG", score=3.5)
    macro = _make_macro(total=0.0)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0)
    assert fusion.matrix_authorized is False
    assert "B + Macro neutre" in fusion.matrix_reason


def test_matrix_low_tech_rejected() -> None:
    """Tech < 3.0 → toujours rejete."""
    scorer = FusionScorer()
    setup = _make_setup(direction="LONG", score=2.5)
    macro = _make_macro(total=2.5)
    fusion = scorer.calculate_total(macro, setup, timing_score=2.0)
    assert fusion.matrix_authorized is False
    assert "< 3.0" in fusion.matrix_reason


def test_strict_threshold_below_2_5() -> None:
    """Score total < 2.5 sans exception → N/A et rejet."""
    scorer = FusionScorer()
    setup = _make_setup(score=3.0)
    macro = _make_macro(total=-0.5)
    fusion = scorer.calculate_total(macro, setup, timing_score=0.0)
    assert fusion.grade == "N/A"
    assert fusion.matrix_authorized is False


# ------------------------------------------------------------------
# Tests Signal Generation
# ------------------------------------------------------------------

def test_signal_generation_long() -> None:
    generator = SignalGenerator()
    setup = _make_setup(direction="LONG", score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    assert plan.direction == "LONG"
    assert plan.grade == "A+"
    assert plan.sl_price < plan.preferred_entry
    assert plan.tp1_price > plan.preferred_entry
    assert plan.rr_ratio >= 2.0
    assert plan.invalidation_price == setup.ob.ob_low
    assert plan.expiration_minutes == 45
    # Nouveaux champs Phase 5
    assert plan.pair == "XAUUSD"
    assert plan.valid_until != ""
    assert plan.setup_type != ""
    assert plan.killzone != ""
    assert plan.notes != ""
    assert plan.sl_distance_pct > 0
    assert plan.tp1_ratio is not None
    assert plan.tp1_allocation_pct == 50
    assert plan.macro_context != {}
    assert plan.technical_context != {}


def test_signal_generation_short() -> None:
    generator = SignalGenerator()
    setup = _make_setup(direction="SHORT", score=4.5)
    fusion = FusionScore(
        total=3.8, grade="A+", macro_component=0.5,
        technical_component=2.25, timing_component=1.0,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("SHORT")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    assert plan.direction == "SHORT"
    assert plan.sl_price > plan.preferred_entry
    assert plan.tp1_price < plan.preferred_entry


def test_signal_rejected_low_grade() -> None:
    generator = SignalGenerator()
    setup = _make_setup(score=2.0)
    fusion = FusionScore(
        total=1.2, grade="N/A", macro_component=0.0,
        technical_component=0.5, timing_component=0.2,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is None


def test_signal_rejected_matrix() -> None:
    """Signal rejete par la matrice meme si score suffisant."""
    generator = SignalGenerator()
    setup = _make_setup(direction="LONG", score=5.0)
    fusion = FusionScore(
        total=3.5, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.0,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=False, matrix_reason="A+ + Macro contre",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is None


def test_signal_has_sizing() -> None:
    """Le plan doit contenir le sizing calcule par le RiskEngine."""
    generator = SignalGenerator()
    setup = _make_setup(score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    assert plan.position_size_lots is not None
    assert plan.position_size_lots > 0
    assert plan.risk_amount_dollars is not None
    assert plan.risk_pct is not None
    # Grade A+ → risk 1.0%
    assert plan.risk_pct == 1.0


def test_sl_distance_calculation() -> None:
    """Le SL doit respecter les bornes techniques."""
    generator = SignalGenerator()
    setup = _make_setup(direction="LONG", score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    # Distance SL >= sl_min_dollars (15$)
    assert plan.sl_distance_dollars >= 15.0
    # Distance SL <= 1% du prix
    max_sl = plan.preferred_entry * 0.01
    assert plan.sl_distance_dollars <= max_sl + 0.1  # tolerance


def test_pips_calculation() -> None:
    """1 pip XAU/USD = 0.01 → pips = dollars * 100."""
    generator = SignalGenerator()
    setup = _make_setup(direction="LONG", score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    expected_pips = round(plan.sl_distance_dollars * 100, 1)
    assert plan.sl_distance_pips == expected_pips


def test_signal_id_format() -> None:
    generator = SignalGenerator()
    setup = _make_setup(score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    assert plan.signal_id.startswith("SIG-")
    parts = plan.signal_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD


# ------------------------------------------------------------------
# Tests ATR-based SL
# ------------------------------------------------------------------

def test_sl_with_atr() -> None:
    """SL avec ATR fourni doit utiliser max(min_dollars, ATR * 0.5)."""
    from modules.technical.liquidity import LiquidityPool
    generator = SignalGenerator()
    # Prix eleve pour eviter le clamp max 1%
    ob = OrderBlock(
        type=OBType.BULLISH,
        index=10,
        timestamp="2024-01-01T10:00:00Z",
        ob_low=3000.0,
        ob_high=3002.0,
        impulse_start=2999.5,
        impulse_end=3005.0,
        freshness=OBFreshness.FRESH,
    )
    setup = TechnicalSetup(
        direction="LONG",
        entry_zone=(3000.0, 3002.0),
        sl_zone=(2998.0, 2999.0),
        tp_zones=[(3010.0, 3011.0)],
        ob=ob,
        score=5.0,
        grade="A+",
    )
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = [LiquidityPool(type="PSYCH", price=3070.0, label="niveau 3070", strength=2.0)]
    # ATR = 50$ → buffer = max(15, 25) = 25
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[], atr_value=50.0)
    assert plan is not None
    assert plan.sl_distance_dollars >= 25.0


def test_sl_without_atr() -> None:
    """SL sans ATR doit utiliser le fallback."""
    generator = SignalGenerator()
    setup = _make_setup(direction="LONG", score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
        matrix_authorized=True, matrix_reason="",
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    assert plan.sl_distance_dollars >= 15.0


# ------------------------------------------------------------------
# Tests Invalidation
# ------------------------------------------------------------------

def test_invalidation_long() -> None:
    plan = TradePlan(
        signal_id="SIG-TEST-001",
        direction="LONG",
        invalidation_price=2340.0,
    )
    assert SignalInvalidator.check_invalidation_long(plan, 2339.5) is True
    assert SignalInvalidator.check_invalidation_long(plan, 2340.5) is False


def test_invalidation_short() -> None:
    plan = TradePlan(
        signal_id="SIG-TEST-001",
        direction="SHORT",
        invalidation_price=2342.0,
    )
    assert SignalInvalidator.check_invalidation_short(plan, 2342.5) is True
    assert SignalInvalidator.check_invalidation_short(plan, 2341.5) is False


def test_expiration() -> None:
    from datetime import datetime, timezone, timedelta
    plan = TradePlan(
        signal_id="SIG-TEST-001",
        valid_until=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    )
    assert SignalInvalidator.check_expiration(plan) is True

    plan2 = TradePlan(
        signal_id="SIG-TEST-002",
        valid_until=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )
    assert SignalInvalidator.check_expiration(plan2) is False


def test_macro_invalidation() -> None:
    plan = TradePlan(signal_id="SIG-TEST-001")
    assert SignalInvalidator.check_macro_invalidation(plan, []) is False
    assert SignalInvalidator.check_macro_invalidation(plan, ["FOMC_LOCK"]) is True


if __name__ == "__main__":
    test_fusion_a_plus()
    test_fusion_b()
    test_fusion_rejected()
    test_fusion_sentiment_exception_short()
    test_fusion_sentiment_exception_long()
    test_fusion_no_exception_neutral()
    test_matrix_a_plus_aligned()
    test_matrix_a_plus_neutral_exception()
    test_matrix_a_plus_against_rejected()
    test_matrix_b_neutral_rejected()
    test_matrix_low_tech_rejected()
    test_strict_threshold_below_2_5()
    test_signal_generation_long()
    test_signal_generation_short()
    test_signal_rejected_low_grade()
    test_signal_rejected_matrix()
    test_signal_has_sizing()
    test_sl_distance_calculation()
    test_pips_calculation()
    test_signal_id_format()
    test_sl_with_atr()
    test_sl_without_atr()
    test_invalidation_long()
    test_invalidation_short()
    test_expiration()
    test_macro_invalidation()
    print("[OK] Tous les tests Phase 5 ont passe.")
