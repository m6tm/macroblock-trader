"""Tests de validation Phase 0 — Fondation complète."""

import sys
from pathlib import Path

# Ajoute src/ au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.config import Settings, load_settings, validate_startup
from core.event_bus import Event, EventBus, EventType
from core.events import (
    MarketDataEvent,
    MacroUpdateEvent,
    TechnicalSetupEvent,
    SignalGeneratedEvent,
    TradeExecutedEvent,
    TradeClosedEvent,
    UserFeedbackEvent,
    VectorMemoryEvent,
    SimilarTradesFoundEvent,
)
from core.exceptions import (
    MacroBlockError,
    DataFetchError,
    RiskLockError,
    ConfigValidationError,
)
from core.resilience import safe_handler, safe_call, install_global_exception_hook


def test_settings_defaults() -> None:
    s = Settings()
    assert s.trading.asset == "XAU/USD"
    assert s.trading.risk_pct_a_plus == 1.0
    assert s.trading.max_trades_simultaneous == 1
    assert s.data_dir.exists()


def test_settings_validation_ok() -> None:
    s = Settings()
    validate_startup(s)  # ne doit pas lever


def test_settings_validation_bad_risk() -> None:
    s = Settings()
    s.trading.risk_pct_b = 2.0
    s.trading.risk_pct_a_plus = 1.0
    try:
        validate_startup(s)
        assert False, "Devrait lever ConfigValidationError"
    except ConfigValidationError:
        pass


def test_settings_validation_bad_tf() -> None:
    s = Settings()
    s.timeframes.entry = "M45"
    try:
        validate_startup(s)
        assert False, "Devrait lever ConfigValidationError"
    except ConfigValidationError:
        pass


def test_event_bus_pub_sub() -> None:
    bus = EventBus()
    received = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe(EventType.MARKET_DATA, handler)
    bus.emit_typed(
        EventType.MARKET_DATA,
        payload={"price": 2300.0},
        source_module="test",
    )

    assert len(received) == 1
    assert received[0].payload["price"] == 2300.0
    assert received[0].source_module == "test"


def test_event_bus_isolation() -> None:
    """Un handler en erreur ne bloque pas les autres."""
    bus = EventBus()
    results = []

    def bad_handler(_event: Event) -> None:
        raise RuntimeError("boom")

    def good_handler(event: Event) -> None:
        results.append(event.payload["id"])

    bus.subscribe(EventType.MACRO_UPDATE, bad_handler)
    bus.subscribe(EventType.MACRO_UPDATE, good_handler)

    bus.emit_typed(EventType.MACRO_UPDATE, payload={"id": 42})
    assert results == [42]


def test_safe_handler_decorator() -> None:
    """safe_handler isole l'exception sans la propager."""
    bus = EventBus()

    @safe_handler
    def flaky_handler(event: Event) -> None:
        if event.payload.get("fail"):
            raise RuntimeError("flaky")

    bus.subscribe(EventType.MARKET_DATA, flaky_handler)
    # ne doit pas lever
    bus.emit_typed(EventType.MARKET_DATA, payload={"fail": True})


def test_safe_call() -> None:
    def boom() -> str:
        raise ValueError("boom")

    result = safe_call(boom, default_return="fallback")
    assert result == "fallback"

    def ok() -> str:
        return "success"

    assert safe_call(ok, default_return="fallback") == "success"


def test_typed_events() -> None:
    """Les classes typées produisent des événements avec le bon type."""
    e1 = MarketDataEvent(pair="XAU/USD", timeframe="M15")
    assert e1.event_type == EventType.MARKET_DATA

    e2 = MacroUpdateEvent(macro_score=2, justification="DXY down")
    assert e2.event_type == EventType.MACRO_UPDATE
    assert e2.macro_score == 2

    e3 = TechnicalSetupEvent(direction="SHORT", technical_score=4.2)
    assert e3.event_type == EventType.TECHNICAL_SETUP
    assert e3.direction == "SHORT"

    e4 = SignalGeneratedEvent(grade="A+", total_score=4.5)
    assert e4.event_type == EventType.SIGNAL_GENERATED
    assert e4.grade == "A+"

    e5 = TradeExecutedEvent(trade_id="TRADE-001", entry_price=2300.0)
    assert e5.event_type == EventType.TRADE_EXECUTED

    e6 = TradeClosedEvent(trade_id="TRADE-001", outcome="WIN", pnl_virtual=50.0)
    assert e6.event_type == EventType.TRADE_CLOSED

    e7 = UserFeedbackEvent(trade_id="TRADE-001", execution_quality=5)
    assert e7.event_type == EventType.USER_FEEDBACK

    e8 = VectorMemoryEvent(trade_id="TRADE-001", action="STORE")
    assert e8.event_type == EventType.VECTOR_MEMORY

    e9 = SimilarTradesFoundEvent(reference_trade_id="TRADE-001", adjustment=0.1)
    assert e9.event_type == EventType.SIMILAR_TRADES_FOUND


def test_exception_hierarchy() -> None:
    assert issubclass(DataFetchError, MacroBlockError)
    assert issubclass(RiskLockError, MacroBlockError)
    assert issubclass(ConfigValidationError, MacroBlockError)


def test_main_importable() -> None:
    """Vérifie que main.py est importable sans erreur."""
    import main

    assert hasattr(main, "main")


def test_inter_module_scenario() -> None:
    """Scénario inter-module : producteur → bus → consommateur."""
    bus = EventBus()
    received = []

    @safe_handler
    def consumer(event: Event) -> None:
        received.append({
            "type": event.event_type.name,
            "src": event.source_module,
            "price": event.payload.get("price"),
        })

    bus.subscribe(EventType.MARKET_DATA, consumer)

    # Simule un module producteur
    bus.emit_typed(
        EventType.MARKET_DATA,
        payload={"price": 2350.0, "pair": "XAU/USD"},
        source_module="technical",
    )

    assert len(received) == 1
    assert received[0]["src"] == "technical"
    assert received[0]["price"] == 2350.0


if __name__ == "__main__":
    test_settings_defaults()
    test_settings_validation_ok()
    test_settings_validation_bad_risk()
    test_settings_validation_bad_tf()
    test_event_bus_pub_sub()
    test_event_bus_isolation()
    test_safe_handler_decorator()
    test_safe_call()
    test_typed_events()
    test_exception_hierarchy()
    test_main_importable()
    test_inter_module_scenario()
    print("✅ Tous les tests Phase 0 (complet) ont passé.")
