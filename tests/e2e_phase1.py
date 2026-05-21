"""Test E2E Phase 1 — Donnees reelles, aucun mock.

Ce script recupere de vraies donnees sur Internet :
- XAU/USD M5/M15/H1/H4 via OANDA (temps reel)
- Calendrier economique (endpoint public ForexFactory)
- DXY proxy via EUR/USD sur OANDA
- Les stocke dans le DataStore natif
- Affiche un resume actionnable
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loguru import logger

from core.logger import setup_logging
from data.calendar import EconomicCalendar
from data.normalizer import DataStore, OHLCVNormalizer
from data.fetcher import DataFetcher


def e2e_calendar() -> None:
    """Recupere le vrai calendrier economique de la semaine."""
    logger.info("→ Recuperation calendrier economique (endpoint public)...")
    cal = EconomicCalendar(cache_ttl=300)
    events = cal.fetch()

    logger.info(f"   {len(events)} evenements bruts recus")

    high = [e for e in events if e.is_high_impact and e.is_gold_relevant]
    logger.info(f"   {len(high)} evenements HAUT IMPACT pertinents pour l'or")

    if high:
        logger.info("   Prochains evenements cles :")
        for e in high[:5]:
            logger.info(
                f"      📅 {e.date} {e.time} | {e.currency} | {e.title} "
                f"| impact={e.impact} | prev={e.previous} | fore={e.forecast}"
            )
    else:
        logger.info("   Aucun evenement haut impact Or dans les donnees actuelles.")

    return events


def e2e_oanda(store: DataStore) -> None:
    """Recupere les vraies donnees XAU/USD et DXY proxy via OANDA."""
    logger.info("→ Recuperation donnees OANDA (temps reel)...")
    fetcher = DataFetcher(store=store)

    for tf in ("M5", "M15", "H1", "H4"):
        data = fetcher.fetch_xauusd(tf, count=5)
        if len(data) > 0:
            latest = data.rows()[-1]
            logger.info(
                f"   ✅ XAU/USD {tf}: {len(data)} candles — "
                f"Dernier O={latest['open']:.2f} H={latest['high']:.2f} "
                f"L={latest['low']:.2f} C={latest['close']:.2f}"
            )
            if tf == "M5" and len(data) > 1:
                gaps = OHLCVNormalizer.check_gaps(data, "M5")
                if gaps:
                    logger.warning(f"   ⚠️  {len(gaps)} gap(s) detecte(s) sur M5")
                else:
                    logger.info("   ✅ Aucun gap detecte sur M5")
        else:
            logger.warning(f"   ❌ XAU/USD {tf}: vide — cle OANDA manquante ?")

    # DXY proxy
    dxy = fetcher.fetch_dxy_m15(count=5)
    if len(dxy) > 0:
        latest = dxy.rows()[-1]
        logger.info(
            f"   ✅ DXY-PROXY (EUR/USD) M15: {len(dxy)} candles — "
            f"Dernier C={latest['close']:.5f}"
        )
    else:
        logger.warning("   ❌ DXY-PROXY: vide")


def e2e_summary(store: DataStore) -> None:
    """Affiche le bilan du DataStore."""
    logger.info("→ Bilan DataStore temps reel :")
    summary = store.summary()
    if not summary:
        logger.warning("   DataStore vide — aucune donnee n'a pu etre recuperee.")
        return

    for key, count in summary.items():
        logger.info(f"   📦 {key} : {count} candles")
        latest = store.get_latest(*key.split("|"))
        if latest:
            logger.info(
                f"      Derniere : O={latest['open']} H={latest['high']} "
                f"L={latest['low']} C={latest['close']} V={latest['volume']}"
            )


def main() -> int:
    setup_logging()
    logger.info("=" * 60)
    logger.info("🧪 TEST E2E — PHASE 1 : COUCHE DONNEES (donnees reelles)")
    logger.info("=" * 60)

    store = DataStore()

    # 1. Calendrier
    e2e_calendar()
    logger.info("")

    # 2. Donnees marché OANDA
    e2e_oanda(store)
    logger.info("")

    # 3. Resume
    e2e_summary(store)
    logger.info("")

    logger.success("🏁 E2E Phase 1 termine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
