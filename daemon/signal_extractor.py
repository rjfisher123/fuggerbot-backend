"""
Signal Extractor Daemon.

Fetches numeric data (FRED) and text data (RSS) for macroeconomic analysis.
"""
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    logging.warning("fredapi not installed. Install with: pip install fredapi")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logging.warning("feedparser not installed. Install with: pip install feedparser")

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# RSS Feed URLs for economic news
RSS_FEED_URLS = [
    "https://www.bloomberg.com/feeds/markets/news.rss",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.wsj.com/xml/rss/3_7085.xml",  # WSJ Markets
    "https://www.ft.com/?format=rss",  # Financial Times
    "https://feeds.feedburner.com/zerohedge/feed",  # Zero Hedge
]


class SignalExtractor:
    """
    Extracts macroeconomic signals from FRED data and RSS feeds.
    
    Provides both hard numeric data (FRED) and soft text data (RSS headlines)
    for regime detection and trading decisions.
    """
    
    def __init__(self):
        """Initialize the signal extractor and load API keys."""
        load_dotenv()
        
        # Load FRED API key
        self.fred_api_key = os.getenv("FRED_API_KEY")
        if not self.fred_api_key:
            logger.warning("FRED_API_KEY not found in environment. FRED data will be unavailable.")
            self.fred_client = None
        elif FRED_AVAILABLE:
            try:
                self.fred_client = Fred(api_key=self.fred_api_key)
                logger.info("FRED client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize FRED client: {e}")
                self.fred_client = None
        else:
            self.fred_client = None
        
        # Keywords for filtering RSS headlines
        self.keywords = ["Fed", "Rates", "Inflation", "GDP", "Federal Reserve", 
                        "FOMC", "Interest Rate", "CPI", "PCE", "Employment"]
        
        logger.info("SignalExtractor initialized")
    
    def get_hard_data(self) -> Dict[str, Any]:
        """
        Fetch hard numeric data from FRED.
        
        Fetches:
        - WALCL: Fed Assets/Liquidity (Total Assets of the Federal Reserve)
        - T10Y2Y: 10-Year Treasury Minus 2-Year Treasury (Yield Curve)
        - VIXCLS: CBOE Volatility Index (VIX)
        
        Returns:
            Dictionary with current values and 1-week changes for each indicator.
            Returns empty dict if FRED is unavailable or fails.
        """
        if not self.fred_client:
            logger.debug("FRED client not available, returning empty hard data")
            return {}
        
        result = {}
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        # Series to fetch
        series_map = {
            "WALCL": "Fed Assets/Liquidity",
            "T10Y2Y": "Yield Curve (10Y-2Y)",
            "VIXCLS": "VIX (Volatility Index)"
        }
        
        for series_id, description in series_map.items():
            try:
                # Fetch current value
                current_data = self.fred_client.get_series(series_id, observation_start=week_ago)
                
                if current_data.empty:
                    logger.warning(f"No data available for {series_id}")
                    continue
                
                # Get most recent value
                current_value = float(current_data.iloc[-1])
                
                # Get value from 1 week ago (or closest available)
                if len(current_data) > 1:
                    week_ago_value = float(current_data.iloc[0])
                    change = current_value - week_ago_value
                    change_pct = (change / week_ago_value * 100) if week_ago_value != 0 else 0.0
                else:
                    week_ago_value = current_value
                    change = 0.0
                    change_pct = 0.0
                
                result[series_id] = {
                    "description": description,
                    "current": current_value,
                    "week_ago": week_ago_value,
                    "change": change,
                    "change_pct": change_pct,
                    "timestamp": today.isoformat()
                }
                
                logger.debug(f"Fetched {series_id}: {current_value:.2f} (change: {change:+.2f})")
                
            except Exception as e:
                logger.error(f"Error fetching {series_id} from FRED: {e}")
                # Continue with other series even if one fails
                continue
        
        if not result:
            logger.warning("No FRED data retrieved, returning empty dict")
        
        return result
    
    def get_soft_data(self) -> List[str]:
        """
        Fetch soft text data from RSS feeds.
        
        Parses RSS feeds and filters for headlines related to:
        - Fed, Rates, Inflation, GDP, Federal Reserve, FOMC, etc.
        
        Returns:
            List of top 5 most recent relevant headlines.
            Returns empty list if RSS parsing fails.
        """
        if not FEEDPARSER_AVAILABLE:
            logger.debug("feedparser not available, returning empty soft data")
            return []
        
        all_headlines = []
        
        for feed_url in RSS_FEED_URLS:
            try:
                feed = feedparser.parse(feed_url)
                
                if feed.bozo:  # feedparser detected a problem
                    logger.debug(f"RSS feed parsing issue for {feed_url}: {feed.bozo_exception}")
                    continue
                
                # Extract headlines from entries
                for entry in feed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    combined_text = f"{title} {summary}".lower()
                    
                    # Check if headline contains any keywords
                    if any(keyword.lower() in combined_text for keyword in self.keywords):
                        # Get published date if available
                        published = entry.get("published_parsed")
                        if published:
                            try:
                                pub_date = datetime(*published[:6])
                            except:
                                pub_date = datetime.now()
                        else:
                            pub_date = datetime.now()
                        
                        all_headlines.append({
                            "title": title,
                            "source": feed.feed.get("title", "Unknown"),
                            "published": pub_date,
                            "link": entry.get("link", "")
                        })
                
            except Exception as e:
                logger.error(f"Error parsing RSS feed {feed_url}: {e}")
                # Continue with other feeds even if one fails
                continue
        
        # Sort by published date (most recent first) and take top 5
        all_headlines.sort(key=lambda x: x["published"], reverse=True)
        top_headlines = all_headlines[:5]
        
        # Format as list of headline strings
        result = [h["title"] for h in top_headlines]
        
        if not result:
            logger.debug("No relevant headlines found in RSS feeds")
        
        return result
    
    def get_all_signals(self) -> Dict[str, Any]:
        """
        Get both hard and soft data in a single call.
        
        Returns:
            Dictionary with 'hard_data' and 'soft_data' keys.
            Always returns a dict structure even if data is empty.
        """
        try:
            hard_data = self.get_hard_data()
        except Exception as e:
            logger.error(f"Error getting hard data: {e}")
            hard_data = {}
        
        try:
            soft_data = self.get_soft_data()
        except Exception as e:
            logger.error(f"Error getting soft data: {e}")
            soft_data = []
        
        return {
            "hard_data": hard_data,
            "soft_data": soft_data,
            "timestamp": datetime.now().isoformat()
        }

