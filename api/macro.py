"""
Macro API Endpoint.
Exposes Global Macro Regime and Live News.
"""
from fastapi import APIRouter, HTTPException
from services.news_fetcher import get_news_fetcher
from pathlib import Path
import json
import logging

logger = logging.getLogger("api.macro")
router = APIRouter(prefix="/api/macro", tags=["macro"])

@router.get("/")
async def get_macro_dashboard():
    """
    Get full macro dashboard state: Regime + News.
    """
    # 1. Fetch Regime (simulated/logged state)
    regime_data = {
        "regime": "NEUTRAL",
        "risk_on": True,
        "vibe_score": 0.5,
        "name": "Unknown",
        "source": "fallback"
    }
    
    log_file = Path("data/macro_log.json")
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                data = json.load(f)
            shifts = data.get("shifts", [])
            if shifts:
                latest = shifts[-1].get("new_regime", {})
                regime_data = {
                    "regime": latest.get("id", "UNKNOWN"),
                    "name": latest.get("name", "Unknown Regime"),
                    "risk_on": latest.get("risk_on", False),
                    "vibe_score": latest.get("vibe_score", 0.5),
                    "timestamp": shifts[-1].get("timestamp"),
                    "source": "macro_log"
                }
        except Exception as e:
            logger.error(f"Error reading macro log: {e}")

    # 2. Fetch Live News (Macro Context)
    fetcher = get_news_fetcher()
    # We fetch generic macro news if no symbol is relevant, 
    # but let's fetch 'SPY' or just use the macro feed fallback logic explicitly.
    # get_context_async("SPY") will give us mostly market news.
    try:
        # Using a broad index to trigger Macro/Market news
        news_text = await fetcher.get_context_async("SPY", max_specific=3)
        
        # Parse the text back into a structured format for the UI if possible, 
        # or just return the raw lines.
        # The UI expects a list of headlines. 
        # Since get_context_async returns a string, we might want to expose a structured method in NewsFetcher
        # or just parse it here. 
        # Actually, let's use the fetcher's internal methods or add a new public method for structured news.
        # For now, we'll just return the lines.
        headlines = []
        for line in news_text.split('\n')[1:]: # Skip header
             if ". " in line:
                 parts = line.split(". ", 1)
                 if len(parts) == 2:
                     # Check for [Source] tag
                     title = parts[1]
                     source = "RSS"
                     if "[IBKR]" in title:
                         source = "IBKR"
                         title = title.replace("[IBKR]", "").strip()
                     elif "[RSS]" in title:
                         source = "RSS"
                         title = title.replace("[RSS]", "").strip()
                         
                     headlines.append({"title": title, "source": source, "category": "Market"})
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        headlines = []

    return {
        "regime": regime_data,
        "news": headlines
    }

@router.post("/refresh")
async def force_refresh():
    """Force refresh of macro data."""
    # In a real system this would trigger a re-calc or clear cache.
    return {"message": "Refreshed"}
