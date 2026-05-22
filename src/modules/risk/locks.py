"""Locks de risque — conditions qui bloquent tout signal."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import List, Optional

from loguru import logger


@dataclass
class LockStatus:
    """Etat des locks de risque."""

    locked: bool = False
    reasons: List[str] = field(default_factory=list)

    def add(self, reason: str) -> None:
        self.locked = True
        self.reasons.append(reason)


class RiskLockChecker:
    """Verifie les locks de risque avant emission d'un signal."""

    def check_max_trades(
        self,
        open_trade_count: int,
        max_allowed: int,
    ) -> Optional[str]:
        """Bloque si trop de trades ouverts."""
        if open_trade_count >= max_allowed:
            return f"Max trades atteint ({open_trade_count}/{max_allowed})"
        return None

    def check_drawdown_daily(
        self,
        drawdown_pct: float,
        limit_pct: float,
    ) -> Optional[str]:
        """Bloque si drawdown journalier depasse."""
        if drawdown_pct >= limit_pct:
            return f"Drawdown journalier {drawdown_pct:.2f}% >= limite {limit_pct}%"
        return None

    def check_drawdown_weekly(
        self,
        drawdown_pct: float,
        limit_pct: float,
    ) -> Optional[str]:
        """Bloque si drawdown hebdomadaire depasse."""
        if drawdown_pct >= limit_pct:
            return f"Drawdown hebdomadaire {drawdown_pct:.2f}% >= limite {limit_pct}%"
        return None

    def check_weekend_gap(
        self,
        enabled: bool = True,
        dt: Optional[datetime] = None,
    ) -> Optional[str]:
        """Bloque les signaux pendant le weekend (vendredi soir → dimanche cloture H1).

        Conserve le dimanche soir apres cloture H1 pour le gap possible.
        """
        if not enabled:
            return None
        if dt is None:
            dt = datetime.now(timezone.utc)

        weekday = dt.weekday()  # 0=Lundi, 6=Dimanche
        if weekday == 4:  # Vendredi
            # Apres 21h UTC = marche ferme
            if dt.time() >= time(21, 0):
                return "Weekend gap lock — marche ferme (Vendredi > 21h UTC)"
        elif weekday == 5:  # Samedi
            return "Weekend gap lock — marche ferme (Samedi)"
        elif weekday == 6:  # Dimanche
            # Avant 21h UTC = marche encore ferme (ouverture FX a 21h/22h)
            if dt.time() < time(21, 0):
                return "Weekend gap lock — marche ferme (Dimanche < 21h UTC)"
        return None

    def run_all_checks(
        self,
        open_trade_count: int,
        max_trades: int,
        drawdown_daily_pct: float,
        drawdown_weekly_pct: float,
        dd_daily_limit: float,
        dd_weekly_limit: float,
        weekend_lock_enabled: bool = True,
        dt: Optional[datetime] = None,
    ) -> LockStatus:
        """Execute tous les checks de lock et retourne le statut."""
        status = LockStatus()

        reason = self.check_max_trades(open_trade_count, max_trades)
        if reason:
            status.add(reason)

        reason = self.check_drawdown_daily(drawdown_daily_pct, dd_daily_limit)
        if reason:
            status.add(reason)

        reason = self.check_drawdown_weekly(drawdown_weekly_pct, dd_weekly_limit)
        if reason:
            status.add(reason)

        reason = self.check_weekend_gap(weekend_lock_enabled, dt)
        if reason:
            status.add(reason)

        if status.locked:
            logger.warning(f"Risk locks actifs : {status.reasons}")
        return status
