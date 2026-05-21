"""Scoring Sentiment — Agrégation COT / Retail / FearGreed en score -2 a +2.

Formule :
    Score Sentiment = (COT × 0.40) + (Retail × 0.40) + (FearGreed × 0.20)

Interpretation :
    +2  -> Extreme Fear / Smart Money Long   (fort biais haussier comportemental)
    +1  -> Fear / Commercials accumulent     (biais haussier modere)
     0  -> Neutre
    -1  -> Greed / Commercials distribuent   (biais baissier modere)
    -2  -> Extreme Greed / Smart Money Short (fort biais baissier comportemental)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from modules.sentiment.core import (
    COTRecord,
    FearGreedIndex,
    RetailRatio,
    SentimentSnapshot,
)


@dataclass
class SentimentScore:
    """Resultat du scoring sentiment."""

    total: float
    grade: str
    cot_signal: float
    retail_signal: float
    fear_greed_signal: float
    justification: str


class SentimentScorer:
    """Calcule le score sentiment specifique a l'or."""

    W_COT = 0.40
    W_RETAIL = 0.40
    W_FEAR_GREED = 0.20

    # ------------------------------------------------------------------
    # Composantes
    # ------------------------------------------------------------------

    def calculate_cot_signal(self, cot: Optional[COTRecord]) -> float:
        """COT : Commercials net long = haussier ; NonComm net long = baissier.

        Returns:
            Score brut entre -2 et +2 (avant ponderation).
        """
        if cot is None:
            return 0.0

        # Smart money (Commercials) achete = haussier pour l'or
        if cot.comm_net > 0:
            if cot.is_historic_extreme and cot.extreme_type == "COMMERCIAL_EXTREME_LONG":
                return 2.0
            return 1.0

        # Dumb money (NonCommercials) achete = baissier pour l'or (crowded trade)
        if cot.non_comm_net > 0:
            if cot.is_historic_extreme and cot.extreme_type == "NON_COMMERCIAL_EXTREME_LONG":
                return -2.0
            return -1.0

        return 0.0

    def calculate_retail_signal(self, retail: Optional[RetailRatio]) -> float:
        """Retail : contrarian — retail long = baissier, retail short = haussier.

        Returns:
            Score brut entre -2 et +2 (avant ponderation).
        """
        if retail is None:
            return 0.0

        long_pct = retail.long_pct

        if long_pct >= 80:
            return -2.0  # Extreme cupidite haussiere → favoriser shorts
        if long_pct >= 70:
            return -1.0
        if long_pct <= 20:
            return 2.0  # Extreme peur baissiere → favoriser longs
        if long_pct <= 30:
            return 1.0

        return 0.0

    def calculate_fear_greed_signal(self, fg: Optional[FearGreedIndex]) -> float:
        """Fear & Greed : peur = haussier, cupidite = baissier.

        Returns:
            Score brut entre -2 et +2 (avant ponderation).
        """
        if fg is None:
            return 0.0

        val = fg.value

        if val <= 20:
            return 2.0  # Extreme fear → opportunite d'achat
        if val <= 40:
            return 1.0  # Fear → legere opportunite d'achat
        if val >= 81:
            return -2.0  # Extreme greed → danger haussier
        if val >= 61:
            return -1.0  # Greed → prudence haussiere

        return 0.0

    # ------------------------------------------------------------------
    # Agregation
    # ------------------------------------------------------------------

    def calculate_total(self, snapshot: SentimentSnapshot) -> SentimentScore:
        """Agrège les trois composantes en un score final -2 a +2."""
        cot_raw = self.calculate_cot_signal(snapshot.cot)
        retail_raw = self.calculate_retail_signal(snapshot.retail)
        fg_raw = self.calculate_fear_greed_signal(snapshot.fear_greed)

        total = (
            cot_raw * self.W_COT
            + retail_raw * self.W_RETAIL
            + fg_raw * self.W_FEAR_GREED
        )

        total = round(max(-2.0, min(2.0, total)), 2)
        grade = self._grade(total)
        justification = self._build_justification(
            total, cot_raw, retail_raw, fg_raw, snapshot
        )

        logger.info(f"Score Sentiment: {total} ({grade})")
        return SentimentScore(
            total=total,
            grade=grade,
            cot_signal=round(cot_raw * self.W_COT, 2),
            retail_signal=round(retail_raw * self.W_RETAIL, 2),
            fear_greed_signal=round(fg_raw * self.W_FEAR_GREED, 2),
            justification=justification,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 1.5:
            return "EXTREME FEAR / SMART MONEY LONG"
        if score >= 0.5:
            return "FEAR / COMMERCIALS ACCUMULENT"
        if score >= -0.5:
            return "NEUTRE"
        if score >= -1.5:
            return "GREED / COMMERCIALS DISTRIBUENT"
        return "EXTREME GREED / SMART MONEY SHORT"

    @staticmethod
    def _build_justification(
        total: float,
        cot_raw: float,
        retail_raw: float,
        fg_raw: float,
        snapshot: SentimentSnapshot,
    ) -> str:
        parts = [f"Score Sentiment: {total}"]

        if snapshot.cot:
            parts.append(
                f"COT(CommNet={snapshot.cot.comm_net:+d},NonCommNet={snapshot.cot.non_comm_net:+d})"
                f" → {cot_raw:.1f}"
            )
        else:
            parts.append("COT: indisponible → 0.0")

        if snapshot.retail:
            parts.append(
                f"Retail({snapshot.retail.long_pct:.0f}% long) → {retail_raw:.1f}"
            )
        else:
            parts.append("Retail: indisponible → 0.0")

        if snapshot.fear_greed:
            parts.append(
                f"FearGreed({snapshot.fear_greed.value:.0f},{snapshot.fear_greed.classification})"
                f" → {fg_raw:.1f}"
            )
        else:
            parts.append("FearGreed: indisponible → 0.0")

        return " | ".join(parts)
