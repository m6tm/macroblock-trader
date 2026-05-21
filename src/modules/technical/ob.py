"""Detection des Order Blocks (OB) — Smart Money Concepts.

Un Order Block est la derniere candle institutionnelle avant un mouvement
impulsif. Sur l'or, on accepte la mitigation a 50%.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from data.compat import OHLCVData


class OBType(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class OBFreshness(Enum):
    FRESH = "FRESH"          # Jamais mitigue
    FIRST_TOUCH = "FIRST_TOUCH"  # Premiere mitigation
    MITIGATED = "MITIGATED"  # Deja mitigue


@dataclass
class OrderBlock:
    type: OBType
    index: int
    timestamp: str
    ob_low: float
    ob_high: float
    impulse_start: float
    impulse_end: float
    freshness: OBFreshness
    mitigated_pct: float = 0.0
    confluence_score: float = 0.0

    def zone(self) -> Tuple[float, float]:
        return (self.ob_low, self.ob_high)

    def is_valid_for_entry(self) -> bool:
        """Un OB est valide si frais ou premiere mitigation (specifique Or)."""
        return self.freshness in (OBFreshness.FRESH, OBFreshness.FIRST_TOUCH)


def _candle_body(open_p: float, close_p: float) -> float:
    return abs(close_p - open_p)


def _is_bearish_candle(open_p: float, close_p: float) -> bool:
    return close_p < open_p


def _is_bullish_candle(open_p: float, close_p: float) -> bool:
    return close_p > open_p


def detect_bullish_ob(
    data: OHLCVData,
    impulsion_threshold: float = 15.0,
    lookback_impulse: int = 3,
) -> List[OrderBlock]:
    """Detecte les Order Blocks bullish sur XAU/USD.

    Critere : derniere candle baissiere avant un mouvement haussier impulsif
    d'au moins `impulsion_threshold` dollars (defaut 15$ pour l'or).
    """
    rows = data.rows()
    if len(rows) < lookback_impulse + 2:
        return []

    obs: List[OrderBlock] = []

    for i in range(len(rows) - lookback_impulse):
        c = rows[i]
        open_i = float(c["open"])
        close_i = float(c["close"])
        high_i = float(c["high"])
        low_i = float(c["low"])

        # La candle candidate doit etre baissiere (ou neutre)
        if close_i >= open_i:
            continue

        # Mesure l'impulsion suivante : move haussier sur les N candles suivantes
        future_low = min(float(rows[i + k]["low"]) for k in range(1, lookback_impulse + 1))
        future_high = max(float(rows[i + k]["high"]) for k in range(1, lookback_impulse + 1))
        impulse = future_high - close_i

        if impulse < impulsion_threshold:
            continue

        # Verifie qu'il y a au moins une continuation haussiere nette
        # (pas juste un wick)
        future_close = float(rows[i + lookback_impulse]["close"])
        if future_close <= close_i:
            continue

        ob = OrderBlock(
            type=OBType.BULLISH,
            index=i,
            timestamp=str(c["timestamp"]),
            ob_low=low_i,
            ob_high=high_i,
            impulse_start=close_i,
            impulse_end=future_high,
            freshness=OBFreshness.FRESH,
        )
        obs.append(ob)

    logger.debug(f"Bullish OB detectes : {len(obs)}")
    return obs


def detect_bearish_ob(
    data: OHLCVData,
    impulsion_threshold: float = 15.0,
    lookback_impulse: int = 3,
) -> List[OrderBlock]:
    """Detecte les Order Blocks bearish sur XAU/USD.

    Critere : derniere candle haussiere avant un mouvement baissier impulsif
    d'au moins `impulsion_threshold` dollars.
    """
    rows = data.rows()
    if len(rows) < lookback_impulse + 2:
        return []

    obs: List[OrderBlock] = []

    for i in range(len(rows) - lookback_impulse):
        c = rows[i]
        open_i = float(c["open"])
        close_i = float(c["close"])
        high_i = float(c["high"])
        low_i = float(c["low"])

        # La candle candidate doit etre haussiere
        if close_i <= open_i:
            continue

        # Mesure l'impulsion baissiere suivante
        future_low = min(float(rows[i + k]["low"]) for k in range(1, lookback_impulse + 1))
        future_high = max(float(rows[i + k]["high"]) for k in range(1, lookback_impulse + 1))
        impulse = close_i - future_low

        if impulse < impulsion_threshold:
            continue

        future_close = float(rows[i + lookback_impulse]["close"])
        if future_close >= close_i:
            continue

        ob = OrderBlock(
            type=OBType.BEARISH,
            index=i,
            timestamp=str(c["timestamp"]),
            ob_low=low_i,
            ob_high=high_i,
            impulse_start=close_i,
            impulse_end=future_low,
            freshness=OBFreshness.FRESH,
        )
        obs.append(ob)

    logger.debug(f"Bearish OB detectes : {len(obs)}")
    return obs


def calculate_freshness(
    ob: OrderBlock,
    data: OHLCVData,
    mitigation_threshold: float = 0.5,
) -> OrderBlock:
    """Calcule la fraicheur d'un OB par rapport au prix actuel.

    Args:
        ob: Order block a evaluer
        data: Toutes les candles (pour voir si le prix est revenu dans l'OB)
        mitigation_threshold: Seuil de mitigation accepte (0.5 = 50% pour l'or)

    Returns:
        OrderBlock mis a jour avec freshness et mitigated_pct
    """
    rows = data.rows()
    if ob.index >= len(rows) - 1:
        return ob

    zone_height = ob.ob_high - ob.ob_low
    if zone_height <= 0:
        return ob

    # On regarde les candles APRES l'OB
    max_mitigation = 0.0
    for j in range(ob.index + 1, len(rows)):
        low_j = float(rows[j]["low"])
        high_j = float(rows[j]["high"])

        if ob.type == OBType.BULLISH:
            # Mitigation = le prix descend dans l'OB
            if low_j <= ob.ob_high:
                penetration = min(ob.ob_high - low_j, zone_height)
                max_mitigation = max(max_mitigation, penetration / zone_height)
        else:
            # Bearish OB : mitigation = le prix monte dans l'OB
            if high_j >= ob.ob_low:
                penetration = min(high_j - ob.ob_low, zone_height)
                max_mitigation = max(max_mitigation, penetration / zone_height)

    ob.mitigated_pct = max_mitigation

    if max_mitigation == 0:
        ob.freshness = OBFreshness.FRESH
    elif max_mitigation <= mitigation_threshold:
        ob.freshness = OBFreshness.FIRST_TOUCH
    else:
        ob.freshness = OBFreshness.MITIGATED

    return ob


def filter_valid_obs(
    obs: List[OrderBlock],
    data: OHLCVData,
    mitigation_threshold: float = 0.5,
) -> List[OrderBlock]:
    """Filtre les OB frais ou en premiere mitigation (specifique Or)."""
    valid = []
    for ob in obs:
        ob = calculate_freshness(ob, data, mitigation_threshold)
        if ob.is_valid_for_entry():
            valid.append(ob)
    logger.debug(f"OB valides apres fraicheur : {len(valid)}/{len(obs)}")
    return valid
