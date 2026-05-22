"""Moteur de risque — orchestre sizing, validation et locks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from core.config import Settings
from modules.journal.database import JournalDatabase
from modules.journal.queries import JournalQueries
from modules.risk.locks import RiskLockChecker
from modules.risk.sizing import SizingCalculator, SizingResult
from modules.risk.validator import RiskValidator, ValidationResult


@dataclass
class RiskCheckResult:
    """Resultat complet du check risque."""

    authorized: bool
    reason: str
    sizing: Optional[SizingResult] = None
    validation: Optional[ValidationResult] = None


class RiskEngine:
    """Moteur central de gestion du risque.

    Usage :
        engine = RiskEngine(settings)
        result = engine.check_trade(plan, grade="A+")
        if result.authorized:
            plan.position_size_lots = result.sizing.position_size_lots
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        db: Optional[JournalDatabase] = None,
    ) -> None:
        self.settings = settings or Settings()
        self.db = db
        self.queries = JournalQueries(db) if db else None
        self.validator = RiskValidator()
        self.lock_checker = RiskLockChecker()
        self.sizing_calc = SizingCalculator()

    def check_trade(
        self,
        plan,
        grade: str,
    ) -> RiskCheckResult:
        """Execute la checklist complete risque avant autorisation.

        Args:
            plan: TradePlan genere
            grade: Grade du signal (A+, B, etc.)

        Returns:
            RiskCheckResult avec authorized, reason, sizing.
        """
        # 1. Locks de risque (max trades, drawdown, weekend)
        open_count = 0
        dd_daily = 0.0
        dd_weekly = 0.0
        if self.queries:
            open_count = self.queries.get_open_trade_count()
            dd_daily = self.queries.get_drawdown_today_pct(
                self.settings.risk.capital_virtual
            )
            dd_weekly = self.queries.get_drawdown_week_pct(
                self.settings.risk.capital_virtual
            )

        lock_status = self.lock_checker.run_all_checks(
            open_trade_count=open_count,
            max_trades=self.settings.risk.max_trades_open,
            drawdown_daily_pct=dd_daily,
            drawdown_weekly_pct=dd_weekly,
            dd_daily_limit=self.settings.risk.drawdown_daily_pct,
            dd_weekly_limit=self.settings.risk.drawdown_weekly_pct,
            weekend_lock_enabled=self.settings.risk.weekend_gap_lock,
        )
        if lock_status.locked:
            return RiskCheckResult(
                authorized=False,
                reason="; ".join(lock_status.reasons),
            )

        # 2. Validation SL / R:R / Score
        validation = self.validator.run_full_validation(
            sl_distance_dollars=plan.sl_distance_dollars,
            entry_price=plan.preferred_entry,
            rr_ratio=plan.rr_ratio,
            score_total=plan.score_total,
            sl_min_dollars=self.settings.trading.sl_min_dollars,
            sl_max_pct_price=self.settings.trading.sl_max_pct_price,
            rr_minimum=self.settings.trading.rr_minimum,
        )
        if not validation.all_passed:
            failed = validation.failed_checks
            return RiskCheckResult(
                authorized=False,
                reason="; ".join(f"{c.name}: {c.reason}" for c in failed),
                validation=validation,
            )

        # 3. Sizing
        risk_pct = self.sizing_calc.get_risk_pct_for_grade(
            grade,
            self.settings.risk.risk_pct_a_plus,
            self.settings.risk.risk_pct_b,
        )
        sizing = self.sizing_calc.calculate(
            capital=self.settings.risk.capital_virtual,
            risk_pct=risk_pct,
            sl_distance_dollars=plan.sl_distance_dollars,
            grade=grade,
        )
        if not sizing.is_realistic:
            return RiskCheckResult(
                authorized=False,
                reason=f"Sizing invalide: {sizing.reason}",
                validation=validation,
            )

        logger.success(
            f"Risk check PASSE | Grade {grade} | Risk {risk_pct}% | "
            f"Lots {sizing.position_size_lots:.2f} | "
            f"Trades ouverts {open_count}/{self.settings.risk.max_trades_open}"
        )
        return RiskCheckResult(
            authorized=True,
            reason="All checks passed",
            sizing=sizing,
            validation=validation,
        )
