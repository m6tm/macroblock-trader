"""Tests d'integration Phase 0 — Event Bus et communication inter-modules.

Valide que le bus d'evenements isole les modules et permet
la communication sans imports croises.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from core.event_bus import EventBus, EventType
from core.events import (
    MacroUpdateEvent,
    MarketDataEvent,
    SignalGeneratedEvent,
    TechnicalSetupEvent,
    TradeClosedEvent,
    TradeExecutedEvent,
)
from core.resilience import safe_handler


def test_event_bus_cross_module_scenario() -> None:
    """Scenario cross-module : market_data -> technical -> signal."""
    bus = EventBus()
    received_signals = []

    @safe_handler
    def technical_module(event) -> None:
        if event.event_type == EventType.MARKET_DATA:
            bus.emit_typed(
                EventType.TECHNICAL_SETUP,
                payload={"direction": "LONG", "score": 4.5},
                source_module="technical",
            )

    @safe_handler
    def fusion_module(event) -> None:
        if event.event_type == EventType.TECHNICAL_SETUP:
            bus.emit_typed(
                EventType.SIGNAL_GENERATED,
                payload={"grade": "A+", "rr": 2.5},
                source_module="fusion",
            )

    @safe_handler
    def notification_module(event) -> None:
        if event.event_type == EventType.SIGNAL_GENERATED:
            received_signals.append(event.payload)

    bus.subscribe(EventType.MARKET_DATA, technical_module)
    bus.subscribe(EventType.TECHNICAL_SETUP, fusion_module)
    bus.subscribe(EventType.SIGNAL_GENERATED, notification_module)

    # Simule l'arrivee d'un prix du module data
    bus.emit_typed(
        EventType.MARKET_DATA,
        payload={"pair": "XAU/USD", "price": 2345.0},
        source_module="data",
    )

    assert len(received_signals) == 1
    assert received_signals[0]["grade"] == "A+"


def test_event_bus_isolation_error() -> None:
    """Un module en erreur ne bloque pas les autres handlers."""
    bus = EventBus()
    results = []

    def bad_handler(_event) -> None:
        raise RuntimeError("module crash")

    def good_handler(event) -> None:
        results.append(event.payload["id"])

    bus.subscribe(EventType.MACRO_UPDATE, bad_handler)
    bus.subscribe(EventType.MACRO_UPDATE, good_handler)

    bus.emit_typed(EventType.MACRO_UPDATE, payload={"id": 42})
    assert results == [42]


def test_typed_events_integration() -> None:
    """Les evenements types fonctionnent dans le bus."""
    bus = EventBus()
    received = []

    def handler(event) -> None:
        received.append(type(event).__name__)

    bus.subscribe(EventType.MARKET_DATA, handler)
    bus.subscribe(EventType.MACRO_UPDATE, handler)
    bus.subscribe(EventType.TECHNICAL_SETUP, handler)
    bus.subscribe(EventType.SIGNAL_GENERATED, handler)
    bus.subscribe(EventType.TRADE_EXECUTED, handler)
    bus.subscribe(EventType.TRADE_CLOSED, handler)

    bus.emit(MarketDataEvent(pair="XAU/USD", timeframe="M15"))
    bus.emit(MacroUpdateEvent(macro_score=2, justification="DXY down"))
    bus.emit(TechnicalSetupEvent(direction="LONG", technical_score=4.2))
    bus.emit(SignalGeneratedEvent(grade="A+", total_score=4.5))
    bus.emit(TradeExecutedEvent(trade_id="T-001", entry_price=2300.0))
    bus.emit(TradeClosedEvent(trade_id="T-001", outcome="WIN", pnl_virtual=50.0))

    assert received == [
        "MarketDataEvent",
        "MacroUpdateEvent",
        "TechnicalSetupEvent",
        "SignalGeneratedEvent",
        "TradeExecutedEvent",
        "TradeClosedEvent",
    ]


def test_event_bus_no_circular_imports() -> None:
    """Les modules peuvent etre importes sans imports croises."""
    from modules.macro import core as macro_core
    from modules.sentiment import core as sentiment_core
    from modules.technical import core as technical_core

    # Verification simple : les modules sont importables
    assert hasattr(macro_core, "MacroFetcher")
    assert hasattr(sentiment_core, "SentimentFetcher")
    assert hasattr(technical_core, "detect_swing_highs_lows")


if __name__ == "__main__":
    test_event_bus_cross_module_scenario()
    test_event_bus_isolation_error()
    test_typed_events_integration()
    test_event_bus_no_circular_imports()
    print("[OK] Tests integration Phase 0 (Event Bus) passes.")
