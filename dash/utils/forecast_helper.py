"""Helper functions for fetching historical data and generating forecasts."""
import yfinance as yf
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_historical_prices(
    symbol: str,
    period: str = "1y",
    interval: str = "1d"
) -> Optional[List[float]]:
    """
    Fetch historical price data for a symbol.
    
    Args:
        symbol: Stock or crypto symbol
        period: Period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
    Returns:
        List of closing prices (most recent last) or None if error
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            logger.warning(f"No historical data for {symbol}")
            return None
        
        # Return closing prices as list (oldest to newest)
        prices = hist["Close"].tolist()
        logger.info(f"Fetched {len(prices)} data points for {symbol}")
        return prices
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}", exc_info=True)
        return None


def get_price_statistics(prices: List[float]) -> Dict[str, float]:
    """
    Calculate basic statistics for a price series.
    
    Args:
        prices: List of prices
        
    Returns:
        Dict with statistics
    """
    if not prices:
        return {}
    
    import numpy as np
    prices_array = np.array(prices)
    
    return {
        "current": float(prices[-1]),
        "min": float(np.min(prices_array)),
        "max": float(np.max(prices_array)),
        "mean": float(np.mean(prices_array)),
        "std": float(np.std(prices_array)),
        "volatility_pct": float((np.std(prices_array) / np.mean(prices_array)) * 100),
        "count": len(prices)
    }











