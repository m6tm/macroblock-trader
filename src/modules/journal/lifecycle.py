"""Cycle de vie complet d'un trade — tous les etats du doc 15.

Etats :
    GENERATED → EXECUTED → ACTIVE → CLOSED_* → FEEDBACK_PENDING
                                            → VALIDATED / AUTO_CLOSED → ARCHIVED
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from loguru import logger

from modules.journal.database import JournalDatabase


class TradeLifecycle:
    """Gere le cycle de vie complet d'un trade/signal."""

    def __init__(self, db: JournalDatabase) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 1. Signal
    # ------------------------------------------------------------------

    def create_signal(
        self,
        signal_id: str,
        timestamp_generated: str,
        valid_until: Optional[str],
        pair: str,
        direction: str,
        grade: str,
        score_total: float,
        setup_type: str,
        entry_zone_low: float,
        entry_zone_high: float,
        sl_price: float,
        tp1_price: Optional[float],
        tp2_price: Optional[float],
        tp3_price: Optional[float],
        rr_expected: float,
        rejection_reason: Optional[str] = None,
    ) -> None:
        """Cree un signal dans la table signals."""
        status = "REJECTED" if rejection_reason else "GENERATED"
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO signals (
                    signal_id, timestamp_generated, valid_until, pair, direction,
                    grade, score_total, setup_type, entry_zone_low, entry_zone_high,
                    sl_price, tp1_price, tp2_price, tp3_price, rr_expected, status,
                    rejection_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id, timestamp_generated, valid_until, pair, direction,
                    grade, score_total, setup_type, entry_zone_low, entry_zone_high,
                    sl_price, tp1_price, tp2_price, tp3_price, rr_expected, status,
                    rejection_reason,
                ),
            )
            conn.commit()
        logger.info(f"Signal {signal_id} | {status} | {direction} {grade}")

    def expire_signal(self, signal_id: str) -> None:
        """Marque un signal comme expire."""
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE signals SET status = 'EXPIRED' WHERE signal_id = ?",
                (signal_id,),
            )
            conn.commit()
        logger.info(f"Signal {signal_id} | EXPIRED")

    # ------------------------------------------------------------------
    # 2. Trade — Execution & Activation
    # ------------------------------------------------------------------

    def execute_trade(
        self,
        trade_id: str,
        signal_id: str,
        plan_data: Dict[str, Any],
    ) -> None:
        """Cree un trade a partir d'un signal execute par l'utilisateur.

        Args:
            trade_id: ID unique du trade
            signal_id: ID du signal d'origine
            plan_data: Dictionnaire avec tous les champs du TradePlan
        """
        now = datetime.now(timezone.utc).isoformat()
        d = plan_data

        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT INTO trades (
                    trade_id, signal_id, created_at, signal_timestamp,
                    xauusd_price, dxy_value, dxy_trend_1h, us10y_yield, tips_10y,
                    vix_value, macro_score, macro_justification, sentiment_score,
                    news_lock_active, killzone,
                    setup_type, structure_h4, structure_h1, bos_m15_confirmed,
                    ob_zone_low, ob_zone_high, ob_freshness, fvg_present,
                    fvg_zone_low, fvg_zone_high, liquidity_target, liquidity_price,
                    score_technical,
                    direction, grade, score_total, entry_zone_low, entry_zone_high,
                    sl_price, sl_distance_dollars, tp1_price, tp2_price, tp3_price,
                    rr_expected, risk_pct, position_size_lots,
                    status_virtual, screenshot_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?)
                """,
                (
                    trade_id, signal_id, now, d.get("timestamp_generated", now),
                    d.get("xauusd_price"), d.get("dxy_value"), d.get("dxy_trend_1h"),
                    d.get("us10y_yield"), d.get("tips_10y"), d.get("vix_value"),
                    d.get("macro_score"), d.get("macro_justification"),
                    d.get("sentiment_score"), d.get("news_lock_active", False),
                    d.get("killzone"),
                    d.get("setup_type"), d.get("structure_h4"), d.get("structure_h1"),
                    d.get("bos_m15_confirmed", False),
                    d.get("ob_zone_low"), d.get("ob_zone_high"), d.get("ob_freshness"),
                    d.get("fvg_present", False), d.get("fvg_zone_low"), d.get("fvg_zone_high"),
                    d.get("liquidity_target"), d.get("liquidity_price"),
                    d.get("score_technical"),
                    d.get("direction"), d.get("grade"), d.get("score_total"),
                    d.get("entry_zone_low"), d.get("entry_zone_high"),
                    d.get("sl_price"), d.get("sl_distance_dollars"),
                    d.get("tp1_price"), d.get("tp2_price"), d.get("tp3_price"),
                    d.get("rr_expected"), d.get("risk_pct"), d.get("position_size_lots"),
                    "EXECUTED", d.get("screenshot_path"),
                ),
            )
            conn.execute(
                "UPDATE signals SET status = 'EXECUTED' WHERE signal_id = ?",
                (signal_id,),
            )
            conn.commit()
        logger.success(f"Trade execute {trade_id} | {d.get('direction')} {d.get('grade')} | EXECUTED")

    def activate_trade(self, trade_id: str, entry_price_actual: float) -> None:
        """Marque un trade comme ACTIVE (entre reel effectuee)."""
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE trades SET status_virtual = 'ACTIVE', entry_price_actual = ? WHERE trade_id = ?",
                (entry_price_actual, trade_id),
            )
            conn.commit()
        logger.info(f"Trade {trade_id} | ACTIVE @ {entry_price_actual}")

    # ------------------------------------------------------------------
    # 3. Cloture virtuelle
    # ------------------------------------------------------------------

    def close_trade_virtual(
        self,
        trade_id: str,
        close_price: float,
        outcome: str,  # CLOSED_WIN / CLOSED_LOSS / CLOSED_BE
        duration_minutes: Optional[int] = None,
        tp1_hit: bool = False,
        tp2_hit: bool = False,
        tp3_hit: bool = False,
        sl_hit: bool = False,
    ) -> None:
        """Cloture un trade virtuellement et calcule le P&L."""
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT entry_price_actual, direction, position_size_lots FROM trades WHERE trade_id = ?",
                (trade_id,),
            ).fetchone()
            if not row:
                logger.warning(f"Trade {trade_id} introuvable — cloture ignoree")
                return

            entry_price, direction, lots = row
            if entry_price is None:
                entry_price = conn.execute(
                    "SELECT entry_zone_low FROM trades WHERE trade_id = ?",
                    (trade_id,),
                ).fetchone()[0]

            # P&L virtuel
            if direction == "LONG":
                pnl_dollars = (close_price - entry_price) * (lots or 0)
            else:
                pnl_dollars = (entry_price - close_price) * (lots or 0)

            pnl_pct = (pnl_dollars / 10_000 * 100) if 10_000 > 0 else 0.0

            conn.execute(
                """
                UPDATE trades
                SET status_virtual = ?, close_timestamp_virtual = ?, close_price_virtual = ?,
                    pnl_virtual_dollars = ?, pnl_virtual_pct = ?, duration_minutes = ?,
                    tp1_hit = ?, tp2_hit = ?, tp3_hit = ?, sl_hit = ?
                WHERE trade_id = ?
                """,
                (
                    outcome, now, close_price, pnl_dollars, pnl_pct,
                    duration_minutes, tp1_hit, tp2_hit, tp3_hit, sl_hit, trade_id,
                ),
            )
            conn.commit()

        logger.info(
            f"Trade cloture virtuel {trade_id} | {outcome} | P&L=${pnl_dollars:.2f}"
        )
        self.request_feedback(trade_id)

    # ------------------------------------------------------------------
    # 4. Feedback utilisateur
    # ------------------------------------------------------------------

    def request_feedback(self, trade_id: str) -> None:
        """Passe le trade en attente de feedback."""
        with self.db.connection() as conn:
            conn.execute(
                "UPDATE trades SET user_feedback_status = 'FEEDBACK_PENDING' WHERE trade_id = ?",
                (trade_id,),
            )
            conn.commit()
        logger.info(f"Trade {trade_id} | FEEDBACK_PENDING")

    def submit_feedback(
        self,
        trade_id: str,
        user_executed: bool,
        user_exit_price: Optional[float] = None,
        user_exit_reason: Optional[str] = None,
        pnl_real_dollars: Optional[float] = None,
        user_notes: Optional[str] = None,
        user_satisfaction: Optional[int] = None,
    ) -> None:
        """Enregistre le feedback utilisateur et passe le trade a VALIDATED."""
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE trades
                SET user_executed = ?, user_exit_price = ?, user_exit_reason = ?,
                    pnl_real_dollars = ?, user_notes = ?, user_satisfaction = ?,
                    user_feedback_status = 'VALIDATED', user_feedback_timestamp = ?, validated_at = ?
                WHERE trade_id = ?
                """,
                (
                    user_executed, user_exit_price, user_exit_reason,
                    pnl_real_dollars, user_notes, user_satisfaction,
                    now, now, trade_id,
                ),
            )
            conn.commit()
        logger.success(f"Trade {trade_id} | VALIDATED avec feedback")

    def auto_close_feedback(self, trade_id: str) -> None:
        """Ferme automatiquement le feedback apres 7 jours sans reponse."""
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connection() as conn:
            conn.execute(
                """
                UPDATE trades
                SET user_feedback_status = 'AUTO_CLOSED', user_feedback_timestamp = ?
                WHERE trade_id = ? AND user_feedback_status = 'FEEDBACK_PENDING'
                """,
                (now, trade_id),
            )
            conn.commit()
        logger.info(f"Trade {trade_id} | AUTO_CLOSED (pas de feedback)")

    def archive_old_trades(self, days: int = 30) -> int:
        """Archive les trades VALIDATED ou AUTO_CLOSED vieux de N jours."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.db.connection() as conn:
            cur = conn.execute(
                """
                UPDATE trades
                SET status_virtual = 'ARCHIVED'
                WHERE status_virtual IN ('VALIDATED', 'AUTO_CLOSED')
                  AND validated_at < ?
                """,
                (cutoff,),
            )
            conn.commit()
            count = cur.rowcount
        logger.info(f"Archive: {count} trades archives (> {days} jours)")
        return count
