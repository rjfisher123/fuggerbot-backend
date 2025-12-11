"""FuggerBot core modules."""
from .sms_notifier import send_sms, get_sms_notifier, SMSNotifier
from .alert_router import send_alert, get_alert_router, AlertRouter
from .logger import logger

# Gemini AI (optional - requires google-generativeai)
try:
    from .gemini_client import get_gemini_client, GeminiClient, GEMINI_AVAILABLE
except (ImportError, ValueError):
    GEMINI_AVAILABLE = False
    get_gemini_client = None
    GeminiClient = None

# IBKR trading (optional - requires ib_insync)
# Use lazy import to avoid event loop issues in Streamlit
try:
    from .ibkr_trader import get_ibkr_trader, IBKRTrader, TradeConfirmation, IBKR_AVAILABLE
except (ImportError, RuntimeError):
    IBKR_AVAILABLE = False
    get_ibkr_trader = None
    IBKRTrader = None
    TradeConfirmation = None

__all__ = [
    "send_sms",
    "get_sms_notifier",
    "SMSNotifier",
    "send_alert",
    "get_alert_router",
    "AlertRouter",
    "logger",
]

if GEMINI_AVAILABLE:
    __all__.extend(["get_gemini_client", "GeminiClient"])

if IBKR_AVAILABLE:
    __all__.extend(["get_ibkr_trader", "IBKRTrader", "TradeConfirmation"])