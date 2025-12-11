"""
Enhanced logging system for FuggerBot.

Provides structured logging for:
- Trade events
- Trigger fires
- Forecast creation
- Backtest results
- IBKR callbacks
"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent / "data" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Configure root logger
root_logger = logging.getLogger("fuggerbot")
root_logger.setLevel(logging.DEBUG)

# Remove existing handlers to avoid duplicates
if root_logger.handlers:
    root_logger.handlers.clear()

# Console handler (INFO and above)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)

# File handler (DEBUG and above)
log_file = log_dir / "fuggerbot.log"
file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)

# Prevent propagation to root logger
root_logger.propagate = False


def get_logger(name: str = "fuggerbot") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (e.g., "fuggerbot.trades", "fuggerbot.triggers")
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"fuggerbot.{name}")


# Specialized loggers for different event types
trade_logger = get_logger("trades")
trigger_logger = get_logger("triggers")
forecast_logger = get_logger("forecasts")
backtest_logger = get_logger("backtests")
ibkr_logger = get_logger("ibkr")


def log_trade_event(
    event_type: str,
    symbol: str,
    action: str,
    quantity: float,
    price: Optional[float] = None,
    trade_id: Optional[str] = None,
    status: Optional[str] = None,
    **kwargs
):
    """
    Log a trade event.
    
    Args:
        event_type: Type of event (e.g., "requested", "approved", "executed", "rejected")
        symbol: Trading symbol
        action: BUY or SELL
        quantity: Number of shares
        price: Execution or limit price
        trade_id: Trade ID
        status: Trade status
        **kwargs: Additional metadata
    """
    message = f"TRADE {event_type.upper()}: {symbol} {action} {quantity}"
    if price:
        message += f" @ ${price:.2f}"
    if trade_id:
        message += f" (ID: {trade_id})"
    if status:
        message += f" [Status: {status}]"
    
    extra_data = {
        "event_type": "trade",
        "trade_type": event_type,
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "price": price,
        "trade_id": trade_id,
        "status": status,
        **kwargs
    }
    
    trade_logger.info(message, extra={"data": extra_data})


def log_trigger_fire(
    trigger_id: str,
    symbol: str,
    condition: str,
    threshold: float,
    current_price: float,
    action: str,
    **kwargs
):
    """
    Log a trigger fire event.
    
    Args:
        trigger_id: Trigger ID
        symbol: Trading symbol
        condition: Trigger condition (e.g., "<", ">", "drop_pct")
        threshold: Threshold value
        current_price: Current price when trigger fired
        action: Trigger action (e.g., "notify", "buy", "sell")
        **kwargs: Additional metadata
    """
    message = f"TRIGGER FIRED: {symbol} {condition} {threshold} (current: ${current_price:.2f}) → {action}"
    
    extra_data = {
        "event_type": "trigger_fire",
        "trigger_id": trigger_id,
        "symbol": symbol,
        "condition": condition,
        "threshold": threshold,
        "current_price": current_price,
        "action": action,
        **kwargs
    }
    
    trigger_logger.info(message, extra={"data": extra_data})


def log_forecast_creation(
    forecast_id: str,
    symbol: str,
    horizon: int,
    trust_score: float,
    fqs_score: Optional[float] = None,
    recommendation: Optional[str] = None,
    **kwargs
):
    """
    Log forecast creation.
    
    Args:
        forecast_id: Forecast ID
        symbol: Trading symbol
        horizon: Forecast horizon (days)
        trust_score: Trust score (0-1)
        fqs_score: Forecast Quality Score (0-1)
        recommendation: Trading recommendation
        **kwargs: Additional metadata
    """
    message = f"FORECAST CREATED: {symbol} (ID: {forecast_id[:12]}..., horizon: {horizon}d, trust: {trust_score:.2f})"
    if fqs_score:
        message += f", FQS: {fqs_score:.2f}"
    if recommendation:
        message += f", Recommendation: {recommendation}"
    
    extra_data = {
        "event_type": "forecast_creation",
        "forecast_id": forecast_id,
        "symbol": symbol,
        "horizon": horizon,
        "trust_score": trust_score,
        "fqs_score": fqs_score,
        "recommendation": recommendation,
        **kwargs
    }
    
    forecast_logger.info(message, extra={"data": extra_data})


def log_backtest_result(
    backtest_id: str,
    forecast_id: str,
    symbol: str,
    mae: float,
    mape: float,
    directional_accuracy: float,
    **kwargs
):
    """
    Log backtest result.
    
    Args:
        backtest_id: Backtest ID
        forecast_id: Forecast ID that was evaluated
        symbol: Trading symbol
        mae: Mean Absolute Error
        mape: Mean Absolute Percentage Error
        directional_accuracy: Directional accuracy (%)
        **kwargs: Additional metadata
    """
    message = (
        f"BACKTEST RESULT: {symbol} (Forecast: {forecast_id[:12]}...)"
        f" - MAE: ${mae:.2f}, MAPE: {mape:.2f}%, "
        f"Directional: {directional_accuracy:.1f}%"
    )
    
    extra_data = {
        "event_type": "backtest_result",
        "backtest_id": backtest_id,
        "forecast_id": forecast_id,
        "symbol": symbol,
        "mae": mae,
        "mape": mape,
        "directional_accuracy": directional_accuracy,
        **kwargs
    }
    
    backtest_logger.info(message, extra={"data": extra_data})


def log_ibkr_event(
    event_type: str,
    message: str,
    connected: Optional[bool] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs
):
    """
    Log IBKR callback/event.
    
    Args:
        event_type: Type of event (e.g., "connected", "disconnected", "order_update", "error")
        message: Event message
        connected: Connection status
        host: IBKR host
        port: IBKR port
        **kwargs: Additional metadata
    """
    log_message = f"IBKR {event_type.upper()}: {message}"
    if connected is not None:
        log_message += f" (Connected: {connected})"
    if host and port:
        log_message += f" [{host}:{port}]"
    
    extra_data = {
        "event_type": "ibkr",
        "ibkr_event_type": event_type,
        "connected": connected,
        "host": host,
        "port": port,
        **kwargs
    }
    
    ibkr_logger.info(log_message, extra={"data": extra_data})


# Main logger (for general use)
logger = root_logger





