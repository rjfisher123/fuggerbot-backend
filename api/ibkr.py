"""
IBKR API endpoints.

Provides endpoints for monitoring and controlling the IBKR connection.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict
import logging
from execution.connection_manager import get_connection_manager

router = APIRouter(prefix="/api/ibkr", tags=["ibkr"])

class ConnectionStatus(BaseModel):
    connected: bool
    host: Optional[str] = None
    port: Optional[int] = None
    paper_trading: Optional[bool] = None
    client_id: Optional[int] = None
    error: Optional[str] = None

class ConnectResponse(BaseModel):
    success: bool
    message: str

@router.get("/status", response_model=ConnectionStatus)
async def get_status(paper_trading: bool = False):
    """Get current IBKR connection status."""
    try:
        client = get_ibkr_client(paper_trading=paper_trading)
        status = client.get_connection_status()
        return status
    except Exception as e:
        logger.error(f"Error fetching IBKR status: {e}", exc_info=True)
        return {
            "connected": False,
            "error": str(e)
        }

class ConnectRequest(BaseModel):
    port: Optional[int] = None

@router.post("/connect", response_model=ConnectResponse)
async def connect_ibkr(request: ConnectRequest):
    """
    Connect to IBKR TWS/Gateway.
    """
    manager = get_connection_manager()
    
    # Use provided port or fallback to env/default
    target_port = request.port if request.port else 7497
    
    try:
        success = await manager.connect_async(port=target_port)
        
        if success:
            return {
                "status": "connected", 
                "message": f"Successfully connected to IBKR on port {target_port}"
            }
        else:
            # Return 200 with error status to avoid client crashing, or 503?
            # 503 is better for "Service Unavailable"
            raise HTTPException(status_code=503, detail="Failed to establish connection to TWS/Gateway")
            
    except RuntimeError as e:
         # Loop conflicts
         logger.error(f"Runtime error during connection: {e}")
         raise HTTPException(status_code=500, detail="Async Loop Conflict (Check Server Logs)")
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disconnect", response_model=ConnectResponse)
async def disconnect_ibkr(paper_trading: bool = False):
    """Disconnect from IBKR."""
    try:
        client = get_ibkr_client(paper_trading=paper_trading)
        client.disconnect()
        return {"success": True, "message": "Disconnected"}
    except Exception as e:
        logger.error(f"Error disconnecting from IBKR: {e}", exc_info=True)
        return {"success": False, "message": f"Error disconnecting: {str(e)}"}
