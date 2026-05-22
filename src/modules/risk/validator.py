"""Validation des parametres de risque d'un plan de trade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from loguru import logger


@dataclass
class ValidationCheck:
    """Resultat d'un check de validation."""

    name: str
    passed: bool
    reason: str = ""


@dataclass
class ValidationResult:
    """Resultat complet de la validation risque."""

    checks: List[ValidationCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> List[ValidationCheck]:
        return [c for c in self.checks if not c.passed]

    def add(self, name: str, passed: bool, reason: str = "") -> None:
        self.checks.append(ValidationCheck(name=name, passed=passed, reason=reason))
        if not passed:
            logger.warning(f"Risk check FAIL — {name}: {reason}")
        else:
            logger.debug(f"Risk check PASS — {name}")


class RiskValidator:
    """Valide qu'un plan respecte toutes les regles de risque."""

    def validate_sl(
        self,
        sl_distance_dollars: float,
        entry_price: float,
        sl_min_dollars: float,
        sl_max_pct_price: float,
    ) -> ValidationCheck:
        """Valide la distance SL."""
        if sl_distance_dollars < sl_min_dollars:
            return ValidationCheck(
                name="SL_MIN",
                passed=False,
                reason=f"SL ${sl_distance_dollars:.2f} < min ${sl_min_dollars}",
            )
        max_sl = entry_price * (sl_max_pct_price / 100)
        if sl_distance_dollars > max_sl:
            return ValidationCheck(
                name="SL_MAX",
                passed=False,
                reason=f"SL ${sl_distance_dollars:.2f} > max ${max_sl:.2f} ({sl_max_pct_price}%)",
            )
        return ValidationCheck(name="SL_BOUNDS", passed=True)

    def validate_rr(
        self,
        rr_ratio: float,
        rr_minimum: float,
    ) -> ValidationCheck:
        """Valide le R:R minimum."""
        if rr_ratio < rr_minimum:
            return ValidationCheck(
                name="R_R_MINIMUM",
                passed=False,
                reason=f"R:R {rr_ratio} < minimum {rr_minimum}",
            )
        return ValidationCheck(name="R_R_MINIMUM", passed=True)

    def validate_score(
        self,
        score_total: float,
        min_signal: float = 2.5,
    ) -> ValidationCheck:
        """Valide que le score total est suffisant."""
        if score_total < min_signal:
            return ValidationCheck(
                name="SCORE_MINIMUM",
                passed=False,
                reason=f"Score {score_total} < minimum {min_signal}",
            )
        return ValidationCheck(name="SCORE_MINIMUM", passed=True)

    def run_full_validation(
        self,
        sl_distance_dollars: float,
        entry_price: float,
        rr_ratio: float,
        score_total: float,
        sl_min_dollars: float,
        sl_max_pct_price: float,
        rr_minimum: float,
    ) -> ValidationResult:
        """Execute toute la checklist de validation."""
        result = ValidationResult()
        result.add(
            "SCORE_MINIMUM",
            score_total >= 2.5,
            f"Score {score_total} < 2.5" if score_total < 2.5 else "",
        )
        result.add(
            "SL_MIN",
            sl_distance_dollars >= sl_min_dollars,
            f"SL ${sl_distance_dollars:.2f} < ${sl_min_dollars}" if sl_distance_dollars < sl_min_dollars else "",
        )
        max_sl = entry_price * (sl_max_pct_price / 100)
        result.add(
            "SL_MAX",
            sl_distance_dollars <= max_sl,
            f"SL ${sl_distance_dollars:.2f} > ${max_sl:.2f}" if sl_distance_dollars > max_sl else "",
        )
        result.add(
            "R_R_MINIMUM",
            rr_ratio >= rr_minimum,
            f"R:R {rr_ratio} < {rr_minimum}" if rr_ratio < rr_minimum else "",
        )
        return result
