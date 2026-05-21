"""Tests de validation Phase 2 — Module Technique SMC."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from data.compat import make_ohlcv_data
from modules.technical.core import (
    Trend,
    detect_bos_choch,
    detect_swing_highs_lows,
    get_trend,
)
from modules.technical.fvg import (
    detect_bearish_fvg,
    detect_bullish_fvg,
    fvg_ob_confluence,
)
from modules.technical.liquidity import (
    detect_equal_highs,
    detect_equal_lows,
    detect_psychological_levels,
    get_current_killzone,
)
from modules.technical.ob import (
    OBFreshness,
    OBType,
    calculate_freshness,
    detect_bearish_ob,
    detect_bullish_ob,
    filter_valid_obs,
)
from modules.technical.scorer import TechnicalScorer


def _make_trending_data(direction: str, n: int = 30) -> list:
    """Genere des candles synthetiques avec une tendance claire et des swings."""
    from datetime import datetime, timezone
    candles = []
    base = 4500.0
    for i in range(n):
        # Creer des oscillations pour generer des swings
        wave = 10 * (1 if i % 4 < 2 else -1)
        if direction == "UP":
            drift = i * 3
        else:
            drift = -i * 3
        o = base + drift + wave
        c = o + (2 if wave > 0 else -2)
        h = max(o, c) + 2
        l = min(o, c) - 2
        ts = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        ts = ts.replace(hour=i % 24, minute=(i // 24) * 5)
        candles.append(
            {
                "time": ts.isoformat(),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": 100,
            }
        )
    return candles


def _make_ob_bullish_fixture() -> list:
    """Candles avec un bullish OB clair a l'index 1 (jamais mitigue)."""
    return [
        {"time": "2024-01-01T10:00:00Z", "open": 4500, "high": 4502, "low": 4498, "close": 4501, "volume": 100},
        {"time": "2024-01-01T10:05:00Z", "open": 4501, "high": 4503, "low": 4500, "close": 4500, "volume": 100},  # OB candidat [4500, 4503]
        {"time": "2024-01-01T10:10:00Z", "open": 4504, "high": 4506, "low": 4504, "close": 4505, "volume": 100},  # low=4504 > ob_high=4503 → pas de mitigation
        {"time": "2024-01-01T10:15:00Z", "open": 4505, "high": 4520, "low": 4504, "close": 4518, "volume": 100},  # impulsion +18$
        {"time": "2024-01-01T10:20:00Z", "open": 4518, "high": 4522, "low": 4517, "close": 4521, "volume": 100},
    ]


def _make_ob_bearish_fixture() -> list:
    """Candles avec un bearish OB clair a l'index 2."""
    return [
        {"time": "2024-01-01T10:00:00Z", "open": 4520, "high": 4522, "low": 4518, "close": 4519, "volume": 100},
        {"time": "2024-01-01T10:05:00Z", "open": 4519, "high": 4521, "low": 4517, "close": 4520, "volume": 100},  # OB candidat (haussiere)
        {"time": "2024-01-01T10:10:00Z", "open": 4520, "high": 4522, "low": 4515, "close": 4516, "volume": 100},
        {"time": "2024-01-01T10:15:00Z", "open": 4516, "high": 4517, "low": 4500, "close": 4502, "volume": 100},  # impulsion -18$
        {"time": "2024-01-01T10:20:00Z", "open": 4502, "high": 4503, "low": 4499, "close": 4501, "volume": 100},
    ]


def _make_fvg_fixture() -> list:
    """Candles avec un bullish FVG clair (low[2] > high[0])."""
    return [
        {"time": "2024-01-01T10:00:00Z", "open": 4500, "high": 4502, "low": 4498, "close": 4501, "volume": 100},
        {"time": "2024-01-01T10:05:00Z", "open": 4501, "high": 4503, "low": 4500, "close": 4502, "volume": 100},
        {"time": "2024-01-01T10:10:00Z", "open": 4510, "high": 4512, "low": 4508, "close": 4511, "volume": 100},  # gap
    ]


# ------------------------------------------------------------------
# Tests Structure
# ------------------------------------------------------------------

def test_detect_swing_highs_lows() -> None:
    candles = _make_trending_data("UP", n=20)
    data = make_ohlcv_data(candles, "XAU/USD", "H1")
    highs, lows = detect_swing_highs_lows(data, lookback=2)
    assert len(highs) > 0
    assert len(lows) > 0
    assert all(h.type == "high" for h in highs)
    assert all(l.type == "low" for l in lows)


def test_get_trend_bullish() -> None:
    candles = _make_trending_data("UP", n=30)
    data = make_ohlcv_data(candles, "XAU/USD", "H1")
    assert get_trend(data, lookback=2) == Trend.BULLISH


def test_get_trend_bearish() -> None:
    candles = _make_trending_data("DOWN", n=30)
    data = make_ohlcv_data(candles, "XAU/USD", "H1")
    assert get_trend(data, lookback=2) == Trend.BEARISH


def test_detect_bos_choch() -> None:
    candles = _make_trending_data("UP", n=30)
    data = make_ohlcv_data(candles, "XAU/USD", "H1")
    highs, lows = detect_swing_highs_lows(data, lookback=2)
    events = detect_bos_choch(data, highs, lows)
    assert len(events) > 0
    assert all(e.type in ("BOS", "CHoCH") for e in events)


# ------------------------------------------------------------------
# Tests Order Blocks
# ------------------------------------------------------------------

