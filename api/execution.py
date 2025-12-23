"""
Execution API.

Endpoints for manual trade execution and connection status.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Literal
import logging

from config.settings import get_settings
from execution.ibkr import get_ibkr_trader, get_paper_trading_trader

logger = logging.getLogger("api.execution")

router = APIRouter(prefix="/api/trade", tags=["trade"])

class TradeRequest(BaseModel):
    symbol: str
    action: Literal["BUY", "SELL"]
    quantity: float
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    price: Optional[float] = None

class TradeResponse(BaseModel):
    status: str
    order_id: Optional[str] = None
    message: str

class ConnectionStatus(BaseModel):
    connected: bool
    account_id: str
    host: str
    port: int
    mode: str
    error: Optional[str] = None

@router.get("/status", response_model=ConnectionStatus)
async def get_connection_status():
    """Check IBKR connection status."""
    settings = get_settings()
    
    # Use Manager directly for truth
    from execution.connection_manager import get_connection_manager
    manager = get_connection_manager()
    
    health = manager.check_health()
    
    connected = health["connected"]
    port = health["port"]
    
    mode = "LIVE" if settings.live_trading_enabled else ("PAPER" if port == 7497 else "RESTRICTED")
    
    return {
        "connected": connected,
        "account_id": str(health.get("account", "N/A")),
        "host": str(health.get("host", "N/A")),
        "port": port,
        "mode": mode,
        "error": health.get("error")
    }

@router.post("/execute", response_model=TradeResponse)
async def execute_trade(trade: TradeRequest):
    """
    Execute a manual trade.
    
    Requires LIVE_TRADING_ENABLED to be True (or running on Paper Port).
    """
    settings = get_settings()
    bridge = get_bridge()
    
    if not bridge:
        raise HTTPException(status_code=503, detail="IBKR Bridge not initialized")
        
    # Safety Check
    is_paper_port = (bridge.port == 7497)
    if not settings.live_trading_enabled and not is_paper_port:
        raise HTTPException(
            status_code=403, 
            detail="Live Execution is DISABLED. Enable it in Settings or switch to Paper Trading port (7497)."
        )
        
    logging.info(f"👨‍💻 Manual execution requested: {trade}")
    
    try:
        order = bridge.execute_trade(
            action=trade.action,
            symbol=trade.symbol,
            quantity=trade.quantity,
            order_type=trade.order_type,
            limit_price=trade.price or 0.0
        )
        
        if order:
            return {
                "status": "submitted",
                "order_id": str(order.orderId),
                "message": f"Order submitted: {trade.action} {trade.quantity} {trade.symbol}"
            }
        else:
             raise HTTPException(status_code=500, detail="Order execution failed (Check logs)")
             
    except Exception as e:
        logger.error(f"Manual execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
