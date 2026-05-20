"""Configuration du logger structuré avec loguru."""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(
    log_dir: Path = Path("logs"),
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: str = "30 days",
) -> None:
    """Configure loguru avec sortie console + fichier rotatif.

    Args:
        log_dir: Répertoire de stockage des logs.
        level: Niveau de log minimum (DEBUG, INFO, WARNING, ERROR).
        rotation: Taille ou période de rotation du fichier.
        retention: Durée de rétention des fichiers de log.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "macroblock.log"

    # Retire le handler par défaut pour éviter les doublons
    logger.remove()

    # Handler console (format lisible)
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
        colorize=True,
    )

    # Handler fichier (JSON structuré pour analyse)
    logger.add(
        str(log_file),
        level=level,
        format="{time:ISO} | {level} | {name}:{function}:{line} | {message}",
        rotation=rotation,
        retention=retention,
        compression="gz",
        enqueue=True,
    )
