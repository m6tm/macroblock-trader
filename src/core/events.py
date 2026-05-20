"""Classes d'événements typés pour l'EventBus.

Chaque classe porte sa sémantique métier et ses champs attendus,
mais reste compatible avec la classe de base Event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Literal

from core.event_bus import Event, EventType


@dataclass(frozen=True)
class MarketDataEvent(Event):
    """Nouvelles données de marché OHLCV ou tick."""

    pair: str = "XAU/USD"
    timeframe: str = "M15"
    candle: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.MARKET_DATA)


@dataclass(frozen=True)
class MacroUpdateEvent(Event):
    """Mise à jour du score macro ou des données fondamentales."""

    dxy_momentum: float = 0.0
    real_yields: float = 0.0
    fed_policy_score: float = 0.0
    risk_sentiment: float = 0.0
    inflation_surprise: float = 0.0
    macro_score: int = 0
    justification: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.MACRO_UPDATE)


@dataclass(frozen=True)
class TechnicalSetupEvent(Event):
    """Détection d'un setup technique SMC."""

    direction: Literal["LONG", "SHORT"] = "LONG"
    ob_zone: tuple = ()
    fvg_zone: tuple = ()
    bos_confirmed: bool = False
    choch_confirmed: bool = False
    liquidity_target: float = 0.0
    killzone_active: str = ""
    technical_score: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.TECHNICAL_SETUP)


@dataclass(frozen=True)
class SignalGeneratedEvent(Event):
    """Un signal complet a été généré après fusion des scores."""

    signal_id: str = ""
    grade: Literal["A+", "B", "C", "N/A"] = "N/A"
    total_score: float = 0.0
    macro_score: int = 0
    technical_score: float = 0.0
    timing_score: float = 0.0
    entry_zone: tuple = ()
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    risk_reward: float = 0.0
    validity_until: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.SIGNAL_GENERATED)


@dataclass(frozen=True)
class TradeExecutedEvent(Event):
    """L'utilisateur a confirmé l'exécution d'un signal."""

    trade_id: str = ""
    signal_id: str = ""
    entry_price: float = 0.0
    size_units: float = 0.0
    direction: Literal["LONG", "SHORT"] = "LONG"

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.TRADE_EXECUTED)


@dataclass(frozen=True)
class TradeClosedEvent(Event):
    """Clôture virtuelle d'un trade (SL, TP, BE, expiration...)."""

    trade_id: str = ""
    exit_price: float = 0.0
    outcome: Literal["WIN", "LOSS", "BE", "EXPIRED"] = "BE"
    pnl_virtual: float = 0.0
    close_reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.TRADE_CLOSED)


@dataclass(frozen=True)
class UserFeedbackEvent(Event):
    """Feedback utilisateur sur un trade exécuté manuellement."""

    trade_id: str = ""
    user_executed: bool = False
    slippage_note: str = ""
    emotion_note: str = ""
    execution_quality: int = 0  # 1-5

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.USER_FEEDBACK)


@dataclass(frozen=True)
class VectorMemoryEvent(Event):
    """Demande de vectorisation ou stockage d'un trade en mémoire."""

    trade_id: str = ""
    action: Literal["STORE", "UPDATE", "DELETE"] = "STORE"

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.VECTOR_MEMORY)


@dataclass(frozen=True)
class SimilarTradesFoundEvent(Event):
    """Résultat d'une recherche de trades similaires dans ChromaDB."""

    reference_trade_id: str = ""
    similar_trade_ids: list = field(default_factory=list)
    similarities: list = field(default_factory=list)
    adjustment: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.SIMILAR_TRADES_FOUND)
