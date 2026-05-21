"""Tests d'integration Phase 1 — Pipeline de donnees.

Valide le flux complet : OANDA client -> Fetcher -> Normalizer -> DataStore -> Calendar.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from data.calendar import EconomicCalendar, EconomicEvent
from data.fetcher import DataFetcher
from data.normalizer import DataStore, OHLCVNormalizer
from data.oanda_client import OandaClient


def test_fetcher_store_integration() -> None:
    """Le fetcher stocke automatiquement dans le DataStore."""
    store = DataStore()
    fetcher = DataFetcher(store=store)

    fake_candles = [
        {"time": "2024-01-01T10:00:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
        {"time": "2024-01-01T10:05:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
    ]

    with patch.object(fetcher.oanda, "get_candles", return_value=fake_candles):
        data = fetcher.fetch_xauusd_m5(count=2)

    assert len(data) == 2
    assert "XAU/USD|M5" in store.summary()
    assert store.summary()["XAU/USD|M5"] == 2


def test_normalizer_gaps_detected() -> None:
    """Le pipeline detecte les gaps dans les donnees."""
    raw = [
        {"time": "2024-01-01T10:00:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
        {"time": "2024-01-01T10:30:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
    ]
    norm = OHLCVNormalizer.normalize(raw, "XAU/USD", "M5")
    gaps = OHLCVNormalizer.check_gaps(norm, "M5")
    assert len(gaps) == 1


def test_oanda_client_retry_then_success() -> None:
    """Le client retry sur erreur 429 puis reussit."""
    import httpx

    req = MagicMock()
    resp_429 = MagicMock()
    resp_429.status_code = 429
    err_429 = httpx.HTTPStatusError("429", request=req, response=resp_429)
    resp_429.raise_for_status.side_effect = err_429

    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.raise_for_status.return_value = None
    resp_ok.json.return_value = {"candles": []}

    with patch("data.oanda_client.httpx.Client") as mock_class:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.request.side_effect = [resp_429, resp_ok]
        mock_class.return_value = mock_instance

        client = OandaClient(api_key="test_key", base_backoff=0.001)
        candles = client.get_candles("XAU_USD", "M5", count=1)

        assert len(candles) == 0
        assert mock_instance.request.call_count == 2


def test_calendar_high_impact_filter() -> None:
    """Le calendrier filtre correctement les evenements haut impact pour l'or."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    future_date = (now + timedelta(hours=2)).strftime("%Y-%m-%d")
    future_time = (now + timedelta(hours=2)).strftime("%H:%M")

    cal = EconomicCalendar(cache_ttl=999999)  # Cache tres long pour isoler
    cal._cached_events = [
        EconomicEvent(title="NFP", currency="USD", date=future_date, time=future_time, impact="High"),
        EconomicEvent(title="GDP", currency="EUR", date=future_date, time=future_time, impact="Medium"),
        EconomicEvent(title="CPI", currency="USD", date=future_date, time=future_time, impact="High"),
    ]
    cal._last_fetch = 9999999999.0

    events = cal.get_high_impact_events(hours_ahead=48)
    assert len(events) == 2
    assert all(e.is_high_impact for e in events)
    assert all(e.is_gold_relevant for e in events)


def test_full_data_pipeline_mock() -> None:
    """Pipeline complet : client OANDA -> fetcher -> store -> normalizer."""
    store = DataStore()
    fetcher = DataFetcher(store=store)

    fake_candles = [
        {"time": "2024-01-01T10:00:00Z", "open": "2000.0", "high": "2001.0", "low": "1999.0", "close": "2000.5", "volume": "100"},
        {"time": "2024-01-01T10:05:00Z", "open": "2000.5", "high": "2002.0", "low": "2000.0", "close": "2001.5", "volume": "150"},
    ]

    with patch.object(fetcher.oanda, "get_candles", return_value=fake_candles):
        fetcher.fetch_xauusd_m5(count=2)
        fetcher.fetch_xauusd_m15(count=2)

    summary = store.summary()
    assert "XAU/USD|M5" in summary
    assert "XAU/USD|M15" in summary

    latest_m5 = store.get_latest("XAU/USD", "M5")
    assert latest_m5 is not None
    assert latest_m5["close"] == 2001.5
    assert isinstance(latest_m5["volume"], int)


if __name__ == "__main__":
    test_fetcher_store_integration()
    test_normalizer_gaps_detected()
    test_oanda_client_retry_then_success()
    test_calendar_high_impact_filter()
    test_full_data_pipeline_mock()
    print("[OK] Tests integration Phase 1 (Data Pipeline) passes.")
