"""Gestion des captures d'ecran au moment du signal.

Genere un chart OHLCV simple avec matplotlib et le sauvegarde
au format PNG dans screenshots/.

Si matplotlib n'est pas disponible, la fonction retourne un chemin
vide et logue un avertissement (mode degrade).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from core.config import Settings


def _has_matplotlib() -> bool:
    try:
        import matplotlib

        return True
    except ImportError:
        return False


def capture_chart(
    candles: List[Dict[str, Any]],
    signal_id: str,
    pair: str = "XAU/USD",
    settings: Optional[Settings] = None,
    title_suffix: str = "",
) -> Optional[Path]:
    """Genere un chart a partir des candles et le sauvegarde.

    Args:
        candles: Liste de dicts OHLCV normalises
        signal_id: Identifiant du signal (utilise pour le nom de fichier)
        pair: Paire affichee
        settings: Configuration (pour le chemin screenshots/)
        title_suffix: Suffixe ajoute au titre

    Returns:
        Path du fichier PNG ou None si echec
    """
    if not _has_matplotlib():
        logger.warning("matplotlib non installe — screenshot indisponible")
        return None

    if not candles:
        logger.warning("Aucune candle fournie — screenshot annule")
        return None

    settings = settings or Settings()
    out_dir = settings.screenshot_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{signal_id}.png"

    try:
        import matplotlib

        matplotlib.use("Agg")  # Mode non-interactif
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from datetime import datetime

        # Extraction des donnees
        times = []
        opens = []
        highs = []
        lows = []
        closes = []

        for c in candles:
            ts = c.get("timestamp", "")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                times.append(dt)
                opens.append(float(c["open"]))
                highs.append(float(c["high"]))
                lows.append(float(c["low"]))
                closes.append(float(c["close"]))
            except (ValueError, TypeError, KeyError):
                continue

        if len(times) < 2:
            logger.warning("Pas assez de donnees valides pour le chart")
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        # Trace les candles comme des segments verticaux
        for i in range(len(times)):
            color = "green" if closes[i] >= opens[i] else "red"
            ax.plot([times[i], times[i]], [lows[i], highs[i]], color="black", linewidth=0.8)
            ax.plot([times[i], times[i]], [opens[i], closes[i]], color=color, linewidth=3)

        ax.set_title(f"{pair} — {signal_id} {title_suffix}".strip())
        ax.set_xlabel("Temps")
        ax.set_ylabel("Prix")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()
        ax.grid(True, alpha=0.3)

        fig.savefig(str(out_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

        logger.info(f"Screenshot sauvegarde: {out_path}")
        return out_path

    except Exception as exc:
        logger.error(f"Erreur generation screenshot: {exc}")
        return None
