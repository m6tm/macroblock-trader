"""Tests de validation Phase 0 — Fondation."""

import sys
from pathlib import Path

# Ajoute src/ au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.config import Settings, load_settings
from core.event_bus import Event, EventBus, EventType
from core.exceptions import MacroBlockError, DataFetchError, RiskLockError


def test_settings_defaults() -> None:
    s = Settings()
    assert s.trading.asset == "XAU/USD"
    assert s.trading.risk_pct_a_plus == 1.0
    assert s.trading.max_trades_simultaneous == 1
    assert s.data_dir.exists()


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


def test_exception_hierarchy() -> None:
    assert issubclass(DataFetchError, MacroBlockError)
    assert issubclass(RiskLockError, MacroBlockError)


def test_main_importable() -> None:
    """Vérifie que main.py est importable sans erreur."""
    import main

    assert hasattr(main, "main")


if __name__ == "__main__":
    test_settings_defaults()
    test_event_bus_pub_sub()
    test_event_bus_isolation()
    test_exception_hierarchy()
    test_main_importable()
    print("✅ Tous les tests Phase 0 ont passé.")
