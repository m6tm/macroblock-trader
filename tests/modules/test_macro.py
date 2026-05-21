"""Tests de validation Phase 3 — Module Macro."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from data.calendar import EconomicEvent
from modules.macro.core import MacroSnapshot
from modules.macro.locks import MacroLock, MacroLockDetector
from modules.macro.scorer import MacroScorer


def test_scorer_dxy_bullish() -> None:
    """DXY en baisse = vent haussier pour l'or."""
    scorer = MacroScorer()
    snap = MacroSnapshot(
        dxy_momentum_pct=-0.35,
        dxy_trend="DOWN",
        tips_10y_value=None,
        upcoming_events=[],
    )
    score = scorer.calculate_total(snap)
    assert score.total > 0
    assert score.dxy_component > 0


def test_scorer_dxy_bearish() -> None:
    """DXY en hausse = vent baissier pour l'or."""
    scorer = MacroScorer()
    snap = MacroSnapshot(
        dxy_momentum_pct=0.35,
        dxy_trend="UP",
        tips_10y_value=None,
        upcoming_events=[],
    )
    score = scorer.calculate_total(snap)
    assert score.total < 0
    assert score.dxy_component < 0


def test_scorer_tips_high() -> None:
    """TIPS > 2% et monte = baissier."""
    scorer = MacroScorer()
    snap = MacroSnapshot(
        dxy_momentum_pct=0.0,
        dxy_trend="NEUTRAL",
        tips_10y_value=2.5,
        tips_10y_trend="UP",
        upcoming_events=[],
    )
    score = scorer.calculate_total(snap)
    assert score.yields_component < 0


def test_scorer_tips_negative() -> None:
    """TIPS negatif = tres haussier."""
    scorer = MacroScorer()
    snap = MacroSnapshot(
        dxy_momentum_pct=0.0,
        dxy_trend="NEUTRAL",
        tips_10y_value=-0.5,
        tips_10y_trend="DOWN",
        upcoming_events=[],
    )
    score = scorer.calculate_total(snap)
    assert score.yields_component > 0


def test_scorer_fed_hawkish() -> None:
    """Evenement hawkish = baissier."""
    scorer = MacroScorer()
    events = [
        EconomicEvent(
            title="Fed Rate Hike",
            currency="USD",
            date="2024-01-01",
            time="14:00",
            impact="High",
        )
    ]
    snap = MacroSnapshot(
        dxy_momentum_pct=0.0,
        dxy_trend="NEUTRAL",
        tips_10y_value=None,
        upcoming_events=events,
    )
    score = scorer.calculate_total(snap)
    assert score.fed_component <= 0


def test_scorer_fed_dovish() -> None:
    """Evenement dovish = haussier."""
    scorer = MacroScorer()
    events = [
        EconomicEvent(
            title="Fed Rate Cut",
            currency="USD",
            date="2024-01-01",
            time="14:00",
            impact="High",
        )
    ]
    snap = MacroSnapshot(
        dxy_momentum_pct=0.0,
        dxy_trend="NEUTRAL",
        tips_10y_value=None,
        upcoming_events=events,
    )
    score = scorer.calculate_total(snap)
    assert score.fed_component >= 0


def test_scorer_inflation_surprise() -> None:
    """CPI au-dessus des attentes = haussier."""
    scorer = MacroScorer()
    events = [
        EconomicEvent(
            title="CPI m/m",
            currency="USD",
            date="2024-01-01",
            time="14:00",
            impact="High",
            forecast="0.1%",
            actual="0.5%",
        )
    ]
    snap = MacroSnapshot(
        dxy_momentum_pct=0.0,
        dxy_trend="NEUTRAL",
        tips_10y_value=None,
        upcoming_events=events,
    )
    score = scorer.calculate_total(snap)
    assert score.inflation_component > 0


def test_scorer_boundaries() -> None:
    """Le score reste entre -3 et +3."""
    scorer = MacroScorer()
    snap = MacroSnapshot(
        dxy_momentum_pct=-0.5,
        dxy_trend="DOWN",
        tips_10y_value=-0.5,
        tips_10y_trend="DOWN",
        upcoming_events=[],
    )
    score = scorer.calculate_total(snap)
    assert -3.0 <= score.total <= 3.0


def test_lock_fomc() -> None:
    """Un evenement FOMC dans 30 min declenche un lock."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch, MagicMock

    detector = MacroLockDetector()
    future_event = EconomicEvent(
        title="FOMC Statement",
        currency="USD",
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        time=(datetime.now(timezone.utc) + timedelta(minutes=15)).strftime("%H:%M"),
        impact="High",
    )

    with patch.object(detector.calendar, "get_high_impact_events", return_value=[future_event]):
        lock = detector.check_fomc_lock()
        assert lock is not None
        assert lock.name == "FOMC_LOCK"
        assert lock.severity == "CRITICAL"


def test_lock_dxy_spike() -> None:
    """Un spike DXY > 0.2% declenche un lock."""
    detector = MacroLockDetector()
    lock = detector.check_dxy_spike_lock(dxy_change_pct=0.25)
    assert lock is not None
    assert lock.name == "DXY_SPIKE_LOCK"


def test_no_lock_normal_conditions() -> None:
    """Sans evenements ni spikes, aucun lock."""
    from unittest.mock import patch

    detector = MacroLockDetector()
    with patch.object(detector.calendar, "get_high_impact_events", return_value=[]):
        locks = detector.get_active_locks(dxy_change_pct=0.05, yield_change_bps=0.01)
        assert len(locks) == 0


def test_lock_list_contains_reasons() -> None:
    """Les locks contiennent une raison explicable."""
    detector = MacroLockDetector()
    lock = detector.check_dxy_spike_lock(0.3)
    assert lock is not None
    assert "DXY" in lock.reason
    assert lock.active_until is not None


if __name__ == "__main__":
    test_scorer_dxy_bullish()
    test_scorer_dxy_bearish()
    test_scorer_tips_high()
    test_scorer_tips_negative()
    test_scorer_fed_hawkish()
    test_scorer_fed_dovish()
    test_scorer_inflation_surprise()
    test_scorer_boundaries()
    test_lock_fomc()
    test_lock_dxy_spike()
    test_no_lock_normal_conditions()
    test_lock_list_contains_reasons()
    print("[OK] Tous les tests Phase 3 ont passe.")
