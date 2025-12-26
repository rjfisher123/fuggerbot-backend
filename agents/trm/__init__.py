"""
Tiny Recursive Model (TRM) Agents.

Level 2 (Perception) agents that digest raw data into semantic understanding.
"""
from agents.trm.news_digest_agent import NewsDigestAgent, NewsDigest, get_news_digest_agent
from agents.trm.memory_summarizer import MemorySummarizer, MemoryNarrative, get_memory_summarizer

__all__ = [
    "NewsDigestAgent",
    "NewsDigest",
    "get_news_digest_agent",
    "MemorySummarizer",
    "MemoryNarrative",
    "get_memory_summarizer",
]








