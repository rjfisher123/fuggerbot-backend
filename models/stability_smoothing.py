"""
Forecast Stability Smoothing with Hysteresis and Rolling Medians.

Prevents threshold-based systems from flipping easily.
"""
import numpy as np
from typing import List, Optional, Dict, Any
from collections import deque
import logging

logger = logging.getLogger(__name__)


class StabilitySmoother:
    """Smooths forecast metrics to prevent rapid flipping."""
    
    def __init__(
        self,
        fqs_threshold: float = 0.05,
        regime_window: int = 3,
        uncertainty_alpha: float = 0.3
    ):
        """
        Initialize stability smoother.
        
        Args:
            fqs_threshold: Minimum change required to switch FQS category (0.05 = 5%)
            regime_window: Rolling window size for regime smoothing
            uncertainty_alpha: EMA alpha for uncertainty smoothing
        """
        self.fqs_threshold = fqs_threshold
        self.regime_window = regime_window
        self.uncertainty_alpha = uncertainty_alpha
        
        # History tracking
        self.fqs_history: Dict[str, deque] = {}
        self.regime_history: Dict[str, deque] = {}
        self.uncertainty_history: Dict[str, Dict[str, float]] = {}
        self.action_history: Dict[str, deque] = {}
    
    def smooth_fqs(
        self,
        symbol: str,
        current_fqs: float,
        category: str
    ) -> tuple[float, str]:
        """
        Smooth FQS with hysteresis to prevent category flipping.
        
        Args:
            symbol: Symbol identifier
            current_fqs: Current FQS score
            category: Current category (Excellent/Good/Fair/Poor)
            
        Returns:
            Smoothed FQS and category
        """
        if symbol not in self.fqs_history:
            self.fqs_history[symbol] = deque(maxlen=5)
        
        history = self.fqs_history[symbol]
        
        if len(history) == 0:
            # First value - no smoothing
            history.append(current_fqs)
            return current_fqs, category
        
        # Get last smoothed value
        last_smoothed = history[-1]
        
        # Calculate change
        change = abs(current_fqs - last_smoothed)
        
        # Apply hysteresis: only update if change > threshold
        if change < self.fqs_threshold:
            # Keep previous value (hysteresis)
            smoothed_fqs = last_smoothed
            logger.debug(f"FQS hysteresis for {symbol}: change {change:.4f} < threshold {self.fqs_threshold}")
        else:
            # Update
            smoothed_fqs = current_fqs
        
        history.append(smoothed_fqs)
        
        # Reclassify category based on smoothed value
        smoothed_category = self._classify_fqs_category(smoothed_fqs)
        
        return smoothed_fqs, smoothed_category
    
    def smooth_regime(
        self,
        symbol: str,
        current_regime: str
    ) -> str:
        """
        Smooth regime classification using rolling median.
        
        Args:
            symbol: Symbol identifier
            current_regime: Current regime classification
            
        Returns:
            Smoothed regime
        """
        if symbol not in self.regime_history:
            self.regime_history[symbol] = deque(maxlen=self.regime_window)
        
        history = self.regime_history[symbol]
        history.append(current_regime)
        
        if len(history) < self.regime_window:
            # Not enough history - return current
            return current_regime
        
        # Use most common regime in window (mode)
        regime_counts = {}
        for regime in history:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        smoothed_regime = max(regime_counts.items(), key=lambda x: x[1])[0]
        
        if smoothed_regime != current_regime:
            logger.debug(f"Regime smoothed for {symbol}: {current_regime} → {smoothed_regime}")
        
        return smoothed_regime
    
    def smooth_uncertainty(
        self,
        symbol: str,
        current_uncertainty: float
    ) -> float:
        """
        Smooth uncertainty using exponential moving average.
        
        Args:
            symbol: Symbol identifier
            current_uncertainty: Current uncertainty value
            
        Returns:
            Smoothed uncertainty
        """
        if symbol not in self.uncertainty_history:
            self.uncertainty_history[symbol] = {"value": current_uncertainty}
        
        history = self.uncertainty_history[symbol]
        last_value = history["value"]
        
        # EMA: new = alpha * current + (1 - alpha) * last
        smoothed = self.uncertainty_alpha * current_uncertainty + (1 - self.uncertainty_alpha) * last_value
        
        history["value"] = smoothed
        
        return smoothed
    
    def check_action_stability(
        self,
        symbol: str,
        current_action: str
    ) -> tuple[bool, str]:
        """
        Check if action is stable (requires 2 consecutive evaluations).
        
        Args:
            symbol: Symbol identifier
            current_action: Current recommended action
            
        Returns:
            (is_stable, stable_action)
        """
        if symbol not in self.action_history:
            self.action_history[symbol] = deque(maxlen=2)
        
        history = self.action_history[symbol]
        history.append(current_action)
        
        if len(history) < 2:
            # Not enough history - not stable yet
            return False, current_action
        
        # Check if last 2 are the same
        if history[0] == history[1]:
            return True, current_action
        else:
            # Unstable - return previous action
            return False, history[0]
    
    @staticmethod
    def _classify_fqs_category(fqs: float) -> str:
        """Classify FQS into category."""
        if fqs >= 0.8:
            return "Excellent"
        elif fqs >= 0.65:
            return "Good"
        elif fqs >= 0.5:
            return "Fair"
        else:
            return "Poor"
    
    def reset_symbol(self, symbol: str) -> None:
        """Reset history for a symbol."""
        if symbol in self.fqs_history:
            self.fqs_history[symbol].clear()
        if symbol in self.regime_history:
            self.regime_history[symbol].clear()
        if symbol in self.uncertainty_history:
            del self.uncertainty_history[symbol]
        if symbol in self.action_history:
            self.action_history[symbol].clear()




