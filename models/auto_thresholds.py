"""
Auto-Calibrated Thresholds System.

Automatically adjusts thresholds based on market conditions and performance.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from collections import deque
import logging

logger = logging.getLogger(__name__)


class AutoThresholdCalibrator:
    """Automatically calibrates trading thresholds."""
    
    def __init__(
        self,
        lookback_period: int = 30,
        adaptation_rate: float = 0.1
    ):
        """
        Initialize auto-threshold calibrator.
        
        Args:
            lookback_period: Days to look back for calibration
            adaptation_rate: Rate of threshold adaptation (0-1)
        """
        self.lookback_period = lookback_period
        self.adaptation_rate = adaptation_rate
        
        # Threshold history
        self.fqs_bands: Dict[str, deque] = {}
        self.regime_penalties: Dict[str, float] = {}
        self.drift_triggers: Dict[str, deque] = {}
    
    def calibrate_fqs_bands(
        self,
        symbol: str,
        fqs_history: List[float],
        performance_history: List[float]
    ) -> Dict[str, float]:
        """
        Calibrate FQS bands based on performance.
        
        Args:
            symbol: Trading symbol
            fqs_history: Historical FQS scores
            performance_history: Historical performance (returns)
            
        Returns:
            Dict with calibrated FQS bands
        """
        if len(fqs_history) < 10 or len(performance_history) < 10:
            return {
                "min_fqs": 0.5,
                "optimal_fqs": 0.65,
                "excellent_fqs": 0.8
            }
        
        # Find FQS threshold that maximizes performance
        fqs_performance = list(zip(fqs_history, performance_history))
        sorted_fqs = sorted(fqs_performance, key=lambda x: x[0])
        
        best_threshold = 0.5
        best_performance = 0.0
        
        for i in range(len(sorted_fqs)):
            threshold = sorted_fqs[i][0]
            # Average performance above threshold
            above_threshold = [p for f, p in sorted_fqs if f >= threshold]
            if above_threshold:
                avg_performance = np.mean(above_threshold)
                if avg_performance > best_performance:
                    best_performance = avg_performance
                    best_threshold = threshold
        
        # Set bands around optimal threshold
        min_fqs = max(0.3, best_threshold - 0.15)
        optimal_fqs = best_threshold
        excellent_fqs = min(1.0, best_threshold + 0.15)
        
        return {
            "min_fqs": float(min_fqs),
            "optimal_fqs": float(optimal_fqs),
            "excellent_fqs": float(excellent_fqs)
        }
    
    def calibrate_regime_penalties(
        self,
        regime_performance: Dict[str, List[float]]
    ) -> Dict[str, float]:
        """
        Calibrate penalties for different regimes.
        
        Args:
            regime_performance: Dict of regime -> list of performance values
            
        Returns:
            Dict of regime -> penalty multiplier
        """
        penalties = {}
        
        # Calculate average performance per regime
        regime_avg_performance = {}
        for regime, perfs in regime_performance.items():
            if perfs:
                regime_avg_performance[regime] = np.mean(perfs)
        
        if not regime_avg_performance:
            return {
                "normal": 1.0,
                "high_volatility": 0.5,
                "low_predictability": 0.0,
                "overconfidence": 0.0,
                "data_quality_degradation": 0.0
            }
        
        # Normal regime as baseline
        baseline = regime_avg_performance.get("normal", 0.0)
        
        for regime, avg_perf in regime_avg_performance.items():
            if baseline != 0:
                # Penalty = relative performance
                penalty = max(0.0, min(1.0, avg_perf / baseline))
            else:
                penalty = 0.5 if regime == "normal" else 0.0
            
            penalties[regime] = float(penalty)
        
        return penalties
    
    def calibrate_drift_triggers(
        self,
        drift_history: List[float],
        performance_history: List[float]
    ) -> Dict[str, float]:
        """
        Calibrate drift detection triggers.
        
        Args:
            drift_history: Historical drift scores
            performance_history: Historical performance
            
        Returns:
            Dict with drift trigger thresholds
        """
        if len(drift_history) < 10:
            return {
                "warning_threshold": 0.5,
                "critical_threshold": 0.7,
                "auto_halt_threshold": 0.9
            }
        
        # Find drift levels that correlate with poor performance
        drift_performance = list(zip(drift_history, performance_history))
        
        # Sort by drift
        sorted_drift = sorted(drift_performance, key=lambda x: x[0])
        
        # Find thresholds where performance degrades
        warning_threshold = 0.5
        critical_threshold = 0.7
        auto_halt_threshold = 0.9
        
        # Find where performance drops below baseline
        baseline_performance = np.median([p for _, p in sorted_drift])
        
        for drift, perf in sorted_drift:
            if perf < baseline_performance * 0.8:  # 20% degradation
                if warning_threshold == 0.5:
                    warning_threshold = drift
                elif critical_threshold == 0.7:
                    critical_threshold = drift
                else:
                    auto_halt_threshold = drift
                    break
        
        return {
            "warning_threshold": float(warning_threshold),
            "critical_threshold": float(critical_threshold),
            "auto_halt_threshold": float(auto_halt_threshold)
        }
    
    def update_thresholds(
        self,
        symbol: str,
        current_metrics: Dict[str, Any],
        performance: float
    ) -> Dict[str, Any]:
        """
        Update thresholds adaptively based on recent performance.
        
        Args:
            symbol: Trading symbol
            current_metrics: Current forecast metrics
            performance: Recent performance
            
        Returns:
            Updated thresholds
        """
        # Track history
        if symbol not in self.fqs_bands:
            self.fqs_bands[symbol] = deque(maxlen=self.lookback_period)
        
        # Update FQS bands
        fqs = current_metrics.get("fqs_score", 0.5)
        self.fqs_bands[symbol].append((fqs, performance))
        
        # Recalibrate periodically
        if len(self.fqs_bands[symbol]) >= self.lookback_period:
            fqs_history = [f for f, _ in self.fqs_bands[symbol]]
            perf_history = [p for _, p in self.fqs_bands[symbol]]
            
            calibrated_bands = self.calibrate_fqs_bands(symbol, fqs_history, perf_history)
            
            # Adapt thresholds
            # Would merge with existing thresholds using adaptation_rate
            return calibrated_bands
        
        return {}





