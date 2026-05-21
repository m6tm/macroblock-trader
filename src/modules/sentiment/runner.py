"""Runner de validation Phase 4 — Module Sentiment.

Usage : python -m src.modules.sentiment.runner
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loguru import logger

from core.logger import setup_logging
from modules.sentiment.core import SentimentFetcher
from modules.sentiment.scorer import SentimentScorer


def main() -> int:
    setup_logging()
    logger.info("=" * 60)
    logger.info("💭 VALIDATION PHASE 4 — MODULE SENTIMENT")
    logger.info("=" * 60)

    fetcher = SentimentFetcher()
    scorer = SentimentScorer()

    # 1. Snapshot sentiment
    logger.info("→ Capture snapshot sentiment...")
    snapshot = fetcher.snapshot()

    if snapshot.cot:
        logger.info(
            f"   COT GOLD — CommNet={snapshot.cot.comm_net:+d} "
            f"NonCommNet={snapshot.cot.non_comm_net:+d} "
            f"Extreme={snapshot.cot.is_historic_extreme}({snapshot.cot.extreme_type})"
        )
    else:
        logger.info("   COT: indisponible (mode degrade)")

    if snapshot.retail:
        logger.info(
            f"   Retail — {snapshot.retail.long_pct:.0f}% long / "
            f"{snapshot.retail.short_pct:.0f}% short"
        )
    else:
        logger.info("   Retail: indisponible (mode degrade)")

    if snapshot.fear_greed:
        logger.info(
            f"   FearGreed — {snapshot.fear_greed.value:.0f} "
            f"({snapshot.fear_greed.classification})"
        )
    else:
        logger.info("   FearGreed: indisponible (mode degrade)")

    # 2. Scoring
    logger.info("→ Calcul score sentiment...")
    score = scorer.calculate_total(snapshot)
    logger.info(f"   Score: {score.total} | Grade: {score.grade}")
    logger.info(f"   Composantes:")
    logger.info(f"      COT        : {score.cot_signal:+.2f}")
    logger.info(f"      Retail     : {score.retail_signal:+.2f}")
    logger.info(f"      FearGreed  : {score.fear_greed_signal:+.2f}")
    logger.info(f"   Justification: {score.justification}")

    # 3. Validation
    logger.info("=" * 60)
    logger.info("📊 BILAN PHASE 4")
    logger.info(f"   Score Sentiment: {score.total} ({score.grade})")
    logger.info("=" * 60)

    ok = -2.0 <= score.total <= 2.0
    if ok:
        logger.success("✅ Phase 4 VALIDE")
    else:
        logger.error("❌ Phase 4 invalide — score hors bornes")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
