"""Moteur Fusion & Scoring — Agregation Macro / Technique / Timing.

Formule :
    SCORE TOTAL = (Score Macro × 0.30) + (Score Technique × 0.50) + (Score Timing × 0.20)

Grade :
    ≥ 3.5  → A+ (Signal Fort)
    2.5–3.5 → B (Signal Moyen)
    1.5–2.5 → C (Signal Faible — logger, ne pas notifier)
    < 1.5   → N/A (Ignorer)

Exceptions sentiment :
    Macro = -3 + Tech = 5 + Sentiment = +2 → Signal B autorisé (contre-trend)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger

from modules.macro.scorer import MacroScore
from modules.sentiment.scorer import SentimentScore
from modules.technical.scorer import TechnicalSetup


@dataclass
class FusionScore:
    """Resultat du scoring global."""

    total: float
    grade: str
    macro_component: float
    technical_component: float
    timing_component: float
    sentiment_adjustment: float
    justification: str
    is_exception: bool = False


class FusionScorer:
    """Cerveau decisionnel — agrege les 3 dimensions en un score univoque."""

    W_MACRO = 0.30
    W_TECH = 0.50
    W_TIMING = 0.20

    # Seuils de grade
    THRESHOLD_A_PLUS = 3.5
    THRESHOLD_B = 2.5
    THRESHOLD_C = 1.5

    # Seuil minimum pour signal (hors exception)
    MIN_SIGNAL = 2.5

    def calculate_total(
        self,
        macro: MacroScore,
        technical: TechnicalSetup,
        timing_score: float,
        sentiment: Optional[SentimentScore] = None,
    ) -> FusionScore:
        """Calcule le score global et le grade.

        Args:
            macro: Score macro -3 a +3
            technical: Setup technique avec score 0 a 5
            timing_score: Score timing 0 a 2 (killzone)
            sentiment: Score sentiment -2 a +2 (optionnel)

        Returns:
            FusionScore avec total et grade.
        """
        macro_component = macro.total * self.W_MACRO
        technical_component = technical.score * self.W_TECH
        timing_component = timing_score * self.W_TIMING

        total = macro_component + technical_component + timing_component

        # Exception sentiment : contre-trend extreme fear/greed
        sentiment_adjustment = 0.0
        is_exception = False
        if sentiment is not None:
            sentiment_adjustment = self._evaluate_sentiment_exception(
                macro.total, technical.score, sentiment.total
            )
            if sentiment_adjustment > 0:
                is_exception = True
                total += sentiment_adjustment
                logger.info(
                    f"Exception sentiment active — ajustement +{sentiment_adjustment} "
                    f"(macro={macro.total}, tech={technical.score}, sentiment={sentiment.total})"
                )

        total = round(total, 2)
        grade = self._grade(total, is_exception)
        justification = self._build_justification(
            total, grade, macro_component, technical_component,
            timing_component, sentiment_adjustment, is_exception
        )

        logger.info(f"Score Fusion: {total} ({grade}) | exception={is_exception}")
        return FusionScore(
            total=total,
            grade=grade,
            macro_component=round(macro_component, 2),
            technical_component=round(technical_component, 2),
            timing_component=round(timing_component, 2),
            sentiment_adjustment=round(sentiment_adjustment, 2),
            justification=justification,
            is_exception=is_exception,
        )

    # ------------------------------------------------------------------
    # Exceptions
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_sentiment_exception(
        macro_total: float, technical_score: float, sentiment_total: float
    ) -> float:
        """Evalue si le sentiment autorise une exception contre-trend.

        Regle : Macro=-3 + Tech=5 + Sentiment=+2 → Signal B autorisé.
        On applique un bonus de +0.5 si les conditions sont proches.
        """
        # Macro fortement baissier + tech exceptionnel + sentiment fear extreme
        if macro_total <= -2.0 and technical_score >= 4.5 and sentiment_total >= 1.5:
            return 0.5
        # Macro fortement haussier + tech exceptionnel + sentiment greed extreme
        if macro_total >= 2.0 and technical_score >= 4.5 and sentiment_total <= -1.5:
            return 0.5
        return 0.0

    # ------------------------------------------------------------------
    # Grading
    # ------------------------------------------------------------------

    def _grade(self, total: float, is_exception: bool) -> str:
        if total >= self.THRESHOLD_A_PLUS:
            return "A+"
        if total >= self.THRESHOLD_B:
            return "B"
        if total >= self.THRESHOLD_C:
            return "C"
        if is_exception and total >= self.MIN_SIGNAL - 0.5:
            return "B (EXCEPTION)"
        return "N/A"

    @staticmethod
    def _build_justification(
        total: float,
        grade: str,
        macro_c: float,
        tech_c: float,
        timing_c: float,
        sentiment_adj: float,
        is_exception: bool,
    ) -> str:
        parts = [f"Fusion={total} ({grade})"]
        parts.append(f"Macro×0.30={macro_c:.2f}")
        parts.append(f"Tech×0.50={tech_c:.2f}")
        parts.append(f"Timing×0.20={timing_c:.2f}")
        if sentiment_adj:
            parts.append(f"Sentiment+{sentiment_adj:.2f} (exception)")
        return " | ".join(parts)
