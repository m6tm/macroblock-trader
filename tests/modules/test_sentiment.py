"""Tests de validation Phase 4 — Module Sentiment."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from modules.sentiment.core import (
    COTFetcher,
    COTRecord,
    FearGreedFetcher,
    FearGreedIndex,
    RetailFetcher,
    RetailRatio,
    SentimentFetcher,
    SentimentSnapshot,
)
from modules.sentiment.scorer import SentimentScorer


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_cot_text(
    non_comm_long: int = 200_000,
    non_comm_short: int = 150_000,
    comm_long: int = 300_000,
    comm_short: int = 400_000,
) -> str:
    """Genere une ligne CFTC legacy factice pour l'or (088691).

    Le parser utilise les slices [45:55], [55:65], [75:85], [85:95].
    On construit une ligne avec le bon padding.
    """
    code = "088691"
    name = "GOLD - COMMODITY EXCHANGE INC. "
    # Padding pour arriver jusqu'a l'offset 45
    prefix = f"{code}{name:30s}"
    prefix = prefix[:45].ljust(45)

    nc_long = str(non_comm_long).rjust(10)
    nc_short = str(non_comm_short).rjust(10)
    # 10 chars de padding entre 65 et 75
    mid_pad = " " * 10
    c_long = str(comm_long).rjust(10)
    c_short = str(comm_short).rjust(10)

    line = f"{prefix}{nc_long}{nc_short}{mid_pad}{c_long}{c_short}"
    return line


# ------------------------------------------------------------------
# Tests COT
# ------------------------------------------------------------------

def test_cot_parse_success() -> None:
    fetcher = COTFetcher(url="http://dummy")
    text = _make_cot_text(
        non_comm_long=200_000,
        non_comm_short=150_000,
        comm_long=300_000,
        comm_short=400_000,
    )
    record = fetcher._parse(text)
    assert record is not None
    assert record.cftc_code == "088691"
    assert record.non_comm_long == 200_000
    assert record.non_comm_short == 150_000
    assert record.comm_long == 300_000
    assert record.comm_short == 400_000
    assert record.non_comm_net == 50_000
    assert record.comm_net == -100_000


def test_cot_fetch_mock() -> None:
    """Le fetcher telecharge et parse correctement."""
    fetcher = COTFetcher(url="http://dummy")
    text = _make_cot_text(
        non_comm_long=250_000,
        non_comm_short=100_000,
        comm_long=350_000,
        comm_short=200_000,
    )
    with patch.object(fetcher, "_download", return_value=text):
        record = fetcher.fetch()
    assert record is not None
    assert record.comm_net == 150_000  # Comm long > short -> haussier
    assert record.non_comm_net == 150_000


def test_cot_fetch_fail() -> None:
    """En cas d'erreur reseau, retourne None sans planter."""
    fetcher = COTFetcher(url="http://dummy")
    with patch.object(fetcher, "_download", side_effect=Exception("network down")):
        record = fetcher.fetch()
    assert record is None


def test_cot_extreme_commercial_long() -> None:
    """Commercials >90% long = extreme haussier."""
    fetcher = COTFetcher()
    text = _make_cot_text(
        non_comm_long=10_000,
        non_comm_short=90_000,
        comm_long=950_000,
        comm_short=50_000,
    )
    record = fetcher._parse(text)
    assert record is not None
    assert record.is_historic_extreme is True
    assert record.extreme_type == "COMMERCIAL_EXTREME_LONG"


def test_cot_extreme_noncommercial_long() -> None:
    """NonCommercials >90% long = extreme baissier (crowded trade)."""
    fetcher = COTFetcher()
    text = _make_cot_text(
        non_comm_long=950_000,
        non_comm_short=50_000,
        comm_long=100_000,
        comm_short=900_000,
    )
    record = fetcher._parse(text)
    assert record is not None
    assert record.is_historic_extreme is True
    assert record.extreme_type == "NON_COMMERCIAL_EXTREME_LONG"


