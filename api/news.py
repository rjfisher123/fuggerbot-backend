"""
News Debugging API.
"""
from fastapi import APIRouter, HTTPException
from services.news_fetcher import get_news_fetcher

router = APIRouter(prefix="/api/news", tags=["news"])

@router.get("/test/{symbol}")
async def test_ibkr_news(symbol: str):
    """
    Debug endpoint to fetch news directly from IBKR.
    """
    fetcher = get_news_fetcher()
    try:
        # 1. Fetch from IBKR
        ib_news = await fetcher.fetch_ibkr_news(symbol)
        
        # 2. Fetch context (merged)
        context = await fetcher.get_context_async(symbol)
        
        return {
            "symbol": symbol,
            "ib_raw_count": len(ib_news),
            "ib_raw": ib_news,
            "merged_context": context
        }
@router.get("/debug")
async def debug_news():
    """
    Debug endpoint to check connectivity.
    """
    return await test_ibkr_news("SPY")

@router.post("/refresh")
async def refresh_news():
    """Clear news cache (placeholder)."""
    return {"status": "cleared"}
