"""Client API OANDA v20 — candles, retry, rate limiting.

Documentaton : https://developer.oanda.com/rest-live-v20/introduction/
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from core.config import Settings
from core.exceptions import DataFetchError

OANDA_PRACTICE_URL = "https://api-fxpractice.oanda.com"
OANDA_LIVE_URL = "https://api-fxtrade.oanda.com"

GRANULARITY_MAP = {
    "M1": "M1",
    "M5": "M5",
    "M15": "M15",
    "M30": "M30",
    "H1": "H1",
    "H4": "H4",
    "D1": "D",
}


class OandaClient:
    """Client HTTP pour l'API OANDA avec retry exponentiel et rate limiting."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        practice: bool = True,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> None:
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = OANDA_PRACTICE_URL if practice else OANDA_LIVE_URL
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self._last_request_time: float = 0.0
        self._min_interval: float = 0.2  # 5 req/sec max

        if not self.api_key:
            logger.warning("OANDA_API_KEY manquant — le client fonctionnera en mode degrade")

    @classmethod
    def from_settings(cls, settings: Settings, **kwargs) -> "OandaClient":
        return cls(
            api_key=settings.oanda_api_key,
            account_id=settings.oanda_account_id,
            **kwargs,
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _rate_limit(self) -> None:
        """Attend si necessaire pour respecter le rate limit."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            sleep_time = self._min_interval - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _request(
        self, method: str, path: str, **kwargs
    ) -> httpx.Response:
        """Effectue une requete HTTP avec retry et backoff exponentiel."""
        url = f"{self.base_url}{path}"
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            self._rate_limit()
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.request(
                        method, url, headers=self._headers(), **kwargs
                    )
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as exc:
                last_exception = exc
                if exc.response.status_code == 429:
                    wait = self.base_backoff * (2 ** (attempt - 1))
                    logger.warning(f"Rate limit OANDA — attente {wait}s (tentative {attempt})")
                    time.sleep(wait)
                elif exc.response.status_code >= 500:
                    wait = self.base_backoff * (2 ** (attempt - 1))
                    logger.warning(f"Erreur serveur OANDA {exc.response.status_code} — retry dans {wait}s")
                    time.sleep(wait)
                else:
                    raise DataFetchError(f"OANDA HTTP {exc.response.status_code}: {exc.response.text}") from exc
            except httpx.RequestError as exc:
                last_exception = exc
                wait = self.base_backoff * (2 ** (attempt - 1))
                logger.warning(f"Erreur reseau OANDA — retry dans {wait}s (tentative {attempt})")
                time.sleep(wait)

        raise DataFetchError(f"OANDA echec apres {self.max_retries} tentatives") from last_exception

    def get_candles(
        self,
        instrument: str,
        granularity: str,
        count: int = 100,
        price: str = "M",
    ) -> List[Dict[str, Any]]:
        """Recupere les candles OHLCV pour un instrument.

        Args:
            instrument: Format OANDA, ex: "XAU_USD"
            granularity: M1, M5, M15, M30, H1, H4, D
            count: Nombre de candles (max 5000)
            price: M (mid), B (bid), A (ask)

        Returns:
            Liste de dicts avec time, open, high, low, close, volume
        """
        path = f"/v3/instruments/{instrument}/candles"
        params = {
            "granularity": GRANULARITY_MAP.get(granularity, granularity),
            "count": min(count, 5000),
            "price": price,
        }

        logger.info(f"OANDA — fetch {instrument} {granularity} x{count}")
        resp = self._request("GET", path, params=params)
        data = resp.json()

        candles = data.get("candles", [])
        parsed: List[Dict[str, Any]] = []
        price_key = price.lower()

        for c in candles:
            parsed.append(
                {
                    "time": c.get("time"),
                    "open": float(c[price_key]["o"]),
                    "high": float(c[price_key]["h"]),
                    "low": float(c[price_key]["l"]),
                    "close": float(c[price_key]["c"]),
                    "volume": int(c.get("volume", 0)),
                    "complete": c.get("complete", True),
                }
            )

        logger.info(f"OANDA — recu {len(parsed)} candles")
        return parsed
