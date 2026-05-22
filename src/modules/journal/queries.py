"""Requetes, analytics et exports sur le journal de trades."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

from modules.journal.database import JournalDatabase, TradeRecord


class JournalQueries:
    """Requetes analytiques et exports sur le journal."""

    def __init__(self, db: JournalDatabase) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Trades ouverts / actifs
    # ------------------------------------------------------------------

    def get_open_trades(self) -> List[TradeRecord]:
        """Retourne tous les trades ouverts (ACTIVE)."""
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE status_virtual = 'ACTIVE' ORDER BY created_at DESC"
            ).fetchall()
            return [TradeRecord.from_row(r) for r in rows]

    def get_open_trade_count(self) -> int:
        """Nombre de trades actuellement ouverts."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE status_virtual = 'ACTIVE'"
            ).fetchone()
            return row[0] if row else 0

    def get_trade_by_id(self, trade_id: str) -> Optional[TradeRecord]:
        """Retourne un trade par son ID."""
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM trades WHERE trade_id = ?", (trade_id,)
            ).fetchone()
            return TradeRecord.from_row(row) if row else None

    # ------------------------------------------------------------------
    # P&L & Drawdown
    # ------------------------------------------------------------------

    def get_today_pnl(self) -> float:
        """P&L total des trades clotures aujourd'hui."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_virtual_dollars), 0) FROM trades WHERE status_virtual IN ('CLOSED_WIN', 'CLOSED_LOSS', 'CLOSED_BE') AND signal_timestamp LIKE ?",
                (f"{today}%",),
            ).fetchone()
            return float(row[0]) if row else 0.0

    def get_week_pnl(self) -> float:
        """P&L total des trades clotures cette semaine (7 derniers jours)."""
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_virtual_dollars), 0) FROM trades WHERE status_virtual IN ('CLOSED_WIN', 'CLOSED_LOSS', 'CLOSED_BE') AND signal_timestamp >= ?",
                (week_ago,),
            ).fetchone()
            return float(row[0]) if row else 0.0

    def get_drawdown_today_pct(self, capital: float) -> float:
        """Drawdown journalier en pourcentage du capital."""
        if capital <= 0:
            return 0.0
        pnl = self.get_today_pnl()
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

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def get_trades_awaiting_feedback(self, limit: int = 50) -> List[TradeRecord]:
        """Trades en attente de feedback (FEEDBACK_PENDING)."""
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM trades
                WHERE user_feedback_status = 'FEEDBACK_PENDING'
                ORDER BY close_timestamp_virtual DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [TradeRecord.from_row(r) for r in rows]

    def get_feedback_overdue(self, hours: int = 168) -> List[TradeRecord]:
        """Trades dont le feedback est en retard (defaut: 7 jours)."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM trades
                WHERE user_feedback_status = 'FEEDBACK_PENDING'
                  AND close_timestamp_virtual < ?
                ORDER BY close_timestamp_virtual ASC
                """,
                (cutoff,),
            ).fetchall()
            return [TradeRecord.from_row(r) for r in rows]

    # ------------------------------------------------------------------
    # Requetes par setup / killzone
    # ------------------------------------------------------------------

    def get_trades_by_setup_type(self, setup_type: str, limit: int = 50) -> List[TradeRecord]:
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE setup_type = ? ORDER BY signal_timestamp DESC LIMIT ?",
                (setup_type, limit),
            ).fetchall()
            return [TradeRecord.from_row(r) for r in rows]

    def get_trades_by_killzone(self, killzone: str, limit: int = 50) -> List[TradeRecord]:
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE killzone = ? ORDER BY signal_timestamp DESC LIMIT ?",
                (killzone, limit),
            ).fetchall()
            return [TradeRecord.from_row(r) for r in rows]

    # ------------------------------------------------------------------
    # Win rate analytics
    # ------------------------------------------------------------------

    def get_win_rate(self) -> float:
        """Win rate sur les trades clotures virtuellement."""
        with self.db.connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE status_virtual IN ('CLOSED_WIN', 'CLOSED_LOSS')"
            ).fetchone()[0]
            wins = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE status_virtual = 'CLOSED_WIN'"
            ).fetchone()[0]
            if total == 0:
                return 0.0
            return wins / total * 100

    def get_win_rate_by_setup(self) -> Dict[str, Dict[str, float]]:
        """Win rate par type de setup."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT setup_type,
                       COUNT(*) as total,
                       SUM(CASE WHEN status_virtual = 'CLOSED_WIN' THEN 1 ELSE 0 END) as wins
                FROM trades
                WHERE status_virtual IN ('CLOSED_WIN', 'CLOSED_LOSS')
                GROUP BY setup_type
                """
            ).fetchall()
            return {
                r[0]: {"total": r[1], "wins": r[2], "win_rate": (r[2] / r[1] * 100) if r[1] > 0 else 0}
                for r in rows
            }

    def get_win_rate_by_killzone(self) -> Dict[str, Dict[str, float]]:
        """Win rate par killzone."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT killzone,
                       COUNT(*) as total,
                       SUM(CASE WHEN status_virtual = 'CLOSED_WIN' THEN 1 ELSE 0 END) as wins
                FROM trades
                WHERE status_virtual IN ('CLOSED_WIN', 'CLOSED_LOSS')
                GROUP BY killzone
                """
            ).fetchall()
            return {
                r[0]: {"total": r[1], "wins": r[2], "win_rate": (r[2] / r[1] * 100) if r[1] > 0 else 0}
                for r in rows
            }

    def get_total_trades_count(self) -> int:
        with self.db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM trades").fetchone()
            return row[0] if row else 0

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------

    def export_to_csv(self, filepath: Path) -> None:
        """Exporte tous les trades au format CSV."""
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM trades ORDER BY signal_timestamp DESC").fetchall()
            if not rows:
                logger.warning("Aucun trade a exporter")
                return

            fieldnames = rows[0].keys()
            with open(filepath, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: row[k] for k in fieldnames})

        logger.success(f"Export CSV: {filepath} ({len(rows)} trades)")

    def export_to_json(self, filepath: Path) -> None:
        """Exporte tous les trades au format JSON."""
        with self.db.connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM trades ORDER BY signal_timestamp DESC").fetchall()
            if not rows:
                logger.warning("Aucun trade a exporter")
                return

            data = []
            for row in rows:
                record = {k: row[k] for k in row.keys()}
                data.append(record)

            with open(filepath, "w", encoding="utf-8") as fh:
                json.dump({"trades": data, "exported_at": datetime.now(timezone.utc).isoformat()}, fh, indent=2, default=str)

        logger.success(f"Export JSON: {filepath} ({len(rows)} trades)")

    # ------------------------------------------------------------------
    # Post-trade log
    # ------------------------------------------------------------------

    def log_post_trade(self, trade_id: str) -> str:
        """Genere un resume structuré d'un trade pour les logs."""
        record = self.get_trade_by_id(trade_id)
        if not record:
            return f"Trade {trade_id} introuvable"

        lines = [
            f"=== POST-TRADE {trade_id} ===",
            f"Setup: {record.setup_type or 'N/A'} | {record.direction} {record.grade}",
            f"Entry: {record.entry_price_actual or 'N/A'} | SL: {record.sl_price} | TP1: {record.tp1_price}",
            f"P&L virtuel: ${record.pnl_virtual_dollars or 0:.2f}",
            f"P&L reel: ${record.pnl_real_dollars or 0:.2f}",
            f"Feedback: {record.user_feedback_status or 'N/A'}",
            f"Notes: {record.notes or ''}",
            "=" * 40,
        ]
        summary = "\n".join(lines)
        logger.info(summary)
        return summary
