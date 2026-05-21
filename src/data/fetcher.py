"""Couche de recuperation des donnees de marche.

XAU/USD : OANDA (temps reel)
Contexte macro : OANDA via proxy EUR/USD (DXY), FRED (yields) si cle disponible.
Yahoo Finance retire — source differee et inoperante sur Termux.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permet le lancement avec `python -m src.data.fetcher`
_src_root = Path(__file__).resolve().parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from typing import Any, Dict, List, Optional

from loguru import logger

from core.config import Settings
from core.exceptions import DataFetchError
from core.resilience import safe_call
from data.compat import make_ohlcv_data, OHLCVData
from data.normalizer import OHLCVNormalizer
from data.oanda_client import OandaClient


def _instrument_to_oanda(pair: str) -> str:
    """Convertit XAU/USD en XAU_USD."""
    return pair.replace("/", "_")


class DataFetcher:
    """Orchestre la recuperation de toutes les donnees necessaires."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        store: Optional[Any] = None,
    ) -> None:
        self.settings = settings or Settings()
        self.oanda = OandaClient.from_settings(self.settings)
        self.store = store

    # ------------------------------------------------------------------
    # 1.2 XAU/USD via OANDA (temps reel)
    # ------------------------------------------------------------------
    def fetch_xauusd(
        self, timeframe: str, count: int = 500
    ) -> OHLCVData:
        """Recupere les candles XAU/USD pour un timeframe donne.

        Args:
            timeframe: M5, M15, H1, H4
            count: nombre de candles

        Returns:
            OHLCVData (DataFrame pandas si disponible, sinon list[dict])
        """
        instrument = _instrument_to_oanda(self.settings.trading.asset)
        try:
            raw = self.oanda.get_candles(instrument, timeframe, count)
            data = make_ohlcv_data(raw, self.settings.trading.asset, timeframe)
        except DataFetchError:
            logger.error(f"Echec recuperation {instrument} {timeframe}")
            data = make_ohlcv_data([], self.settings.trading.asset, timeframe)
            raw = []

        # Stockage dans le DataStore si disponible
        if self.store is not None and raw:
            self.store.ingest(self.settings.trading.asset, timeframe, raw)

        # Verification automatique des gaps en M5
        if timeframe == "M5" and len(data) > 1:
            gaps = OHLCVNormalizer.check_gaps(data, "M5")
            if gaps:
                logger.warning(f"Fetcher M5 — {len(gaps)} gap(s) detecte(s)")

        return data

    def fetch_xauusd_m5(self, count: int = 500) -> OHLCVData:
        return self.fetch_xauusd("M5", count)

    def fetch_xauusd_m15(self, count: int = 500) -> OHLCVData:
        return self.fetch_xauusd("M15", count)

    def fetch_xauusd_h1(self, count: int = 200) -> OHLCVData:
        return self.fetch_xauusd("H1", count)

    def fetch_xauusd_h4(self, count: int = 100) -> OHLCVData:
        return self.fetch_xauusd("H4", count)

    # ------------------------------------------------------------------
    # 1.3 Contexte marche (proxy OANDA + FRED)
    # ------------------------------------------------------------------
    def fetch_dxy_m15(self, count: int = 100) -> OHLCVData:
        """Dollar Index — proxy via EUR/USD sur OANDA (correlation inverse ~-0.90).

        EUR/USD monte  => USD baisse => DXY baisse => Or haussier
        EUR/USD baisse => USD monte  => DXY monte  => Or baissier
        """
        try:
            raw = self.oanda.get_candles("EUR_USD", "M15", count)
            data = make_ohlcv_data(raw, "DXY-PROXY", "M15")
        except DataFetchError:
            logger.warning("DXY proxy (EUR/USD) non disponible — retour vide")
            data = make_ohlcv_data([], "DXY-PROXY", "M15")
            raw = []

        if self.store is not None and raw:
            self.store.ingest("DXY-PROXY", "M15", raw)

        return data

    def fetch_tips_10y(self, count: int = 30) -> OHLCVData:
        """TIPS 10Y Real Yield — via FRED (DFII10)."""
        raw = safe_call(self._fetch_fred, "DFII10", count, default_return=[])
        return make_ohlcv_data(raw, "TIPS10Y", "D1")

    # ------------------------------------------------------------------
    # Helpers contexte
    # ------------------------------------------------------------------
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
    from data.normalizer import DataStore

    store = DataStore()
    fetcher = DataFetcher(store=store)

    logger.info("=== Validation Phase 1 — Fetcher ===")

    for tf in ("M5", "M15", "H1", "H4"):
        data = fetcher.fetch_xauusd(tf, count=10)
        logger.info(f"XAU/USD {tf}: {len(data)} candles")
        if len(data) > 0:
            latest = data.rows()[-1]
            logger.info(
                f"  Dernier: O={latest['open']} H={latest['high']} "
                f"L={latest['low']} C={latest['close']}"
            )

    dxy = fetcher.fetch_dxy_m15(5)
    logger.info(f"DXY-PROXY (EUR/USD): {len(dxy)} candles")

    tips = fetcher.fetch_tips_10y(5)
    logger.info(f"TIPS10Y: {len(tips)} points")

    summary = store.summary()
    logger.info(f"DataStore summary: {summary}")
    logger.success("Validation Phase 1 terminee")