# ------------------------------------------------------------------
# Tests Retail
# ------------------------------------------------------------------

def test_retail_parse() -> None:
    fetcher = RetailFetcher()
    data = {"XAUUSD": {"long": 65, "short": 35}}
    ratio = fetcher._parse(data, "XAU/USD")
    assert ratio is not None
    assert ratio.long_pct == 65.0
    assert ratio.short_pct == 35.0


def test_retail_no_url() -> None:
    """Sans URL configuree, le fetcher retourne None (degrade)."""
    fetcher = RetailFetcher()
    assert fetcher.fetch() is None


# ------------------------------------------------------------------
# Tests FearGreed
# ------------------------------------------------------------------

def test_fear_greed_parse_mock() -> None:
    fetcher = FearGreedFetcher()
    mock_json = {
        "name": "Fear and Greed Index",
        "data": [
            {
                "value": "25",
                "value_classification": "Fear",
                "timestamp": "1627776000",
            }
        ],
    }
    with patch("modules.sentiment.core.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = mock_json
        mock_get.return_value = mock_resp

        fg = fetcher.fetch()
        assert fg is not None
        assert fg.value == 25.0
        assert fg.classification == "Fear"


def test_fear_greed_fail() -> None:
    """En cas d'erreur API, retourne None sans planter."""
    fetcher = FearGreedFetcher()
    with patch("modules.sentiment.core.httpx.get", side_effect=Exception("timeout")):
        fg = fetcher.fetch()
    assert fg is None


# ------------------------------------------------------------------
# Tests Scoring
# ------------------------------------------------------------------

def test_score_cot_commercial_long() -> None:
    scorer = SentimentScorer()
    cot = COTRecord(comm_long=500_000, comm_short=100_000)
    sig = scorer.calculate_cot_signal(cot)
    assert sig == 1.0  # Comm net long -> haussier


def test_score_cot_commercial_extreme() -> None:
    scorer = SentimentScorer()
    cot = COTRecord(
        comm_long=950_000,
        comm_short=50_000,
        is_historic_extreme=True,
        extreme_type="COMMERCIAL_EXTREME_LONG",
    )
    sig = scorer.calculate_cot_signal(cot)
    assert sig == 2.0


def test_score_cot_noncommercial_long() -> None:
    scorer = SentimentScorer()
    cot = COTRecord(non_comm_long=500_000, non_comm_short=100_000)
    sig = scorer.calculate_cot_signal(cot)
    assert sig == -1.0  # NonComm net long -> baissier


def test_score_cot_none() -> None:
    scorer = SentimentScorer()
    assert scorer.calculate_cot_signal(None) == 0.0


def test_score_retail_extreme_long() -> None:
    scorer = SentimentScorer()
    retail = RetailRatio(long_pct=85, short_pct=15)
    assert scorer.calculate_retail_signal(retail) == -2.0


def test_score_retail_moderate_long() -> None:
    scorer = SentimentScorer()
    retail = RetailRatio(long_pct=75, short_pct=25)
    assert scorer.calculate_retail_signal(retail) == -1.0


def test_score_retail_extreme_short() -> None:
    scorer = SentimentScorer()
    retail = RetailRatio(long_pct=15, short_pct=85)
    assert scorer.calculate_retail_signal(retail) == 2.0


def test_score_retail_none() -> None:
    scorer = SentimentScorer()
    assert scorer.calculate_retail_signal(None) == 0.0


def test_score_feargreed_extreme_fear() -> None:
    scorer = SentimentScorer()
    fg = FearGreedIndex(value=15, classification="Extreme Fear")
    assert scorer.calculate_fear_greed_signal(fg) == 2.0


def test_score_feargreed_greed() -> None:
    scorer = SentimentScorer()
    fg = FearGreedIndex(value=75, classification="Greed")
    assert scorer.calculate_fear_greed_signal(fg) == -1.0


def test_score_feargreed_none() -> None:
    scorer = SentimentScorer()
    assert scorer.calculate_fear_greed_signal(None) == 0.0


def test_score_total_bullish() -> None:
    """Tous les signaux haussiers doivent donner un score proche de +2."""
    scorer = SentimentScorer()
    snapshot = SentimentSnapshot(
        cot=COTRecord(
            comm_long=900_000,
            comm_short=100_000,
            is_historic_extreme=True,
            extreme_type="COMMERCIAL_EXTREME_LONG",
        ),
        retail=RetailRatio(long_pct=10, short_pct=90),
        fear_greed=FearGreedIndex(value=10, classification="Extreme Fear"),
    )
    score = scorer.calculate_total(snapshot)
    assert score.total >= 1.5
    assert score.grade == "EXTREME FEAR / SMART MONEY LONG"


def test_score_total_bearish() -> None:
    """Tous les signaux baissiers doivent donner un score proche de -2."""
    scorer = SentimentScorer()
    snapshot = SentimentSnapshot(
        cot=COTRecord(
            non_comm_long=900_000,
            non_comm_short=100_000,
            is_historic_extreme=True,
            extreme_type="NON_COMMERCIAL_EXTREME_LONG",
        ),
        retail=RetailRatio(long_pct=90, short_pct=10),
        fear_greed=FearGreedIndex(value=95, classification="Extreme Greed"),
    )
    score = scorer.calculate_total(snapshot)
    assert score.total <= -1.5
    assert score.grade == "EXTREME GREED / SMART MONEY SHORT"


def test_score_total_neutral() -> None:
    """Sans donnees, le score doit etre neutre (0)."""
    scorer = SentimentScorer()
    snapshot = SentimentSnapshot(cot=None, retail=None, fear_greed=None)
    score = scorer.calculate_total(snapshot)
    assert score.total == 0.0
    assert score.grade == "NEUTRE"


def test_score_total_mixed() -> None:
    """COT haussier + Retail neutre + Fear neutre = score modere positif."""
    scorer = SentimentScorer()
    snapshot = SentimentSnapshot(
        cot=COTRecord(comm_long=500_000, comm_short=200_000),
        retail=RetailRatio(long_pct=55, short_pct=45),
        fear_greed=FearGreedIndex(value=50, classification="Neutral"),
    )
    score = scorer.calculate_total(snapshot)
    assert 0.3 <= score.total <= 1.0


# ------------------------------------------------------------------
# Tests Integration
# ------------------------------------------------------------------

def test_sentiment_fetcher_snapshot() -> None:
    """Le fetcher agrege les trois sources."""
    cot_fetcher = COTFetcher(url="http://dummy")
    retail_fetcher = RetailFetcher()
    fg_fetcher = FearGreedFetcher()

    text = _make_cot_text(comm_long=500_000, comm_short=100_000)

    with patch.object(cot_fetcher, "_download", return_value=text):
        with patch.object(retail_fetcher, "fetch", return_value=RetailRatio(long_pct=30, short_pct=70)):
            with patch.object(fg_fetcher, "fetch", return_value=FearGreedIndex(value=20, classification="Fear")):
                fetcher = SentimentFetcher(
                    cot_fetcher=cot_fetcher,
                    retail_fetcher=retail_fetcher,
                    fg_fetcher=fg_fetcher,
                )
                snap = fetcher.snapshot()

    assert snap.cot is not None
    assert snap.retail is not None
    assert snap.fear_greed is not None
    assert snap.cot.comm_net == 400_000


# ------------------------------------------------------------------
# Tests Config & Fallback
# ------------------------------------------------------------------

def test_cot_fallback_csv() -> None:
    """Le fetcher lit un fichier CSV local en fallback."""
    import tempfile
    csv_content = (
        "cftc_code,commodity,non_comm_long,non_comm_short,comm_long,comm_short\n"
        "088691,GOLD,200000,150000,300000,400000\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        path = f.name

    fetcher = COTFetcher(url="http://dummy", fallback_file=path)
    with patch.object(fetcher, "_download", side_effect=Exception("404")):
        record = fetcher.fetch()
    assert record is not None
    assert record.comm_net == -100_000
    assert record.non_comm_net == 50_000

    import os
    os.unlink(path)


def test_cot_fallback_txt() -> None:
    """Le fetcher lit un fichier texte fixe local en fallback."""
    import tempfile
    text = _make_cot_text(comm_long=500_000, comm_short=100_000)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        path = f.name

    fetcher = COTFetcher(url="http://dummy", fallback_file=path)
    with patch.object(fetcher, "_download", side_effect=Exception("404")):
        record = fetcher.fetch()
    assert record is not None
    assert record.comm_net == 400_000

    import os
    os.unlink(path)


def test_retail_with_url_mock() -> None:
    """Le retail fetcher utilise l'URL configuree."""
    fetcher = RetailFetcher(url="http://dummy-api")
    mock_json = {"XAUUSD": {"long": 72, "short": 28}}
    with patch("modules.sentiment.core.httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = mock_json
        mock_get.return_value = mock_resp

        ratio = fetcher.fetch("XAU/USD")
        assert ratio is not None
        assert ratio.long_pct == 72.0
        assert ratio.source == "custom_api"


def test_feargreed_disabled() -> None:
    """Si desactive, le fetcher retourne None immediatement."""
    fetcher = FearGreedFetcher(enabled=False)
    assert fetcher.fetch() is None


def test_sentiment_fetcher_reads_config() -> None:
    """SentimentFetcher lit les settings pour configurer les sous-fetchers."""
    from core.config import SentimentConfig
    cfg = SentimentConfig(
        cot_url="http://custom-cot",
        retail_sentiment_url="http://custom-retail",
        fear_greed_enabled=False,
    )
    # On mock load_settings en passant settings directement
    fetcher = SentimentFetcher(settings=cfg)
    assert fetcher.cot.url == "http://custom-cot"
    assert fetcher.retail.url == "http://custom-retail"
    assert fetcher.fg.enabled is False


def test_grade_boundaries() -> None:
    scorer = SentimentScorer()
    assert scorer._grade(2.0) == "EXTREME FEAR / SMART MONEY LONG"
    assert scorer._grade(1.5) == "EXTREME FEAR / SMART MONEY LONG"
    assert scorer._grade(1.0) == "FEAR / COMMERCIALS ACCUMULENT"
    assert scorer._grade(0.0) == "NEUTRE"
    assert scorer._grade(-0.5) == "NEUTRE"
    assert scorer._grade(-1.0) == "GREED / COMMERCIALS DISTRIBUENT"
    assert scorer._grade(-2.0) == "EXTREME GREED / SMART MONEY SHORT"


if __name__ == "__main__":
    test_cot_parse_success()
    test_cot_fetch_mock()
    test_cot_fetch_fail()
    test_cot_extreme_commercial_long()
    test_cot_extreme_noncommercial_long()
    test_retail_parse()
    test_retail_no_url()
    test_fear_greed_parse_mock()
    test_fear_greed_fail()
    test_score_cot_commercial_long()
    test_score_cot_commercial_extreme()
    test_score_cot_noncommercial_long()
    test_score_cot_none()
    test_score_retail_extreme_long()
    test_score_retail_moderate_long()
    test_score_retail_extreme_short()
    test_score_retail_none()
    test_score_feargreed_extreme_fear()
    test_score_feargreed_greed()
    test_score_feargreed_none()
    test_score_total_bullish()
    test_score_total_bearish()
    test_score_total_neutral()
    test_score_total_mixed()
    test_sentiment_fetcher_snapshot()
    test_grade_boundaries()
    print("[OK] Tous les tests Phase 4 ont passe.")
