"""Initialisation et schema SQLite complet du journal de trading.

Schema : 40+ champs repartis en 6 categories (Identification, Contexte, Setup,
Plan, Resultat virtuel, Feedback utilisateur).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    timestamp_generated DATETIME NOT NULL,
    valid_until DATETIME,
    pair TEXT,
    direction TEXT,
    grade TEXT,
    score_total REAL,
    setup_type TEXT,
    entry_zone_low REAL,
    entry_zone_high REAL,
    sl_price REAL,
    tp1_price REAL,
    tp2_price REAL,
    tp3_price REAL,
    rr_expected REAL,
    status TEXT DEFAULT 'GENERATED',
    rejection_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(timestamp_generated);

CREATE TABLE IF NOT EXISTS trades (
    -- A. Identification
    trade_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    validated_at DATETIME,

    -- B. Contexte marche (snapshot au moment du signal)
    signal_timestamp DATETIME NOT NULL,
    xauusd_price REAL,
    dxy_value REAL,
    dxy_trend_1h TEXT,
    us10y_yield REAL,
    tips_10y REAL,
    vix_value REAL,
    macro_score INTEGER,
    macro_justification TEXT,
    sentiment_score INTEGER,
    news_lock_active BOOLEAN DEFAULT 0,
    killzone TEXT,

    -- C. Setup technique
    setup_type TEXT,
    structure_h4 TEXT,
    structure_h1 TEXT,
    bos_m15_confirmed BOOLEAN DEFAULT 0,
    ob_zone_low REAL,
    ob_zone_high REAL,
    ob_freshness TEXT,
    fvg_present BOOLEAN DEFAULT 0,
    fvg_zone_low REAL,
    fvg_zone_high REAL,
    liquidity_target TEXT,
    liquidity_price REAL,
    score_technical REAL,

    -- D. Plan de trade
    direction TEXT NOT NULL,
    grade TEXT,
    score_total REAL,
    entry_zone_low REAL,
    entry_zone_high REAL,
    entry_price_actual REAL,
    sl_price REAL,
    sl_distance_dollars REAL,
    tp1_price REAL,
    tp2_price REAL,
    tp3_price REAL,
    rr_expected REAL,
    risk_pct REAL,
    position_size_lots REAL,

    -- E. Resultat virtuel (calcule par le bot)
    status_virtual TEXT DEFAULT 'PENDING',
    close_timestamp_virtual DATETIME,
    close_price_virtual REAL,
    pnl_virtual_dollars REAL DEFAULT 0,
    pnl_virtual_pct REAL DEFAULT 0,
    duration_minutes INTEGER,
    tp1_hit BOOLEAN DEFAULT 0,
    tp2_hit BOOLEAN DEFAULT 0,
    tp3_hit BOOLEAN DEFAULT 0,
    sl_hit BOOLEAN DEFAULT 0,
    screenshot_path TEXT,

    -- F. Feedback utilisateur
    user_executed BOOLEAN DEFAULT 0,
    user_entry_price REAL,
    user_exit_price REAL,
    user_exit_reason TEXT,
    pnl_real_dollars REAL,
    pnl_real_pct REAL,
    user_feedback_status TEXT DEFAULT 'PENDING',
    user_feedback_timestamp DATETIME,
    user_notes TEXT,
    slippage_vs_bot REAL,
    execution_delay_min INTEGER,
    user_satisfaction INTEGER
);

CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(signal_timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status_virtual);
CREATE INDEX IF NOT EXISTS idx_trades_feedback ON trades(user_feedback_status);
CREATE INDEX IF NOT EXISTS idx_trades_setup ON trades(setup_type, killzone);
"""


class JournalDatabase:
    """Connexion et gestion du schema SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)
            logger.debug(f"Journal SQLite initialise — {self.db_path}")

    def connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)


@dataclass
class TradeRecord:
    """Representation d'un trade en base."""

    trade_id: str
    signal_id: str
    direction: str
    grade: str
    status_virtual: str
    entry_price_actual: Optional[float] = None
    close_price_virtual: Optional[float] = None
    sl_price: Optional[float] = None
    tp1_price: Optional[float] = None
    tp2_price: Optional[float] = None
    tp3_price: Optional[float] = None
    position_size_lots: Optional[float] = None
    risk_pct: Optional[float] = None
    pnl_virtual_dollars: Optional[float] = None
    pnl_virtual_pct: Optional[float] = None
    pnl_real_dollars: Optional[float] = None
    pnl_real_pct: Optional[float] = None
    created_at: Optional[str] = None
    close_timestamp_virtual: Optional[str] = None
    close_reason: Optional[str] = None
    duration_minutes: Optional[int] = None
    tp1_hit: Optional[bool] = None
    tp2_hit: Optional[bool] = None
    tp3_hit: Optional[bool] = None
    sl_hit: Optional[bool] = None
    user_feedback_status: Optional[str] = None
    user_executed: Optional[bool] = None
    user_exit_price: Optional[float] = None
    user_exit_reason: Optional[str] = None
    user_satisfaction: Optional[int] = None
    user_notes: Optional[str] = None
    macro_justification: Optional[str] = None
    setup_type: Optional[str] = None
    killzone: Optional[str] = None
    score_total: Optional[float] = None
    score_technical: Optional[float] = None
    rr_expected: Optional[float] = None
    xauusd_price: Optional[float] = None
    macro_score: Optional[int] = None
    sentiment_score: Optional[int] = None
    screenshot_path: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TradeRecord":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        bool_fields = {"tp1_hit", "tp2_hit", "tp3_hit", "sl_hit", "user_executed",
                       "fvg_present", "bos_m15_confirmed", "news_lock_active"}
        kwargs: dict = {}
        for k in row.keys():
            if k not in valid_keys:
                continue
            val = row[k]
            # Convertir SQLite int 0/1 en bool pour les champs booleens
            if k in bool_fields and isinstance(val, int):
                val = bool(val)
            kwargs[k] = val
        return cls(**kwargs)
