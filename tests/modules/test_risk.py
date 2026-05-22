"""Tests Phase 6 — Module Risk (sizing, validation, locks, engine)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from modules.risk.sizing import SizingCalculator
from modules.risk.validator import RiskValidator, ValidationResult
from modules.risk.locks import RiskLockChecker
from modules.risk.engine import RiskEngine


# ------------------------------------------------------------------
# Sizing
# ------------------------------------------------------------------

def test_sizing_a_plus() -> None:
    calc = SizingCalculator()
    result = calc.calculate(capital=10_000, risk_pct=1.0, sl_distance_dollars=35.0, grade="A+")
    assert result.is_realistic is True
    assert result.position_size_lots == 100.0 / 35.0  # ~2.86 lots
    assert result.risk_amount_dollars == 100.0
    assert result.risk_pct == 1.0


def test_sizing_b() -> None:
    calc = SizingCalculator()
    result = calc.calculate(capital=10_000, risk_pct=0.5, sl_distance_dollars=35.0, grade="B")
    assert result.is_realistic is True
    assert result.risk_amount_dollars == 50.0
    assert result.risk_pct == 0.5


def test_sizing_too_large() -> None:
    calc = SizingCalculator()
    # SL tres petit → lots enormes
    result = calc.calculate(capital=100_000, risk_pct=1.0, sl_distance_dollars=5.0, grade="A+")
    assert result.is_realistic is False
    assert "over-leverage" in result.reason


def test_sizing_zero_sl() -> None:
    calc = SizingCalculator()
    result = calc.calculate(capital=10_000, risk_pct=1.0, sl_distance_dollars=0.0, grade="A+")
    assert result.is_realistic is False


# ------------------------------------------------------------------
# Validator
# ------------------------------------------------------------------

def test_validator_sl_min() -> None:
    v = RiskValidator()
    check = v.validate_sl(sl_distance_dollars=10.0, entry_price=2340.0, sl_min_dollars=15.0, sl_max_pct_price=1.0)
    assert check.passed is False
    assert "SL_MIN" in check.name


def test_validator_sl_max() -> None:
    v = RiskValidator()
    check = v.validate_sl(sl_distance_dollars=50.0, entry_price=2340.0, sl_min_dollars=15.0, sl_max_pct_price=1.0)
    assert check.passed is False
    assert "SL_MAX" in check.name


def test_validator_sl_ok() -> None:
    v = RiskValidator()
    check = v.validate_sl(sl_distance_dollars=20.0, entry_price=2340.0, sl_min_dollars=15.0, sl_max_pct_price=1.0)
    assert check.passed is True


def test_validator_rr_fail() -> None:
    v = RiskValidator()
    check = v.validate_rr(rr_ratio=1.5, rr_minimum=2.0)
    assert check.passed is False


def test_validator_rr_ok() -> None:
    v = RiskValidator()
    check = v.validate_rr(rr_ratio=2.5, rr_minimum=2.0)
    assert check.passed is True


def test_validator_score_fail() -> None:
    v = RiskValidator()
    check = v.validate_score(score_total=2.0, min_signal=2.5)
    assert check.passed is False


def test_validator_full() -> None:
    v = RiskValidator()
    result = v.run_full_validation(
        sl_distance_dollars=20.0,
        entry_price=2340.0,
        rr_ratio=2.5,
        score_total=3.5,
        sl_min_dollars=15.0,
        sl_max_pct_price=1.0,
        rr_minimum=2.0,
    )
    assert result.all_passed is True
    assert len(result.checks) == 4


# ------------------------------------------------------------------
# Locks
# ------------------------------------------------------------------

def test_locks_max_trades() -> None:
    checker = RiskLockChecker()
    reason = checker.check_max_trades(open_trade_count=1, max_allowed=1)
    assert reason is not None
    assert "Max trades" in reason


def test_locks_drawdown_daily() -> None:
    checker = RiskLockChecker()
    reason = checker.check_drawdown_daily(drawdown_pct=2.5, limit_pct=2.0)
    assert reason is not None
    assert "Drawdown journalier" in reason


def test_locks_weekend_gap() -> None:
    from datetime import datetime, timezone
    checker = RiskLockChecker()
    # Samedi
    dt = datetime(2024, 1, 6, 12, 0, tzinfo=timezone.utc)
    reason = checker.check_weekend_gap(enabled=True, dt=dt)
    assert reason is not None
    assert "Weekend" in reason


def test_locks_weekend_gap_disabled() -> None:
    checker = RiskLockChecker()
    reason = checker.check_weekend_gap(enabled=False)
    assert reason is None


def test_locks_all_pass() -> None:
    checker = RiskLockChecker()
    status = checker.run_all_checks(
        open_trade_count=0,
        max_trades=1,
        drawdown_daily_pct=0.0,
        drawdown_weekly_pct=0.0,
        dd_daily_limit=2.0,
        dd_weekly_limit=4.0,
        weekend_lock_enabled=True,
    )
    assert status.locked is False


# ------------------------------------------------------------------
# Engine
# ------------------------------------------------------------------

def test_engine_full_check_pass() -> None:
    from modules.fusion.generator import TradePlan
    engine = RiskEngine()
    plan = TradePlan(
        signal_id="SIG-TEST",
        direction="LONG",
        grade="A+",
        score_total=4.0,
        preferred_entry=2500.0,
        sl_distance_dollars=20.0,
        rr_ratio=2.5,
    )
    result = engine.check_trade(plan, grade="A+")
    assert result.authorized is True
    assert result.sizing is not None
    assert result.sizing.position_size_lots > 0


def test_engine_full_check_fail_rr() -> None:
    from modules.fusion.generator import TradePlan
    engine = RiskEngine()
    plan = TradePlan(
        signal_id="SIG-TEST",
        direction="LONG",
        grade="B",
        score_total=3.0,
        preferred_entry=2500.0,
        sl_distance_dollars=20.0,
        rr_ratio=1.5,
    )
    result = engine.check_trade(plan, grade="B")
    assert result.authorized is False
    assert "R_R_MINIMUM" in result.reason


if __name__ == "__main__":
    test_sizing_a_plus()
    test_sizing_b()
    test_sizing_too_large()
    test_sizing_zero_sl()
    test_validator_sl_min()
    test_validator_sl_max()
    test_validator_sl_ok()
    test_validator_rr_fail()
    test_validator_rr_ok()
    test_validator_score_fail()
    test_validator_full()
    test_locks_max_trades()
    test_locks_drawdown_daily()
    test_locks_weekend_gap()
    test_locks_weekend_gap_disabled()
    test_locks_all_pass()
    test_engine_full_check_pass()
    test_engine_full_check_fail_rr()
    print("[OK] Tous les tests Phase 6 (Risk) ont passe.")
