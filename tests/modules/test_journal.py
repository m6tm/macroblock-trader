"""Tests Phase 7 complete — Journal SQLite (cycle de vie, feedback, exports)."""

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
# Signal lifecycle
# ------------------------------------------------------------------

def test_create_and_expire_signal() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)

    lifecycle.create_signal(
        signal_id="SIG-20240101-001",
        timestamp_generated="2024-01-01T10:00:00Z",
        valid_until="2024-01-01T10:45:00Z",
        pair="XAUUSD",
        direction="LONG",
        grade="A+",
        score_total=4.2,
        setup_type="Bullish OB + FVG",
        entry_zone_low=2340.0,
        entry_zone_high=2342.0,
        sl_price=2325.0,
        tp1_price=2375.0,
        tp2_price=2390.0,
        tp3_price=None,
        rr_expected=2.3,
    )

    with db.connection() as conn:
        row = conn.execute("SELECT status FROM signals WHERE signal_id = ?", ("SIG-20240101-001",)).fetchone()
        assert row[0] == "GENERATED"

    lifecycle.expire_signal("SIG-20240101-001")
    with db.connection() as conn:
        row = conn.execute("SELECT status FROM signals WHERE signal_id = ?", ("SIG-20240101-001",)).fetchone()
        assert row[0] == "EXPIRED"


def test_rejected_signal() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    lifecycle.create_signal(
        signal_id="SIG-20240101-002",
        timestamp_generated="2024-01-01T10:00:00Z",
        valid_until=None,
        pair="XAUUSD",
        direction="SHORT",
        grade="N/A",
        score_total=1.2,
        setup_type="N/A",
        entry_zone_low=0.0,
        entry_zone_high=0.0,
        sl_price=0.0,
        tp1_price=None,
        tp2_price=None,
        tp3_price=None,
        rr_expected=0.0,
        rejection_reason="R:R insuffisant",
    )
    with db.connection() as conn:
        row = conn.execute("SELECT status, rejection_reason FROM signals WHERE signal_id = ?", ("SIG-20240101-002",)).fetchone()
        assert row[0] == "REJECTED"
        assert "R:R insuffisant" in row[1]


# ------------------------------------------------------------------
# Trade lifecycle
# ------------------------------------------------------------------

def test_execute_and_activate_trade() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)

    plan_data = {
        "timestamp_generated": "2024-01-01T10:00:00Z",
        "direction": "LONG",
        "grade": "A+",
        "score_total": 4.2,
        "setup_type": "Bullish OB + FVG",
        "entry_zone_low": 2340.0,
        "entry_zone_high": 2342.0,
        "sl_price": 2325.0,
        "sl_distance_dollars": 16.5,
        "tp1_price": 2375.0,
        "tp2_price": 2390.0,
        "tp3_price": None,
        "rr_expected": 2.3,
        "risk_pct": 1.0,
        "position_size_lots": 6.0,
        "killzone": "London Fix AM",
        "macro_score": 2,
        "macro_justification": "DXY weak",
        "score_technical": 5.0,
    }

    lifecycle.execute_trade("TRADE-20240101-001", "SIG-20240101-001", plan_data)

    queries = JournalQueries(db)
    trade = queries.get_trade_by_id("TRADE-20240101-001")
    assert trade is not None
    assert trade.status_virtual == "EXECUTED"
    assert trade.grade == "A+"

    lifecycle.activate_trade("TRADE-20240101-001", entry_price_actual=2341.0)
    trade = queries.get_trade_by_id("TRADE-20240101-001")
    assert trade.status_virtual == "ACTIVE"
    assert trade.entry_price_actual == 2341.0


def test_close_trade_virtual() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    plan_data = {
        "timestamp_generated": "2024-01-01T10:00:00Z",
        "direction": "LONG",
        "grade": "A+",
        "score_total": 4.2,
        "setup_type": "Bullish OB",
        "entry_zone_low": 2340.0,
        "entry_zone_high": 2342.0,
        "sl_price": 2325.0,
        "sl_distance_dollars": 16.5,
        "tp1_price": 2375.0,
        "tp2_price": None,
        "tp3_price": None,
        "rr_expected": 2.3,
        "risk_pct": 1.0,
        "position_size_lots": 6.0,
        "killzone": "London Fix AM",
        "macro_score": 2,
        "macro_justification": "DXY weak",
        "score_technical": 5.0,
    }

    lifecycle.execute_trade("TRADE-001", "SIG-001", plan_data)
    lifecycle.activate_trade("TRADE-001", 2341.0)
    lifecycle.close_trade_virtual(
        trade_id="TRADE-001",
        close_price=2376.0,
        outcome="CLOSED_WIN",
        duration_minutes=45,
        tp1_hit=True,
    )

    trade = queries.get_trade_by_id("TRADE-001")
    assert trade.status_virtual == "CLOSED_WIN"
    assert trade.pnl_virtual_dollars == (2376.0 - 2341.0) * 6.0  # 210.0
    assert trade.tp1_hit is True
    assert trade.user_feedback_status == "FEEDBACK_PENDING"


