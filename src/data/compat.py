"""Couche de compatibilite pandas / structures natives.

Sur Windows/macOS/Linux standard : pandas est disponible et les fetchers
retournent des DataFrames.

Sur Termux/Android ou environnement minimal : fallback sur list[dict].
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Detection runtime de pandas
_HAS_PANDAS = False
try:
    import pandas as pd

    _HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore


def has_pandas() -> bool:
    return _HAS_PANDAS


class OHLCVData:
    """Wrapper unifie autour d'un DataFrame pandas ou d'une list[dict].

    Offre l'interface minimale necessaire pour les modules consommateurs :
    - acces par colonne via .col("close")
    - iteration sur les lignes
    - slicing par index
    - conversion vers list[dict]
    """

    def __init__(self, data: Any, pair: str = "", timeframe: str = "") -> None:
        self._data = data
        self.pair = pair
        self.timeframe = timeframe

    @property
    def is_dataframe(self) -> bool:
        return _HAS_PANDAS and isinstance(self._data, pd.DataFrame)

    def col(self, name: str) -> List[Any]:
        """Retourne une colonne sous forme de liste."""
        if self.is_dataframe:
            return self._data[name].tolist()
        return [row.get(name) for row in self._data]

    def rows(self) -> List[Dict[str, Any]]:
        """Retourne toutes les lignes sous forme de list[dict]."""
        if self.is_dataframe:
            return self._data.to_dict("records")
        return list(self._data)

    def tail(self, n: int) -> "OHLCVData":
        """Retourne les n dernieres lignes."""
        if self.is_dataframe:
            return OHLCVData(self._data.tail(n), self.pair, self.timeframe)
        return OHLCVData(self._data[-n:], self.pair, self.timeframe)

    def head(self, n: int) -> "OHLCVData":
        """Retourne les n premieres lignes."""
        if self.is_dataframe:
            return OHLCVData(self._data.head(n), self.pair, self.timeframe)
        return OHLCVData(self._data[:n], self.pair, self.timeframe)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        if self.is_dataframe:
            for _, row in self._data.iterrows():
                yield row.to_dict()
        else:
            yield from self._data

    def __repr__(self) -> str:
        n = len(self._data)
        kind = "DataFrame" if self.is_dataframe else "list"
        return f"OHLCVData({kind}, {n} rows, {self.pair}, {self.timeframe})"


def make_ohlcv_data(
    records: List[Dict[str, Any]],
    pair: str = "",
    timeframe: str = "",
) -> OHLCVData:
    """Cree un OHLCVData a partir de records bruts.

    Utilise un DataFrame pandas si disponible, sinon une list[dict].
    """
    if _HAS_PANDAS and records:
        df = pd.DataFrame(records)
        # Convertit le timestamp en datetime index si present
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.sort_values("timestamp").reset_index(drop=True)
        return OHLCVData(df, pair, timeframe)
    return OHLCVData(records, pair, timeframe)
