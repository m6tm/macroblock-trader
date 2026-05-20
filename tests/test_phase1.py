"""Tests de validation Phase 1 — Couche Donnees."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data.normalizer import OHLCVNormalizer, DataStore
from data.calendar import EconomicCalendar, EconomicEvent
from data.oanda_client import OandaClient, GRANULARITY_MAP
from data.fetcher import DataFetcher
from data.screenshot import capture_chart, _has_matplotlib


def test_granularity_map() -> None:
    assert GRANULARITY_MAP["M5"] == "M5"
    assert GRANULARITY_MAP["H4"] == "H4"
    assert GRANULARITY_MAP["D1"] == "D"


def test_oanda_client_no_key() -> None:
    client = OandaClient(api_key=None)
    assert client.api_key is None
    assert client.base_url == "https://api-fxpractice.oanda.com"


def test_normalizer_basic() -> None:
    raw = [
        {"time": "2024-01-01T10:00:00Z", "open": "2000.0", "high": "2001.0", "low": "1999.0", "close": "2000.5", "volume": "100"},
        {"time": "2024-01-01T10:05:00Z", "open": 2000.5, "high": 2002.0, "low": 2000.0, "close": 2001.5, "volume": 150},
    ]
    norm = OHLCVNormalizer.normalize(raw, "XAU/USD", "M5")
    assert len(norm) == 2
    assert norm[0]["open"] == 2000.0
    assert norm[0]["pair"] == "XAU/USD"
    assert norm[0]["timeframe"] == "M5"
    assert isinstance(norm[0]["volume"], int)


def test_normalizer_gaps() -> None:
    raw = [
        {"time": "2024-01-01T10:00:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
        {"time": "2024-01-01T10:30:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
    ]
    norm = OHLCVNormalizer.normalize(raw, "XAU/USD", "M5")
    gaps = OHLCVNormalizer.check_gaps(norm, "M5")
    assert len(gaps) == 1


def test_data_store() -> None:
    store = DataStore()
    raw = [
        {"time": "2024-01-01T10:00:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
        {"time": "2024-01-01T10:05:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
    ]
    store.ingest("XAU/USD", "M5", raw)
    assert store.get_latest("XAU/USD", "M5") is not None
    assert len(store.get_historical("XAU/USD", "M5", 1)) == 1
    assert len(store.get_all("XAU/USD", "M5")) == 2
    summary = store.summary()
    assert "XAU/USD|M5" in summary


def test_economic_event() -> None:
    e = EconomicEvent(
        title="FOMC Statement",
        currency="USD",
        date="2024-01-01",
        time="14:00",
        impact="High",
    )
    assert e.is_high_impact
    assert e.is_gold_relevant


def test_calendar_cache() -> None:
    cal = EconomicCalendar(cache_ttl=1)
    # Sans reseau — on simule le cache
    cal._cached_events = [
        EconomicEvent(
            title="NFP",
            currency="USD",
            date="2099-01-01",
            time="14:00",
            impact="High",
        )
    ]
    cal._last_fetch = 9999999999.0  # cache frais
    events = cal.fetch()
    assert len(events) == 1
    assert events[0].title == "NFP"


def test_fetcher_without_api_key() -> None:
    fetcher = DataFetcher()
    # Sans cle API, les appels OANDA retournent vide mais ne plantent pas
    data = fetcher.fetch_xauusd_m5(count=5)
    assert isinstance(data, list)


def test_screenshot_without_matplotlib() -> None:
    candles = [
        {"timestamp": "2024-01-01T10:00:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000},
    ]
    path = capture_chart(candles, "SIG-TEST-001")
    if _has_matplotlib():
        assert path is not None
    else:
        assert path is None


if __name__ == "__main__":
    test_granularity_map()
    test_oanda_client_no_key()
    test_normalizer_basic()
    test_normalizer_gaps()
    test_data_store()
    test_economic_event()
    test_calendar_cache()
    test_fetcher_without_api_key()
    test_screenshot_without_matplotlib()
    print("[OK] Tous les tests Phase 1 ont passe.")
