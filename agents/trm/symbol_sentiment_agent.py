"""
Symbol Sentiment Agent - Level 2 Perception Layer.

Specialized agent for fine-grained sentiment analysis of specific tickers,
complimenting the broader NewsDigestAgent.
"""
import logging
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class SentimentZone(str, Enum):
    """Sentiment zones based on score."""
    EUPHORIA = "EUPHORIA"       # > 0.8
    BULLISH = "BULLISH"         # > 0.3
    NEUTRAL = "NEUTRAL"         # -0.3 to 0.3
    BEARISH = "BEARISH"         # < -0.3
    PANIC = "PANIC"             # < -0.8

class SentimentOutput(BaseModel):
    """Output from Symbol Sentiment Agent."""
    symbol: str
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score (-1 to 1)")
    zone: SentimentZone = Field(..., description="Sentiment zone classification")
    volatility_flag: bool = Field(..., description="True if high volatility expected")
    source_count: int = Field(..., description="Number of sources analyzed")
    primary_driver: str = Field(..., description="Main reason for the score")
    timestamp: datetime = Field(default_factory=datetime.now)

class SymbolSentimentAgent:
    """
    Analyzes RSS headlines to produce a granular sentiment score for a specific symbol.
    """
    
    # Simple dictionary-based sentiment for v1 (to be upgraded to LLM later)
    POSITIVE_WORDS = {
        "surge", "jump", "rally", "gain", "climb", "soar", "profit", "beat", 
        "exceeded", "strong", "bull", "upgrade", "buy", "record", "high", "growth",
        "approval", "launch", "partnership", "success"
    }
    
    NEGATIVE_WORDS = {
        "drop", "fall", "plunge", "crash", "loss", "miss", "weak", "bear", 
        "downgrade", "sell", "low", "decline", "warn", "fail", "lawsuit",
        "investigation", "fraud", "ban", "restrict", "hack"
    }
    
    VOLATILITY_WORDS = {
        "volatile", "uncertain", "swing", "wild", "chaos", "turbulence",
        "shock", "surprise", "sudden", "massive"
    }

    def __init__(self):
        """Initialize the agent."""
        logger.info("SymbolSentimentAgent initialized")

    def _analyze_text(self, text: str) -> float:
        """Calculate sentiment score for a single text string."""
        tokens = text.lower().split()
        score = 0.0
        word_count = 0
        
        for token in tokens:
            # Simple clean
            token = token.strip('.,!?:;"')
            if token in self.POSITIVE_WORDS:
                score += 1.0
                word_count += 1
            elif token in self.NEGATIVE_WORDS:
                score -= 1.0
                word_count += 1
        
        # Normalize to -1 to 1 roughly, dampening extreme values
        if word_count == 0:
            return 0.0
        
        # Sigmoid-ish squash or simple ratio? Simple ratio for now.
        final_score = score / max(word_count, 1) # This gives -1 to 1
        return final_score

    def analyze(self, symbol: str, headlines: List[str]) -> SentimentOutput:
        """
        Analyze a list of headlines for a symbol.
        
        Args:
            symbol: Ticker symbol
            headlines: List of headline strings
            
        Returns:
            SentimentOutput object
        """
        if not headlines:
            return SentimentOutput(
                symbol=symbol,
                score=0.0,
                zone=SentimentZone.NEUTRAL,
                volatility_flag=False,
                source_count=0,
                primary_driver="No headlines available"
            )
        
        total_score = 0.0
        volatility_hits = 0
        relevant_headlines = 0
        
        drivers = []
        
        for h in headlines:
            # We assume headlines passed here are already loosely filtered for relevance
            # or we are fine analyzing general market sentiment if symbol specific is scarce
            
            # Check for volatility
            is_volatile = any(w in h.lower() for w in self.VOLATILITY_WORDS)
            if is_volatile:
                volatility_hits += 1
                
            score = self._analyze_text(h)
            if score != 0:
                total_score += score
                relevant_headlines += 1
                drivers.append((abs(score), h)) # Keep track of strongest drivers
        
        # Calculate final average score
        avg_score = total_score / max(relevant_headlines, 1)
        
        # Dampen if very few relevant headlines found
        confidence_weight = min(relevant_headlines / 3.0, 1.0) # Need 3+ headlines for full weight
        final_score = avg_score * confidence_weight
        
        # Determine Zone
        if final_score > 0.8:
            zone = SentimentZone.EUPHORIA
        elif final_score > 0.3:
            zone = SentimentZone.BULLISH
        elif final_score < -0.8:
            zone = SentimentZone.PANIC
        elif final_score < -0.3:
            zone = SentimentZone.BEARISH
        else:
            zone = SentimentZone.NEUTRAL
            
        # Determine Volatility Flag
        vol_flag = (volatility_hits / max(len(headlines), 1)) > 0.2 # >20% headlines mention volatility
        
        # Find primary driver
        drivers.sort(key=lambda x: x[0], reverse=True)
        primary_driver = drivers[0][1] if drivers else "Neutral market chatter"
        
        logger.info(f"Sentiment for {symbol}: {final_score:.2f} ({zone.value})")
        
        return SentimentOutput(
            symbol=symbol,
            score=final_score,
            zone=zone,
            volatility_flag=vol_flag,
            source_count=len(headlines),
            primary_driver=primary_driver
        )

# Singleton
_symbol_sentiment_agent: Optional[SymbolSentimentAgent] = None

def get_symbol_sentiment_agent() -> SymbolSentimentAgent:
    global _symbol_sentiment_agent
    if _symbol_sentiment_agent is None:
        _symbol_sentiment_agent = SymbolSentimentAgent()
    return _symbol_sentiment_agent

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    agent = get_symbol_sentiment_agent()
    
    test_headlines = [
        "Bitcoin surges to new highs on strong volume",
        "Analysts predict massive gains for crypto",
        "Volatile trading expected ahead of Fed meeting"
    ]
    
    result = agent.analyze("BTC-USD", test_headlines)
    print(result.json(indent=2))
