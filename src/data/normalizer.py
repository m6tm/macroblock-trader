"""Normalisation des donnees et cache temps reel en memoire.

Stocke les OHLCV sous forme de listes de dicts normalises (timezone UTC,
types float, index par timestamp). Remplace le DataFrame pandas pour
la compatibilite Termux — migration vers pandas transparente si disponible.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from data.compat import make_ohlcv_data, OHLCVData


class OHLCVNormalizer:
    """Normalise un lot de candles brutes en format interne standard."""

    @staticmethod
    def normalize(
        candles: List[Dict[str, Any]],
        pair: str,
        timeframe: str,
    ) -> OHLCVData:
        """Retourne un OHLCVData normalise (DataFrame pandas si disponible, sinon list[dict]).

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
        return make_ohlcv_data(normalized, pair, timeframe)

    @staticmethod
    def check_gaps(
        data: OHLCVData,
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
        rows = data.rows()

        for i in range(1, len(rows)):
            ts1 = rows[i - 1]["timestamp"]
            ts2 = rows[i]["timestamp"]
            # Support str ISO, datetime, ou pandas Timestamp
            if isinstance(ts1, str):
                t1 = datetime.fromisoformat(ts1.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(ts2.replace("Z", "+00:00"))
            else:
                t1 = ts1.to_pydatetime() if hasattr(ts1, "to_pydatetime") else ts1
                t2 = ts2.to_pydatetime() if hasattr(ts2, "to_pydatetime") else ts2
            delta_min = (t2 - t1).total_seconds() / 60
            if delta_min > expected_min * 1.5:  # tolerance 50%
                gaps.append((str(ts1), str(ts2)))

        if gaps:
            logger.warning(f"{len(gaps)} gap(s) detecte(s) sur {timeframe}")
        return gaps


class DataStore:
    """Cache en memoire des donnees de marche par paire/timeframe.

    Structure interne : { (pair, timeframe) : OHLCVData }
    """

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], OHLCVData] = {}
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
        data = self._store.get(key)
        if data is None:
            return None
        rows = data.rows()
        return rows[-1] if rows else None

    def get_historical(
        self, pair: str, timeframe: str, bars: int
    ) -> OHLCVData:
        """Retourne les N dernieres candles."""
        key = (pair, timeframe)
        data = self._store.get(key)
        if data is None:
            return make_ohlcv_data([], pair, timeframe)
        return data.tail(bars)

    def get_all(self, pair: str, timeframe: str) -> OHLCVData:
        """Retourne toutes les candles stockees."""
        return self._store.get((pair, timeframe), make_ohlcv_data([], pair, timeframe))

    def check_gaps(self, pair: str, timeframe: str) -> List[Tuple[str, str]]:
        """Verifie les gaps pour une paire/timeframe donnee."""
        data = self.get_all(pair, timeframe)
        return self._normalizer.check_gaps(data, timeframe)

    def summary(self) -> Dict[str, int]:
        """Resume du contenu du store."""
        return {f"{k[0]}|{k[1]}": len(v) for k, v in self._store.items()}
