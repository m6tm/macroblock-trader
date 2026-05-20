"""Outils de résilience — dégradation gracieuse et handler global d'exceptions.

Un module en erreur ne doit jamais planter le bus ou les autres modules.
"""

import sys
from functools import wraps
from typing import Any, Callable, TypeVar

from loguru import logger

from core.event_bus import Event

F = TypeVar("F", bound=Callable[..., Any])


def safe_handler(handler: Callable[[Event], None]) -> Callable[[Event], None]:
    """Décorateur qui wrap un handler EventBus pour isoler ses erreurs.

    L'exception est loguée mais n'est pas propagée.
    """

    @wraps(handler)
    def wrapper(event: Event) -> None:
        try:
            handler(event)
        except Exception as exc:
            logger.warning(
                f"[DÉGRADATION] Handler '{handler.__qualname__}' a échoué "
                f"sur {event.event_type.name}: {exc}. Le bus continue."
            )

    return wrapper


def safe_call(
    func: Callable[..., Any],
    *args: Any,
    default_return: Any = None,
    **kwargs: Any,
) -> Any:
    """Appelle une fonction en capturant toute exception.

    En cas d'erreur, retourne `default_return` et logue l'incident.
    C'est le mécanisme central de dégradation gracieuse.
    """
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        logger.warning(
            f"[DÉGRADATION] Appel '{func.__qualname__}' a échoué: {exc}. "
            f"Retour par défaut: {default_return}."
        )
        return default_return


def install_global_exception_hook() -> None:
    """Installe un hook global sur les exceptions non interceptées.

    Remplace sys.excepthook pour loguer proprement les crashs inattendus
    sans polluer stdout.
    """
    original_hook = sys.excepthook

    def _hook(exc_type, exc_value, traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            original_hook(exc_type, exc_value, traceback)
            return
        logger.opt(exception=(exc_type, exc_value, traceback)).critical(
            f"Exception non interceptée: {exc_type.__name__}: {exc_value}"
        )

    sys.excepthook = _hook
