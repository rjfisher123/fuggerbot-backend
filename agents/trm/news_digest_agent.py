"""
News Digest Agent - Level 2 Perception Layer.

Filters and scores raw RSS headlines for high-impact events.
Prevents the LLM from being flooded with irrelevant noise.
"""
import logging
from typing import List, Dict, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)


class NewsSentiment(str, Enum):
    """News sentiment categories."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"


class NewsImpact(str, Enum):
    """News impact levels."""
    CRITICAL = "CRITICAL"  # Immediate market-moving event
    HIGH = "HIGH"  # Significant catalyst
    MEDIUM = "MEDIUM"  # Notable but not urgent
    LOW = "LOW"  # Background noise


class NewsDigest(BaseModel):
    """
    Processed news summary with sentiment and impact scoring.
    """
    impact_level: NewsImpact = Field(..., description="Overall impact level")
    sentiment: NewsSentiment = Field(..., description="Market sentiment")
    summary: str = Field(..., description="Human-readable summary for LLM")
    triggered_keywords: List[str] = Field(default_factory=list, description="High-impact keywords found")
    headline_count: int = Field(..., description="Number of headlines processed")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this digest was created")
    
    def to_prompt_string(self) -> str:
        """
        Format digest for LLM injection.
        
        Returns:
            Formatted string for prompt
        """
        if self.impact_level == NewsImpact.CRITICAL:
            icon = "🚨"
        elif self.impact_level == NewsImpact.HIGH:
            icon = "⚠️"
        elif self.impact_level == NewsImpact.MEDIUM:
            icon = "ℹ️"
        else:
            icon = "📰"
        
        return f"{icon} NEWS DIGEST: {self.summary}"


class NewsDigestAgent:
    """
    News Digest Agent - The Filter.
    
    Scans headlines for high-impact keywords and converts raw RSS
    into actionable sentiment vectors.
    """
    
    # High-impact keyword categories
    CRITICAL_KEYWORDS = {
        "sec", "lawsuit", "investigation", "fraud", "hack", "hacked", 
        "insolvency", "bankrupt", "shutdown", "war", "nuclear", "emergency"
    }
    
    HIGH_IMPACT_KEYWORDS = {
        "rate hike", "rate cut", "fed", "powell", "earnings", "cpi", "inflation",
        "jobs report", "gdp", "recession", "rally", "crash", "surge", "plunge"
    }
    
    BEARISH_KEYWORDS = {
        "crash", "plunge", "lawsuit", "investigation", "fraud", "hack", "bearish",
        "selloff", "sell-off", "decline", "drop", "fall", "weak", "miss", "disappoint"
    }
    
    BULLISH_KEYWORDS = {
        "rally", "surge", "bullish", "breakout", "gains", "rise", "beat", 
        "exceed", "strong", "growth", "upgrade", "buy"
    }
    
    FEAR_KEYWORDS = {
        "fear", "panic", "crisis", "emergency", "war", "recession", "crash"
    }
    
    def __init__(self):
        """Initialize the news digest agent."""
        logger.info("NewsDigestAgent initialized")
    
    def _tokenize(self, text: str) -> Set[str]:
        """
        Tokenize text for keyword matching.
        
        Args:
            text: Input text
        
        Returns:
            Set of lowercase tokens
        """
        # Simple whitespace tokenization, convert to lowercase
        tokens = text.lower().split()
        
        # Also check bi-grams for multi-word keywords
        bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1)]
        
        return set(tokens + bigrams)
    
    def _score_headline(self, headline: str) -> Dict[str, any]:
        """
        Score a single headline for impact and sentiment.
        
        Args:
            headline: Headline text
        
        Returns:
            Dict with impact_score, sentiment, and triggered_keywords
        """
        tokens = self._tokenize(headline)
        
        # Check for keyword matches
        critical_matches = tokens.intersection(self.CRITICAL_KEYWORDS)
        high_matches = tokens.intersection(self.HIGH_IMPACT_KEYWORDS)
        bearish_matches = tokens.intersection(self.BEARISH_KEYWORDS)
        bullish_matches = tokens.intersection(self.BULLISH_KEYWORDS)
        fear_matches = tokens.intersection(self.FEAR_KEYWORDS)
        
        # Calculate impact score
        impact_score = 0
        triggered_keywords = []
        
        if critical_matches:
            impact_score += 100
            triggered_keywords.extend(list(critical_matches))
        if high_matches:
            impact_score += 50
            triggered_keywords.extend(list(high_matches))
        if bearish_matches or bullish_matches:
            impact_score += 10
        
        # Determine sentiment
        if fear_matches or len(bearish_matches) > len(bullish_matches):
            sentiment = NewsSentiment.FEAR if fear_matches else NewsSentiment.BEARISH
        elif len(bullish_matches) > len(bearish_matches):
            sentiment = NewsSentiment.BULLISH
        else:
            sentiment = NewsSentiment.NEUTRAL
        
        return {
            "impact_score": impact_score,
            "sentiment": sentiment,
            "triggered_keywords": triggered_keywords
        }
    
    def _filter_irrelevant(self, headlines: List[str], symbol: str) -> List[str]:
        """
        Filter out headlines that are clearly irrelevant to the symbol.
        
        Args:
            headlines: List of headline strings
            symbol: Trading symbol
        
        Returns:
            Filtered list of headlines
        """
        # For now, simple implementation: keep all headlines
        # In future, could use more sophisticated filtering
        # (e.g., only keep headlines mentioning the symbol or its sector)
        
        # Extract base symbol (remove -USD suffix)
        base_symbol = symbol.upper().replace("-USD", "")
        
        filtered = []
        for headline in headlines:
            headline_upper = headline.upper()
            
            # Always keep high-impact headlines regardless of relevance
            tokens = self._tokenize(headline)
            if tokens.intersection(self.CRITICAL_KEYWORDS) or tokens.intersection(self.HIGH_IMPACT_KEYWORDS):
                filtered.append(headline)
            # Keep symbol-specific headlines
            elif base_symbol in headline_upper:
                filtered.append(headline)
        
        # If we filtered everything out, return original list (don't over-filter)
        return filtered if filtered else headlines
    
    def digest(self, raw_news: str, symbol: str) -> NewsDigest:
        """
        Process raw news text into a digest with impact scoring.
        
        Args:
            raw_news: Raw news text from NewsFetcher (formatted string)
            symbol: Trading symbol for relevance filtering
        
        Returns:
            NewsDigest with impact level and sentiment
        """
        # Parse headlines from formatted string
        lines = raw_news.split("\n")
        headlines = [line.split(". ", 1)[1] if ". " in line else line 
                    for line in lines[1:] if line.strip() and not line.startswith("RECENT") and not line.startswith("BROADER")]
        
        if not headlines:
            logger.info(f"No headlines to process for {symbol}")
            return NewsDigest(
                impact_level=NewsImpact.LOW,
                sentiment=NewsSentiment.NEUTRAL,
                summary="No significant news catalysts detected.",
                headline_count=0
            )
        
        # Filter irrelevant headlines
        filtered_headlines = self._filter_irrelevant(headlines, symbol)
        
        # Score each headline
        scores = [self._score_headline(h) for h in filtered_headlines]
        
        # Aggregate scores
        total_impact = sum(s["impact_score"] for s in scores)
        avg_impact = total_impact / len(scores) if scores else 0
        
        # Collect all triggered keywords
        all_keywords = []
        for s in scores:
            all_keywords.extend(s["triggered_keywords"])
        
        # Count sentiment distribution
        sentiment_counts = {
            NewsSentiment.BULLISH: sum(1 for s in scores if s["sentiment"] == NewsSentiment.BULLISH),
            NewsSentiment.BEARISH: sum(1 for s in scores if s["sentiment"] == NewsSentiment.BEARISH),
            NewsSentiment.FEAR: sum(1 for s in scores if s["sentiment"] == NewsSentiment.FEAR),
            NewsSentiment.NEUTRAL: sum(1 for s in scores if s["sentiment"] == NewsSentiment.NEUTRAL),
        }
        
        # Determine overall sentiment
        max_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        
        # Determine impact level
        if avg_impact >= 80:
            impact_level = NewsImpact.CRITICAL
        elif avg_impact >= 40:
            impact_level = NewsImpact.HIGH
        elif avg_impact >= 15:
            impact_level = NewsImpact.MEDIUM
        else:
            impact_level = NewsImpact.LOW
        
        # Generate summary
        unique_keywords = list(set(all_keywords))[:3]
        if impact_level == NewsImpact.CRITICAL:
            summary = f"CRITICAL EVENT: {', '.join(unique_keywords)}. Market sentiment: {max_sentiment.value}."
        elif impact_level == NewsImpact.HIGH:
            summary = f"HIGH IMPACT: {', '.join(unique_keywords)}. Market sentiment: {max_sentiment.value}."
        elif impact_level == NewsImpact.MEDIUM:
            summary = f"Notable market activity detected. Sentiment: {max_sentiment.value}."
        else:
            summary = "No significant news catalysts detected."
        
        logger.info(f"News digest for {symbol}: {impact_level.value} impact, {max_sentiment.value} sentiment")
        
        return NewsDigest(
            impact_level=impact_level,
            sentiment=max_sentiment,
            summary=summary,
            triggered_keywords=list(set(all_keywords)),
            headline_count=len(filtered_headlines)
        )


# Singleton instance
_news_digest_agent: Optional[NewsDigestAgent] = None


def get_news_digest_agent() -> NewsDigestAgent:
    """
    Get or create singleton NewsDigestAgent instance.
    
    Returns:
        NewsDigestAgent instance
    """
    global _news_digest_agent
    
    if _news_digest_agent is None:
        _news_digest_agent = NewsDigestAgent()
    
    return _news_digest_agent


if __name__ == "__main__":
    # Test the news digest agent
    logging.basicConfig(level=logging.INFO)
    
    # Sample raw news
    test_news = """RECENT NEWS FOR BTC-USD:
1. SEC sues Binance for fraud and money laundering
2. Bitcoin surges 15% on ETF approval hopes
3. Fed signals rate hike pause, crypto markets rally"""
    
    agent = get_news_digest_agent()
    digest = agent.digest(test_news, "BTC-USD")
    
    print("News Digest Test:")
    print(f"Impact: {digest.impact_level.value}")
    print(f"Sentiment: {digest.sentiment.value}")
    print(f"Summary: {digest.summary}")
    print(f"Keywords: {digest.triggered_keywords}")
    print(f"\nFormatted for LLM:\n{digest.to_prompt_string()}")

