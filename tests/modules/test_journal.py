"""Tests Phase 7 minimal — Journal SQLite (trades, cycle de vie, drawdown)."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from modules.journal.database import JournalDatabase, TradeRecord
from modules.journal.lifecycle import TradeLifecycle
from modules.journal.queries import JournalQueries


def _make_db() -> JournalDatabase:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return JournalDatabase(Path(tmp.name))


# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------

def test_database_init() -> None:
    db = _make_db()
    with db.connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {t[0] for t in tables}
    assert "trades" in names
    assert "signals" in names


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------

def test_create_and_close_trade() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)

    lifecycle.create_trade(
        trade_id="TRADE-001",
        signal_id="SIG-001",
        direction="LONG",
        grade="A+",
        entry_price=2341.0,
        sl_price=2324.5,
        tp1_price=2375.0,
        position_size_lots=6.0,
        risk_amount=100.0,
        risk_pct=1.0,
    )

    queries = JournalQueries(db)
    open_trades = queries.get_open_trades()
    assert len(open_trades) == 1
    assert open_trades[0].trade_id == "TRADE-001"
    assert open_trades[0].status == "OPEN"

    lifecycle.close_trade(trade_id="TRADE-001", exit_price=2380.0, close_reason="TP1 atteint")
    open_trades = queries.get_open_trades()
    assert len(open_trades) == 0

    closed = queries.get_win_rate()
    assert closed == 100.0


def test_trade_pnl_long() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    lifecycle.create_trade(
        trade_id="TRADE-002",
        signal_id="SIG-002",
        direction="LONG",
        grade="B",
        entry_price=2340.0,
        sl_price=2325.0,
        position_size_lots=3.0,
        risk_amount=50.0,
        risk_pct=0.5,
    )
    lifecycle.close_trade(trade_id="TRADE-002", exit_price=2330.0, close_reason="SL touche")

    queries = JournalQueries(db)
    pnl = queries.get_today_pnl()
    assert pnl == -10.0  # 2340 - 2330 = -10


def test_drawdown_tracking() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    # Trade perdant
    lifecycle.create_trade("T-001", "S-001", "LONG", "A+", 2340.0, 2325.0)
    lifecycle.close_trade("T-001", 2320.0, "SL")

    dd = queries.get_drawdown_today_pct(capital=10_000)
    assert dd == 0.2  # 20$ / 10 000 = 0.2%

    dd_week = queries.get_drawdown_week_pct(capital=10_000)
    assert dd_week == 0.2


def test_open_trade_count() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    assert queries.get_open_trade_count() == 0
    lifecycle.create_trade("T-001", "S-001", "LONG", "A+", 2340.0, 2325.0)
    assert queries.get_open_trade_count() == 1
    lifecycle.create_trade("T-002", "S-002", "SHORT", "B", 2350.0, 2365.0)
    assert queries.get_open_trade_count() == 2


if __name__ == "__main__":
    test_database_init()
    test_create_and_close_trade()
    test_trade_pnl_long()
    test_drawdown_tracking()
    test_open_trade_count()
    print("[OK] Tous les tests Phase 7 (Journal) ont passe.")
