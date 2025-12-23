"""
Settings API.

Endpoints for managing application configuration, including the Live Trading safety switch.
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import logging

from config.settings import get_settings, Settings

logger = logging.getLogger("api.settings")

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsResponse(BaseModel):
    env_state: str
    live_trading_enabled: bool
    deepseek_model: str

class ToggleRequest(BaseModel):
    enabled: bool

@router.get("/", response_model=SettingsResponse)
async def get_current_settings():
    """Get current configuration state."""
    settings = get_settings()
    return {
        "env_state": settings.env_state,
        "live_trading_enabled": settings.live_trading_enabled,
        "deepseek_model": settings.deepseek_model
    }

@router.post("/toggle_trading")
async def toggle_live_trading(request: ToggleRequest):
    """
    Enable or Disable live trading execution.
    
    WARNING: Enabling this allows the system to place real orders.
    """
    settings = get_settings()
    
    if request.enabled:
        logger.warning("🛑 LIVE TRADING ENDABLED BY USER REQUEST")
    else:
        logger.info("🔒 Live trading disabled by user request")
        
    # Update in-memory settings
    # Note: Pydantic models are immutable by default in v2, but BaseSettings might allow it or we need to replace the instance
    # Actually BaseSettings are mutable unless configured otherwise.
    settings.live_trading_enabled = request.enabled
    
    return {
        "message": f"Live trading is now {'ENABLED' if request.enabled else 'DISABLED'}",
        "live_trading_enabled": settings.live_trading_enabled
    }
