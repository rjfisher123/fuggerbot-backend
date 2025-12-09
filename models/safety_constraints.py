"""
Safety Constraints Engine.

Enforces hard safety rails (drift spike halt, high-vol auto-flat, coherence breaks).
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SafetyConstraintsEngine:
    """Evaluates safety constraints before trades."""

    def __init__(
        self,
        drift_halt_threshold: float = 0.8,
        volatility_flat_threshold: float = 0.35,
        coherence_break_threshold: float = 0.5
    ):
        """
        Initialize safety engine.

        Args:
            drift_halt_threshold: Drift score to halt trading
            volatility_flat_threshold: Volatility to flatten positions
            coherence_break_threshold: Coherence score below which to stop trading
        """
        self.drift_halt_threshold = drift_halt_threshold
        self.volatility_flat_threshold = volatility_flat_threshold
        self.coherence_break_threshold = coherence_break_threshold

    def evaluate(
        self,
        drift_score: float,
        volatility: float,
        coherence_score: float,
        frs_score: float,
        meta_reliability: float
    ) -> Dict[str, Any]:
        """
        Evaluate safety constraints.

        Returns:
            Dict with pass/fail status and recommended actions
        """
        issues = []

        if drift_score >= self.drift_halt_threshold:
            issues.append("DRIFT_SPIKE")

        if volatility >= self.volatility_flat_threshold:
            issues.append("HIGH_VOLATILITY")

        if coherence_score <= self.coherence_break_threshold:
            issues.append("COHERENCE_BREAK")

        if frs_score < 0.4 or meta_reliability < 0.4:
            issues.append("LOW_CONFIDENCE")

        all_clear = len(issues) == 0

        return {
            "all_clear": all_clear,
            "issues": issues,
            "blocking_reason": issues[0] if issues else None,
            "action": self._recommended_action(issues)
        }

    @staticmethod
    def _recommended_action(issues):
        if "DRIFT_SPIKE" in issues:
            return "HALT_TRADING"
        if "HIGH_VOLATILITY" in issues:
            return "FLATTEN_POSITIONS"
        if "COHERENCE_BREAK" in issues:
            return "STOP_NEW_TRADES"
        if "LOW_CONFIDENCE" in issues:
            return "WAIT_FOR_CONFIRMATION"
        return "PROCEED"




