"""
Position Sizing Engine (Kelly-Lite + Stability Constraints).

Calculates optimal position size based on risk metrics and stability.
"""
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculates position sizes with stability constraints."""
    
    def __init__(
        self,
        max_position_size: float = 0.10,  # 10% max per position
        risk_tolerance: float = 0.02,  # 2% max risk per trade
        kelly_fraction: float = 0.25  # Use 25% of Kelly criterion
    ):
        """
        Initialize position sizer.
        
        Args:
            max_position_size: Maximum position size as fraction of portfolio
            risk_tolerance: Maximum risk per trade as fraction of portfolio
            kelly_fraction: Fraction of Kelly criterion to use (0.25 = Kelly-lite)
        """
        self.max_position_size = max_position_size
        self.risk_tolerance = risk_tolerance
        self.kelly_fraction = kelly_fraction
    
    def calculate_position_size(
        self,
        expected_return_pct: float,
        risk_pct: float,
        fqs_score: float,
        regime: Dict[str, Any],
        drift_score: Optional[float] = None,
        stability_factor: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate recommended position size.
        
        Args:
            expected_return_pct: Expected return percentage
            risk_pct: Risk/uncertainty percentage
            fqs_score: Forecast Quality Score (0-1)
            regime: Regime classification dict
            drift_score: Optional drift score (0-1, higher = more drift)
            stability_factor: Optional stability factor (0-1, higher = more stable)
            
        Returns:
            Dict with position size recommendation and breakdown
        """
        # Base Kelly-lite calculation
        if risk_pct <= 0:
            kelly_base = 0.0
        else:
            # Kelly = (expected_return / risk) * win_probability
            # Simplified: use expected_return/risk as proxy
            kelly_ratio = expected_return_pct / risk_pct
            kelly_base = kelly_ratio * self.kelly_fraction
        
        # Apply FQS multiplier
        fqs_multiplier = fqs_score
        
        # Apply stability factor (if provided)
        if stability_factor is not None:
            stability_multiplier = stability_factor
        else:
            # Default: assume moderate stability
            stability_multiplier = 0.7
        
        # Apply regime adjustment
        regime_type = regime.get("regime", "normal")
        regime_multiplier = self._get_regime_multiplier(regime_type)
        
        # Apply drift penalty
        if drift_score is not None and drift_score > 0.5:
            drift_multiplier = 1.0 - (drift_score - 0.5) * 0.5  # Reduce by up to 25%
        else:
            drift_multiplier = 1.0
        
        # Calculate final position size
        position_size = (
            kelly_base *
            fqs_multiplier *
            stability_multiplier *
            regime_multiplier *
            drift_multiplier
        )
        
        # Apply hard caps
        position_size = min(position_size, self.max_position_size)
        
        # Zero out for problematic regimes
        if regime_type in ["overconfidence", "data_quality_degradation", "low_predictability"]:
            position_size = 0.0
            logger.warning(f"Position size set to 0 due to regime: {regime_type}")
        
        # Ensure non-negative
        position_size = max(0.0, position_size)
        
        return {
            "position_size_pct": float(position_size * 100),  # As percentage
            "position_size_fraction": float(position_size),  # As fraction
            "breakdown": {
                "kelly_base": float(kelly_base),
                "fqs_multiplier": float(fqs_multiplier),
                "stability_multiplier": float(stability_multiplier),
                "regime_multiplier": float(regime_multiplier),
                "drift_multiplier": float(drift_multiplier)
            },
            "recommendation": self._get_recommendation(position_size, regime_type)
        }
    
    def _get_regime_multiplier(self, regime_type: str) -> float:
        """Get position size multiplier based on regime."""
        multipliers = {
            "normal": 1.0,
            "high_volatility": 0.5,  # Reduce position in high vol
            "low_predictability": 0.0,  # Zero out
            "overconfidence": 0.0,  # Zero out
            "data_quality_degradation": 0.0  # Zero out
        }
        return multipliers.get(regime_type, 0.5)  # Default to conservative
    
    def _get_recommendation(self, position_size: float, regime_type: str) -> str:
        """Get human-readable recommendation."""
        if position_size == 0.0:
            return "DO NOT TRADE - Regime or risk constraints"
        elif position_size < 0.01:
            return "MINIMAL POSITION - Very small size recommended"
        elif position_size < 0.03:
            return "SMALL POSITION - Conservative sizing"
        elif position_size < 0.07:
            return "MODERATE POSITION - Standard sizing"
        else:
            return "LARGE POSITION - Aggressive sizing (monitor closely)"





