"""Calcul de la taille de position (lots) selon le capital et le risque.

Formule (spec Or) :
    Taille (lots) = Risque en $ / Distance SL en $

Exemple :
    Capital = 10 000 $, Risk A+ = 1.0%, SL = 35 $
    Risk$ = 100 $, Lots = 100 / 35 = 0.28 lots
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from loguru import logger


@dataclass
class SizingResult:
    """Resultat du calcul de sizing."""

    position_size_lots: float
    risk_amount_dollars: float
    risk_pct: float
    is_realistic: bool
    reason: str = ""


class SizingCalculator:
    """Calcule la taille de position pour XAU/USD."""

    # Valeur approximative d'un pip (0.01$) pour 1 lot standard (100 oz) sur XAU/USD
    # En pratique cela depend du broker, mais 1$ / pip / lot est standard
    PIP_VALUE_PER_LOT = 1.0  # 1 pip = 0.01$ → 100 oz × 0.01$ = 1$

    def calculate(
        self,
        capital: float,
        risk_pct: float,
        sl_distance_dollars: float,
        grade: str = "B",
    ) -> SizingResult:
        """Calcule le sizing.

        Args:
            capital: Capital virtuel en $
            risk_pct: Pourcentage du capital a risquer
            sl_distance_dollars: Distance SL en $
            grade: Grade du signal (A+ ou B) — informatif

        Returns:
            SizingResult avec lots, risk_amount, etc.
        """
        if capital <= 0:
            return SizingResult(
                position_size_lots=0.0,
                risk_amount_dollars=0.0,
                risk_pct=0.0,
                is_realistic=False,
                reason="Capital invalide",
            )

        if sl_distance_dollars <= 0:
            return SizingResult(
                position_size_lots=0.0,
                risk_amount_dollars=0.0,
                risk_pct=0.0,
                is_realistic=False,
                reason="Distance SL invalide",
            )

        risk_amount = capital * (risk_pct / 100.0)

        # Formule spec : lots = risk$ / SL$
        lots = risk_amount / sl_distance_dollars

        # Bornes realistes pour l'or
        # Min : 0.01 lot (micro), Max : 10.0 lots (limite prudente sur 10k$+)
        is_realistic = 0.01 <= lots <= 10.0
        reason = ""
        if lots < 0.01:
            reason = f"Sizing trop faible ({lots:.4f} lots < 0.01)"
            lots = 0.0
            is_realistic = False
        elif lots > 10.0:
            reason = f"Sizing trop eleve ({lots:.2f} lots > 10.0) — over-leverage"
            lots = 0.0
            is_realistic = False

        logger.info(
            f"Sizing {grade} | Capital=${capital:.0f} | Risk={risk_pct}% "
            f"(${risk_amount:.2f}) | SL=${sl_distance_dollars:.2f} → {lots:.2f} lots"
        )

        return SizingResult(
            position_size_lots=lots,
            risk_amount_dollars=risk_amount,
            risk_pct=risk_pct,
            is_realistic=is_realistic,
            reason=reason,
        )

    @staticmethod
    def get_risk_pct_for_grade(grade: str, risk_a_plus: float, risk_b: float) -> float:
        """Retourne le % de risque selon le grade."""
        if grade == "A+":
            return risk_a_plus
        return risk_b
