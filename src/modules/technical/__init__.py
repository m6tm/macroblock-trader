"""Module Technique SMC — Smart Money Concepts pour XAU/USD."""

import sys
from pathlib import Path

_src_root = Path(__file__).resolve().parent.parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from modules.technical.core import (
    StructureEvent,
    SwingPoint,
    Trend,
    detect_bos_choch,
    detect_swing_highs_lows,
    get_trend,
    get_trend_label,
)
from modules.technical.fvg import (
    FairValueGap,
    FVGType,
    check_fvg_mitigation,
    detect_bearish_fvg,
    detect_bullish_fvg,
    fvg_ob_confluence,
)
from modules.technical.liquidity import (
    LiquidityPool,
    detect_equal_highs,
    detect_equal_lows,
    detect_previous_session_levels,
    detect_psychological_levels,
    get_current_killzone,
    is_killzone_active,
)
from modules.technical.ob import (
    OBFreshness,
    OBType,
    OrderBlock,
    calculate_freshness,
    detect_bearish_ob,
    detect_bullish_ob,
    filter_valid_obs,
)
from modules.technical.scorer import TechnicalScorer, TechnicalSetup, build_setup

__all__ = [
    "Trend",
    "SwingPoint",
    "StructureEvent",
    "detect_swing_highs_lows",
    "detect_bos_choch",
    "get_trend",
    "get_trend_label",
    "OBType",
    "OBFreshness",
    "OrderBlock",
    "detect_bullish_ob",
    "detect_bearish_ob",
    "calculate_freshness",
    "filter_valid_obs",
    "FVGType",
    "FairValueGap",
    "detect_bullish_fvg",
    "detect_bearish_fvg",
    "check_fvg_mitigation",
    "fvg_ob_confluence",
    "LiquidityPool",
    "detect_equal_highs",
    "detect_equal_lows",
    "detect_psychological_levels",
    "detect_previous_session_levels",
    "get_current_killzone",
    "is_killzone_active",
    "TechnicalScorer",
    "TechnicalSetup",
    "build_setup",
]
