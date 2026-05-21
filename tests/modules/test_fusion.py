"""Tests de validation Phase 5 — Moteur Fusion & Signal."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from modules.fusion.scoring import FusionScorer, FusionScore
from modules.fusion.generator import SignalGenerator, TradePlan
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
        LiquidityPool(type="PSYCH", price=2305.0, label="niveau 2305", strength=2.0),
        LiquidityPool(type="PDL", price=2290.0, label="prev day low", strength=2.5),
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
# Tests Signal Generation
# ------------------------------------------------------------------

def test_signal_generation_long() -> None:
    generator = SignalGenerator()
    setup = _make_setup(direction="LONG", score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
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


def test_signal_generation_short() -> None:
    generator = SignalGenerator()
    setup = _make_setup(direction="SHORT", score=4.5)
    fusion = FusionScore(
        total=3.8, grade="A+", macro_component=0.5,
        technical_component=2.25, timing_component=1.0,
        sentiment_adjustment=0.0, justification="mock",
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
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is None


def test_signal_no_sizing() -> None:
    """Le plan ne doit pas contenir de champs sizing/risque."""
    generator = SignalGenerator()
    setup = _make_setup(score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
    )
    plan = generator.generate(setup, fusion, pools=[], fvgs=[])
    assert plan is not None
    assert not hasattr(plan, "position_size")
    assert not hasattr(plan, "risk_pct")
    assert not hasattr(plan, "capital_at_risk")


def test_sl_distance_calculation() -> None:
    """Le SL doit respecter les bornes techniques."""
    generator = SignalGenerator()
    setup = _make_setup(direction="LONG", score=5.0)
    fusion = FusionScore(
        total=4.2, grade="A+", macro_component=1.0,
        technical_component=2.5, timing_component=0.7,
        sentiment_adjustment=0.0, justification="mock",
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
    )
    pools = _make_pools("LONG")
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])
    assert plan is not None
    assert plan.signal_id.startswith("SIG-")
    parts = plan.signal_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD


if __name__ == "__main__":
    test_fusion_a_plus()
    test_fusion_b()
    test_fusion_rejected()
    test_fusion_sentiment_exception_short()
    test_fusion_sentiment_exception_long()
    test_fusion_no_exception_neutral()
    test_signal_generation_long()
    test_signal_generation_short()
    test_signal_rejected_low_grade()
    test_signal_no_sizing()
    test_sl_distance_calculation()
    test_pips_calculation()
    test_signal_id_format()
    print("[OK] Tous les tests Phase 5 ont passe.")
