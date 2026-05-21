"""Module Macro — Calcul du vent dominant pour l'or (XAU/USD).

Agrège DXY, yields, calendrier economique et sentiment pour produire
un score directionnel -3 (baissier) a +3 (haussier).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from data.calendar import EconomicCalendar, EconomicEvent
from data.compat import OHLCVData
from data.fetcher import DataFetcher


@dataclass
class MacroSnapshot:
    """Snapshot des donnees macro brutes."""

    dxy_momentum_pct: float = 0.0  # Variation DXY en %
    dxy_trend: str = "NEUTRAL"
    tips_10y_value: Optional[float] = None
    tips_10y_trend: str = "NEUTRAL"
    vix_value: Optional[float] = None
    sp500_momentum_pct: float = 0.0
    upcoming_events: List[EconomicEvent] = None
    active_locks: List[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if self.upcoming_events is None:
            self.upcoming_events = []
        if self.active_locks is None:
            self.active_locks = []
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class MacroFetcher:
    """Recupere toutes les donnees brutes necessaires au scoring macro."""

    def __init__(self, fetcher: Optional[DataFetcher] = None) -> None:
        self.fetcher = fetcher or DataFetcher()
        self.calendar = EconomicCalendar()

    def get_dxy_momentum(self, candles: int = 4) -> Tuple[float, str]:
        """Retourne (variation_pct, tendance) du DXY proxy (EUR/USD inverse).

        EUR/USD monte => DXY baisse => Or haussier
        """
        data = self.fetcher.fetch_dxy_m15(count=candles)
        rows = data.rows()
        if len(rows) < 2:
            logger.warning("DXY proxy — pas assez de donnees")
            return 0.0, "NEUTRAL"

        start = float(rows[0]["close"])
        end = float(rows[-1]["close"])
        if start == 0:
            return 0.0, "NEUTRAL"

        # Variation EUR/USD
        eur_usd_change = (end - start) / start * 100
        # Inverse pour obtenir le mouvement DXY
        dxy_change = -eur_usd_change

        if dxy_change > 0.15:
            trend = "UP"
        elif dxy_change < -0.15:
            trend = "DOWN"
        else:
            trend = "NEUTRAL"

        logger.debug(f"DXY proxy: {dxy_change:.3f}% | trend={trend}")
        return round(dxy_change, 3), trend

    def get_tips_10y_value(self) -> Tuple[Optional[float], str]:
        """Retourne (valeur, tendance) du TIPS 10Y via FRED."""
        data = self.fetcher.fetch_tips_10y(count=5)
        rows = data.rows()
        if not rows:
            logger.warning("TIPS 10Y — pas de donnees (FRED_API_KEY manquant ?)")
            return None, "NEUTRAL"

        # Les donnees FRED ont une structure differente (champ 'value')
        values = [r.get("value") for r in rows if r.get("value") is not None]
        if not values:
            return None, "NEUTRAL"

        current = float(values[0])
        previous = float(values[-1]) if len(values) > 1 else current

        if current > previous + 0.05:
            trend = "UP"
        elif current < previous - 0.05:
            trend = "DOWN"
        else:
            trend = "NEUTRAL"

        logger.debug(f"TIPS 10Y: {current:.2f}% | trend={trend}")
        return round(current, 2), trend

    def get_upcoming_events(self, hours_ahead: int = 4) -> List[EconomicEvent]:
        """Evenements haut impact a venir."""
        return self.calendar.get_high_impact_events(hours_ahead=hours_ahead)

    def get_all_events(self) -> List[EconomicEvent]:
        """Tous les evenements de la semaine."""
        return self.calendar.fetch()

    def snapshot(self) -> MacroSnapshot:
        """Capture un snapshot complet des conditions macro."""
        dxy_pct, dxy_trend = self.get_dxy_momentum()
        tips_val, tips_trend = self.get_tips_10y_value()
        events = self.get_upcoming_events(hours_ahead=4)

        return MacroSnapshot(
            dxy_momentum_pct=dxy_pct,
            dxy_trend=dxy_trend,
            tips_10y_value=tips_val,
            tips_10y_trend=tips_trend,
            vix_value=None,  # Source indisponible sur Termux
            sp500_momentum_pct=0.0,
            upcoming_events=events,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
