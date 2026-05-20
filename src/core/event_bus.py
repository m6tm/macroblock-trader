"""Event Bus interne — Pub/Sub en mémoire, single-threaded.

Aucun broker externe (Redis, RabbitMQ). Les modules communiquent
uniquement via ce bus. Aucun import direct entre modules du même
niveau sous src/modules/.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List

from loguru import logger


class EventType(Enum):
    """Types d'événements échangés sur le bus."""

    MARKET_DATA = auto()
    MACRO_UPDATE = auto()
    TECHNICAL_SETUP = auto()
    SIGNAL_GENERATED = auto()
    TRADE_EXECUTED = auto()
    TRADE_CLOSED = auto()
    USER_FEEDBACK = auto()
    VECTOR_MEMORY = auto()
    SIMILAR_TRADES_FOUND = auto()
    RISK_LOCK = auto()
    NOTIFICATION_SENT = auto()


@dataclass(frozen=True, slots=True)
class Event:
    """Classe de base pour tous les événements du bus."""

    event_type: EventType = EventType.MARKET_DATA
    payload: Dict[str, Any] = field(default_factory=dict)
    source_module: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __repr__(self) -> str:
        return (
            f"Event({self.event_id} | {self.event_type.name} | "
            f"src={self.source_module})"
        )


class EventBus:
    """Bus d'événements in-process, pub/sub sans sérialisation."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {
            etype: [] for etype in EventType
        }

    def subscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        """Abonne un handler à un type d'événement."""
        self._subscribers[event_type].append(handler)
        logger.debug(f"Handler abonné à {event_type.name}")

    def unsubscribe(
        self, event_type: EventType, handler: Callable[[Event], None]
    ) -> None:
        """Désabonne un handler."""
        try:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Handler désabonné de {event_type.name}")
        except ValueError:
            logger.warning(f"Handler non trouvé pour {event_type.name}")

    def emit(self, event: Event) -> None:
        """Émet un événement vers tous les handlers abonnés.

        Un handler qui lève une exception ne bloque pas les autres.
        """
        handlers = self._subscribers.get(event.event_type, [])
        if not handlers:
            logger.trace(f"Aucun handler pour {event.event_type.name}")
            return

        logger.debug(f"Émission {event}")
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.error(
                    f"Erreur handler {handler.__qualname__} sur {event}: {exc}"
                )

    def emit_typed(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        source_module: str = "unknown",
    ) -> Event:
        """Crée et émet un événement en une seule étape."""
        event = Event(
            event_type=event_type,
            payload=payload,
            source_module=source_module,
        )
        self.emit(event)
        return event
