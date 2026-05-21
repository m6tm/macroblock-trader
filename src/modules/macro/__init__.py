"""Module Macro — Vent dominant pour l'or (XAU/USD)."""

import sys
from pathlib import Path

_src_root = Path(__file__).resolve().parent.parent.parent
if str(_src_root) not in sys.path:
    sys.path.insert(0, str(_src_root))

from modules.macro.core import MacroFetcher, MacroSnapshot
from modules.macro.locks import MacroLock, MacroLockDetector
from modules.macro.scorer import MacroScore, MacroScorer

__all__ = [
    "MacroFetcher",
    "MacroSnapshot",
    "MacroLock",
    "MacroLockDetector",
    "MacroScore",
    "MacroScorer",
]
