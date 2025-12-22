"""
Forecast service for integration with trigger engine and trading system.

This service provides a simple interface for getting forecast-based trading recommendations
that can be used by the trigger engine or other components.
"""
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.forecast_trader import ForecastTrader
from dash.utils.forecast_helper import get_historical_prices

logger = logging.getLogger(__name__)

# Global forecast trader instance
_forecast_trader: Optional[ForecastTrader] = None


def get_forecast_service() -> ForecastTrader:
    """
    Get or create the global forecast trader instance.
    
    Returns:
        ForecastTrader instance
    """
    global _forecast_trader
    if _forecast_trader is None:
        _forecast_trader = ForecastTrader()
        logger.info("Forecast service initialized")
    return _forecast_trader


def get_forecast_recommendation(
    symbol: str,
    forecast_horizon: int = 30,
    period: str = "1y"
) -> Optional[Dict[str, Any]]:
    """
    Get a trading recommendation based on forecast analysis.
    
    Args:
        symbol: Trading symbol
        forecast_horizon: Number of periods to forecast
        period: Historical data period (1y, 2y, etc.)
        
    Returns:
        Dict with recommendation or None if analysis fails
    """
    try:
        # Get historical data
        prices = get_historical_prices(symbol, period=period)
        
        if not prices or len(prices) < 20:
            logger.warning(f"Insufficient historical data for {symbol}")
            return None
        
        # Analyze
        forecast_service = get_forecast_service()
        result = forecast_service.analyze_symbol(
            symbol=symbol,
            historical_prices=prices,
            forecast_horizon=forecast_horizon
        )
        
        if not result.get("success"):
            logger.warning(f"Forecast analysis failed for {symbol}: {result.get('error')}")
            return None
        
        # Only return if trusted
        if result["trust_evaluation"].is_trusted:
            recommendation = result["recommendation"]
            return {
                "symbol": symbol,
                "action": recommendation["action"],
                "expected_return_pct": recommendation.get("expected_return_pct", 0),
                "risk_pct": recommendation.get("risk_pct", 0),
                "confidence": recommendation.get("confidence", "unknown"),
                "trust_score": recommendation.get("trust_score", 0),
                "reason": recommendation.get("reason", ""),
                "forecast_horizon": forecast_horizon
            }
        else:
            logger.info(f"Forecast for {symbol} did not pass trust filter")
            return None
            
    except Exception as e:
        logger.error(f"Error getting forecast recommendation for {symbol}: {e}", exc_info=True)
        return None


def check_forecast_trigger(
    symbol: str,
    current_price: float,
    trigger_price: float,
    forecast_horizon: int = 30
) -> Dict[str, Any]:
    """
    Check if a price trigger should be executed based on forecast analysis.
    
    This combines traditional price triggers with forecast-based validation.
    
    Args:
        symbol: Trading symbol
        current_price: Current market price
        trigger_price: Trigger price threshold
        forecast_horizon: Forecast horizon for analysis
        
    Returns:
        Dict with recommendation and forecast analysis
    """
    result = {
        "symbol": symbol,
        "current_price": current_price,
        "trigger_price": trigger_price,
        "price_diff_pct": ((current_price - trigger_price) / trigger_price) * 100,
        "forecast_recommendation": None,
        "should_execute": False,
        "reason": ""
    }
    
    # Get forecast recommendation
    forecast_rec = get_forecast_recommendation(symbol, forecast_horizon=forecast_horizon)
    
    if forecast_rec:
        result["forecast_recommendation"] = forecast_rec
        
        # Combine price trigger with forecast recommendation
        price_trigger_hit = current_price < trigger_price  # Assuming buy trigger
        
        if price_trigger_hit and forecast_rec["action"] == "BUY":
            result["should_execute"] = True
            result["reason"] = (
                f"Price trigger hit ({current_price:.2f} < {trigger_price:.2f}) "
                f"and forecast recommends BUY (expected return: {forecast_rec['expected_return_pct']:.2f}%)"
            )
        elif price_trigger_hit and forecast_rec["action"] in ["HOLD", "SELL"]:
            result["should_execute"] = False
            result["reason"] = (
                f"Price trigger hit but forecast recommends {forecast_rec['action']}. "
                f"Forecast suggests {forecast_rec['reason']}"
            )
        elif not price_trigger_hit:
            result["should_execute"] = False
            result["reason"] = "Price trigger not hit"
    else:
        # No forecast available - fall back to price trigger only
        price_trigger_hit = current_price < trigger_price
        result["should_execute"] = price_trigger_hit
        result["reason"] = (
            "Forecast analysis unavailable. Using price trigger only."
            if price_trigger_hit else "Price trigger not hit"
        )
    
    return result











