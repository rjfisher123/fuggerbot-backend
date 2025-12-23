"""
Financial News Fetcher Service.

Fetches relevant financial news from RSS feeds to provide market context for trading decisions.
"""
import logging
from typing import Dict, List, Optional
import feedparser
from datetime import datetime

logger = logging.getLogger(__name__)

# Hardcoded RSS Feed URLs
RSS_FEEDS = {
    "MACRO": [
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # CNBC Economy
        "https://www.reuters.com/finance/markets",  # Reuters Markets
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  # WSJ Markets
    ],
    "CRYPTO": [
        "https://cointelegraph.com/rss",  # CoinTelegraph
        "https://www.coindesk.com/arc/outboundfeeds/rss/",  # CoinDesk
    ],
    "TECH": [
        "https://www.cnbc.com/id/19854910/device/rss/rss.html",  # CNBC Tech
        "https://feeds.reuters.com/reuters/technologyNews",  # Reuters Tech
    ],
}


class NewsFetcher:
    """
    Fetches and filters financial news from RSS feeds.
    
    Provides market context by retrieving relevant headlines based on trading symbol.
    """
    
    def __init__(self):
        """Initialize the news fetcher."""
        self.feeds = RSS_FEEDS
        logger.info("NewsFetcher initialized")
    
    def _determine_category(self, symbol: str) -> str:
        """
        Determine news category based on trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USD', 'AAPL', 'NVDA')
        
        Returns:
            Category string: 'CRYPTO', 'TECH', or 'MACRO'
        """
        symbol_upper = symbol.upper()
        
        # Crypto: symbols with -USD suffix
        if "-USD" in symbol_upper:
            return "CRYPTO"
        
        # Tech stocks: Common tech symbols
        tech_symbols = [
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", 
            "NVDA", "AMD", "INTC", "NFLX", "CRM", "ORCL", "CSCO"
        ]
        if symbol_upper in tech_symbols:
            return "TECH"
        
        # Default to MACRO for all other symbols
        return "MACRO"
    
    def _fetch_feed(self, url: str) -> List[Dict[str, str]]:
        """
        Fetch and parse a single RSS feed.
        
        Args:
            url: RSS feed URL
        
        Returns:
            List of headline dictionaries with 'title' and 'published' keys
        """
        try:
            feed = feedparser.parse(url)
            
            headlines = []
            for entry in feed.entries[:10]:  # Limit to top 10 from each feed
                headline = {
                    "title": entry.get("title", "").strip(),
                    "published": entry.get("published", datetime.now().isoformat()),
                    "link": entry.get("link", "")
                }
                headlines.append(headline)
            
            return headlines
        
        except Exception as e:
            logger.warning(f"Failed to fetch feed {url}: {e}")
            return []
    
    def _filter_headlines(self, headlines: List[Dict[str, str]], symbol: str) -> List[Dict[str, str]]:
        """
        Filter headlines for relevance to a specific symbol.
        
        Args:
            headlines: List of headline dictionaries
            symbol: Trading symbol to search for
        
        Returns:
            Filtered list of relevant headlines
        """
        symbol_upper = symbol.upper()
        
        # Extract base symbol (remove -USD suffix for crypto)
        base_symbol = symbol_upper.replace("-USD", "")
        
        # Keywords to search for
        search_terms = [base_symbol]
        
        # Add common name variants for crypto
        crypto_names = {
            "BTC": ["Bitcoin", "BTC"],
            "ETH": ["Ethereum", "ETH"],
            "SOL": ["Solana", "SOL"],
            "ADA": ["Cardano", "ADA"],
        }
        if base_symbol in crypto_names:
            search_terms.extend(crypto_names[base_symbol])
        
        # Filter headlines containing any search term
        filtered = []
        for headline in headlines:
            title_upper = headline["title"].upper()
            if any(term in title_upper for term in search_terms):
                filtered.append(headline)
        
        return filtered
    
    def get_context(self, symbol: str, max_specific: int = 3, max_fallback: int = 5) -> str:
        """
        Get news context for a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USD', 'NVDA')
            max_specific: Maximum number of symbol-specific headlines to return
            max_fallback: Maximum number of macro headlines to return as fallback
        
        Returns:
            Formatted string with news headlines for LLM injection
        """
        category = self._determine_category(symbol)
        logger.info(f"Fetching news context for {symbol} (category: {category})")
        
        # Fetch feeds for the determined category
        all_headlines = []
        for feed_url in self.feeds.get(category, []):
            headlines = self._fetch_feed(feed_url)
            all_headlines.extend(headlines)
        
        if not all_headlines:
            logger.warning(f"No headlines fetched for {symbol}")
            return "No recent news available."
        
        # Filter for symbol-specific headlines
        specific_headlines = self._filter_headlines(all_headlines, symbol)
        
        if specific_headlines:
            # Return top N specific headlines
            selected = specific_headlines[:max_specific]
            logger.info(f"Found {len(specific_headlines)} specific headlines for {symbol}, returning top {len(selected)}")
            
            context_lines = [f"RECENT NEWS FOR {symbol}:"]
            for i, headline in enumerate(selected, 1):
                context_lines.append(f"{i}. {headline['title']}")
            
            return "\n".join(context_lines)
        
        else:
            # Fallback to generic MACRO headlines
            logger.info(f"No specific headlines for {symbol}, using MACRO fallback")
            
            macro_headlines = []
            for feed_url in self.feeds.get("MACRO", []):
                headlines = self._fetch_feed(feed_url)
                macro_headlines.extend(headlines)
            
            if not macro_headlines:
                return "No recent news available."
            
            selected = macro_headlines[:max_fallback]
            
            context_lines = [f"BROADER MARKET NEWS (no specific news for {symbol}):"]
            for i, headline in enumerate(selected, 1):
                context_lines.append(f"{i}. {headline['title']}")
            
            return "\n".join(context_lines)


    async def fetch_ibkr_news(self, symbol: str) -> List[Dict[str, str]]:
        """
        Fetch news from IBKR API.
        """
        from execution.connection_manager import get_connection_manager
        from ib_insync import Stock, Contract
        
        manager = get_connection_manager()
        if not manager.connected:
            return []
            
        ib = manager.get_ib()
        if not ib.isConnected():
             return []
             
        headlines = []
        try:
            # Check for news providers if needed, though usually configured in TWS
            # providers = await ib.reqNewsProvidersAsync()
            # logger.debug(f"News providers: {providers}")
            
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            await ib.qualifyContractsAsync(contract)
            
            if not contract.conId:
                logger.warning(f"Could not resolve contract for {symbol}")
                return []

            # Request historical news
            # BRFG = Briefing.com, BUS = Business Wire, RTRS = Reuters
            provider_codes = "BRFG+BUS+RTRS" 
            
            # Use safe async request
            news_items = await ib.reqHistoricalNewsAsync(
                contract.conId, 
                provider_codes, 
                "", 
                "", 
                10,
                [] 
            )
            
            for item in news_items:
                headlines.append({
                    "title": item.headline,
                    "published": str(item.time),
                    "link": "", 
                    "source": "IBKR" # Explicit source
                })
                
        except Exception as e:
            logger.warning(f"Failed to fetch IBKR news for {symbol}: {e}")
            
        return headlines

    async def get_context_async(self, symbol: str, max_specific: int = 5) -> str:
        """
        Get news context for a trading symbol (Async).
        Merges RSS and IBKR news.
        """
        category = self._determine_category(symbol)
        
        # 1. RSS Feeds (Sync but fast enough, or could be threaded)
        # We'll run in executor to be safe if strictly async
        import asyncio
        loop = asyncio.get_running_loop()
        
        def fetch_rss():
             all_headlines = []
             for feed_url in self.feeds.get(category, []):
                all_headlines.extend(self._fetch_feed(feed_url))
             return self._filter_headlines(all_headlines, symbol)
             
        rss_headlines = await loop.run_in_executor(None, fetch_rss)
        
        # 2. IBKR News
        ib_headlines = await self.fetch_ibkr_news(symbol)
        
        # Merge
        # Prioritize IBKR as it is more specific
        merged = ib_headlines + rss_headlines
        
        if not merged:
            # Fallback
            def fetch_macro():
                macro = []
                for feed_url in self.feeds.get("MACRO", []):
                    macro.extend(self._fetch_feed(feed_url))
                return macro[:5]
            
            macro_headlines = await loop.run_in_executor(None, fetch_macro)
            if not macro_headlines:
                return "No recent news available."
                
            return "\n".join([f"{i}. {h['title']}" for i, h in enumerate(macro_headlines, 1)])

        # Select top N
        selected = merged[:max_specific]
        
        context_lines = [f"NEWS FOR {symbol} (Source: IBKR/RSS):"]
        for i, h in enumerate(selected, 1):
             source = h.get("source", "RSS")
             context_lines.append(f"{i}. [{source}] {h['title']}")
             
        return "\n".join(context_lines)

# Singleton instance
_news_fetcher: Optional[NewsFetcher] = None

def get_news_fetcher() -> NewsFetcher:
    """Get singleton."""
    global _news_fetcher
    if _news_fetcher is None:
        _news_fetcher = NewsFetcher()
    return _news_fetcher

# Async Convenience
async def get_news_context_async(symbol: str) -> str:
    fetcher = get_news_fetcher()
    return await fetcher.get_context_async(symbol)







