"""
Integration module connecting forecasts and trust filter to trading decisions.

This module provides a high-level interface for:
1. Generating forecasts for trading symbols
2. Evaluating forecast trust
3. Making trading recommendations based on trusted forecasts
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import numpy as np

from .tsfm.inference import ChronosInferenceEngine
from .tsfm.schemas import ForecastInput, ForecastOutput
from .trust.filter import TrustFilter
from .trust.schemas import TrustEvaluation, TrustFilterConfig

logger = logging.getLogger(__name__)


class ForecastTrader:
    """
    High-level interface for forecast-based trading decisions.
    
    Combines forecasting (Phase 1) and trust filtering (Phase 2) to provide
    trading recommendations.
    """
    
    def __init__(
        self,
        trust_config: Optional[TrustFilterConfig] = None,
        model_name: str = "amazon/chronos-t5-tiny"
    ):
        """
        Initialize ForecastTrader.
        
        Args:
            trust_config: TrustFilterConfig for trust evaluation
            model_name: Chronos model name
        """
        self.forecast_engine = ChronosInferenceEngine(model_name=model_name)
        self.trust_filter = TrustFilter(config=trust_config)
        logger.info("ForecastTrader initialized")
    
    def analyze_symbol(
        self,
        symbol: str,
        historical_prices: List[float],
        forecast_horizon: int = 30,
        context_length: Optional[int] = None,
        current_volatility: Optional[float] = None,
        historical_volatility: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze a symbol: generate forecast and evaluate trust.
        
        Args:
            symbol: Trading symbol
            historical_prices: Historical price series
            forecast_horizon: Number of periods to forecast
            context_length: Context window size (None = use all)
            current_volatility: Current market volatility
            historical_volatility: Historical average volatility
            
        Returns:
            Dict with forecast, trust evaluation, and trading recommendation
        """
        logger.info(f"Analyzing {symbol} with {len(historical_prices)} historical points")
        
        # Generate forecast
        forecast_input = ForecastInput(
            series=historical_prices,
            forecast_horizon=forecast_horizon,
            context_length=context_length,
            metadata={"symbol": symbol, "timestamp": datetime.now().isoformat()}
        )
        
        try:
            forecast = self.forecast_engine.forecast(forecast_input)
            logger.info(f"Forecast generated for {symbol} in {forecast.inference_time_ms:.1f}ms")
        except Exception as e:
            logger.error(f"Forecast generation failed for {symbol}: {e}", exc_info=True)
            return {
                "symbol": symbol,
                "success": False,
                "error": str(e),
                "forecast": None,
                "trust_evaluation": None,
                "recommendation": None
            }
        
        # Evaluate trust
        trust_eval = self.trust_filter.evaluate(
            forecast=forecast,
            input_data=forecast_input,
            symbol=symbol,
            current_volatility=current_volatility,
            historical_volatility=historical_volatility
        )
        
        # Generate trading recommendation
        recommendation = self._generate_recommendation(
            forecast=forecast,
            trust_eval=trust_eval,
            current_price=historical_prices[-1] if historical_prices else None
        )
        
        return {
            "symbol": symbol,
            "success": True,
            "forecast": forecast,
            "trust_evaluation": trust_eval,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_recommendation(
        self,
        forecast: ForecastOutput,
        trust_eval: TrustEvaluation,
        current_price: Optional[float]
    ) -> Dict[str, Any]:
        """
        Generate trading recommendation based on forecast and trust.
        
        Args:
            forecast: ForecastOutput
            trust_eval: TrustEvaluation
            current_price: Current market price (if available)
            
        Returns:
            Dict with trading recommendation
        """
        if not trust_eval.is_trusted:
            return {
                "action": "PASS",
                "reason": "Forecast did not pass trust filter",
                "confidence": trust_eval.metrics.confidence_level,
                "trust_score": trust_eval.metrics.overall_trust_score
            }
        
        # Analyze forecast direction
        point_forecast = np.array(forecast.point_forecast)
        lower_bound = np.array(forecast.lower_bound)
        upper_bound = np.array(forecast.upper_bound)
        
        # Calculate expected return
        if current_price and current_price > 0:
            expected_return_pct = ((np.mean(point_forecast) - current_price) / current_price) * 100
            min_return_pct = ((np.mean(lower_bound) - current_price) / current_price) * 100
            max_return_pct = ((np.mean(upper_bound) - current_price) / current_price) * 100
        else:
            # Use first forecast point as baseline
            expected_return_pct = ((np.mean(point_forecast[1:]) - point_forecast[0]) / point_forecast[0]) * 100
            min_return_pct = ((np.mean(lower_bound[1:]) - point_forecast[0]) / point_forecast[0]) * 100
            max_return_pct = ((np.mean(upper_bound[1:]) - point_forecast[0]) / point_forecast[0]) * 100
        
        # Calculate risk (uncertainty range)
        uncertainty_range = np.mean(upper_bound - lower_bound)
        if current_price and current_price > 0:
            risk_pct = (uncertainty_range / current_price) * 100
        else:
            risk_pct = (uncertainty_range / np.mean(point_forecast)) * 100
        
        # Ensure minimum risk floor (market always has some uncertainty)
        # If bounds are identical or very close, use historical volatility as proxy
        if risk_pct < 0.1:  # Less than 0.1% uncertainty seems unrealistic
            # Use historical volatility of the forecast as minimum risk estimate
            forecast_volatility = np.std(point_forecast)
            if current_price and current_price > 0:
                min_risk = (forecast_volatility / current_price) * 100
            else:
                min_risk = (forecast_volatility / np.mean(point_forecast)) * 100
            # Use the higher of calculated risk or minimum risk (at least 1% for market risk)
            risk_pct = max(risk_pct, min_risk, 1.0)  # Minimum 1% to account for market risk
        
        # Determine action based on expected return and risk
        if expected_return_pct > 5.0 and min_return_pct > 0:
            action = "BUY"
            reason = f"Strong bullish forecast: {expected_return_pct:.1f}% expected return"
        elif expected_return_pct > 2.0 and min_return_pct > -2.0:
            action = "BUY"
            reason = f"Moderate bullish forecast: {expected_return_pct:.1f}% expected return"
        elif expected_return_pct < -5.0 and max_return_pct < 0:
            action = "SELL"
            reason = f"Strong bearish forecast: {expected_return_pct:.1f}% expected return"
        elif expected_return_pct < -2.0 and max_return_pct < 2.0:
            action = "SELL"
            reason = f"Moderate bearish forecast: {expected_return_pct:.1f}% expected return"
        else:
            action = "HOLD"
            reason = f"Neutral forecast: {expected_return_pct:.1f}% expected return"
        
        # Adjust for high risk
        if risk_pct > 15.0:
            if action in ["BUY", "SELL"]:
                action = "HOLD"
                reason += f" (High risk: {risk_pct:.1f}% uncertainty)"
        
        return {
            "action": action,
            "reason": reason,
            "expected_return_pct": float(expected_return_pct),
            "min_return_pct": float(min_return_pct),
            "max_return_pct": float(max_return_pct),
            "risk_pct": float(risk_pct),
            "confidence": trust_eval.metrics.confidence_level,
            "trust_score": trust_eval.metrics.overall_trust_score,
            "forecast_horizon": forecast.forecast_horizon
        }
    
    def analyze_multiple_symbols(
        self,
        symbol_data: Dict[str, List[float]],
        forecast_horizon: int = 30,
        context_length: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple symbols in batch.
        
        Args:
            symbol_data: Dict mapping symbols to historical price lists
            forecast_horizon: Number of periods to forecast
            context_length: Context window size
            
        Returns:
            Dict mapping symbols to analysis results
        """
        results = {}
        
        for symbol, prices in symbol_data.items():
            results[symbol] = self.analyze_symbol(
                symbol=symbol,
                historical_prices=prices,
                forecast_horizon=forecast_horizon,
                context_length=context_length
            )
        
        return results
    
    def get_trusted_recommendations(
        self,
        analyses: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter analyses to return only trusted trading recommendations.
        
        Args:
            analyses: Dict from analyze_multiple_symbols
            
        Returns:
            List of trusted recommendations
        """
        trusted = []
        
        for symbol, analysis in analyses.items():
            if (analysis.get("success") and 
                analysis.get("trust_evaluation") and 
                analysis.get("trust_evaluation").is_trusted and
                analysis.get("recommendation") and
                analysis["recommendation"]["action"] != "PASS"):
                trusted.append({
                    "symbol": symbol,
                    **analysis["recommendation"]
                })
        
        # Sort by expected return (descending)
        trusted.sort(key=lambda x: x.get("expected_return_pct", 0), reverse=True)
        
        return trusted
    
    def update_accuracy_history(self, symbol: str, actual_prices: List[float], forecast: ForecastOutput) -> None:
        """
        Update historical accuracy based on actual prices vs forecast.
        
        Args:
            symbol: Trading symbol
            actual_prices: Actual prices that occurred
            forecast: Original forecast that was made
        """
        if len(actual_prices) < len(forecast.point_forecast):
            logger.warning(f"Insufficient actual prices for {symbol} accuracy calculation")
            return
        
        # Calculate accuracy metrics
        forecast_points = np.array(forecast.point_forecast[:len(actual_prices)])
        actual = np.array(actual_prices)
        
        # Mean Absolute Percentage Error (MAPE)
        mape = np.mean(np.abs((actual - forecast_points) / (actual + 1e-10))) * 100
        
        # Convert to accuracy score (0-1, higher is better)
        # MAPE of 0% = perfect (score 1.0), MAPE of 50% = poor (score 0.0)
        accuracy = max(0.0, min(1.0, 1.0 - (mape / 50.0)))
        
        # Update trust filter's accuracy history
        self.trust_filter.update_accuracy_history(symbol, accuracy)
        
        logger.info(f"Updated accuracy for {symbol}: {accuracy:.3f} (MAPE: {mape:.2f}%)")


