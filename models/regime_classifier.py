"""
Confidence Regime Classification.

Labels forecasts by regime type for automated trading rules.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from models.tsfm.schemas import ForecastOutput
from models.trust.schemas import TrustEvaluation


class RegimeClassifier:
    """Classifies forecast confidence regimes."""
    
    @staticmethod
    def classify_regime(
        forecast: ForecastOutput,
        trust_eval: TrustEvaluation,
        historical_series: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Classify the confidence regime for a forecast.
        
        Args:
            forecast: ForecastOutput
            trust_eval: TrustEvaluation
            historical_series: Optional historical data
            
        Returns:
            Dict with regime classification
        """
        point_forecast = np.array(forecast.point_forecast)
        lower_bound = np.array(forecast.lower_bound)
        upper_bound = np.array(forecast.upper_bound)
        
        metrics = trust_eval.metrics
        
        # Calculate regime indicators
        uncertainty_ranges = upper_bound - lower_bound
        uncertainty_ratio = np.mean(uncertainty_ranges / np.abs(point_forecast))
        
        # Historical volatility
        if historical_series and len(historical_series) > 1:
            hist_array = np.array(historical_series)
            recent_vol = np.std(hist_array[-min(30, len(hist_array)):])
            forecast_vol = np.std(point_forecast)
            vol_ratio = forecast_vol / (recent_vol + 1e-10)
        else:
            vol_ratio = 1.0
        
        # Data quality
        data_quality = metrics.data_quality_score
        
        # Trust score
        trust_score = metrics.overall_trust_score
        
        # Classify regime
        regime = "normal"
        confidence = "high"
        warnings = []
        
        # High Volatility Regime
        if vol_ratio > 1.5:
            regime = "high_volatility"
            warnings.append("Forecast volatility significantly exceeds historical")
            confidence = "medium"
        
        # Low Predictability Regime
        elif trust_score < 0.55 or metrics.consistency_score < 0.5:
            regime = "low_predictability"
            warnings.append("Low trust or consistency score - reduced predictability")
            confidence = "low"
        
        # Overconfidence Regime
        elif uncertainty_ratio < 0.05 and trust_score > 0.8:
            regime = "overconfidence"
            warnings.append("Very tight uncertainty bounds with high trust - possible overconfidence")
            confidence = "medium"
        
        # Data Quality Degradation Regime
        elif data_quality < 0.6:
            regime = "data_quality_degradation"
            warnings.append("Data quality concerns detected")
            confidence = "low"
        
        # Normal Regime (default)
        else:
            regime = "normal"
            if trust_score > 0.75:
                confidence = "high"
            elif trust_score > 0.6:
                confidence = "medium"
            else:
                confidence = "low"
        
        # Trading action recommendations based on regime
        trading_action = RegimeClassifier._get_trading_action(regime, confidence)
        
        return {
            "regime": regime,
            "regime_label": RegimeClassifier._get_regime_label(regime),
            "confidence": confidence,
            "warnings": warnings,
            "trading_action": trading_action,
            "indicators": {
                "uncertainty_ratio": float(uncertainty_ratio),
                "volatility_ratio": float(vol_ratio),
                "data_quality": float(data_quality),
                "trust_score": float(trust_score)
            }
        }
    
    @staticmethod
    def _get_regime_label(regime: str) -> str:
        """Get human-readable regime label."""
        labels = {
            "normal": "Normal Regime",
            "high_volatility": "High Volatility Regime",
            "low_predictability": "Low Predictability Regime",
            "overconfidence": "Overconfidence Regime",
            "data_quality_degradation": "Data Quality Degradation Regime"
        }
        return labels.get(regime, "Unknown Regime")
    
    @staticmethod
    def _get_trading_action(regime: str, confidence: str) -> str:
        """Get recommended trading action based on regime."""
        if regime == "normal":
            if confidence == "high":
                return "proceed_normal"
            else:
                return "proceed_cautious"
        elif regime == "high_volatility":
            return "reduce_position_size"
        elif regime == "low_predictability":
            return "pause_trading"
        elif regime == "overconfidence":
            return "increase_risk_checks"
        elif regime == "data_quality_degradation":
            return "pause_trading"
        else:
            return "proceed_cautious"










