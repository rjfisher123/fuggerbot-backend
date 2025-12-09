"""
Context module for FuggerBot.

Provides data structures and utilities for tracking macroeconomic regimes
and their impact on trading decisions.
"""
from context.schemas import RegimeType, MacroRegime
from context.tracker import RegimeTracker, NEUTRAL_REGIME

__all__ = [
    "RegimeType",
    "MacroRegime",
    "RegimeTracker",
    "NEUTRAL_REGIME",
]

