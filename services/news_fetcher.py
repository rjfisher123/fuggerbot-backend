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


# Singleton instance
_news_fetcher: Optional[NewsFetcher] = None


def get_news_fetcher() -> NewsFetcher:
    """
    Get or create singleton NewsFetcher instance.
    
    Returns:
        NewsFetcher instance
    """
    global _news_fetcher
    
    if _news_fetcher is None:
        _news_fetcher = NewsFetcher()
    
    return _news_fetcher


# Convenience function
def get_news_context(symbol: str) -> str:
    """
    Convenience function to get news context for a symbol.
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Formatted news context string
    """
    fetcher = get_news_fetcher()
    return fetcher.get_context(symbol)


if __name__ == "__main__":
    # Test the news fetcher
    logging.basicConfig(level=logging.INFO)
    
    test_symbols = ["BTC-USD", "ETH-USD", "NVDA", "AAPL", "JPM"]
    
    for symbol in test_symbols:
        print("=" * 60)
        print(f"Testing: {symbol}")
        print("=" * 60)
        
        context = get_news_context(symbol)
        print(context)
        print()







