"""Normalisation des donnees et cache temps reel en memoire.

Stocke les OHLCV sous forme de listes de dicts normalises (timezone UTC,
types float, index par timestamp). Remplace le DataFrame pandas pour
la compatibilite Termux — migration vers pandas transparente si disponible.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class OHLCVNormalizer:
    """Normalise un lot de candles brutes en format interne standard."""

    @staticmethod
    def normalize(
        candles: List[Dict[str, Any]],
        pair: str,
        timeframe: str,
    ) -> List[Dict[str, Any]]:
        """Retourne une liste de dicts normalises.

        Champs garantis : timestamp (ISO UTC), open, high, low, close, volume, pair, timeframe
        """
        normalized: List[Dict[str, Any]] = []
        for c in candles:
            ts = c.get("time")
            if ts is None:
                continue
            # Normalise le timestamp en ISO UTC
            if isinstance(ts, datetime):
                ts_iso = ts.astimezone(timezone.utc).isoformat()
            elif isinstance(ts, str):
                # OANDA fournit deja ISO 8601
                ts_iso = ts
            else:
                continue

            try:
                normalized.append(
                    {
                        "timestamp": ts_iso,
                        "open": float(c["open"]),
                        "high": float(c["high"]),
                        "low": float(c["low"]),
                        "close": float(c["close"]),
                        "volume": int(c.get("volume", 0)),
                        "pair": pair,
                        "timeframe": timeframe,
                        "complete": c.get("complete", True),
                    }
                )
            except (ValueError, TypeError, KeyError):
                continue

        # Tri chronologique
        normalized.sort(key=lambda x: x["timestamp"])
        return normalized

    @staticmethod
    def check_gaps(
        candles: List[Dict[str, Any]],
        timeframe: str,
        max_gap_minutes: Optional[int] = None,
    ) -> List[Tuple[str, str]]:
        """Detecte les trous de donnees entre candles consecutives.

        Returns:
            Liste de tuples (timestamp_avant, timestamp_apres) pour chaque gap.
        """
        gap_map = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}
        expected_min = max_gap_minutes or gap_map.get(timeframe, 5)
        gaps: List[Tuple[str, str]] = []

        for i in range(1, len(candles)):
            t1 = datetime.fromisoformat(candles[i - 1]["timestamp"].replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(candles[i]["timestamp"].replace("Z", "+00:00"))
            delta_min = (t2 - t1).total_seconds() / 60
            if delta_min > expected_min * 1.5:  # tolerance 50%
                gaps.append((candles[i - 1]["timestamp"], candles[i]["timestamp"]))

        if gaps:
            logger.warning(f"{len(gaps)} gap(s) detecte(s) sur {timeframe}")
        return gaps


class DataStore:
    """Cache en memoire des donnees de marche par paire/timeframe.

    Structure interne : { (pair, timeframe) : [candle, candle, ...] }
    """

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self._normalizer = OHLCVNormalizer()

    def ingest(
        self,
        pair: str,
        timeframe: str,
        raw_candles: List[Dict[str, Any]],
    ) -> None:
        """Normalise et stocke un lot de candles."""
        normalized = self._normalizer.normalize(raw_candles, pair, timeframe)
        key = (pair, timeframe)
        self._store[key] = normalized
        logger.debug(f"DataStore ingere {len(normalized)} candles pour {key}")

    def get_latest(self, pair: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Retourne la derniere candle disponible."""
        key = (pair, timeframe)
        data = self._store.get(key, [])
        return data[-1] if data else None

    def get_historical(
        self, pair: str, timeframe: str, bars: int
    ) -> List[Dict[str, Any]]:
        """Retourne les N dernieres candles."""
        key = (pair, timeframe)
        data = self._store.get(key, [])
        return data[-bars:] if data else []

    def get_all(self, pair: str, timeframe: str) -> List[Dict[str, Any]]:
        """Retourne toutes les candles stockees."""
        return self._store.get((pair, timeframe), [])

    def check_gaps(self, pair: str, timeframe: str) -> List[Tuple[str, str]]:
        """Verifie les gaps pour une paire/timeframe donnee."""
        data = self.get_all(pair, timeframe)
        return self._normalizer.check_gaps(data, timeframe)

    def summary(self) -> Dict[str, int]:
        """Resume du contenu du store."""
        return {f"{k[0]}|{k[1]}": len(v) for k, v in self._store.items()}
