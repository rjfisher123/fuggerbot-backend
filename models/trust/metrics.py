"""Trust metrics calculation for forecast evaluation."""
import numpy as np
from typing import List, Optional, Dict, Any
import logging

from ..tsfm.schemas import ForecastOutput, ForecastInput

logger = logging.getLogger(__name__)


class TrustMetricsCalculator:
    """Calculates various trust metrics for forecasts."""
    
    @staticmethod
    def calculate_uncertainty_score(forecast: ForecastOutput) -> float:
        """
        Calculate trust score based on forecast uncertainty.
        
        Lower uncertainty (tighter bounds) = higher trust score.
        
        Args:
            forecast: ForecastOutput with bounds
            
        Returns:
            Uncertainty-based trust score (0-1)
        """
        point_forecast = np.array(forecast.point_forecast)
        lower_bound = np.array(forecast.lower_bound)
        upper_bound = np.array(forecast.upper_bound)
        
        # Calculate uncertainty range as percentage of point forecast
        uncertainty_ranges = upper_bound - lower_bound
        
        # Avoid division by zero
        point_abs = np.abs(point_forecast)
        point_abs = np.where(point_abs < 1e-10, 1.0, point_abs)
        
        uncertainty_ratios = uncertainty_ranges / point_abs
        
        # Normalize: lower ratio = higher trust
        # Use exponential decay: score = exp(-ratio / threshold)
        # Typical good forecast has ratio < 0.2, poor has ratio > 0.5
        threshold = 0.3
        raw_scores = np.exp(-uncertainty_ratios / threshold)
        
        # Average across all forecast steps
        avg_score = np.mean(raw_scores)
        
        # Clip to [0, 1] and apply sigmoid for smoother scaling
        score = 1.0 / (1.0 + np.exp(-5 * (avg_score - 0.5)))
        
        return float(np.clip(score, 0.0, 1.0))
    
    @staticmethod
    def calculate_consistency_score(
        forecast: ForecastOutput,
        historical_series: Optional[List[float]] = None
    ) -> float:
        """
        Calculate trust score based on forecast consistency.
        
        Checks if forecast is consistent with historical patterns.
        
        Args:
            forecast: ForecastOutput
            historical_series: Optional historical data for comparison
            
        Returns:
            Consistency-based trust score (0-1)
        """
        point_forecast = np.array(forecast.point_forecast)
        
        # Check for unrealistic jumps or discontinuities
        if len(point_forecast) < 2:
            return 0.5  # Neutral score for single-point forecasts
        
        # Calculate rate of change
        changes = np.diff(point_forecast)
        change_ratios = changes / (np.abs(point_forecast[:-1]) + 1e-10)
        
        # Penalize extreme changes (>50% per step is suspicious)
        extreme_change_penalty = np.sum(np.abs(change_ratios) > 0.5) / len(change_ratios)
        
        # Check for monotonicity violations (if historical suggests trend)
        if historical_series and len(historical_series) > 1:
            hist_array = np.array(historical_series)
            recent_trend = np.mean(np.diff(hist_array[-min(10, len(hist_array)):]))
            
            # If historical has strong trend, forecast should continue it
            if abs(recent_trend) > 0.01 * abs(np.mean(hist_array)):
                forecast_trend = np.mean(changes)
                trend_consistency = 1.0 - min(1.0, abs(forecast_trend - recent_trend) / (abs(recent_trend) + 1e-10))
            else:
                trend_consistency = 0.7  # Neutral if no clear trend
        else:
            trend_consistency = 0.7
        
        # Check bounds consistency (upper should be >= lower, point should be in between)
        lower = np.array(forecast.lower_bound)
        upper = np.array(forecast.upper_bound)
        point = point_forecast
        
        bounds_consistency = np.mean(
            (point >= lower) & (point <= upper)
        )
        
        # Combine scores
        consistency_score = (
            0.4 * (1.0 - extreme_change_penalty) +
            0.3 * trend_consistency +
            0.3 * bounds_consistency
        )
        
        return float(np.clip(consistency_score, 0.0, 1.0))
    
    @staticmethod
    def calculate_data_quality_score(
        input_data: Optional[ForecastInput] = None,
        historical_series: Optional[List[float]] = None
    ) -> float:
        """
        Calculate trust score based on input data quality.
        
        Args:
            input_data: Original ForecastInput (if available)
            historical_series: Historical series data
            
        Returns:
            Data quality score (0-1)
        """
        if historical_series is None:
            if input_data:
                historical_series = input_data.series
            else:
                return 0.5  # Neutral if no data available
        
        series = np.array(historical_series)
        
        # Check for sufficient length
        length_score = min(1.0, len(series) / 50.0)  # Prefer 50+ points
        
        # Check for missing/NaN values
        nan_ratio = np.sum(np.isnan(series)) / len(series)
        completeness_score = 1.0 - nan_ratio
        
        # Check for outliers (using IQR method)
        if len(series) > 4:
            q1, q3 = np.percentile(series, [25, 75])
            iqr = q3 - q1
            if iqr > 0:
                outliers = np.sum(
                    (series < q1 - 3 * iqr) | (series > q3 + 3 * iqr)
                )
                outlier_ratio = outliers / len(series)
                outlier_score = 1.0 - min(1.0, outlier_ratio * 2)  # Penalize outliers
            else:
                outlier_score = 0.5  # Neutral if no variance
        else:
            outlier_score = 0.7
        
        # Check for sufficient variance (constant series is suspicious)
        if len(series) > 1:
            variance = np.var(series)
            mean_abs = np.abs(np.mean(series))
            if mean_abs > 0:
                cv = np.sqrt(variance) / mean_abs  # Coefficient of variation
                variance_score = min(1.0, cv * 10)  # Prefer CV > 0.1
            else:
                variance_score = 0.5
        else:
            variance_score = 0.5
        
        # Combine scores
        quality_score = (
            0.3 * length_score +
            0.3 * completeness_score +
            0.2 * outlier_score +
            0.2 * variance_score
        )
        
        return float(np.clip(quality_score, 0.0, 1.0))
    
    @staticmethod
    def calculate_historical_accuracy(
        symbol: Optional[str] = None,
        accuracy_history: Optional[Dict[str, float]] = None
    ) -> Optional[float]:
        """
        Retrieve historical accuracy score if available.
        
        Args:
            symbol: Symbol to look up accuracy for
            accuracy_history: Dictionary mapping symbols to accuracy scores
            
        Returns:
            Historical accuracy score (0-1) or None if not available
        """
        if accuracy_history and symbol:
            return accuracy_history.get(symbol)
        return None
    
    @staticmethod
    def calculate_market_regime_score(
        current_volatility: Optional[float] = None,
        historical_volatility: Optional[float] = None
    ) -> Optional[float]:
        """
        Calculate market regime compatibility score.
        
        Higher volatility or regime changes may reduce forecast reliability.
        
        Args:
            current_volatility: Current market volatility measure
            historical_volatility: Historical average volatility
            
        Returns:
            Market regime score (0-1) or None if data unavailable
        """
        if current_volatility is None or historical_volatility is None:
            return None
        
        if historical_volatility == 0:
            return 0.5  # Neutral if no historical baseline
        
        # Compare current to historical
        volatility_ratio = current_volatility / historical_volatility
        
        # Moderate volatility (0.5x to 2x historical) is good
        # Extreme volatility (>3x) reduces trust
        if 0.5 <= volatility_ratio <= 2.0:
            regime_score = 1.0
        elif 2.0 < volatility_ratio <= 3.0:
            regime_score = 0.7
        elif 0.3 <= volatility_ratio < 0.5:
            regime_score = 0.8
        else:
            regime_score = 0.4  # Extreme volatility
        
        return float(np.clip(regime_score, 0.0, 1.0))
    
    @staticmethod
    def calculate_overall_trust_score(
        uncertainty_score: float,
        consistency_score: float,
        data_quality_score: float,
        historical_accuracy: Optional[float] = None,
        market_regime_score: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate weighted overall trust score.
        
        Args:
            uncertainty_score: Uncertainty-based score
            consistency_score: Consistency-based score
            data_quality_score: Data quality score
            historical_accuracy: Optional historical accuracy
            market_regime_score: Optional market regime score
            weights: Optional custom weights (defaults to standard weights)
            
        Returns:
            Overall trust score (0-1)
        """
        if weights is None:
            weights = {
                "uncertainty": 0.3,
                "consistency": 0.25,
                "data_quality": 0.25,
                "historical_accuracy": 0.15,
                "market_regime": 0.05
            }
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Calculate weighted sum
        overall_score = (
            weights.get("uncertainty", 0.0) * uncertainty_score +
            weights.get("consistency", 0.0) * consistency_score +
            weights.get("data_quality", 0.0) * data_quality_score
        )
        
        # Add optional components if available
        if historical_accuracy is not None:
            overall_score += weights.get("historical_accuracy", 0.0) * historical_accuracy
        else:
            # Redistribute weight if historical accuracy unavailable
            remaining = weights.get("historical_accuracy", 0.0)
            if remaining > 0:
                # Redistribute to other components proportionally
                scale = 1.0 + remaining / (1.0 - remaining)
                overall_score *= scale
        
        if market_regime_score is not None:
            overall_score += weights.get("market_regime", 0.0) * market_regime_score
        else:
            # Similar redistribution
            remaining = weights.get("market_regime", 0.0)
            if remaining > 0:
                scale = 1.0 + remaining / (1.0 - remaining)
                overall_score *= scale
        
        return float(np.clip(overall_score, 0.0, 1.0))
    
    @staticmethod
    def classify_confidence_level(trust_score: float) -> str:
        """
        Classify confidence level based on trust score.
        
        Args:
            trust_score: Overall trust score (0-1)
            
        Returns:
            Confidence level: "low", "medium", or "high"
        """
        if trust_score >= 0.75:
            return "high"
        elif trust_score >= 0.55:
            return "medium"
        else:
            return "low"






