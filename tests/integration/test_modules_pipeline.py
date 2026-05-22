"""Tests d'integration Phases 2-5 — Pipeline complet modules.

Valide les flux :
  Phase 2 : Donnees -> Detection OB/FVG -> Scoring technique
  Phase 3 : Donnees -> Snapshot macro -> Scoring macro
  Phase 4 : Fetchers -> Snapshot sentiment -> Scoring sentiment
  Phase 5 : Macro + Tech + Sentiment -> Fusion -> Signal
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from data.compat import OHLCVData
from modules.fusion.generator import SignalGenerator
from modules.fusion.scoring import FusionScorer
from modules.macro.core import MacroSnapshot
from modules.macro.locks import MacroLockDetector
from modules.macro.scorer import MacroScore, MacroScorer
from modules.sentiment.core import (
    COTRecord,
    FearGreedIndex,
    RetailRatio,
    SentimentSnapshot,
)
from modules.sentiment.scorer import SentimentScorer
from modules.technical.core import Trend
from modules.technical.fvg import FairValueGap, FVGType
from modules.technical.liquidity import LiquidityPool
from modules.technical.ob import OBType, OrderBlock, OBFreshness
from modules.technical.scorer import TechnicalScorer, TechnicalSetup


def _make_ohlcv_data() -> OHLCVData:
    """Cree des donnees OHLCV factices."""
    rows = [
        {"timestamp": "2024-01-01T10:00:00Z", "open": 2340.0, "high": 2342.0, "low": 2339.0, "close": 2341.0, "volume": 100},
        {"timestamp": "2024-01-01T10:05:00Z", "open": 2341.0, "high": 2345.0, "low": 2340.0, "close": 2344.0, "volume": 150},
        {"timestamp": "2024-01-01T10:10:00Z", "open": 2344.0, "high": 2346.0, "low": 2343.0, "close": 2345.0, "volume": 120},
        {"timestamp": "2024-01-01T10:15:00Z", "open": 2345.0, "high": 2348.0, "low": 2344.0, "close": 2347.0, "volume": 200},
        {"timestamp": "2024-01-01T10:20:00Z", "open": 2347.0, "high": 2349.0, "low": 2346.0, "close": 2348.0, "volume": 180},
    ]
    return OHLCVData(data=rows, pair="XAU/USD", timeframe="M5")


def _make_ob(direction: str = "LONG") -> OrderBlock:
    return OrderBlock(
        type=OBType.BULLISH if direction == "LONG" else OBType.BEARISH,
        index=10,
        timestamp="2024-01-01T10:00:00Z",
        ob_low=2340.0,
        ob_high=2342.0,
        impulse_start=2339.5,  # wick proche pour R:R favorable
        impulse_end=2345.0,
        freshness=OBFreshness.FRESH,
    )


# ------------------------------------------------------------------
# Phase 2 — Technique
# ------------------------------------------------------------------

def test_technical_pipeline_ob_fvg_scoring() -> None:
    """Pipeline technique : donnees -> OB -> FVG -> scoring."""
    data = _make_ohlcv_data()
    ob = _make_ob("LONG")
    fvg = FairValueGap(type=FVGType.BULLISH, index=1, timestamp="2024-01-01T10:05:00Z", fvg_low=2342.5, fvg_high=2343.5, gap_size=1.0)
    pool = LiquidityPool(type="PSYCH", price=2375.0, label="niveau", strength=2.0)

    scorer = TechnicalScorer()
    score, grade = scorer.calculate_total(
        direction="LONG",
        h1_trend=Trend.BULLISH,
        h4_trend=Trend.BULLISH,
        has_bos=True,
        ob=ob,
        fvgs=[fvg],
        pools=[pool],
    )

    assert score >= 3.0
    assert grade in ("A+", "A", "B")


# ------------------------------------------------------------------
# Phase 3 — Macro
# ------------------------------------------------------------------

def test_macro_pipeline_snapshot_to_score() -> None:
    """Pipeline macro : snapshot -> scoring -> locks."""
    snapshot = MacroSnapshot(
        dxy_momentum_pct=-0.3,
        dxy_trend="DOWN",
        tips_10y_value=0.5,
        tips_10y_trend="DOWN",
        upcoming_events=[],
    )

    scorer = MacroScorer()
    score = scorer.calculate_total(snapshot)

    assert -3.0 <= score.total <= 3.0
    assert score.grade in ("VENT HAUSSIER PARFAIT", "VENT HAUSSIER MODERE", "POUSSEE HAUSSIERE", "NEUTRE")

    locks = MacroLockDetector()
    active = locks.get_active_locks(dxy_change_pct=-0.3, yield_change_bps=0.0)
    assert isinstance(active, list)


# ------------------------------------------------------------------
# Phase 4 — Sentiment
# ------------------------------------------------------------------

def test_sentiment_pipeline_full() -> None:
    """Pipeline sentiment : COT + Retail + FearGreed -> score."""
    scorer = SentimentScorer()
    snapshot = SentimentSnapshot(
        cot=COTRecord(
            comm_long=700_000,
            comm_short=200_000,
            is_historic_extreme=False,
            extreme_type="NONE",
        ),
        retail=RetailRatio(long_pct=25, short_pct=75),
        fear_greed=FearGreedIndex(value=20, classification="Fear"),
    )

    score = scorer.calculate_total(snapshot)
    assert score.total > 0  # Haussier (fear + commercial long)
    assert score.cot_signal > 0
    assert score.retail_signal > 0
    assert score.fear_greed_signal > 0


# ------------------------------------------------------------------
# Phase 5 — Fusion
# ------------------------------------------------------------------

def test_fusion_pipeline_macro_tech_to_signal() -> None:
    """Pipeline fusion : macro + tech + timing -> grade -> signal."""
    from modules.macro.scorer import MacroScore

    macro = MacroScore(
        total=2.5,
        grade="HAUSSIER",
        dxy_component=0.3,
        yields_component=0.2,
        fed_component=0.1,
        risk_component=0.0,
        inflation_component=0.1,
        justification="mock",
    )
    setup = TechnicalSetup(
        direction="LONG",
        entry_zone=(2340.0, 2342.0),
        sl_zone=(2338.0, 2339.0),
        tp_zones=[(2350.0, 2351.0)],
        ob=_make_ob("LONG"),
        score=5.0,
        grade="A+",
    )

    fusion_scorer = FusionScorer()
    fusion = fusion_scorer.calculate_total(macro, setup, timing_score=2.0)

    assert fusion.grade == "A+"
    assert fusion.total >= 3.5

    generator = SignalGenerator()
    pools = [LiquidityPool(type="PSYCH", price=2375.0, label="niveau", strength=2.0)]
    plan = generator.generate(setup, fusion, pools=pools, fvgs=[])

    assert plan is not None
    assert plan.direction == "LONG"
    assert plan.rr_ratio >= 2.0
    assert plan.sl_distance_dollars >= 15.0
    assert plan.sl_distance_pips == plan.sl_distance_dollars * 100


def test_fusion_pipeline_with_sentiment_exception() -> None:
    """Pipeline fusion avec exception sentiment contre-trend."""
    from modules.macro.scorer import MacroScore
    from modules.sentiment.scorer import SentimentScore

    macro = MacroScore(
        total=2.5, grade="HAUSSIER",
        dxy_component=0.3, yields_component=0.2, fed_component=0.1,
        risk_component=0.0, inflation_component=0.1, justification="mock",
    )
    setup = TechnicalSetup(
        direction="SHORT",
        entry_zone=(2340.0, 2342.0),
        sl_zone=(2343.0, 2344.0),
        tp_zones=[(2330.0, 2331.0)],
        ob=_make_ob("SHORT"),
        score=5.0,
        grade="A+",
    )
    sentiment = SentimentScore(
        total=-2.0, grade="EXTREME GREED",
        cot_signal=-0.8, retail_signal=-0.8, fear_greed_signal=-0.4,
        justification="mock",
    )

    fusion_scorer = FusionScorer()
    fusion = fusion_scorer.calculate_total(macro, setup, timing_score=2.0, sentiment=sentiment)

    assert fusion.is_exception is True
    assert fusion.grade == "A+"


# ------------------------------------------------------------------
# End-to-End complet
# ------------------------------------------------------------------

def test_end_to_end_full_pipeline() -> None:
    """Pipeline E2E complet : donnees brutes -> signal genere."""
    data = _make_ohlcv_data()
    ob = _make_ob("LONG")
    fvg = FairValueGap(type=FVGType.BULLISH, index=1, timestamp="2024-01-01T10:05:00Z", fvg_low=2342.5, fvg_high=2343.5, gap_size=1.0)
    pool = LiquidityPool(type="PSYCH", price=2375.0, label="niveau", strength=2.0)

    # Phase 2 : Technique
    tech_scorer = TechnicalScorer()
    tech_score, tech_grade = tech_scorer.calculate_total(
        direction="LONG",
        h1_trend=Trend.BULLISH,
        h4_trend=Trend.BULLISH,
        has_bos=True,
        ob=ob,
        fvgs=[fvg],
        pools=[pool],
    )
    setup = TechnicalSetup(
        direction="LONG",
        entry_zone=ob.zone(),
        sl_zone=(ob.ob_low * 0.999, ob.ob_low),
        tp_zones=[(pool.price, pool.price + 2.0)],
        ob=ob,
        score=tech_score,
        grade=tech_grade,
        timeframe="M15",
    )

    # Phase 3 : Macro
    macro_snapshot = MacroSnapshot(
        dxy_momentum_pct=-0.2,
        dxy_trend="DOWN",
        tips_10y_value=0.8,
        tips_10y_trend="DOWN",
        upcoming_events=[],
    )
    macro_scorer = MacroScorer()
    macro_score = macro_scorer.calculate_total(macro_snapshot)
    # Forcer un macro aligned pour valider la matrice en E2E
    macro_score = MacroScore(
        total=2.0,
        grade="POUSSEE HAUSSIERE",
        dxy_component=macro_score.dxy_component,
        yields_component=macro_score.yields_component,
        fed_component=macro_score.fed_component,
        risk_component=macro_score.risk_component,
        inflation_component=macro_score.inflation_component,
        justification=macro_score.justification,
    )

    # Phase 4 : Sentiment
    sentiment_snapshot = SentimentSnapshot(
        cot=COTRecord(comm_long=600_000, comm_short=300_000),
        retail=RetailRatio(long_pct=30, short_pct=70),
        fear_greed=FearGreedIndex(value=25, classification="Fear"),
    )
    sentiment_scorer = SentimentScorer()
    sentiment_score = sentiment_scorer.calculate_total(sentiment_snapshot)

    # Phase 5 : Fusion
    fusion_scorer = FusionScorer()
    fusion = fusion_scorer.calculate_total(
        macro_score, setup, timing_score=2.0, sentiment=sentiment_score
    )

    assert fusion.grade in ("A+", "B")

    generator = SignalGenerator()
    plan = generator.generate(setup, fusion, pools=[pool], fvgs=[])

    assert plan is not None
    assert plan.signal_id.startswith("SIG-")
    assert plan.direction == "LONG"
    assert plan.rr_ratio >= 2.0
    assert plan.invalidation_price == ob.ob_low
    assert plan.expiration_minutes == 45


if __name__ == "__main__":
    test_technical_pipeline_ob_fvg_scoring()
    test_macro_pipeline_snapshot_to_score()
    test_sentiment_pipeline_full()
    test_fusion_pipeline_macro_tech_to_signal()
    test_fusion_pipeline_with_sentiment_exception()
    test_end_to_end_full_pipeline()
    print("[OK] Tests integration Phases 2-5 (Modules Pipeline) passes.")
