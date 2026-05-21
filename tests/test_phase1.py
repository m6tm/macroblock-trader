"""Tests de validation Phase 1 — Couche Donnees."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx

from data.normalizer import OHLCVNormalizer, DataStore
from data.calendar import EconomicCalendar, EconomicEvent
from data.oanda_client import OandaClient, GRANULARITY_MAP
from data.fetcher import DataFetcher
from data.screenshot import capture_chart, _has_matplotlib
from data.compat import has_pandas, make_ohlcv_data


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
    rows = norm.rows()
    assert len(rows) == 2
    assert rows[0]["open"] == 2000.0
    assert rows[0]["pair"] == "XAU/USD"
    assert rows[0]["timeframe"] == "M5"
    assert isinstance(rows[0]["volume"], int)


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
    assert len(data) == 0


def test_screenshot_without_matplotlib() -> None:
    candles = [
        {"timestamp": "2024-01-01T10:00:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000},
    ]
    path = capture_chart(candles, "SIG-TEST-001")
    if _has_matplotlib():
        assert path is not None
    else:
        assert path is None


# ------------------------------------------------------------------
# Tests mocks HTTP (completement Phase 1)
# ------------------------------------------------------------------


def _mock_httpx_client(mock_response):
    """Helper pour mocker httpx.Client en context manager."""
    patcher = patch("data.oanda_client.httpx.Client")

    def _enter(mock_class):
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.request.return_value = mock_response
        mock_class.return_value = mock_instance
        return mock_instance

    return patcher, _enter


def test_oanda_client_mock_success() -> None:
    """Le client parse correctement les candles OANDA."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "candles": [
            {
                "time": "2024-01-01T10:00:00Z",
                "volume": 100,
                "mid": {"o": "2000.0", "h": "2001.0", "l": "1999.0", "c": "2000.5"},
                "complete": True,
            },
            {
                "time": "2024-01-01T10:05:00Z",
                "volume": 150,
                "mid": {"o": "2000.5", "h": "2002.0", "l": "2000.0", "c": "2001.5"},
                "complete": True,
            },
        ]
    }

    patcher, enter = _mock_httpx_client(mock_resp)
    with patcher as mock_class:
        mock_instance = enter(mock_class)
        client = OandaClient(api_key="test_key")
        candles = client.get_candles("XAU_USD", "M5", count=2)

        assert len(candles) == 2
        assert candles[0]["close"] == 2000.5
        assert candles[1]["volume"] == 150
        mock_instance.request.assert_called_once()


def test_oanda_client_mock_retry_429() -> None:
    """Retry exponentiel sur 429 puis succes."""
    req = MagicMock()
    resp_429 = MagicMock()
    resp_429.status_code = 429
    err_429 = httpx.HTTPStatusError("429", request=req, response=resp_429)
    resp_429.raise_for_status.side_effect = err_429

    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.raise_for_status.return_value = None
    resp_ok.json.return_value = {"candles": []}

    patcher, _ = _mock_httpx_client(None)
    with patcher as mock_class:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.request.side_effect = [resp_429, resp_ok]
        mock_class.return_value = mock_instance

        client = OandaClient(api_key="test_key", base_backoff=0.001)
        candles = client.get_candles("XAU_USD", "M5", count=1)

        assert len(candles) == 0
        assert mock_instance.request.call_count == 2


def test_oanda_client_mock_500_then_fail() -> None:
    """Echec definitif apres 3 retries sur 5xx."""
    req = MagicMock()
    resp_500 = MagicMock()
    resp_500.status_code = 500
    err_500 = httpx.HTTPStatusError("500", request=req, response=resp_500)
    resp_500.raise_for_status.side_effect = err_500

    patcher, _ = _mock_httpx_client(None)
    with patcher as mock_class:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.request.side_effect = [resp_500, resp_500, resp_500]
        mock_class.return_value = mock_instance

        client = OandaClient(api_key="test_key", base_backoff=0.001)
        try:
            client.get_candles("XAU_USD", "M5", count=1)
            assert False, "Devrait lever DataFetchError"
        except Exception as exc:
            assert "echec" in str(exc).lower() or "OANDA" in str(exc)