def test_detect_bullish_ob() -> None:
    candles = _make_ob_bullish_fixture()
    data = make_ohlcv_data(candles, "XAU/USD", "M5")
    obs = detect_bullish_ob(data, impulsion_threshold=10.0, lookback_impulse=3)
    assert len(obs) >= 1
    ob = obs[0]
    assert ob.type == OBType.BULLISH
    assert ob.ob_low == 4500
    assert ob.ob_high == 4503


def test_detect_bearish_ob() -> None:
    candles = _make_ob_bearish_fixture()
    data = make_ohlcv_data(candles, "XAU/USD", "M5")
    obs = detect_bearish_ob(data, impulsion_threshold=10.0, lookback_impulse=3)
    assert len(obs) >= 1
    ob = obs[0]
    assert ob.type == OBType.BEARISH


def test_ob_freshness() -> None:
    candles = _make_ob_bullish_fixture()
    data = make_ohlcv_data(candles, "XAU/USD", "M5")
    obs = detect_bullish_ob(data, impulsion_threshold=10.0)
    ob = calculate_freshness(obs[0], data, mitigation_threshold=0.5)
    assert ob.freshness == OBFreshness.FRESH


def test_filter_valid_obs() -> None:
    candles = _make_ob_bullish_fixture()
    data = make_ohlcv_data(candles, "XAU/USD", "M5")
    obs = detect_bullish_ob(data, impulsion_threshold=10.0)
    valid = filter_valid_obs(obs, data, mitigation_threshold=0.5)
    assert len(valid) >= 1


# ------------------------------------------------------------------
# Tests FVG
# ------------------------------------------------------------------

def test_detect_bullish_fvg() -> None:
    candles = _make_fvg_fixture()
    data = make_ohlcv_data(candles, "XAU/USD", "M5")
    fvgs = detect_bullish_fvg(data)
    assert len(fvgs) == 1
    assert fvgs[0].fvg_low == 4502
    assert fvgs[0].fvg_high == 4508


def test_detect_bearish_fvg() -> None:
    # Inverse le fixture pour un bearish FVG
    candles = [
        {"time": "2024-01-01T10:00:00Z", "open": 4510, "high": 4512, "low": 4508, "close": 4511, "volume": 100},
        {"time": "2024-01-01T10:05:00Z", "open": 4511, "high": 4513, "low": 4509, "close": 4510, "volume": 100},
        {"time": "2024-01-01T10:10:00Z", "open": 4500, "high": 4502, "low": 4498, "close": 4501, "volume": 100},
    ]
    data = make_ohlcv_data(candles, "XAU/USD", "M5")
    fvgs = detect_bearish_fvg(data)
    assert len(fvgs) == 1


def test_fvg_ob_confluence() -> None:
    from modules.technical.fvg import FairValueGap, FVGType
    fvg = FairValueGap(
        type=FVGType.BULLISH, index=0, timestamp="t",
        fvg_low=4500, fvg_high=4505, gap_size=5,
    )
    assert fvg_ob_confluence(fvg, 4498, 4503) is True
    assert fvg_ob_confluence(fvg, 4510, 4515, max_distance=3) is False


# ------------------------------------------------------------------
# Tests Liquidite
# ------------------------------------------------------------------

def test_detect_equal_highs() -> None:
    candles = [
        {"time": "2024-01-01T10:00:00Z", "open": 4500, "high": 4510, "low": 4498, "close": 4505, "volume": 100},
        {"time": "2024-01-01T10:05:00Z", "open": 4505, "high": 4508, "low": 4500, "close": 4502, "volume": 100},
        {"time": "2024-01-01T10:10:00Z", "open": 4502, "high": 4510.1, "low": 4500, "close": 4508, "volume": 100},
    ]
    data = make_ohlcv_data(candles, "XAU/USD", "M5")
    eqh = detect_equal_highs(data, tolerance=0.15, min_candles_between=1)
    assert len(eqh) >= 1


def test_detect_psychological_levels() -> None:
    pools = detect_psychological_levels(4513.0, range_around=50, step=50)
    prices = [p.price for p in pools]
    assert 4500 in prices
    assert 4550 in prices


# ------------------------------------------------------------------
# Tests Scoring
# ------------------------------------------------------------------

def test_scorer_max() -> None:
    scorer = TechnicalScorer()
    score, grade = scorer.calculate_total(
        direction="LONG",
        h1_trend=Trend.BULLISH,
        h4_trend=Trend.BULLISH,
        has_bos=True,
        ob=None,
        fvgs=[],
        pools=[],
    )
    # structure(1) + bos(1) + killzone(0 ou 0.5)
    assert score in (2.0, 2.5)


def test_scorer_min() -> None:
    scorer = TechnicalScorer()
    score, grade = scorer.calculate_total(
        direction="LONG",
        h1_trend=Trend.BEARISH,
        h4_trend=Trend.BEARISH,
        has_bos=False,
        ob=None,
        fvgs=[],
        pools=[],
    )
    assert score < 3.0
    assert grade == "F"


if __name__ == "__main__":
    test_detect_swing_highs_lows()
    test_get_trend_bullish()
    test_get_trend_bearish()
    test_detect_bos_choch()
    test_detect_bullish_ob()
    test_detect_bearish_ob()
    test_ob_freshness()
    test_filter_valid_obs()
    test_detect_bullish_fvg()
    test_detect_bearish_fvg()
    test_fvg_ob_confluence()
    test_detect_equal_highs()
    test_detect_psychological_levels()
    test_scorer_max()
    test_scorer_min()
    print("[OK] Tous les tests Phase 2 ont passe.")
