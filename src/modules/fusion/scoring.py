"""Moteur Fusion & Scoring — Agregation Macro / Technique / Timing.

Formule :
    SCORE TOTAL = (Score Macro × 0.30) + (Score Technique × 0.50) + (Score Timing × 0.20)

Grade :
    ≥ 3.5  → A+ (Signal Fort)
    2.5–3.5 → B (Signal Moyen)
    1.5–2.5 → C (Signal Faible — logger, ne pas notifier)
    < 1.5   → N/A (Ignorer)

Matrice Macro × Technique :
    - A+ + Macro aligned  → A+ autorisé
    - A+ + Macro neutre   → B autorisé (exception si timing=2)
    - A+ + Macro contre   → REJET
    - B  + Macro aligned  → B autorisé
    - B  + Macro neutre   → REJET
    - B  + Macro contre   → REJET
    - <B + quelque soit   → REJET

Exceptions sentiment :
    Macro = -3 + Tech = 5 + Sentiment = +2 → Signal B autorisé (contre-trend)
    Macro = 0 + Tech = 5 + Timing = 2 → Signal B autorisé (setup exceptionnel)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

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
    matrix_authorized: bool = True
    matrix_reason: str = ""


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

        # Exception macro neutre + tech 5 + timing 2
        matrix_adjustment = 0.0
        if self._is_neutral_macro_exception(macro.total, technical.score, timing_score):
            is_exception = True
            matrix_adjustment = 0.0  # Pas de bonus score, mais autorisation matrix
            logger.info(
                f"Exception macro neutre — setup exceptionnel sans vent contraire "
                f"(macro={macro.total}, tech={technical.score}, timing={timing_score})"
            )

        total = round(total, 2)

        # Matrice de decision Macro × Technique
        authorized, matrix_reason = self.evaluate_macro_technique_matrix(
            macro, technical, timing_score, is_exception
        )

        # Rejection stricte si score < 2.5 et pas d'exception
        if total < self.MIN_SIGNAL and not is_exception:
            grade = "N/A"
            authorized = False
            if authorized:  # matrice autorisait mais score insuffisant
                matrix_reason = f"Score {total} < {self.MIN_SIGNAL} — signal insuffisant"
            else:
                matrix_reason = f"{matrix_reason} | Score {total} < {self.MIN_SIGNAL}"
        else:
            grade = self._grade(total, is_exception)

        justification = self._build_justification(
            total, grade, macro_component, technical_component,
            timing_component, sentiment_adjustment, is_exception, matrix_reason
        )

        logger.info(f"Score Fusion: {total} ({grade}) | exception={is_exception} | matrix_ok={authorized}")
        return FusionScore(
            total=total,
            grade=grade,
            macro_component=round(macro_component, 2),
            technical_component=round(technical_component, 2),
            timing_component=round(timing_component, 2),
            sentiment_adjustment=round(sentiment_adjustment, 2),
            justification=justification,
            is_exception=is_exception,
            matrix_authorized=authorized,
            matrix_reason=matrix_reason,
        )

    # ------------------------------------------------------------------
    # Matrice de decision Macro × Technique
    # ------------------------------------------------------------------

    def evaluate_macro_technique_matrix(
        self,
        macro: MacroScore,
        technical: TechnicalSetup,
        timing_score: float,
        is_exception: bool = False,
    ) -> Tuple[bool, str]:
        """Evalue si le setup est autorise par la matrice Macro × Technique.

        Returns:
            Tuple (autorise, raison).
        """
        tech_score = technical.score
        macro_total = macro.total
        direction = technical.direction

        # Tech < 3.0 → toujours rejeté
        if tech_score < 3.0:
            return False, f"Setup tech {tech_score} < 3.0 — pas de signal"

        # Determiner l'alignement macro
        aligned = self._is_macro_aligned(macro_total, direction)
        against = self._is_macro_against(macro_total, direction)
        neutral = abs(macro_total) < 0.5

        if tech_score >= 5.0:
            # SETUP A+ (5/5)
            if aligned:
                return True, "A+ + Macro aligned → Signal Fort (A+)"
            if neutral:
                if timing_score >= 2.0 or is_exception:
                    return True, "A+ + Macro neutre + Timing 2 → Signal B autorise (exception)"
                return False, "A+ + Macro neutre mais timing < 2 → rejete"
            if against:
                return False, "A+ + Macro contre → PAS DE TRADE"

        elif tech_score >= 3.0:
            # SETUP B (3-4/5)
            if aligned:
                return True, "B + Macro aligned → Signal B autorise"
            if neutral:
                return False, "B + Macro neutre → PAS DE TRADE"
            if against:
                return False, "B + Macro contre → PAS DE TRADE"

        return False, "Setup tech insuffisant"

    @staticmethod
    def _is_macro_aligned(macro_total: float, direction: str) -> bool:
        """Macro est-il dans le meme sens que le trade ?"""
        if direction == "LONG":
            return macro_total >= 1.5
        return macro_total <= -1.5

    @staticmethod
    def _is_macro_against(macro_total: float, direction: str) -> bool:
        """Macro est-il contre le sens du trade ?"""
        if direction == "LONG":
            return macro_total <= -1.5
        return macro_total >= 1.5

    @staticmethod
    def _is_neutral_macro_exception(macro_total: float, tech_score: float, timing_score: float) -> bool:
        """Exception : Macro neutre (0) + Tech 5 + Timing 2 → Signal B autorise."""
        return abs(macro_total) < 0.5 and tech_score >= 5.0 and timing_score >= 2.0

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
        matrix_reason: str = "",
    ) -> str:
        parts = [f"Fusion={total} ({grade})"]
        parts.append(f"Macro×0.30={macro_c:.2f}")
        parts.append(f"Tech×0.50={tech_c:.2f}")
        parts.append(f"Timing×0.20={timing_c:.2f}")
        if sentiment_adj:
            parts.append(f"Sentiment+{sentiment_adj:.2f} (exception)")
        if matrix_reason:
            parts.append(f"Matrix: {matrix_reason}")
        return " | ".join(parts)
