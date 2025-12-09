"""
Forecast Quality Scoring (FQS) system.

Produces a single 0-1 score blending multiple quality factors.
"""
import numpy as np
from typing import List, Optional, Dict, Any
from models.tsfm.schemas import ForecastOutput
from models.trust.schemas import TrustEvaluation


class ForecastQualityScorer:
    """Calculates Forecast Quality Score (FQS)."""
    
    @staticmethod
    def calculate_directional_strength(
        forecast: ForecastOutput,
        historical_series: Optional[List[float]] = None
    ) -> float:
        """
        Calculate directional strength (how clear is the forecast direction?).
        
        Args:
            forecast: ForecastOutput
            historical_series: Optional historical data
            
        Returns:
            Directional strength score (0-1)
        """
        point_forecast = np.array(forecast.point_forecast)
        
        if len(point_forecast) < 2:
            return 0.5  # Neutral for single point
        
        # Calculate trend strength
        changes = np.diff(point_forecast)
        change_magnitudes = np.abs(changes)
        mean_change = np.mean(change_magnitudes)
        
        # Consistency of direction
        if len(changes) > 1:
            direction_consistency = np.sum(np.sign(changes[0]) == np.sign(changes)) / len(changes)
        else:
            direction_consistency = 1.0
        
        # Relative to historical volatility
        if historical_series and len(historical_series) > 1:
            hist_vol = np.std(historical_series[-min(20, len(historical_series)):])
            if hist_vol > 0:
                relative_strength = min(1.0, mean_change / hist_vol)
            else:
                relative_strength = 0.5
        else:
            relative_strength = min(1.0, mean_change / (np.mean(np.abs(point_forecast)) + 1e-10))
        
        # Combine factors
        directional_strength = (
            0.4 * direction_consistency +
            0.3 * min(1.0, relative_strength * 2) +
            0.3 * min(1.0, mean_change / (np.std(point_forecast) + 1e-10))
        )
        
        return float(np.clip(directional_strength, 0.0, 1.0))
    
    @staticmethod
    def calculate_uncertainty_width_score(forecast: ForecastOutput) -> float:
        """
        Score based on uncertainty width (optimal range, not too wide/too narrow).
        
        Args:
            forecast: ForecastOutput
            
        Returns:
            Uncertainty width score (0-1)
        """
        point_forecast = np.array(forecast.point_forecast)
        lower_bound = np.array(forecast.lower_bound)
        upper_bound = np.array(forecast.upper_bound)
        
        uncertainty_ranges = upper_bound - lower_bound
        point_abs = np.abs(point_forecast)
        point_abs = np.where(point_abs < 1e-10, 1.0, point_abs)
        
        uncertainty_ratios = uncertainty_ranges / point_abs
        
        # Optimal uncertainty is 10-20% of point forecast
        # Too narrow (<5%) = overconfident
        # Too wide (>40%) = underconfident
        optimal_min = 0.10
        optimal_max = 0.20
        
        scores = []
        for ratio in uncertainty_ratios:
            if optimal_min <= ratio <= optimal_max:
                score = 1.0  # Optimal
            elif ratio < optimal_min:
                # Too narrow - penalize overconfidence
                score = ratio / optimal_min
            else:
                # Too wide - penalize underconfidence
                score = max(0.0, 1.0 - (ratio - optimal_max) / optimal_max)
            scores.append(score)
        
        return float(np.clip(np.mean(scores), 0.0, 1.0))
    
    @staticmethod
    def calculate_volatility_alignment(
        forecast: ForecastOutput,
        historical_series: Optional[List[float]] = None
    ) -> float:
        """
        Check if forecast volatility aligns with historical volatility.
        
        Args:
            forecast: ForecastOutput
            historical_series: Optional historical data
            
        Returns:
            Volatility alignment score (0-1)
        """
        point_forecast = np.array(forecast.point_forecast)
        forecast_vol = np.std(point_forecast)
        
        if historical_series and len(historical_series) > 1:
            hist_array = np.array(historical_series)
            recent_vol = np.std(hist_array[-min(30, len(hist_array)):])
            
            if recent_vol > 0:
                vol_ratio = forecast_vol / recent_vol
                # Ideal ratio is 0.8-1.2 (forecast vol similar to historical)
                if 0.8 <= vol_ratio <= 1.2:
                    alignment = 1.0
                elif vol_ratio < 0.8:
                    # Forecast too calm
                    alignment = vol_ratio / 0.8
                else:
                    # Forecast too volatile
                    alignment = max(0.0, 1.0 - (vol_ratio - 1.2) / 1.2)
            else:
                alignment = 0.5
        else:
            alignment = 0.7  # Neutral if no historical data
        
        return float(np.clip(alignment, 0.0, 1.0))
    
    @staticmethod
    def calculate_forecast_stability(
        forecast_history: List[ForecastOutput],
        symbol: Optional[str] = None
    ) -> float:
        """
        Calculate stability of last N forecasts.
        
        Args:
            forecast_history: List of previous ForecastOutputs
            
        Returns:
            Stability score (0-1)
        """
        if len(forecast_history) < 2:
            return 0.7  # Neutral if insufficient history
        
        # Compare recent forecasts
        recent = forecast_history[-min(5, len(forecast_history)):]
        
        point_forecasts = [np.array(f.point_forecast) for f in recent]
        
        # Calculate variance in forecasts
        if len(point_forecasts[0]) > 0:
            # Align lengths
            min_len = min(len(pf) for pf in point_forecasts)
            aligned = [pf[:min_len] for pf in point_forecasts]
            
            # Calculate coefficient of variation across forecasts
            mean_forecast = np.mean(aligned, axis=0)
            std_across_forecasts = np.std(aligned, axis=0)
            
            if np.mean(np.abs(mean_forecast)) > 0:
                cv = np.mean(std_across_forecasts) / np.mean(np.abs(mean_forecast))
                # Lower CV = more stable
                stability = max(0.0, 1.0 - cv * 2)
            else:
                stability = 0.5
        else:
            stability = 0.5
        
        return float(np.clip(stability, 0.0, 1.0))
    
    @staticmethod
    def calculate_fqs(
        forecast: ForecastOutput,
        trust_eval: TrustEvaluation,
        historical_series: Optional[List[float]] = None,
        forecast_history: Optional[List[ForecastOutput]] = None,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate Forecast Quality Score (FQS).
        
        Args:
            forecast: ForecastOutput
            trust_eval: TrustEvaluation
            historical_series: Optional historical data
            forecast_history: Optional list of previous forecasts
            
        Returns:
            Dict with FQS score and component breakdown
        """
        # Calculate component scores
        directional_strength = ForecastQualityScorer.calculate_directional_strength(
            forecast, historical_series
        )
        
        uncertainty_width = ForecastQualityScorer.calculate_uncertainty_width_score(forecast)
        
        volatility_alignment = ForecastQualityScorer.calculate_volatility_alignment(
            forecast, historical_series
        )
        
        if forecast_history:
            stability = ForecastQualityScorer.calculate_forecast_stability(forecast_history, symbol)
        else:
            stability = 0.7  # Default if no history
        
        # Weighted combination
        weights = {
            "directional_strength": 0.30,
            "uncertainty_width": 0.25,
            "volatility_alignment": 0.25,
            "stability": 0.20
        }
        
        fqs = (
            weights["directional_strength"] * directional_strength +
            weights["uncertainty_width"] * uncertainty_width +
            weights["volatility_alignment"] * volatility_alignment +
            weights["stability"] * stability
        )
        
        return {
            "fqs_score": float(np.clip(fqs, 0.0, 1.0)),
            "components": {
                "directional_strength": directional_strength,
                "uncertainty_width": uncertainty_width,
                "volatility_alignment": volatility_alignment,
                "stability": stability
            },
            "weights": weights,
            "interpretation": ForecastQualityScorer._interpret_fqs(fqs)
        }
    
    @staticmethod
    def _interpret_fqs(score: float) -> str:
        """Interpret FQS score."""
        if score >= 0.8:
            return "Excellent - High confidence in expected return"
        elif score >= 0.65:
            return "Good - Moderate confidence in expected return"
        elif score >= 0.5:
            return "Fair - Low-moderate confidence in expected return"
        else:
            return "Poor - Low confidence in expected return"

