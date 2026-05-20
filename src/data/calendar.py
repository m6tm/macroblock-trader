"""Calendrier economique — scraper ForexFactory avec cache 5 minutes.

Utilise l'endpoint JSON interne de ForexFactory (endpoint public communautaire)
ou fallback sur le parsing HTML si indisponible.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from loguru import logger

from core.resilience import safe_call

FRED_JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_TTL_SECONDS = 300  # 5 minutes

HIGH_IMPACT_KEYWORDS = {
    "FOMC",
    "Non-Farm",
    "NFP",
    "CPI",
    "PPI",
    "PCE",
    "GDP",
    "Retail Sales",
    "Unemployment",
    "Interest Rate",
    "Fed",
}


@dataclass(frozen=True)
class EconomicEvent:
    """Evenement economique parse."""

    title: str
    currency: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    impact: str  # Low, Medium, High
    forecast: str = ""
    previous: str = ""
    actual: str = ""

    @property
    def is_high_impact(self) -> bool:
        return self.impact.upper() == "HIGH"

    @property
    def is_gold_relevant(self) -> bool:
        """Vrai si l'evenement concerne USD ou est globalement significatif pour l'or."""
        if self.currency in ("USD", "ALL"):
            return True
        title_upper = self.title.upper()
        return any(kw.upper() in title_upper for kw in HIGH_IMPACT_KEYWORDS)


class EconomicCalendar:
    """Calendrier economique avec cache en memoire."""

    def __init__(self, cache_ttl: int = CACHE_TTL_SECONDS) -> None:
        self._cache_ttl = cache_ttl
        self._last_fetch: float = 0.0
        self._cached_events: List[EconomicEvent] = []

    def _is_stale(self) -> bool:
        return time.time() - self._last_fetch > self._cache_ttl

    def fetch(self) -> List[EconomicEvent]:
        """Recupere les evenements de la semaine (avec cache)."""
        if not self._is_stale() and self._cached_events:
            logger.debug("Calendrier economique — cache utilise")
            return self._cached_events

        events = safe_call(self._fetch_json, default_return=[])
        if not events:
            logger.warning("Echec fetch JSON calendrier — tentative HTML")
            events = safe_call(self._fetch_html, default_return=[])

        self._cached_events = events
        self._last_fetch = time.time()
        logger.info(f"Calendrier mis a jour — {len(events)} evenements")
        return events

    def get_high_impact_events(self, hours_ahead: int = 24) -> List[EconomicEvent]:
        """Retourne les evenements a haut impact dans les N heures a venir."""
        now = datetime.now(timezone.utc)
        events = self.fetch()
        relevant = []

        for e in events:
            if not e.is_high_impact or not e.is_gold_relevant:
                continue
            try:
                event_dt = datetime.strptime(
                    f"{e.date} {e.time}", "%Y-%m-%d %H:%M"
                ).replace(tzinfo=timezone.utc)
                delta_hours = (event_dt - now).total_seconds() / 3600
                if 0 <= delta_hours <= hours_ahead:
                    relevant.append(e)
            except ValueError:
                continue

        return sorted(relevant, key=lambda x: f"{x.date} {x.time}")

    def is_macro_lock_active(self) -> bool:
        """Vrai si un evenement haut impact majeur est dans moins de 30 minutes."""
        events = self.get_high_impact_events(hours_ahead=0.5)
        return len(events) > 0

    # ------------------------------------------------------------------
    # Fetchers internes
    # ------------------------------------------------------------------
    def _fetch_json(self) -> List[EconomicEvent]:
        resp = httpx.get(FRED_JSON_URL, timeout=30.0)
        resp.raise_for_status()
        raw = resp.json()
        return [self._parse_json_item(item) for item in raw if self._parse_json_item(item)]

    @staticmethod
    def _parse_json_item(item: Dict[str, str]) -> Optional[EconomicEvent]:
        try:
            return EconomicEvent(
                title=item.get("title", "").strip(),
                currency=item.get("country", "").strip(),
                date=item.get("date", "").strip(),
                time=item.get("time", "").strip(),
                impact=item.get("impact", "Low").strip(),
                forecast=item.get("forecast", ""),
                previous=item.get("previous", ""),
                actual=item.get("actual", ""),
            )
        except Exception:
            return None

    def _fetch_html(self) -> List[EconomicEvent]:
        """Fallback HTML scraping (minimal)."""
        url = "https://www.forexfactory.com/calendar"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = httpx.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("beautifulsoup4 non installe — HTML parsing indisponible")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        events: List[EconomicEvent] = []
        # ForexFactory structure change souvent — c'est un fallback best-effort
        for row in soup.select("tr.calendar_row"):
            try:
                tds = row.find_all("td")
                if len(tds) < 4:
                    continue
                date = tds[0].get_text(strip=True)
                time = tds[1].get_text(strip=True)
                currency = tds[2].get_text(strip=True)
                impact_elem = tds[3].find("span", class_="impact")
                impact = "Low"
                if impact_elem:
                    for cls in impact_elem.get("class", []):
                        if cls in ("high", "medium"):
                            impact = cls.capitalize()
                            break
                title = tds[4].get_text(strip=True) if len(tds) > 4 else ""
                events.append(
                    EconomicEvent(
                        title=title,
                        currency=currency,
                        date=date,
                        time=time,
                        impact=impact,
                    )
                )
            except Exception:
                continue

        return events
