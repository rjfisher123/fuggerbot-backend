"""
Market data API endpoints for live prices and charts.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import yfinance as yf
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dash.utils.price_feed import get_price
from dash.utils.forecast_helper import get_historical_prices
from core.logger import logger

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/price/{symbol}")
async def get_live_price(symbol: str) -> Dict[str, Any]:
    """
    Get current live price for a symbol.
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Dict with current price and timestamp
    """
    try:
        price = get_price(symbol.upper())
        if price is None:
            raise HTTPException(status_code=404, detail=f"Price not available for {symbol}")
        
        return {
            "symbol": symbol.upper(),
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching price: {str(e)}")


@router.get("/prices")
async def get_multiple_prices(symbols: str = Query(..., description="Comma-separated list of symbols")) -> Dict[str, Any]:
    """
    Get current prices for multiple symbols.
    
    Args:
        symbols: Comma-separated list of symbols (e.g., "AAPL,MSFT,GOOGL")
    
    Returns:
        Dict mapping symbols to prices
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        prices = {}
        
        for symbol in symbol_list:
            price = get_price(symbol)
            if price is not None:
                prices[symbol] = price
        
        return {
            "prices": prices,
            "timestamp": datetime.now().isoformat(),
            "count": len(prices)
        }
    except Exception as e:
        logger.error(f"Error fetching prices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching prices: {str(e)}")


@router.get("/chart/{symbol}")
async def get_price_chart(
    symbol: str,
    period: str = Query("1d", description="Period: 1d, 5d, 1mo, 3mo, 6mo, 1y"),
    interval: str = Query("5m", description="Interval: 1m, 5m, 15m, 30m, 1h, 1d")
) -> Dict[str, Any]:
    """
    Get price chart data for a symbol.
    
    Args:
        symbol: Trading symbol
        period: Time period for chart
        interval: Data interval
    
    Returns:
        Dict with timestamps and prices for charting
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data available for {symbol}")
        
        # Convert to chart-friendly format
        timestamps = [ts.isoformat() for ts in hist.index]
        closes = hist["Close"].tolist()
        opens = hist["Open"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        volumes = hist["Volume"].tolist()
        
        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": {
                "timestamps": timestamps,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes
            },
            "current_price": closes[-1] if closes else None,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {str(e)}")


@router.get("/trade-timeline")
async def get_trade_timeline(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, description="Number of trades to return")
) -> Dict[str, Any]:
    """
    Get trade execution timeline for charting.
    
    Args:
        symbol: Optional symbol filter
        limit: Maximum number of trades
    
    Returns:
        Dict with trade timeline data
    """
    try:
        from services.trade_service import get_trade_service
        from persistence.db import SessionLocal
        from persistence.repositories_trades import TradeExecutionRepository
        
        with SessionLocal() as session:
            repo = TradeExecutionRepository(session)
            
            if symbol:
                executions = repo.list_by_symbol(symbol.upper(), limit=limit)
            else:
                executions = repo.list_recent(limit=limit)
            
            trades = []
            for exec in executions:
                trades.append({
                    "timestamp": exec.execution_time.isoformat() if exec.execution_time else None,
                    "symbol": exec.symbol,
                    "action": exec.action,
                    "quantity": exec.quantity,
                    "price": exec.execution_price,
                    "status": exec.status,
                    "order_id": exec.order_id
                })
            
            return {
                "trades": trades,
                "count": len(trades),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error fetching trade timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching trade timeline: {str(e)}")