def test_feedback_lifecycle() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    plan_data = {
        "timestamp_generated": "2024-01-01T10:00:00Z",
        "direction": "LONG",
        "grade": "A+",
        "score_total": 4.2,
        "setup_type": "Bullish OB",
        "entry_zone_low": 2340.0,
        "entry_zone_high": 2342.0,
        "sl_price": 2325.0,
        "sl_distance_dollars": 16.5,
        "tp1_price": 2375.0,
        "tp2_price": None,
        "tp3_price": None,
        "rr_expected": 2.3,
        "risk_pct": 1.0,
        "position_size_lots": 6.0,
        "killzone": "London Fix AM",
        "macro_score": 2,
        "macro_justification": "DXY weak",
        "score_technical": 5.0,
    }

    lifecycle.execute_trade("TRADE-FB-001", "SIG-FB-001", plan_data)
    lifecycle.activate_trade("TRADE-FB-001", 2341.0)
    lifecycle.close_trade_virtual("TRADE-FB-001", 2376.0, "CLOSED_WIN")

    # Feedback pending
    pending = queries.get_trades_awaiting_feedback()
    assert len(pending) == 1
    assert pending[0].trade_id == "TRADE-FB-001"

    # Submit feedback
    lifecycle.submit_feedback(
        trade_id="TRADE-FB-001",
        user_executed=True,
        user_exit_price=2375.5,
        user_exit_reason="TP1",
        pnl_real_dollars=207.0,
        user_notes="Bonne execution",
        user_satisfaction=5,
    )

    trade = queries.get_trade_by_id("TRADE-FB-001")
    assert trade.user_feedback_status == "VALIDATED"
    assert trade.user_executed is True
    assert trade.user_satisfaction == 5

    # No more pending
    pending = queries.get_trades_awaiting_feedback()
    assert len(pending) == 0


def test_auto_close_feedback() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    plan_data = {
        "timestamp_generated": "2024-01-01T10:00:00Z",
        "direction": "LONG",
        "grade": "B",
        "score_total": 3.2,
        "setup_type": "Bullish OB",
        "entry_zone_low": 2340.0,
        "entry_zone_high": 2342.0,
        "sl_price": 2325.0,
        "sl_distance_dollars": 16.5,
        "tp1_price": 2375.0,
        "tp2_price": None,
        "tp3_price": None,
        "rr_expected": 2.0,
        "risk_pct": 0.5,
        "position_size_lots": 3.0,
        "killzone": "NY Open",
        "macro_score": 1,
        "macro_justification": "Neutral",
        "score_technical": 4.0,
    }

    lifecycle.execute_trade("TRADE-AC-001", "SIG-AC-001", plan_data)
    lifecycle.close_trade_virtual("TRADE-AC-001", 2330.0, "CLOSED_LOSS")

    lifecycle.auto_close_feedback("TRADE-AC-001")
    trade = queries.get_trade_by_id("TRADE-AC-001")
    assert trade.user_feedback_status == "AUTO_CLOSED"


# ------------------------------------------------------------------
# Queries & Analytics
# ------------------------------------------------------------------

def test_win_rate_by_setup() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    def _make_plan(setup_type: str) -> dict:
        return {
            "timestamp_generated": "2024-01-01T10:00:00Z",
            "direction": "LONG", "grade": "A+", "score_total": 4.2,
            "setup_type": setup_type, "entry_zone_low": 2340.0,
            "entry_zone_high": 2342.0, "sl_price": 2325.0,
            "sl_distance_dollars": 16.5, "tp1_price": 2375.0,
            "tp2_price": None, "tp3_price": None, "rr_expected": 2.3,
            "risk_pct": 1.0, "position_size_lots": 6.0,
            "killzone": "London Fix AM", "macro_score": 2,
            "macro_justification": "DXY weak", "score_technical": 5.0,
        }

    lifecycle.execute_trade("T-001", "S-001", _make_plan("OB+FVG"))
    lifecycle.close_trade_virtual("T-001", 2376.0, "CLOSED_WIN")

    lifecycle.execute_trade("T-002", "S-002", _make_plan("OB+FVG"))
    lifecycle.close_trade_virtual("T-002", 2320.0, "CLOSED_LOSS")

    lifecycle.execute_trade("T-003", "S-003", _make_plan("OB only"))
    lifecycle.close_trade_virtual("T-003", 2376.0, "CLOSED_WIN")

    wr = queries.get_win_rate_by_setup()
    assert "OB+FVG" in wr
    assert wr["OB+FVG"]["total"] == 2
    assert wr["OB+FVG"]["win_rate"] == 50.0
    assert wr["OB only"]["win_rate"] == 100.0


