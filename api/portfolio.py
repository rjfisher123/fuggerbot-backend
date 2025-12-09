"""
Portfolio dashboard API.

Renders a FastAPI page showing portfolio summary and paper trading history.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.portfolio_service_db import PortfolioServiceDB
from persistence.db import SessionLocal
from core.logger import logger

dashboard_router = APIRouter(tags=["dashboard"])

# Setup templates
templates_dir = project_root / "ui" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

# Add JSON filter to Jinja2
import json as json_module
def tojson_filter(obj):
    """Convert Python object to JSON string."""
    return json_module.dumps(obj)
jinja_env.filters['tojson'] = tojson_filter

portfolio_service = PortfolioServiceDB(SessionLocal)


def get_portfolio_service():
    return portfolio_service

def render_template(template_name: str, context: dict) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(**context)


@dashboard_router.get("/portfolio", response_class=HTMLResponse)
async def portfolio_dashboard(request: Request):
    """
    Render the portfolio dashboard page.
    """
    try:
        service = get_portfolio_service()
        positions_raw = service.get_positions()
        trades_raw = service.get_paper_trades()
        
        # Convert SQLAlchemy models to dicts
        open_positions = []
        for pos in positions_raw:
            # Get current price for each position
            from dash.utils.price_feed import get_price
            current_price = get_price(pos.symbol) if hasattr(pos, 'symbol') else None
            
            # Map Position model fields (symbol, quantity, cost_basis) to template fields
            entry_price = float(pos.cost_basis) if hasattr(pos, 'cost_basis') and pos.cost_basis else 0.0
            shares = float(pos.quantity) if hasattr(pos, 'quantity') else 0.0
            current_price = current_price or entry_price
            
            position_value = current_price * shares
            unrealized_pnl = (current_price - entry_price) * shares if entry_price > 0 else 0.0
            unrealized_pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
            
            position_dict = {
                "symbol": pos.symbol if hasattr(pos, 'symbol') else "UNKNOWN",
                "entry_price": entry_price,
                "current_price": current_price,
                "shares": shares,
                "position_value": position_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "entry_date": pos.updated_at.isoformat() if hasattr(pos, 'updated_at') and pos.updated_at else None
            }
            
            open_positions.append(position_dict)
        
        # Convert trades to dicts
        # PaperTrade model has: symbol, side, quantity, price, timestamp
        trade_history = []
        for trade in trades_raw:
            # For PaperTrade, we need to calculate P/L from pairs of trades
            # This is simplified - in a real system you'd match entry/exit pairs
            trade_dict = {
                "symbol": trade.symbol if hasattr(trade, 'symbol') else "UNKNOWN",
                "entry_price": float(trade.price) if hasattr(trade, 'price') and trade.side == "BUY" else 0.0,
                "exit_price": float(trade.price) if hasattr(trade, 'price') and trade.side == "SELL" else 0.0,
                "pnl": 0.0,  # Would need to calculate from entry/exit pairs
                "pnl_pct": 0.0,
                "exit_reason": None,
                "holding_period_days": 0,
                "entry_date": trade.timestamp.isoformat() if hasattr(trade, 'timestamp') and trade.timestamp else None,
                "exit_date": trade.timestamp.isoformat() if hasattr(trade, 'timestamp') and trade.timestamp and trade.side == "SELL" else None
            }
            trade_history.append(trade_dict)
        
        # Calculate summary from positions and trades
        from datetime import datetime
        initial_capital = 100000.0  # Default initial capital
        total_capital = initial_capital
        total_realized_pnl = 0.0
        closed_trades = 0
        winning_trades = 0
        
        # Calculate from paper trades
        for trade in trade_history:
            if trade.get("pnl") is not None:
                total_realized_pnl += trade.get("pnl", 0)
                closed_trades += 1
                if trade.get("pnl", 0) > 0:
                    winning_trades += 1
        
        total_capital = initial_capital + total_realized_pnl
        total_return_pct = ((total_capital - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0
        total_realized_pnl_pct = (total_realized_pnl / initial_capital) * 100 if initial_capital > 0 else 0
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        summary = {
            "initial_capital": initial_capital,
            "total_capital": total_capital,
            "total_return_pct": total_return_pct,
            "total_realized_pnl": total_realized_pnl,
            "total_realized_pnl_pct": total_realized_pnl_pct,
            "win_rate": win_rate,
            "closed_trades": closed_trades
        }
        
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = render_template(
            "portfolio.html",
            {
                "summary": summary,
                "open_positions": open_positions,
                "trade_history": trade_history,
                "last_updated": last_updated,
            },
        )
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error rendering portfolio dashboard: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<h1>Error</h1><p>Unable to load portfolio data: {str(e)}</p>",
            status_code=500,
        )

