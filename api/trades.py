"""
Trades dashboard API.

Renders a FastAPI page for managing trade approvals and history.
"""
from fastapi import APIRouter, Request, Form, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
import sys
import uuid
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.trade_service import get_trade_service
from workers.ibkr_heartbeat import get_latest_status
from persistence.db import SessionLocal
from persistence.repositories_trades import TradeRequestRepository
from core.logger import logger
from core.auth import require_auth

router = APIRouter(prefix="/api/trades", tags=["trades"])
dashboard_router = APIRouter(tags=["dashboard"])

templates_dir = project_root / "ui" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))


def render_template(template_name: str, context: dict) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(**context)


def build_context(success_message: str | None = None, error_message: str | None = None) -> dict:
    """Collect data for the trades dashboard."""
    trade_service = get_trade_service(paper_trading=False)
    pending_trades = trade_service.list_pending_trades()
    trade_history = trade_service.get_trade_history(limit=20)
    
    # Get connection status from database (updated by heartbeat worker)
    db_status = get_latest_status(paper_trading=False)
    if db_status:
        connection_status = {
            "connected": db_status.connected,
            "host": db_status.host,
            "port": db_status.port,
            "paper_trading": db_status.paper_trading,
            "client_id": db_status.client_id,
            "last_checked": db_status.last_checked.isoformat() if db_status.last_checked else None,
            "last_connected": db_status.last_connected.isoformat() if db_status.last_connected else None,
            "reconnect_attempts": db_status.reconnect_attempts,
            "error": db_status.error_message
        }
    else:
        # Fallback to direct check if no DB record exists
        connection_status = trade_service.get_connection_status()
    
    # Extract unique symbols from pending trades for price charts
    symbols = list(set([trade.get("symbol") for trade in pending_trades if trade.get("symbol")]))
    
    # Get symbols from trade history too
    for trade in trade_history:
        if trade.get("symbol") and trade.get("symbol") not in symbols:
            symbols.append(trade.get("symbol"))

    return {
        "pending_trades": pending_trades,
        "trade_history": trade_history,
        "connection_status": connection_status,
        "success_message": success_message,
        "error_message": error_message,
        "symbols": symbols[:10],  # Limit to 10 symbols for performance
    }


def _sanitize_row_id(identifier: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(identifier))
    return f"trade-row-{cleaned}"


def _find_pending_trade(trade_id: str):
    trade_service = get_trade_service(paper_trading=False)
    pending = trade_service.list_pending_trades()
    for trade in pending:
        if str(trade.get("trade_id")) == str(trade_id) or str(trade.get("approval_code")) == str(trade_id):
            return trade
    return None


def _render_trade_row_html(trade_id: str, trade: dict | None = None, message: str | None = None) -> str:
    template = jinja_env.get_template("partials/trade_row.html")
    row_id = _sanitize_row_id(trade_id)
    return template.render(trade=trade, row_id=row_id, message=message)


@dashboard_router.get("/trades", response_class=HTMLResponse)
async def trades_dashboard(request: Request):
    """Render the trades dashboard."""
    context = build_context()
    html_content = render_template("trades.html", context)
    return HTMLResponse(content=html_content)


@dashboard_router.get("/trades/row/{trade_id}", response_class=HTMLResponse)
async def trade_row(trade_id: str):
    """Return a single trade row fragment."""
    trade = _find_pending_trade(trade_id)
    message = None if trade else "Trade processed."
    content = _render_trade_row_html(trade_id, trade=trade, message=message)
    return HTMLResponse(content=content)


@dashboard_router.get("/trades/status", response_class=HTMLResponse)
async def ibkr_status():
    """Return IBKR connection status fragment."""
    context = build_context()
    template = jinja_env.get_template("partials/ibkr_status.html")
    return HTMLResponse(content=template.render(**context))


@dashboard_router.post("/trades/approve", response_class=HTMLResponse)
async def approve_trade(
    request: Request,
    trade_id: str = Form(""),
    approval_code: str = Form(""),
    current_user: dict = Depends(require_auth)
):
    """Approve a trade or check SMS approvals."""
    trade_service = get_trade_service(paper_trading=False)
    code = approval_code.strip() or trade_id.strip()
    result = trade_service.approve_trade(trade_id=code or "", approval_code=approval_code.strip() or None)

    if result.get("success"):
        success_message = f"✅ Trade approved: {result.get('message', 'Executed successfully')}"
        error_message = None
    else:
        success_message = None
        error_message = f"❌ {result.get('message', 'Failed to approve trade')}"

    if request.headers.get("HX-Request") == "true":
        trade = _find_pending_trade(code or trade_id)
        message = None
        if not result.get("success"):
            message = error_message
        elif not trade:
            message = success_message
        content = _render_trade_row_html(code or trade_id, trade=trade, message=message)
        return HTMLResponse(content=content)

    context = build_context(success_message, error_message)
    html_content = render_template("trades.html", context)
    return HTMLResponse(content=html_content)


@dashboard_router.post("/trades/reject", response_class=HTMLResponse)
async def reject_trade(request: Request, trade_id: str = Form(...)):
    """Reject a pending trade."""
    trade_service = get_trade_service(paper_trading=False)
    result = trade_service.reject_trade(trade_id.strip())

    if result.get("success"):
        success_message = result.get("message", "Trade rejected.")
        error_message = None
    else:
        success_message = None
        error_message = result.get("message", "Failed to reject trade.")

    if request.headers.get("HX-Request") == "true":
        trade = _find_pending_trade(trade_id)
        message = error_message or success_message
        content = _render_trade_row_html(trade_id, trade=trade, message=message)
        return HTMLResponse(content=content)

    context = build_context(success_message, error_message)
    html_content = render_template("trades.html", context)
    return HTMLResponse(content=html_content)


@dashboard_router.post("/trades/connect", response_class=HTMLResponse)
async def connect_ibkr(request: Request):
    """Attempt to connect to IBKR."""
    trade_service = get_trade_service(paper_trading=False)
    if trade_service.connect():
        success_message = "✅ Connected to IBKR."
        error_message = None
    else:
        success_message = None
        error_message = "❌ Failed to connect to IBKR. Ensure TWS/IB Gateway is running."

    context = build_context(success_message, error_message)
    html_content = render_template("trades.html", context)
    return HTMLResponse(content=html_content)


# API Request/Response models
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


@router.post("/place", response_model=PlaceTradeResponse, status_code=status.HTTP_201_CREATED)
async def place_trade(
    request: PlaceTradeRequest,
    current_user: dict = Depends(require_auth)
) -> PlaceTradeResponse:
    """
    Place a new trade request.
    
    Args:
        request: Trade placement request with symbol, action, quantity, etc.
    
    Returns:
        PlaceTradeResponse with request_id and status
    
    Raises:
        HTTPException: If validation fails or trade request creation fails
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