def test_trades_by_killzone() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    def _make_plan(killzone: str) -> dict:
        return {
            "timestamp_generated": "2024-01-01T10:00:00Z",
            "direction": "LONG", "grade": "A+", "score_total": 4.2,
            "setup_type": "OB+FVG", "entry_zone_low": 2340.0,
            "entry_zone_high": 2342.0, "sl_price": 2325.0,
            "sl_distance_dollars": 16.5, "tp1_price": 2375.0,
            "tp2_price": None, "tp3_price": None, "rr_expected": 2.3,
            "risk_pct": 1.0, "position_size_lots": 6.0,
            "killzone": killzone, "macro_score": 2,
            "macro_justification": "DXY weak", "score_technical": 5.0,
        }

    lifecycle.execute_trade("T-KZ-001", "S-KZ-001", _make_plan("London Fix AM"))
    lifecycle.execute_trade("T-KZ-002", "S-KZ-002", _make_plan("London Fix PM"))

    trades_am = queries.get_trades_by_killzone("London Fix AM")
    assert len(trades_am) == 1
    assert trades_am[0].trade_id == "T-KZ-001"


# ------------------------------------------------------------------
# Exports
# ------------------------------------------------------------------

def test_export_csv_json() -> None:
    import tempfile
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    plan_data = {
        "timestamp_generated": "2024-01-01T10:00:00Z",
        "direction": "LONG", "grade": "A+", "score_total": 4.2,
        "setup_type": "OB+FVG", "entry_zone_low": 2340.0,
        "entry_zone_high": 2342.0, "sl_price": 2325.0,
        "sl_distance_dollars": 16.5, "tp1_price": 2375.0,
        "tp2_price": None, "tp3_price": None, "rr_expected": 2.3,
        "risk_pct": 1.0, "position_size_lots": 6.0,
        "killzone": "London Fix AM", "macro_score": 2,
        "macro_justification": "DXY weak", "score_technical": 5.0,
    }

    lifecycle.execute_trade("T-EXP-001", "S-EXP-001", plan_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "trades.csv"
        json_path = Path(tmpdir) / "trades.json"

        queries.export_to_csv(csv_path)
        queries.export_to_json(json_path)

        assert csv_path.exists()
        assert json_path.exists()
        assert csv_path.stat().st_size > 0
        assert json_path.stat().st_size > 0


# ------------------------------------------------------------------
# Post-trade log
# ------------------------------------------------------------------

def test_log_post_trade() -> None:
    db = _make_db()
    lifecycle = TradeLifecycle(db)
    queries = JournalQueries(db)

    plan_data = {
        "timestamp_generated": "2024-01-01T10:00:00Z",
        "direction": "LONG", "grade": "A+", "score_total": 4.2,
        "setup_type": "OB+FVG", "entry_zone_low": 2340.0,
        "entry_zone_high": 2342.0, "sl_price": 2325.0,
        "sl_distance_dollars": 16.5, "tp1_price": 2375.0,
        "tp2_price": None, "tp3_price": None, "rr_expected": 2.3,
        "risk_pct": 1.0, "position_size_lots": 6.0,
        "killzone": "London Fix AM", "macro_score": 2,
        "macro_justification": "DXY weak", "score_technical": 5.0,
    }

    lifecycle.execute_trade("T-LOG-001", "S-LOG-001", plan_data)
    lifecycle.close_trade_virtual("T-LOG-001", 2376.0, "CLOSED_WIN")

    summary = queries.log_post_trade("T-LOG-001")
    assert "T-LOG-001" in summary
    assert "CLOSED_WIN" in summary or "P&L virtuel" in summary


if __name__ == "__main__":
    test_database_init()
    test_create_and_expire_signal()
    test_rejected_signal()
    test_execute_and_activate_trade()
    test_close_trade_virtual()
    test_feedback_lifecycle()
    test_auto_close_feedback()
    test_win_rate_by_setup()
    test_trades_by_killzone()
    test_export_csv_json()
    test_log_post_trade()
    print("[OK] Tous les tests Phase 7 (Journal complet) ont passe.")
