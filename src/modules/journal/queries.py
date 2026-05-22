"""Requetes et analytics sur le journal de trades."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from loguru import logger

from modules.journal.database import JournalDatabase, TradeRecord


class JournalQueries:
    """Requetes analytiques sur le journal."""

    def __init__(self, db: JournalDatabase) -> None:
        self.db = db

    def get_open_trades(self) -> List[TradeRecord]:
        """Retourne tous les trades ouverts."""
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'OPEN' ORDER BY opened_at DESC"
            ).fetchall()
            return [TradeRecord.from_row(r) for r in rows]

    def get_open_trade_count(self) -> int:
        """Nombre de trades actuellement ouverts."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE status = 'OPEN'"
            ).fetchone()
            return row[0] if row else 0

    def get_today_pnl(self) -> float:
        """P&L total des trades clotures aujourd'hui."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_dollars), 0) FROM trades WHERE status IN ('CLOSED_WIN', 'CLOSED_LOSS', 'BE') AND opened_at LIKE ?",
                (f"{today}%",),
            ).fetchone()
            return float(row[0]) if row else 0.0

    def get_week_pnl(self) -> float:
        """P&L total des trades clotures cette semaine (7 derniers jours)."""
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_dollars), 0) FROM trades WHERE status IN ('CLOSED_WIN', 'CLOSED_LOSS', 'BE') AND opened_at >= ?",
                (week_ago,),
            ).fetchone()
            return float(row[0]) if row else 0.0

    def get_drawdown_today_pct(self, capital: float) -> float:
        """Drawdown journalier en pourcentage du capital."""
        if capital <= 0:
            return 0.0
        pnl = self.get_today_pnl()
        # Drawdown = perte negative / capital
        if pnl < 0:
            return abs(pnl) / capital * 100
        return 0.0

    def get_drawdown_week_pct(self, capital: float) -> float:
        """Drawdown hebdomadaire en pourcentage du capital."""
        if capital <= 0:
            return 0.0
        pnl = self.get_week_pnl()
        if pnl < 0:
            return abs(pnl) / capital * 100
        return 0.0

    def get_total_trades_count(self) -> int:
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM trades").fetchone()
            return row[0] if row else 0

    def get_win_rate(self) -> float:
        """Win rate sur les trades clotures."""
        with self.db.connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE status IN ('CLOSED_WIN', 'CLOSED_LOSS')"
            ).fetchone()[0]
            wins = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE status = 'CLOSED_WIN'"
            ).fetchone()[0]
            if total == 0:
                return 0.0
            return wins / total * 100
