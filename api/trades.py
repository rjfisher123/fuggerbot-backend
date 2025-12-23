"""
Trades dashboard API.

Provides JSON endpoints for managing trade approvals and history.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import sys
import uuid
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.trade_service import get_trade_service
from persistence.db import SessionLocal
from persistence.repositories_trades import TradeRequestRepository
from core.logger import logger
from core.auth import require_auth

router = APIRouter(prefix="/api/trades", tags=["trades"])

# --- Request/Response Models ---

class TradeRequestModel(BaseModel):
    trade_id: str
    symbol: str
    action: str
    quantity: int
    order_type: str
    limit_price: Optional[float] = None
    approval_code: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    forecast_id: Optional[str] = None
    paper_trading: bool = False

class TradeActionRequest(BaseModel):
    trade_id: str
    approval_code: Optional[str] = None

class ActionResponse(BaseModel):
    success: bool
    message: str

class PlaceTradeRequest(BaseModel):
    """Request model for placing a trade."""
    
    symbol: str = Field(..., description="Trading symbol", min_length=1, max_length=10)
    action: str = Field(..., description="BUY or SELL")
    qty: int = Field(..., description="Quantity (number of shares)", gt=0)
    order_type: str = Field(default="MARKET", description="Order type: MARKET, LIMIT, etc.")
    limit_price: Optional[float] = Field(None, description="Limit price (required for LIMIT orders)", gt=0)
    tif: Optional[str] = Field(default="DAY", description="Time in force: DAY, GTC, IOC, FOK")
    forecast_id: Optional[str] = Field(None, description="Optional forecast ID for tracking")
    paper_trading: bool = Field(default=False, description="Whether this is paper trading")

class PlaceTradeResponse(BaseModel):
    """Response model for placed trade."""
    
    request_id: str = Field(..., description="Trade request ID")
    status: str = Field(..., description="Request status")
    approval_code: Optional[str] = Field(None, description="Approval code for this request")
    expires_at: Optional[str] = Field(None, description="When the request expires (ISO format)")

# --- Endpoints ---

@router.get("/pending", response_model=List[TradeRequestModel])
async def get_pending_trades():
    """Get list of pending trade requests."""
    try:
        trade_service = get_trade_service(paper_trading=False)
        pending = trade_service.list_pending_trades()
        
        # Convert dicts/models to Pydantic
        results = []
        for t in pending:
            results.append(TradeRequestModel(
                trade_id=str(t.get("trade_id")),
                symbol=t.get("symbol"),
                action=t.get("action"),
                quantity=int(t.get("quantity")),
                order_type=t.get("order_type"),
                limit_price=t.get("price"),
                approval_code=t.get("approval_code"),
                status=t.get("status"),
                created_at=str(t.get("created_at")) if t.get("created_at") else None,
                expires_at=str(t.get("expires_at")) if t.get("expires_at") else None,
                forecast_id=t.get("forecast_id"),
                paper_trading=bool(t.get("paper_trading", False))
            ))
        return results
    except Exception as e:
        logger.error(f"Error fetching pending trades: {e}", exc_info=True)
        return []

@router.get("/history", response_model=List[TradeRequestModel])
async def get_trade_history():
    """Get history of processed trades."""
    try:
        trade_service = get_trade_service(paper_trading=False)
        history = trade_service.get_trade_history(limit=50)
        
        results = []
        for t in history:
            results.append(TradeRequestModel(
                trade_id=str(t.get("trade_id")),
                symbol=t.get("symbol"),
                action=t.get("action"),
                quantity=int(t.get("quantity")),
                order_type=t.get("order_type"),
                limit_price=t.get("price"),
                approval_code=t.get("approval_code"),
                status=t.get("status"),
                created_at=str(t.get("created_at")) if t.get("created_at") else None,
                expires_at=str(t.get("expires_at")) if t.get("expires_at") else None,
                forecast_id=t.get("forecast_id"),
                paper_trading=bool(t.get("paper_trading", False))
            ))
        return results
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}", exc_info=True)
        return []

@router.post("/approve", response_model=ActionResponse)
async def approve_trade(
    request: TradeActionRequest,
    current_user: dict = Depends(require_auth)
):
    """Approve a pending trade."""
    try:
        trade_service = get_trade_service(paper_trading=False)
        code = request.approval_code.strip() if request.approval_code else request.trade_id.strip()
        
        result = trade_service.approve_trade(
            trade_id=code,
            approval_code=request.approval_code.strip() if request.approval_code else None
        )

        return ActionResponse(
            success=result.get("success", False),
            message=result.get("message", "Unknown result")
        )
    except Exception as e:
        logger.error(f"Error approving trade: {e}", exc_info=True)
        return ActionResponse(success=False, message=f"Error: {str(e)}")

@router.post("/reject", response_model=ActionResponse)
async def reject_trade(
    request: TradeActionRequest,
    current_user: dict = Depends(require_auth)
):
    """Reject a pending trade."""
    try:
        trade_service = get_trade_service(paper_trading=False)
        result = trade_service.reject_trade(request.trade_id.strip())

        return ActionResponse(
            success=result.get("success", False),
            message=result.get("message", "Unknown result")
        )
    except Exception as e:
        logger.error(f"Error rejecting trade: {e}", exc_info=True)
        return ActionResponse(success=False, message=f"Error: {str(e)}")

@router.post("/place", response_model=PlaceTradeResponse, status_code=status.HTTP_201_CREATED)
async def place_trade(
    request: PlaceTradeRequest,
    current_user: dict = Depends(require_auth)
) -> PlaceTradeResponse:
    """
    Place a new trade request.
    """
    try:
        # Validate action
        action_upper = request.action.upper()
        if action_upper not in ["BUY", "SELL"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. Must be BUY or SELL"
            )
        
        # Validate order_type
        order_type_upper = request.order_type.upper()
        if order_type_upper not in ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid order_type: {request.order_type}. Must be MARKET, LIMIT, STOP, or STOP_LIMIT"
            )
        
        # Validate limit_price for LIMIT orders
        if order_type_upper == "LIMIT" and request.limit_price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit_price is required for LIMIT orders"
            )
        
        # Generate trade_id and approval_code
        trade_id = str(uuid.uuid4())[:8].upper()
        approval_code = f"{random.randint(100000, 999999)}"
        
        # Calculate expiration (30 minutes from now)
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        # Prepare trade_details dict
        trade_details = {
            "symbol": request.symbol.upper(),
            "action": action_upper,
            "quantity": request.qty,
            "order_type": order_type_upper,
            "limit_price": request.limit_price,
            "tif": request.tif or "DAY"
        }
        
        # Create trade request via repository
        with SessionLocal() as session:
            repo = TradeRequestRepository(session)
            trade_request = repo.add_trade_request(
                trade_id=trade_id,
                approval_code=approval_code,
                symbol=request.symbol.upper(),
                action=action_upper,
                quantity=request.qty,
                order_type=order_type_upper,
                price=request.limit_price,
                expires_at=expires_at,
                forecast_id=request.forecast_id,
                trade_details=trade_details,
                paper_trading=request.paper_trading
            )
            
            logger.info(
                f"Trade request created via API: {trade_id} - {request.symbol} {action_upper} {request.qty} "
                f"({order_type_upper})"
            )
            
            return PlaceTradeResponse(
                request_id=trade_id,
                status="pending",
                approval_code=approval_code,
                expires_at=expires_at.isoformat()
            )
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid trade request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error placing trade: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place trade: {str(e)}"
        )

