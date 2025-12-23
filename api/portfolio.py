"""
Portfolio dashboard API.

Provides JSON endpoints for portfolio summary and paper trading history.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.portfolio_service_db import PortfolioServiceDB
from persistence.db import SessionLocal
from core.logger import logger

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

portfolio_service = PortfolioServiceDB(SessionLocal)

def get_portfolio_service():
    return portfolio_service

# --- Response Models ---

class PositionModel(BaseModel):
    symbol: str
    entry_price: float
    current_price: float
    shares: float
    position_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_date: Optional[str] = None

class TradeHistoryModel(BaseModel):
    symbol: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    entry_date: Optional[str] = None
    exit_date: Optional[str] = None
    holding_period_days: int = 0
    exit_reason: Optional[str] = None

class PortfolioSummary(BaseModel):
    initial_capital: float
    total_capital: float
    total_return_pct: float
    total_realized_pnl: float
    total_realized_pnl_pct: float
    win_rate: float
    closed_trades: int
    open_positions: List[PositionModel]
    trade_history: List[TradeHistoryModel]
    last_updated: str

# --- Endpoints ---

@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """
    Get portfolio summary, positions, and trade history.
    """
    try:
        service = get_portfolio_service()
        positions_raw = service.get_positions()
        trades_raw = service.get_paper_trades()
        
        # --- Process Open Positions ---
        open_positions = []
        for pos in positions_raw:
            # Get current price
            from dash.utils.price_feed import get_price
            current_price = get_price(pos.symbol) if hasattr(pos, 'symbol') else None
            
            entry_price = float(pos.cost_basis) if hasattr(pos, 'cost_basis') and pos.cost_basis else 0.0
            shares = float(pos.quantity) if hasattr(pos, 'quantity') else 0.0
            current_price = current_price or entry_price
            
            position_value = current_price * shares
            unrealized_pnl = (current_price - entry_price) * shares if entry_price > 0 else 0.0
            unrealized_pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
            
            open_positions.append(PositionModel(
                symbol=pos.symbol if hasattr(pos, 'symbol') else "UNKNOWN",
                entry_price=entry_price,
                current_price=current_price,
                shares=shares,
                position_value=position_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                entry_date=pos.updated_at.isoformat() if hasattr(pos, 'updated_at') and pos.updated_at else None
            ))
        
        # --- Process Trade History ---
        trade_history = []
        for trade in trades_raw:
            # Simplified logic for now
            trade_history.append(TradeHistoryModel(
                symbol=trade.symbol if hasattr(trade, 'symbol') else "UNKNOWN",
                entry_price=float(trade.price) if hasattr(trade, 'price') and trade.side == "BUY" else 0.0,
                exit_price=float(trade.price) if hasattr(trade, 'price') and trade.side == "SELL" else 0.0,
                pnl=0.0,
                pnl_pct=0.0,
                entry_date=trade.timestamp.isoformat() if hasattr(trade, 'timestamp') and trade.timestamp else None,
                exit_date=trade.timestamp.isoformat() if hasattr(trade, 'timestamp') and trade.timestamp and trade.side == "SELL" else None
            ))
        
        # --- Calculate Summary Metrics ---
        initial_capital = 100000.0
        total_realized_pnl = 0.0
        closed_trades = 0
        winning_trades = 0
        
        # Recalculate PnL from history (mock logic from original file)
        for trade in trade_history:
             if trade.pnl: # pnl is 0.0 in loop above, this logic needs real service support but keeping strict port for now
                 total_realized_pnl += trade.pnl
                 closed_trades += 1
                 if trade.pnl > 0:
                     winning_trades += 1
        
        total_capital = initial_capital + total_realized_pnl
        total_return_pct = ((total_capital - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0.0
        total_realized_pnl_pct = (total_realized_pnl / initial_capital) * 100 if initial_capital > 0 else 0.0
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0
        
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return PortfolioSummary(
            initial_capital=initial_capital,
            total_capital=total_capital,
            total_return_pct=total_return_pct,
            total_realized_pnl=total_realized_pnl,
            total_realized_pnl_pct=total_realized_pnl_pct,
            win_rate=win_rate,
            closed_trades=closed_trades,
            open_positions=open_positions,
            trade_history=trade_history,
            last_updated=last_updated
        )

    except Exception as e:
        logger.error(f"Error serving portfolio summary: {e}", exc_info=True)
        # Return empty/safe default or raise HTTP exception
        return PortfolioSummary(
            initial_capital=100000.0,
            total_capital=100000.0,
            total_return_pct=0.0,
            total_realized_pnl=0.0,
            total_realized_pnl_pct=0.0,
            win_rate=0.0,
            closed_trades=0,
            open_positions=[],
            trade_history=[],
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

