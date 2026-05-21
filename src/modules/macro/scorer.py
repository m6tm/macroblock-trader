"""Scoring Macro Or — Agrégation des 5 piliers en un score -3 a +3.

Formule :
Score Macro = (DXY × 0.30) + (Yields × 0.25) + (Fed × 0.20)
            + (Risk × 0.15) + (Inflation × 0.10)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from loguru import logger

from data.calendar import EconomicEvent
from modules.macro.core import MacroSnapshot


@dataclass
class MacroScore:
    total: float
    grade: str
    dxy_component: float
    yields_component: float
    fed_component: float
    risk_component: float
    inflation_component: float
    justification: str


class MacroScorer:
    """Calcule le score macro specifique a l'or."""

    # Poids des piliers
    W_DXY = 0.30
    W_YIELDS = 0.25
    W_FED = 0.20
    W_RISK = 0.15
    W_INFLATION = 0.10

    def calculate_dxy_component(self, dxy_pct: float, dxy_trend: str) -> float:
        """DXY ↑ = Or ↓ (inverse fort).

        Returns:
            Score entre -1.5 et +1.5 (avant ponderation)
        """
        if dxy_pct > 0.3:
            return -1.5  # Fortement baissier
        if dxy_pct > 0.15:
            return -1.0
        if dxy_pct < -0.3:
            return 1.5  # Fortement haussier
        if dxy_pct < -0.15:
            return 1.0
        return 0.0  # Neutre

    def calculate_yields_component(
        self, tips_value: Optional[float], tips_trend: str
    ) -> float:
        """Yields reels ↑ = Or ↓.

        Returns:
            Score entre -1.5 et +1.5 (avant ponderation)
        """
        if tips_value is None:
            return 0.0

        if tips_value > 2.0 and tips_trend == "UP":
            return -1.5
        if tips_value > 1.0 and tips_trend == "UP":
            return -1.0
        if tips_value > 1.0 and tips_trend == "NEUTRAL":
            return -0.5
        if tips_value < 0.0:
            return 1.5
        if tips_value < 1.0 and tips_trend == "DOWN":
            return 1.0
        if tips_value < 1.0 and tips_trend == "NEUTRAL":
            return 0.5
        return 0.0

    def calculate_fed_component(self, events: List[EconomicEvent]) -> float:
        """Déduit la posture Fed du calendrier economique.

        Cherche les mots-cles hawkish/dovish dans les evenements recents.
        Returns:
            Score entre -1.5 et +1.5 (avant ponderation)
        """
        hawkish_keywords = {"rate hike", "tightening", "qt", "hawkish", "raise rates"}
        dovish_keywords = {"rate cut", "easing", "qe", "dovish", "lower rates", "pause"}

        score = 0.0
        has_fomc = False
        for e in events:
            title_lower = e.title.lower()
            if "fomc" in title_lower:
                has_fomc = True
            if any(kw in title_lower for kw in hawkish_keywords):
                score -= 0.5
            if any(kw in title_lower for kw in dovish_keywords):
                score += 0.5

        # FOMC Meeting Minutes = neutre par defaut sauf si keywords trouves
        if has_fomc and score == 0.0:
            score = 0.0  # Neutre — attendre le contenu

        return max(-1.5, min(1.5, score))

    def calculate_risk_component(
        self, vix: Optional[float], sp500_pct: float
    ) -> float:
        """Risk-Off = Or ↑. Source degradee sur Termux.

        Returns:
            Score entre -1.5 et +1.5 (avant ponderation)
        """
        if vix is not None:
            if vix > 25:
                return 1.5
            if vix > 20:
                return 1.0
            if vix < 12:
                return -1.5
            if vix < 15:
                return -1.0

        # Fallback sur SP500 si VIX indisponible
        if sp500_pct < -2.0:
            return 1.0
        if sp500_pct < -1.0:
            return 0.5
        if sp500_pct > 2.0:
            return -1.0
        if sp500_pct > 1.0:
            return -0.5

        return 0.0

    def calculate_inflation_component(self, events: List[EconomicEvent]) -> float:
        """Surprise inflation haussiere = Or ↑ (hedge).

        Detecte CPI/PPI avec actual > forecast.
        Returns:
            Score entre -1.5 et +1.5 (avant ponderation)
        """
        score = 0.0
        for e in events:
            title_lower = e.title.lower()
            if "cpi" in title_lower or "ppi" in title_lower or "pce" in title_lower:
                # Si on a actual et forecast, on compare
                if e.actual and e.forecast:
                    try:
                        actual_val = float(e.actual.replace("%", ""))
                        forecast_val = float(e.forecast.replace("%", ""))
                        diff = actual_val - forecast_val
                        if diff > 0.3:
                            score += 1.0
                        elif diff > 0.1:
                            score += 0.5
                        elif diff < -0.1:
                            score -= 0.5
                    except ValueError:
                        continue
                else:
                    # Sans donnees chiffrees — evenement connu = potentiel volatile
                    score += 0.0  # Neutre
        return max(-1.5, min(1.5, score))

    def calculate_total(self, snapshot: MacroSnapshot) -> MacroScore:
        """Calcule le score macro final.

        Returns:
            MacroScore avec total entre -3 et +3.
        """
        c_dxy = self.calculate_dxy_component(
            snapshot.dxy_momentum_pct, snapshot.dxy_trend
        )
        c_yields = self.calculate_yields_component(
            snapshot.tips_10y_value, snapshot.tips_10y_trend
        )
        c_fed = self.calculate_fed_component(snapshot.upcoming_events)
        c_risk = self.calculate_risk_component(
            snapshot.vix_value, snapshot.sp500_momentum_pct
        )
        c_inflation = self.calculate_inflation_component(snapshot.upcoming_events)

        total = (
            c_dxy * self.W_DXY
            + c_yields * self.W_YIELDS
            + c_fed * self.W_FED
            + c_risk * self.W_RISK
            + c_inflation * self.W_INFLATION
        )

        total = round(max(-3.0, min(3.0, total)), 2)
        grade = self._grade(total)
        justification = self._build_justification(
            total, c_dxy, c_yields, c_fed, c_risk, c_inflation, snapshot
        )

        logger.info(f"Score Macro Or: {total} ({grade})")
        return MacroScore(
            total=total,
            grade=grade,
            dxy_component=round(c_dxy * self.W_DXY, 2),
            yields_component=round(c_yields * self.W_YIELDS, 2),
            fed_component=round(c_fed * self.W_FED, 2),
            risk_component=round(c_risk * self.W_RISK, 2),
            inflation_component=round(c_inflation * self.W_INFLATION, 2),
            justification=justification,
        )

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 2.5:
            return "VENT HAUSSIER PARFAIT"
        if score >= 1.5:
            return "VENT HAUSSIER MODERE"
        if score >= 0.5:
            return "POUSSEE HAUSSIERE"
        if score > -0.5:
            return "NEUTRE"
        if score > -1.5:
            return "PRESSION BAISSIERE"
        if score > -2.5:
            return "VENT BAISSIER MODERE"
        return "VENT BAISSIER PARFAIT"

    @staticmethod
    def _build_justification(
        total: float,
        c_dxy: float,
        c_yields: float,
        c_fed: float,
        c_risk: float,
        c_inflation: float,
        snapshot: MacroSnapshot,
    ) -> str:
        parts = [f"Score Macro Or: {total}"]
        parts.append(f"DXY: {snapshot.dxy_momentum_pct:+.2f}% → {c_dxy:.2f}")
        if snapshot.tips_10y_value is not None:
            parts.append(f"TIPS10Y: {snapshot.tips_10y_value:.2f}% → {c_yields:.2f}")
        else:
            parts.append("TIPS10Y: indisponible → 0.00")
        parts.append(f"Fed: {c_fed:.2f}")
        parts.append(f"Risk: {c_risk:.2f}")
        parts.append(f"Inflation: {c_inflation:.2f}")
        if snapshot.upcoming_events:
            ev_str = ", ".join(
                f"{e.title} ({e.currency})" for e in snapshot.upcoming_events[:3]
            )
            parts.append(f"Evenements: {ev_str}")
        return " | ".join(parts)
