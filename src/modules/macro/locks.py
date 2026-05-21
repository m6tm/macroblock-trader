"""Macro Locks — Fenêtres de blocage temporaires pour éviter les pièges de news.

Le module publie des locks qui interdisent tout nouveau signal pendant
les periodes a haut risque (FOMC, NFP, CPI, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from loguru import logger

from data.calendar import EconomicCalendar, EconomicEvent


@dataclass
class MacroLock:
    name: str
    reason: str
    active_until: datetime
    severity: str  # "CRITICAL" | "HIGH" | "MEDIUM"


class MacroLockDetector:
    """Detecte les periodes de blocage macro actives."""

    def __init__(self, calendar: Optional[EconomicCalendar] = None) -> None:
        self.calendar = calendar or EconomicCalendar()

    def _parse_event_dt(self, event: EconomicEvent) -> Optional[datetime]:
        """Convertit un EconomicEvent en datetime UTC."""
        try:
            dt = datetime.strptime(
                f"{event.date} {event.time}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def check_fomc_lock(self) -> Optional[MacroLock]:
        """FOMC: 30 min avant → 1h apres."""
        events = self.calendar.get_high_impact_events(hours_ahead=2)
        for e in events:
            if "fomc" in e.title.lower():
                dt = self._parse_event_dt(e)
                if dt is None:
                    continue
                now = datetime.now(timezone.utc)
                if (dt - timedelta(minutes=30)) <= now <= (dt + timedelta(hours=1)):
                    return MacroLock(
                        name="FOMC_LOCK",
                        reason=f"FOMC en cours: {e.title}",
                        active_until=dt + timedelta(hours=1),
                        severity="CRITICAL",
                    )
        return None

    def check_nfp_lock(self) -> Optional[MacroLock]:
        """NFP: 15 min avant → 30 min apres."""
        events = self.calendar.get_high_impact_events(hours_ahead=2)
        for e in events:
            if "non-farm" in e.title.lower() or "nfp" in e.title.lower():
                dt = self._parse_event_dt(e)
                if dt is None:
                    continue
                now = datetime.now(timezone.utc)
                if (dt - timedelta(minutes=15)) <= now <= (dt + timedelta(minutes=30)):
                    return MacroLock(
                        name="NFP_LOCK",
                        reason=f"NFP en cours: {e.title}",
                        active_until=dt + timedelta(minutes=30),
                        severity="CRITICAL",
                    )
        return None

    def check_cpi_lock(self) -> Optional[MacroLock]:
        """CPI/PPI: 15 min avant → 30 min apres."""
        events = self.calendar.get_high_impact_events(hours_ahead=2)
        for e in events:
            if any(kw in e.title.lower() for kw in ("cpi", "ppi", "pce")):
                dt = self._parse_event_dt(e)
                if dt is None:
                    continue
                now = datetime.now(timezone.utc)
                if (dt - timedelta(minutes=15)) <= now <= (dt + timedelta(minutes=30)):
                    return MacroLock(
                        name="CPI_LOCK",
                        reason=f"Inflation release: {e.title}",
                        active_until=dt + timedelta(minutes=30),
                        severity="CRITICAL",
                    )
        return None

    def check_london_fix_lock(self) -> Optional[MacroLock]:
        """London Fix AM/PM: 10 min avant → 20 min apres."""
        now = datetime.now(timezone.utc)
        fix_times = [
            (10, 0, "London Fix AM"),
            (15, 0, "London Fix PM"),
        ]
        for hour, minute, name in fix_times:
            fix_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if (fix_dt - timedelta(minutes=10)) <= now <= (fix_dt + timedelta(minutes=20)):
                return MacroLock(
                    name="LONDON_FIX_LOCK",
                    reason=name,
                    active_until=fix_dt + timedelta(minutes=20),
                    severity="HIGH",
                )
        return None

    def check_comex_open_lock(self) -> Optional[MacroLock]:
        """COMEX Open: 13:20 → 13:50 GMT."""
        now = datetime.now(timezone.utc)
        comex_open = now.replace(hour=13, minute=20, second=0, microsecond=0)
        comex_end = now.replace(hour=13, minute=50, second=0, microsecond=0)
        if comex_open <= now <= comex_end:
            return MacroLock(
                name="COMEX_OPEN_LOCK",
                reason="Ouverture futures COMEX",
                active_until=comex_end,
                severity="MEDIUM",
            )
        return None

    def check_dxy_spike_lock(self, dxy_change_pct: float) -> Optional[MacroLock]:
        """Lock si DXY bouge de > 0.2% en 5 min (spike anormal)."""
        if abs(dxy_change_pct) > 0.2:
            direction = "hausse" if dxy_change_pct > 0 else "baisse"
            return MacroLock(
                name="DXY_SPIKE_LOCK",
                reason=f"Spike DXY {direction} {dxy_change_pct:.2f}% en 5 min",
                active_until=datetime.now(timezone.utc) + timedelta(minutes=15),
                severity="HIGH",
            )
        return None

    def check_yield_spike_lock(self, yield_change_bps: float) -> Optional[MacroLock]:
        """Lock si yields bougent de > 5 bps en 5 min."""
        if abs(yield_change_bps) > 0.05:
            direction = "hausse" if yield_change_bps > 0 else "baisse"
            return MacroLock(
                name="YIELD_SPIKE_LOCK",
                reason=f"Spike yields {direction} {yield_change_bps:.2f}bps en 5 min",
                active_until=datetime.now(timezone.utc) + timedelta(minutes=15),
                severity="HIGH",
            )
        return None

    def get_active_locks(
        self,
        dxy_change_pct: float = 0.0,
        yield_change_bps: float = 0.0,
    ) -> List[MacroLock]:
        """Retourne la liste de tous les locks actifs."""
        locks: List[MacroLock] = []
        now = datetime.now(timezone.utc)

        for check in [
            self.check_fomc_lock,
            self.check_nfp_lock,
            self.check_cpi_lock,
            self.check_london_fix_lock,
            self.check_comex_open_lock,
        ]:
            lock = check()
            if lock and lock.active_until > now:
                locks.append(lock)

        # Locks sur spikes (donnees temps reel)
        spike_lock = self.check_dxy_spike_lock(dxy_change_pct)
        if spike_lock:
            locks.append(spike_lock)

        spike_lock = self.check_yield_spike_lock(yield_change_bps)
        if spike_lock:
            locks.append(spike_lock)

        if locks:
            logger.warning(f"Macro Locks actifs: {[l.name for l in locks]}")
        else:
            logger.debug("Aucun macro lock actif")

        return locks
