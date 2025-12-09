"""
Execution module for FuggerBot.

Contains execution wrappers for various brokers and trading platforms.
"""
from execution.ibkr import IBKRBridge

__all__ = [
    "IBKRBridge",
]

