"""Cycle de vie d'un trade — creation, execution, cloture."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from modules.journal.database import JournalDatabase, TradeRecord


class TradeLifecycle:
    """Gere le cycle de vie complet d'un trade."""

    def __init__(self, db: JournalDatabase) -> None:
        self.db = db

    def create_trade(
        self,
        trade_id: str,
        signal_id: str,
        direction: str,
        grade: str,
        entry_price: float,
        sl_price: float,
        tp1_price: Optional[float] = None,
        tp2_price: Optional[float] = None,
        tp3_price: Optional[float] = None,
        position_size_lots: Optional[float] = None,
        risk_amount: Optional[float] = None,
        risk_pct: Optional[float] = None,
        macro_context: Optional[str] = None,
        technical_context: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Cree un nouveau trade avec statut OPEN."""
        opened_at = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO trades (
                    trade_id, signal_id, direction, grade, status,
                    entry_price, sl_price, tp1_price, tp2_price, tp3_price,
                    position_size_lots, risk_amount, risk_pct,
                    opened_at, macro_context, technical_context, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_id, signal_id, direction, grade, "OPEN",
                    entry_price, sl_price, tp1_price, tp2_price, tp3_price,
                    position_size_lots, risk_amount, risk_pct,
                    opened_at, macro_context, technical_context, notes,
                ),
            )
            conn.commit()
        logger.info(f"Trade cree {trade_id} | {direction} {grade} | OPEN")

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        close_reason: str,
    ) -> None:
        """Cloture un trade et calcule le P&L."""
        closed_at = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            # Recuperer entry_price et direction
            row = conn.execute(
                "SELECT entry_price, direction FROM trades WHERE trade_id = ?",
                (trade_id,),
            ).fetchone()
            if not row:
                logger.warning(f"Trade {trade_id} introuvable — cloture ignoree")
                return

            entry_price, direction = row
            if direction == "LONG":
                pnl_dollars = exit_price - entry_price
            else:
                pnl_dollars = entry_price - exit_price

            status = "CLOSED_WIN" if pnl_dollars > 0 else "CLOSED_LOSS" if pnl_dollars < 0 else "BE"

            conn.execute(
                """
                UPDATE trades
                SET status = ?, exit_price = ?, closed_at = ?, close_reason = ?, pnl_dollars = ?
                WHERE trade_id = ?
                """,
                (status, exit_price, closed_at, close_reason, pnl_dollars, trade_id),
            )
            conn.commit()

        logger.info(
            f"Trade cloture {trade_id} | {status} | P&L=${pnl_dollars:.2f} | {close_reason}"
        )

    def update_trade_pnl(
        self,
        trade_id: str,
        current_price: float,
    ) -> Optional[float]:
        """Met a jour le P&L virtuel d'un trade ouvert."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT entry_price, direction, position_size_lots FROM trades WHERE trade_id = ?",
                (trade_id,),
            ).fetchone()
            if not row:
                return None
            entry_price, direction, lots = row
            if direction == "LONG":
                pnl = (current_price - entry_price) * (lots or 0)
            else:
                pnl = (entry_price - current_price) * (lots or 0)
            return pnl
