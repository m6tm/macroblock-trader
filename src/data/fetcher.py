"""Couche de recuperation des donnees de marche.

XAU/USD : OANDA
Contexte (DXY, VIX, yields) : yfinance ou FRED (fallback degrade)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from core.config import Settings
from core.exceptions import DataFetchError
from core.resilience import safe_call
from data.oanda_client import OandaClient


def _instrument_to_oanda(pair: str) -> str:
    """Convertit XAU/USD en XAU_USD."""
    return pair.replace("/", "_")


class DataFetcher:
    """Orchestre la recuperation de toutes les donnees necessaires."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self.oanda = OandaClient.from_settings(self.settings)

    # ------------------------------------------------------------------
    # 1.2 XAU/USD via OANDA
    # ------------------------------------------------------------------
    def fetch_xauusd(
        self, timeframe: str, count: int = 500
    ) -> List[Dict[str, Any]]:
        """Recupere les candles XAU/USD pour un timeframe donne.

        Args:
            timeframe: M5, M15, H1, H4
            count: nombre de candles

        Returns:
            Liste de dicts {time, open, high, low, close, volume, complete}
        """
        instrument = _instrument_to_oanda(self.settings.trading.asset)
        try:
            return self.oanda.get_candles(instrument, timeframe, count)
        except DataFetchError:
            logger.error(f"Echec recuperation {instrument} {timeframe}")
            return []

    def fetch_xauusd_m5(self, count: int = 500) -> List[Dict[str, Any]]:
        return self.fetch_xauusd("M5", count)

    def fetch_xauusd_m15(self, count: int = 500) -> List[Dict[str, Any]]:
        return self.fetch_xauusd("M15", count)

    def fetch_xauusd_h1(self, count: int = 200) -> List[Dict[str, Any]]:
        return self.fetch_xauusd("H1", count)

    def fetch_xauusd_h4(self, count: int = 100) -> List[Dict[str, Any]]:
        return self.fetch_xauusd("H4", count)

    # ------------------------------------------------------------------
    # 1.3 Contexte marche
    # ------------------------------------------------------------------
    def fetch_dxy_m15(self, count: int = 100) -> List[Dict[str, Any]]:
        """Dollar Index — via OANDA (pas de DXY natif, on utilise USD_Index ou yfinance)."""
        try:
            return self.oanda.get_candles("USD_Index", "M15", count)
        except DataFetchError:
            logger.warning("DXY non disponible via OANDA — retour vide")
            return []

    def fetch_vix_m15(self, count: int = 100) -> List[Dict[str, Any]]:
        """VIX — non disponible sur OANDA Forex, tentative yfinance."""
        return safe_call(self._fetch_yfinance, "^VIX", "15m", count, default_return=[])

    def fetch_sp500(self, count: int = 100) -> List[Dict[str, Any]]:
        """S&P 500 — via yfinance."""
        return safe_call(self._fetch_yfinance, "^GSPC", "1h", count, default_return=[])

    def fetch_us10y(self, count: int = 30) -> List[Dict[str, Any]]:
        """US 10Y Treasury Yield — via yfinance (^TNX) ou FRED."""
        return safe_call(self._fetch_yfinance, "^TNX", "1d", count, default_return=[])

    def fetch_tips_10y(self, count: int = 30) -> List[Dict[str, Any]]:
        """TIPS 10Y Real Yield — via FRED (DFII10)."""
        return safe_call(self._fetch_fred, "DFII10", count, default_return=[])

    # ------------------------------------------------------------------
    # Helpers contexte
    # ------------------------------------------------------------------
    def _fetch_yfinance(
        self, ticker: str, interval: str, period_days: int
    ) -> List[Dict[str, Any]]:
        """Recupere des donnees via yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance non installe — donnees marche indisponibles")
            return []

        t = yf.Ticker(ticker)
        hist = t.history(period=f"{period_days}d", interval=interval)
        if hist.empty:
            return []

        records: List[Dict[str, Any]] = []
        for ts, row in hist.iterrows():
            records.append(
                {
                    "time": ts.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row.get("Volume", 0)),
                }
            )
        return records

    def _fetch_fred(self, series_id: str, count: int) -> List[Dict[str, Any]]:
        """Recupere des donnees FRED."""
        api_key = self.settings.fred_api_key
        if not api_key:
            logger.warning(f"FRED_API_KEY manquant — {series_id} indisponible")
            return []

        import httpx

        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": count,
        }

        try:
            resp = httpx.get(url, params=params, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            obs = data.get("observations", [])
            return [
                {
                    "time": o["date"],
                    "value": float(o["value"]) if o["value"] != "." else None,
                }
                for o in obs
            ]
        except Exception as exc:
            logger.warning(f"FRED {series_id} erreur: {exc}")
            return []


# ----------------------------------------------------------------------
# Entrypoint pour validation de phase
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    sys.path.insert(0, "src")
    from core.logger import setup_logging

    setup_logging()
    fetcher = DataFetcher()

    logger.info("=== Validation Phase 1 — Fetcher ===")

    for tf in ("M5", "M15", "H1", "H4"):
        data = fetcher.fetch_xauusd(tf, count=10)
        logger.info(f"XAU/USD {tf}: {len(data)} candles")

    logger.info(f"DXY: {len(fetcher.fetch_dxy_m15(5))} candles")
    logger.info(f"VIX: {len(fetcher.fetch_vix_m15(5))} candles")
    logger.info(f"US10Y: {len(fetcher.fetch_us10y(5))} points")
    logger.info(f"TIPS10Y: {len(fetcher.fetch_tips_10y(5))} points")

    logger.success("Validation Phase 1 terminee")
