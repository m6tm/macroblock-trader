"""Initialisation et schema SQLite du journal de trading."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    grade TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    entry_price REAL,
    exit_price REAL,
    sl_price REAL,
    tp1_price REAL,
    tp2_price REAL,
    tp3_price REAL,
    position_size_lots REAL,
    risk_amount REAL,
    risk_pct REAL,
    pnl_dollars REAL,
    pnl_pct REAL,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    close_reason TEXT,
    macro_context TEXT,
    technical_context TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_opened_at ON trades(opened_at);
CREATE INDEX IF NOT EXISTS idx_trades_grade ON trades(grade);

CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    timestamp_generated TEXT NOT NULL,
    valid_until TEXT,
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
    rr_ratio REAL,
    status TEXT DEFAULT 'GENERATED',
    rejection_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(timestamp_generated);
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
    status: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    sl_price: Optional[float] = None
    tp1_price: Optional[float] = None
    tp2_price: Optional[float] = None
    tp3_price: Optional[float] = None
    position_size_lots: Optional[float] = None
    risk_amount: Optional[float] = None
    risk_pct: Optional[float] = None
    pnl_dollars: Optional[float] = None
    pnl_pct: Optional[float] = None
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    close_reason: Optional[str] = None
    macro_context: Optional[str] = None
    technical_context: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TradeRecord":
        return cls(**{k: row[k] for k in row.keys()})
