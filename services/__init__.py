"""
Services module for external integrations and utilities.
"""
from services.news_fetcher import get_news_fetcher, get_news_context, NewsFetcher

__all__ = [
    "get_news_fetcher",
    "get_news_context",
    "NewsFetcher",
]
