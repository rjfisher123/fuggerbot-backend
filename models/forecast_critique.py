"""
Forecast critique and model self-evaluation.

Provides analysis of forecast drivers and confidence factors.
"""
import numpy as np
from typing import Dict, Any, List, Optional
from models.tsfm.schemas import ForecastOutput
from models.trust.schemas import TrustEvaluation


class ForecastCritique:
    """Generates model self-evaluation and forecast critique."""
    
    @staticmethod
    def analyze_forecast_drivers(
        forecast: ForecastOutput,
        trust_eval: TrustEvaluation,
        historical_series: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Analyze what's driving the forecast confidence.
        
        Args:
            forecast: ForecastOutput
            trust_eval: TrustEvaluation
            historical_series: Optional historical data
            
        Returns:
            Dict with critique analysis
        """
        critique = {
            "primary_confidence_driver": None,
            "confidence_factors": [],
            "warnings": [],
            "strengths": [],
            "limitations": []
        }
        
        metrics = trust_eval.metrics
        
        # Analyze confidence drivers
        scores = {
            "Trend Stability": metrics.consistency_score,
            "Data Quality": metrics.data_quality_score,
            "Uncertainty": metrics.uncertainty_score,
            "Historical Accuracy": metrics.historical_accuracy or 0.0,
            "Market Regime": metrics.market_regime_score or 0.0
        }
        
        # Find primary driver
        primary_driver = max(scores.items(), key=lambda x: x[1])
        critique["primary_confidence_driver"] = primary_driver[0]
        
        # Build confidence factors
        for factor, score in scores.items():
            if score > 0:
                level = "High" if score > 0.7 else "Medium" if score > 0.5 else "Low"
                critique["confidence_factors"].append({
                    "factor": factor,
                    "score": score,
                    "level": level
                })
        
        # Analyze forecast characteristics
        point_forecast = np.array(forecast.point_forecast)
        lower_bound = np.array(forecast.lower_bound)
        upper_bound = np.array(forecast.upper_bound)
        
        # Calculate forecast trend
        if len(point_forecast) > 1:
            forecast_trend = np.mean(np.diff(point_forecast))
            forecast_volatility = np.std(point_forecast)
            uncertainty_range = np.mean(upper_bound - lower_bound)
            
            # Trend analysis
            if abs(forecast_trend) > forecast_volatility * 0.5:
                direction = "bullish" if forecast_trend > 0 else "bearish"
                critique["strengths"].append(
                    f"Clear {direction} trend detected in forecast"
                )
            else:
                critique["warnings"].append(
                    "Forecast shows weak directional signal - trend is not strong"
                )
            
            # Uncertainty analysis
            uncertainty_ratio = uncertainty_range / np.mean(point_forecast)
            if uncertainty_ratio < 0.1:
                critique["warnings"].append(
                    "Very low uncertainty - model may be overconfident"
                )
            elif uncertainty_ratio > 0.3:
                critique["warnings"].append(
                    "High uncertainty - forecast has wide confidence bounds"
                )
            else:
                critique["strengths"].append(
                    "Reasonable uncertainty range - model confidence is calibrated"
                )
        
        # Historical comparison
        if historical_series:
            hist_array = np.array(historical_series)
            recent_volatility = np.std(hist_array[-min(20, len(hist_array)):])
            forecast_volatility = np.std(point_forecast)
            
            if forecast_volatility > recent_volatility * 1.5:
                critique["warnings"].append(
                    "Forecast volatility exceeds recent historical volatility - may indicate regime change"
                )
            elif forecast_volatility < recent_volatility * 0.5:
                critique["warnings"].append(
                    "Forecast volatility much lower than historical - may underestimate risk"
                )
        
        # Trust score analysis
        if metrics.overall_trust_score < 0.6:
            critique["limitations"].append(
                "Low overall trust score - forecast should be used with caution"
            )
        elif metrics.overall_trust_score > 0.85:
            critique["strengths"].append(
                "High trust score - model has high confidence in this forecast"
            )
        
        # Data quality warnings
        if metrics.data_quality_score < 0.6:
            critique["limitations"].append(
                "Data quality concerns - input data may have issues"
            )
        
        # Consistency warnings
        if metrics.consistency_score < 0.6:
            critique["warnings"].append(
                "Forecast consistency is low - pattern may not be reliable"
            )
        
        return critique
    
    @staticmethod
    def generate_critique_summary(
        forecast: ForecastOutput,
        trust_eval: TrustEvaluation,
        recommendation: Dict[str, Any],
        historical_series: Optional[List[float]] = None
    ) -> str:
        """
        Generate a human-readable critique summary.
        
        Args:
            forecast: ForecastOutput
            trust_eval: TrustEvaluation
            recommendation: Trading recommendation dict
            historical_series: Optional historical data
            
        Returns:
            Critique summary string
        """
        critique = ForecastCritique.analyze_forecast_drivers(
            forecast, trust_eval, historical_series
        )
        
        expected_return = recommendation.get("expected_return_pct", 0)
        risk = recommendation.get("risk_pct", 0)
        action = recommendation.get("action", "HOLD")
        
        summary_parts = []
        
        # Main assessment
        summary_parts.append(
            f"Model sees a {expected_return:.2f}% expected return with {risk:.2f}% uncertainty, "
            f"recommending {action}. "
        )
        
        # Confidence driver
        primary_driver = critique["primary_confidence_driver"]
        if primary_driver:
            if primary_driver == "Trend Stability":
                summary_parts.append(
                    "Confidence is driven primarily by trend stability, indicating a consistent pattern. "
                )
            elif primary_driver == "Data Quality":
                summary_parts.append(
                    "Confidence is driven primarily by high data quality, suggesting reliable inputs. "
                )
            elif primary_driver == "Uncertainty":
                summary_parts.append(
                    "Confidence is driven primarily by low uncertainty, showing tight forecast bounds. "
                )
            else:
                summary_parts.append(
                    f"Confidence is driven primarily by {primary_driver.lower()}. "
                )
        
        # Key warnings
        if critique["warnings"]:
            summary_parts.append("⚠️ Key concerns: " + "; ".join(critique["warnings"][:2]) + ". ")
        
        # Strengths
        if critique["strengths"]:
            summary_parts.append("✅ Strengths: " + "; ".join(critique["strengths"][:2]) + ". ")
        
        return "".join(summary_parts)

