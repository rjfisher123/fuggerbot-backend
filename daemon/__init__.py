"""
Daemon module for FuggerBot.

Contains background services and signal extraction utilities.
"""
from daemon.signal_extractor import SignalExtractor, RSS_FEED_URLS
from daemon.classifier import RegimeClassifier
from daemon.watcher import MacroDaemon

__all__ = [
    "SignalExtractor",
    "RSS_FEED_URLS",
    "RegimeClassifier",
    "MacroDaemon",
]

