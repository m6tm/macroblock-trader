"""Point d'entrée unique du bot MacroBlock.

Un seul processus Python, 8 modules fonctionnels découplés,
communication via EventBus en mémoire.
"""

import signal
import sys
from pathlib import Path

from loguru import logger

from core.config import load_settings, validate_startup
from core.event_bus import EventBus, EventType
from core.logger import setup_logging
from core.resilience import install_global_exception_hook, safe_handler, safe_call


def _graceful_shutdown(signum: int, frame) -> None:  # noqa: ARG001
    """Handler pour SIGINT / SIGTERM."""
    logger.info(f"Signal {signum} reçu — arrêt gracieux.")
    sys.exit(0)


class DegradedModule:
    """Module simulé pour la validation Phase 0.

    En Phase 1+, chaque module réel (Macro, Technique, Risk...) sera
    chargé dynamiquement. Ici on démontre l'isolation via le bus.
    """

    def __init__(self, name: str, bus: EventBus) -> None:
        self.name = name
        self.bus = bus

    def emit_sample(self) -> None:
        """Émet un événement test."""
        safe_call(
            self.bus.emit_typed,
            EventType.MARKET_DATA,
            {"price": 2345.67, "source": self.name},
            self.name,
        )


def main() -> int:
    """Lance le bot : charge la config, initialise le bus, démarre les modules."""
    # 0. Hook global d'exceptions non interceptées
    install_global_exception_hook()

    # 1. Configuration & Logging
    settings = load_settings()
    setup_logging(log_dir=settings.log_dir, level="INFO")

    logger.info("=== MacroBlock Trader — Démarrage ===")
    logger.info(f"Asset cible : {settings.trading.asset}")

    # 2. Validation explicite au démarrage
    try:
        validate_startup(settings)
        logger.success("Configuration validée.")
    except Exception as exc:
        logger.critical(f"Configuration invalide — arrêt: {exc}")
        return 1

    # 3. Event Bus
    bus = EventBus()

    # 4. Handler global de locks risque (dégradation gracieuse)
    @safe_handler
    def _on_risk_lock(event) -> None:
        logger.warning(
            f"[RISK] Lock actif — event={event.event_id}: {event.payload}"
        )

    bus.subscribe(EventType.RISK_LOCK, _on_risk_lock)

    # 5. Test inter-module : un 'module' émet, un autre reçoit et loggue
    received_log: list = []

    @safe_handler
    def _module_consumer(event) -> None:
        """Simule un module consommateur (ex: Journal, Scoring)."""
        price = event.payload.get("price")
        src = event.source_module
        logger.info(f"[CONSOMMATEUR] Reçu de '{src}' — prix={price}")
        received_log.append({"source": src, "price": price})

    bus.subscribe(EventType.MARKET_DATA, _module_consumer)

    # Émission depuis un module producteur simulé
    producer = DegradedModule("macro_sim", bus)
    producer.emit_sample()

    # 6. Validation : event test supplémentaire
    bus.emit_typed(
        event_type=EventType.MARKET_DATA,
        payload={"pair": "XAU/USD", "price": 2345.67, "source": "test"},
        source_module="main",
    )

    logger.success("Bus initialisé — Phase 0 validée.")
    logger.info(f"Messages inter-module reçus: {len(received_log)}")
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
