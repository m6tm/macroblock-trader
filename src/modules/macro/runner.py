"""Runner de validation Phase 3 — Module Macro.

Usage : python -m src.modules.macro.runner
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loguru import logger

from core.logger import setup_logging
from modules.macro.core import MacroFetcher
from modules.macro.locks import MacroLockDetector
from modules.macro.scorer import MacroScorer


def main() -> int:
    setup_logging()
    logger.info("=" * 60)
    logger.info("🌍 VALIDATION PHASE 3 — MODULE MACRO")
    logger.info("=" * 60)

    fetcher = MacroFetcher()
    scorer = MacroScorer()
    locks = MacroLockDetector()

    # 1. Snapshot macro
    logger.info("→ Capture snapshot macro...")
    snapshot = fetcher.snapshot()
    logger.info(f"   DXY proxy: {snapshot.dxy_momentum_pct:+.3f}% | {snapshot.dxy_trend}")
    if snapshot.tips_10y_value is not None:
        logger.info(f"   TIPS 10Y: {snapshot.tips_10y_value:.2f}% | {snapshot.tips_10y_trend}")
    else:
        logger.info("   TIPS 10Y: indisponible (FRED_API_KEY manquant)")

    logger.info(f"   Evenements haut impact (4h): {len(snapshot.upcoming_events)}")
    for e in snapshot.upcoming_events[:5]:
        logger.info(
            f"      📅 {e.date} {e.time} | {e.currency} | {e.title} | {e.impact}"
        )

    # 2. Scoring
    logger.info("→ Calcul score macro...")
    score = scorer.calculate_total(snapshot)
    logger.info(f"   Score: {score.total} | Grade: {score.grade}")
    logger.info(f"   Composantes:")
    logger.info(f"      DXY      : {score.dxy_component:+.2f}")
    logger.info(f"      Yields   : {score.yields_component:+.2f}")
    logger.info(f"      Fed      : {score.fed_component:+.2f}")
    logger.info(f"      Risk     : {score.risk_component:+.2f}")
    logger.info(f"      Inflation: {score.inflation_component:+.2f}")
    logger.info(f"   Justification: {score.justification}")

    # 3. Locks
    logger.info("→ Verification macro locks...")
    active_locks = locks.get_active_locks(
        dxy_change_pct=snapshot.dxy_momentum_pct,
        yield_change_bps=0.0,  # Pas de donnees temps reel yields sur M15
    )
    if active_locks:
        logger.warning(f"   ⚠️  {len(active_locks)} lock(s) actif(s):")
        for lock in active_locks:
            logger.warning(
                f"      🔒 {lock.name} | {lock.reason} | "
                f"severite={lock.severity} | jusqu'a {lock.active_until.isoformat()}"
            )
    else:
        logger.info("   ✅ Aucun macro lock actif")

    # 4. Validation
    logger.info("=" * 60)
    logger.info("📊 BILAN PHASE 3")
    logger.info(f"   Score Macro Or: {score.total} ({score.grade})")
    logger.info(f"   Locks actifs: {len(active_locks)}")
    logger.info("=" * 60)

    # Validation simple : le score doit etre calcule et coherent
    ok = -3.0 <= score.total <= 3.0
    if ok:
        logger.success("✅ Phase 3 VALIDE")
    else:
        logger.error("❌ Phase 3 invalide — score hors bornes")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
