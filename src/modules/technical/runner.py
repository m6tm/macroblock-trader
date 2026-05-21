"""Runner de validation Phase 2 — Detection SMC sur donnees reelles.

Usage : python -m src.modules.technical.runner
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loguru import logger

from core.logger import setup_logging
from data.fetcher import DataFetcher
from data.normalizer import DataStore
from modules.technical.core import detect_bos_choch, detect_swing_highs_lows, get_trend
from modules.technical.fvg import (
    check_fvg_mitigation,
    detect_bearish_fvg,
    detect_bullish_fvg,
)
from modules.technical.liquidity import (
    detect_equal_highs,
    detect_equal_lows,
    detect_previous_session_levels,
    detect_psychological_levels,
    get_current_killzone,
)
from modules.technical.ob import (
    detect_bearish_ob,
    detect_bullish_ob,
    filter_valid_obs,
)
from modules.technical.scorer import TechnicalScorer


def main() -> int:
    setup_logging()
    logger.info("=" * 60)
    logger.info("🔬 VALIDATION PHASE 2 — MODULE TECHNIQUE SMC")
    logger.info("=" * 60)

    fetcher = DataFetcher()
    store = DataStore()

    # ------------------------------------------------------------------
    # 1. Recuperation donnees (48h ~ 576 candles M15, ~48 candles H1)
    # ------------------------------------------------------------------
    logger.info("→ Recuperation XAU/USD H1 x120 (5 jours)...")
    h1_data = fetcher.fetch_xauusd_h1(count=120)
    logger.info(f"   H1: {len(h1_data)} candles")

    logger.info("→ Recuperation XAU/USD M15 x480 (5 jours)...")
    m15_data = fetcher.fetch_xauusd_m15(count=480)
    logger.info(f"   M15: {len(m15_data)} candles")

    if len(h1_data) < 10 or len(m15_data) < 10:
        logger.error("Pas assez de donnees pour analyser — arret.")
        return 1

    # ------------------------------------------------------------------
    # 2. Structure de marche
    # ------------------------------------------------------------------
    logger.info("→ Analyse structure de marche...")
    h1_trend = get_trend(h1_data, lookback=3)
    logger.info(f"   Tendance H1: {h1_trend.value}")

    swing_h_h1, swing_l_h1 = detect_swing_highs_lows(h1_data, lookback=3)
    logger.info(f"   Swings H1 — highs={len(swing_h_h1)} lows={len(swing_l_h1)}")

    events_h1 = detect_bos_choch(h1_data, swing_h_h1, swing_l_h1)
    bos_h1 = [e for e in events_h1 if e.type == "BOS"]
    choch_h1 = [e for e in events_h1 if e.type == "CHoCH"]
    logger.info(f"   BOS H1={len(bos_h1)} | CHoCH H1={len(choch_h1)}")

    # M15
    swing_h_m15, swing_l_m15 = detect_swing_highs_lows(m15_data, lookback=5)
    logger.info(f"   Swings M15 — highs={len(swing_h_m15)} lows={len(swing_l_m15)}")

    events_m15 = detect_bos_choch(m15_data, swing_h_m15, swing_l_m15)
    bos_m15 = [e for e in events_m15 if e.type == "BOS"]
    choch_m15 = [e for e in events_m15 if e.type == "CHoCH"]
    logger.info(f"   BOS M15={len(bos_m15)} | CHoCH M15={len(choch_m15)}")

    # ------------------------------------------------------------------
    # 3. Order Blocks
    # ------------------------------------------------------------------
    logger.info("→ Detection Order Blocks...")
    bull_obs = detect_bullish_ob(m15_data, impulsion_threshold=8.0, lookback_impulse=3)
    bear_obs = detect_bearish_ob(m15_data, impulsion_threshold=8.0, lookback_impulse=3)
    logger.info(f"   OB bruts — bullish={len(bull_obs)} bearish={len(bear_obs)}")

    valid_bull = filter_valid_obs(bull_obs, m15_data, mitigation_threshold=0.5)
    valid_bear = filter_valid_obs(bear_obs, m15_data, mitigation_threshold=0.5)
    logger.info(f"   OB valides — bullish={len(valid_bull)} bearish={len(valid_bear)}")

    if valid_bull:
        ob = valid_bull[-1]
        logger.info(
            f"   Dernier Bullish OB: [{ob.ob_low:.2f}, {ob.ob_high:.2f}] "
            f"fraicheur={ob.freshness.value}"
        )
    if valid_bear:
        ob = valid_bear[-1]
        logger.info(
            f"   Dernier Bearish OB: [{ob.ob_low:.2f}, {ob.ob_high:.2f}] "
            f"fraicheur={ob.freshness.value}"
        )

    # ------------------------------------------------------------------
    # 4. Fair Value Gaps
    # ------------------------------------------------------------------
    logger.info("→ Detection FVG...")
    bull_fvgs = detect_bullish_fvg(m15_data)
    bear_fvgs = detect_bearish_fvg(m15_data)
    logger.info(f"   FVG bruts — bullish={len(bull_fvgs)} bearish={len(bear_fvgs)}")

    bull_fvgs = check_fvg_mitigation(bull_fvgs, m15_data)
    bear_fvgs = check_fvg_mitigation(bear_fvgs, m15_data)
    active_bull_fvg = [f for f in bull_fvgs if not f.mitigated]
    active_bear_fvg = [f for f in bear_fvgs if not f.mitigated]
    logger.info(f"   FVG actifs — bullish={len(active_bull_fvg)} bearish={len(active_bear_fvg)}")

    # ------------------------------------------------------------------
    # 5. Liquidite
    # ------------------------------------------------------------------
    logger.info("→ Detection liquidite...")
    eqh = detect_equal_highs(m15_data, tolerance=0.15)
    eql = detect_equal_lows(m15_data, tolerance=0.15)
    session_lvls = detect_previous_session_levels(m15_data)

    if m15_data.rows():
        current_price = float(m15_data.rows()[-1]["close"])
        psych = detect_psychological_levels(current_price)
    else:
        psych = []

    logger.info(
        f"   EQH={len(eqh)} EQL={len(eql)} "
        f"Session={len(session_lvls)} Psych={len(psych)}"
    )

    # ------------------------------------------------------------------
    # 6. Killzone
    # ------------------------------------------------------------------
    kz_name, kz_score = get_current_killzone()
    logger.info(f"   Killzone: {kz_name} (score={kz_score})")

    # ------------------------------------------------------------------
    # 7. Scoring exemple
    # ------------------------------------------------------------------
    logger.info("→ Scoring technique...")
    scorer = TechnicalScorer()

    # Exemple : on prend le dernier OB valide bullish si H1 tendance haussiere
    if valid_bull and h1_trend.value == "BULLISH":
        ob = valid_bull[-1]
        pools = eqh + session_lvls + psych
        score, grade = scorer.calculate_total(
            direction="LONG",
            h1_trend=h1_trend,
            h4_trend=h1_trend,  # simplifie — on n'a pas H4 ici
            has_bos=len(bos_m15) > 0,
            ob=ob,
            fvgs=active_bull_fvg,
            pools=pools,
        )
        logger.info(f"   Setup LONG: score={score} grade={grade}")

    if valid_bear and h1_trend.value == "BEARISH":
        ob = valid_bear[-1]
        pools = eql + session_lvls + psych
        score, grade = scorer.calculate_total(
            direction="SHORT",
            h1_trend=h1_trend,
            h4_trend=h1_trend,
            has_bos=len(bos_m15) > 0,
            ob=ob,
            fvgs=active_bear_fvg,
            pools=pools,
        )
        logger.info(f"   Setup SHORT: score={score} grade={grade}")

    # ------------------------------------------------------------------
    # 8. Validation
    # ------------------------------------------------------------------
    total_ob = len(valid_bull) + len(valid_bear)
    total_fvg = len(active_bull_fvg) + len(active_bear_fvg)

    logger.info("=" * 60)
    logger.info("📊 BILAN PHASE 2")
    logger.info(f"   OB valides detectes : {total_ob} (minimum attendu: 3)")
    logger.info(f"   FVG actifs detectes : {total_fvg} (minimum attendu: 2)")
    logger.info(f"   BOS M15 : {len(bos_m15)}")
    logger.info(f"   CHoCH M15 : {len(choch_m15)}")
    logger.info("=" * 60)

    ok = total_ob >= 3 and total_fvg >= 2
    if ok:
        logger.success("✅ Phase 2 VALIDE")
    else:
        logger.warning("⚠️ Phase 2 partielle — pas assez de setups dans la fenetre 48h")

    return 0


if __name__ == "__main__":
    sys.exit(main())