def test_calendar_json_mock() -> None:
    """Parsing JSON du calendrier economique."""
    mock_payload = [
        {
            "title": "NFP",
            "country": "USD",
            "date": "2099-01-01",
            "time": "14:00",
            "impact": "High",
            "forecast": "200K",
            "previous": "190K",
            "actual": "210K",
        },
        {
            "title": "Retail Sales",
            "country": "EUR",
            "date": "2099-01-01",
            "time": "12:00",
            "impact": "Medium",
        },
    ]

    with patch("data.calendar.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        cal = EconomicCalendar(cache_ttl=0)
        events = cal.fetch()

        assert len(events) == 2
        assert events[0].title == "NFP"
        assert events[0].is_high_impact
        assert events[0].is_gold_relevant
        assert events[1].impact == "Medium"


def test_calendar_html_mock() -> None:
    """Fallback HTML parsing du calendrier."""
    html = """
    <html><body><table>
      <tr class="calendar_row">
        <td>2024-01-15</td>
        <td>10:00</td>
        <td>USD</td>
        <td><span class="impact high">High</span></td>
        <td>CPI m/m</td>
      </tr>
      <tr class="calendar_row">
        <td>2024-01-15</td>
        <td>08:30</td>
        <td>EUR</td>
        <td><span class="impact medium">Medium</span></td>
        <td>GDP q/q</td>
      </tr>
    </table></body></html>
    """

    with patch("data.calendar.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = html
        mock_get.return_value = mock_resp

        cal = EconomicCalendar(cache_ttl=0)
        with patch.object(cal, "_fetch_json", return_value=[]):
            events = cal.fetch()

        assert len(events) == 2
        titles = [e.title for e in events]
        assert "CPI m/m" in titles
        assert "GDP q/q" in titles
        impacts = {e.title: e.impact for e in events}
        assert impacts["CPI m/m"] == "High"
        assert impacts["GDP q/q"] == "Medium"


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
    summary = store.summary()
    assert "XAU/USD|M5" in summary
    assert summary["XAU/USD|M5"] == 2

    latest = store.get_latest("XAU/USD", "M5")
    assert latest is not None
    assert latest["close"] == 2000


def test_fetcher_gap_detection() -> None:
    """Le fetcher detecte automatiquement les gaps en M5."""
    store = DataStore()
    fetcher = DataFetcher(store=store)

    # Gap de 30 minutes en M5 (attendu : 5 min)
    fake_candles = [
        {"time": "2024-01-01T10:00:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
        {"time": "2024-01-01T10:30:00Z", "open": 2000, "high": 2001, "low": 1999, "close": 2000, "volume": 100},
    ]

    with patch.object(fetcher.oanda, "get_candles", return_value=fake_candles):
        data = fetcher.fetch_xauusd_m5(count=2)

    assert len(data) == 2
    # Le store contient les donnees malgre le gap
    assert store.summary()["XAU/USD|M5"] == 2


def test_fetcher_context_degraded() -> None:
    """Sans yfinance ni cles API, les fetchers contexte retournent vide sans planter."""
    fetcher = DataFetcher()
    with patch.object(fetcher, "_fetch_yfinance", return_value=[]):
        assert len(fetcher.fetch_vix_m15(5)) == 0
        assert len(fetcher.fetch_sp500(5)) == 0
        assert len(fetcher.fetch_us10y(5)) == 0
    assert len(fetcher.fetch_tips_10y(5)) == 0
    assert len(fetcher.fetch_dxy_m15(5)) == 0


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
    test_oanda_client_mock_success()
    test_oanda_client_mock_retry_429()
    test_oanda_client_mock_500_then_fail()
    test_calendar_json_mock()
    test_calendar_html_mock()
    test_fetcher_store_integration()
    test_fetcher_gap_detection()
    test_fetcher_context_degraded()
    print("[OK] Tous les tests Phase 1 ont passe.")
