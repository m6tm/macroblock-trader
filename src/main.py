"""Point d'entrée unique du bot MacroBlock.

Un seul processus Python, 8 modules fonctionnels découplés,
communication via EventBus en mémoire.
"""

import signal
import sys
from pathlib import Path

from loguru import logger

from core.config import load_settings
from core.event_bus import EventBus, EventType
from core.logger import setup_logging


def _graceful_shutdown(signum: int, frame) -> None:  # noqa: ARG001
    """Handler pour SIGINT / SIGTERM."""
    logger.info(f"Signal {signum} reçu — arrêt gracieux.")
    sys.exit(0)


def main() -> int:
    """Lance le bot : charge la config, initialise le bus, démarre les modules."""
    # 1. Configuration & Logging
    settings = load_settings()
    setup_logging(log_dir=settings.log_dir, level="INFO")

    logger.info("=== MacroBlock Trader — Démarrage ===")
    logger.info(f"Asset cible : {settings.trading.asset}")

    # 2. Event Bus
    bus = EventBus()

    # 3. Handler global d'exceptions (dégradation gracieuse)
    def _on_error(event) -> None:
        logger.error(f"Module en erreur — event={event.event_id}: {event.payload}")

    bus.subscribe(EventType.RISK_LOCK, _on_error)

    # 4. Événement test (validation Phase 0)
    bus.emit_typed(
        event_type=EventType.MARKET_DATA,
        payload={"pair": "XAU/USD", "price": 2345.67, "source": "test"},
        source_module="main",
    )

    logger.success("Bus initialisé — Phase 0 validée.")
    logger.info("Le bot est en attente (mode fondation).")

    # Boucle infinie simple (sera remplacée par l'orchestrateur en Phase 1+)
    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    try:
        while True:
            signal.pause()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Arrêt demandé.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
