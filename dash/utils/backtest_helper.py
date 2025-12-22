"""
Helper functions for backtesting and forecast evaluation.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from models.forecast_metadata import ForecastMetadata
from dash.utils.forecast_helper import get_historical_prices

logger = logging.getLogger(__name__)


def fetch_actual_prices_for_forecast(forecast_id: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to fetch actual prices for a forecast if the forecast horizon has elapsed.
    
    Args:
        forecast_id: Forecast ID to fetch actuals for
        
    Returns:
        Dict with:
            - 'available': bool - whether data is available
            - 'prices': List[float] - actual prices if available
            - 'message': str - status message
        Or None if forecast not found
    """
    metadata = ForecastMetadata()
    snapshot = metadata.load_forecast_snapshot(forecast_id)
    
    if not snapshot:
        return None
    
    # Extract forecast information
    forecast_timestamp_str = snapshot.get("timestamp")
    if not forecast_timestamp_str:
        return {
            "available": False,
            "prices": None,
            "message": "Forecast timestamp not found in snapshot"
        }
    
    try:
        forecast_timestamp = datetime.fromisoformat(forecast_timestamp_str)
    except (ValueError, TypeError):
        return {
            "available": False,
            "prices": None,
            "message": "Invalid forecast timestamp format"
        }
    
    # Get forecast horizon from parameters
    parameters = snapshot.get("parameters", {})
    forecast_horizon = parameters.get("forecast_horizon", 30)  # Default to 30 days
    
    # Calculate if forecast period has elapsed
    forecast_end_date = forecast_timestamp + timedelta(days=forecast_horizon)
    now = datetime.now()
    
    if now < forecast_end_date:
        days_remaining = (forecast_end_date - now).days
        return {
            "available": False,
            "prices": None,
            "message": f"Forecast period has not elapsed yet. {days_remaining} days remaining."
        }
    
    # Forecast period has elapsed - try to fetch actual prices
    symbol = snapshot.get("symbol")
    if not symbol:
        return {
            "available": False,
            "prices": None,
            "message": "Symbol not found in forecast snapshot"
        }
    
    try:
        # Calculate date range for fetching actual prices
        # Fetch from forecast date to forecast end date
        days_since_forecast = (now - forecast_timestamp).days
        # Fetch a bit more data to ensure we have enough
        period_days = min(days_since_forecast + 5, 90)  # Cap at 90 days
        
        # Convert to yfinance period format
        if period_days <= 5:
            period = "5d"
        elif period_days <= 30:
            period = "1mo"
        elif period_days <= 90:
            period = "3mo"
        else:
            period = "6mo"
        
        # Fetch historical prices
        all_prices = get_historical_prices(symbol, period=period, interval="1d")
        
        if not all_prices:
            return {
                "available": False,
                "prices": None,
                "message": f"Could not fetch price data for {symbol}"
            }
        
        # Find prices in the forecast period
        # We need to match dates, but yfinance returns prices in reverse chronological order (newest first)
        # For simplicity, we'll take the last N prices where N = forecast_horizon
        # This assumes daily data and that the forecast was made on a trading day
        
        # Get the last forecast_horizon prices (these should be the actual prices during forecast period)
        actual_prices = all_prices[-forecast_horizon:] if len(all_prices) >= forecast_horizon else all_prices
        
        if len(actual_prices) < forecast_horizon:
            return {
                "available": False,
                "prices": None,
                "message": f"Only {len(actual_prices)} data points available, need {forecast_horizon}"
            }
        
        return {
            "available": True,
            "prices": actual_prices,
            "message": f"Successfully loaded {len(actual_prices)} actual prices for {symbol}",
            "symbol": symbol,
            "forecast_date": forecast_timestamp.isoformat(),
            "forecast_horizon": forecast_horizon
        }
        
    except Exception as e:
        logger.error(f"Error fetching actual prices for forecast {forecast_id}: {e}", exc_info=True)
        return {
            "available": False,
            "prices": None,
            "message": f"Error fetching price data: {str(e)}"
        }










