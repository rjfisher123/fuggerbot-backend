"""
FuggerBot Reliability Score (FRS) Engine.

Meta-signal combining all quality and stability factors.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from models.tsfm.schemas import ForecastOutput
from models.trust.schemas import TrustEvaluation
from models.forecast_quality import ForecastQualityScorer
from models.regime_classifier import RegimeClassifier
from models.drift_detection import DriftDetector
import logging

logger = logging.getLogger(__name__)


class FRSEngine:
    """Calculates FuggerBot Reliability Score (FRS)."""
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_frs_threshold: float = 0.6
    ):
        """
        Initialize FRS engine.
        
        Args:
            weights: Optional custom weights for FRS components
            min_frs_threshold: Minimum FRS for reliable signals
        """
        self.weights = weights or {
            "fqs": 0.25,
            "trust_score": 0.20,
            "regime": 0.15,
            "stability": 0.15,
            "drift": 0.15,
            "deterministic_divergence": 0.10
        }
        self.min_frs_threshold = min_frs_threshold
        self.quality_scorer = ForecastQualityScorer()
        self.regime_classifier = RegimeClassifier()
    
    def calculate_frs(
        self,
        forecast: ForecastOutput,
        trust_eval: TrustEvaluation,
        fqs: Dict[str, Any],
        regime: Dict[str, Any],
        drift_score: Optional[float] = None,
        stability_score: Optional[float] = None,
        deterministic_divergence: Optional[float] = None,
        historical_series: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate FuggerBot Reliability Score.
        
        Args:
            forecast: ForecastOutput
            trust_eval: TrustEvaluation
            fqs: FQS calculation result
            regime: Regime classification
            drift_score: Optional drift score (0-1, higher = more drift)
            stability_score: Optional stability score (0-1, higher = more stable)
            deterministic_divergence: Optional divergence from deterministic run (0-1)
            historical_series: Optional historical data
            
        Returns:
            Dict with FRS score and breakdown
        """
        # Normalize weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in self.weights.items()}
        else:
            weights = self.weights
        
        # Component scores
        fqs_score = fqs.get("fqs_score", 0.5)
        trust_score = trust_eval.metrics.overall_trust_score
        
        # Regime score (normal regime = 1.0, others penalized)
        regime_type = regime.get("regime", "normal")
        regime_score = 1.0 if regime_type == "normal" else 0.5
        
        # Stability score (default to moderate if not provided)
        if stability_score is None:
            # Calculate from FQS stability component
            stability_score = fqs.get("components", {}).get("stability", 0.7)
        
        # Drift score (inverted: lower drift = higher score)
        if drift_score is None:
            drift_score_normalized = 0.7  # Default: assume no drift
        else:
            drift_score_normalized = 1.0 - drift_score  # Invert (0 drift = 1.0 score)
        
        # Deterministic divergence (lower divergence = higher score)
        if deterministic_divergence is None:
            deterministic_score = 1.0  # Default: assume deterministic
        else:
            deterministic_score = 1.0 - deterministic_divergence
        
        # Calculate weighted FRS
        frs = (
            weights.get("fqs", 0.0) * fqs_score +
            weights.get("trust_score", 0.0) * trust_score +
            weights.get("regime", 0.0) * regime_score +
            weights.get("stability", 0.0) * stability_score +
            weights.get("drift", 0.0) * drift_score_normalized +
            weights.get("deterministic_divergence", 0.0) * deterministic_score
        )
        
        # Ensure in [0, 1] range
        frs = float(np.clip(frs, 0.0, 1.0))
        
        # Reliability classification
        is_reliable = frs >= self.min_frs_threshold
        reliability_level = self._classify_reliability(frs)
        
        return {
            "frs_score": frs,
            "is_reliable": is_reliable,
            "reliability_level": reliability_level,
            "components": {
                "fqs": fqs_score,
                "trust_score": trust_score,
                "regime": regime_score,
                "stability": stability_score,
                "drift": drift_score_normalized,
                "deterministic": deterministic_score
            },
            "weights": weights,
            "interpretation": self._interpret_frs(frs, is_reliable),
            "recommendation": self._get_recommendation(frs, is_reliable, regime_type)
        }
    
    @staticmethod
    def _classify_reliability(frs: float) -> str:
        """Classify reliability level."""
        if frs >= 0.8:
            return "highly_reliable"
        elif frs >= 0.65:
            return "reliable"
        elif frs >= 0.5:
            return "moderate"
        else:
            return "unreliable"
    
    @staticmethod
    def _interpret_frs(frs: float, is_reliable: bool) -> str:
        """Generate human-readable interpretation."""
        if is_reliable:
            if frs >= 0.8:
                return "Highly reliable - FuggerBot has high confidence in this forecast"
            else:
                return "Reliable - FuggerBot has moderate confidence in this forecast"
        else:
            return "Unreliable - FuggerBot has low confidence. Use with caution or wait for better conditions."
    
    @staticmethod
    def _get_recommendation(frs: float, is_reliable: bool, regime_type: str) -> str:
        """Get trading recommendation based on FRS."""
        if not is_reliable:
            return "DO NOT TRADE - Reliability below threshold"
        
        if regime_type != "normal":
            return "TRADE WITH CAUTION - Non-normal regime detected"
        
        if frs >= 0.8:
            return "PROCEED - High reliability signal"
        else:
            return "PROCEED CAUTIOUSLY - Moderate reliability"










