"""
Trade Candidates dashboard API.

Renders a FastAPI page for viewing and promoting trade candidates.
"""
from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import sys
import uuid
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from persistence.db import SessionLocal
from persistence.repositories_triggers import TradeCandidateRepository
from persistence.repositories_trades import TradeRequestRepository
from core.logger import logger

router = APIRouter(prefix="/api/candidates", tags=["candidates"])
dashboard_router = APIRouter(tags=["dashboard"])

templates_dir = project_root / "ui" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))


def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)


@dashboard_router.get("/candidates", response_class=HTMLResponse)
async def candidates_dashboard(request: Request):
    """Render the trade candidates dashboard."""
    try:
        with SessionLocal() as session:
            candidate_repo = TradeCandidateRepository(session)
            
            # Get all candidates sorted by confidence descending
            candidates = candidate_repo.list_recent(limit=100)
            
            # Convert to dicts for template
            candidates_data = []
            for candidate in candidates:
                candidates_data.append({
                    "id": candidate.id,
                    "symbol": candidate.symbol,
                    "action": candidate.action,
                    "confidence": candidate.confidence,
                    "trigger_id": candidate.trigger_id,
                    "created_at": candidate.created_at,
                    "metadata": candidate.candidate_metadata,
                })
            
            context = {
                "candidates": candidates_data,
                "candidates_count": len(candidates_data),
            }
            
            return render_template("candidates.html", context)
            
    except Exception as e:
        logger.error(f"Error rendering candidates dashboard: {e}", exc_info=True)
        context = {
            "candidates": [],
            "candidates_count": 0,
            "error_message": f"Error loading candidates: {str(e)}"
        }
        return render_template("candidates.html", context)


@dashboard_router.post("/candidates/{candidate_id}/promote", response_class=HTMLResponse)
async def promote_candidate(candidate_id: int, request: Request):
    """
    Promote a trade candidate to a pending trade request.
    
    Uses HTMX to return a partial HTML update.
    """
    try:
        with SessionLocal() as session:
            candidate_repo = TradeCandidateRepository(session)
            trade_repo = TradeRequestRepository(session)
            
            # Get the candidate
            candidate = candidate_repo.get_by_id(candidate_id)
            if not candidate:
                return HTMLResponse(
                    content=f'<div class="alert alert-danger">Candidate {candidate_id} not found</div>',
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Check if already promoted (optional - you might want to allow multiple promotions)
            # For now, we'll create a new trade request
            
            # Generate trade request details
            trade_id = str(uuid.uuid4())[:8].upper()
            approval_code = str(uuid.uuid4().int)[:6]
            expires_at = datetime.utcnow() + timedelta(minutes=30)
            
            # Determine quantity (default to 1 share, could be configurable)
            quantity = 1  # Default quantity
            
            # Create trade request
            trade_request = trade_repo.add_trade_request(
                trade_id=trade_id,
                approval_code=approval_code,
                symbol=candidate.symbol,
                action=candidate.action,
                quantity=quantity,
                order_type="MARKET",  # Default to market order
                price=None,  # Market order, no limit price
                expires_at=expires_at,
                forecast_id=None,  # Could link to forecast if available
                trade_details={
                    "candidate_id": candidate.id,
                    "trigger_id": candidate.trigger_id,
                    "confidence": candidate.confidence,
                    "promoted_at": datetime.utcnow().isoformat(),
                },
                paper_trading=False  # Default to live trading, could be configurable
            )
            
            logger.info(f"Promoted candidate {candidate_id} to trade request {trade_id}")
            
            # Return success message (HTMX will replace the row)
            return HTMLResponse(
                content=f'<div class="alert alert-success">✅ Promoted to Trade Request {trade_id}</div>'
            )
            
    except Exception as e:
        logger.error(f"Error promoting candidate {candidate_id}: {e}", exc_info=True)
        return HTMLResponse(
            content=f'<div class="alert alert-danger">Error promoting candidate: {str(e)}</div>',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@dashboard_router.get("/candidates/row/{candidate_id}", response_class=HTMLResponse)
async def get_candidate_row(candidate_id: int, request: Request):
    """Get a single candidate row for HTMX updates."""
    try:
        with SessionLocal() as session:
            candidate_repo = TradeCandidateRepository(session)
            
            candidate = candidate_repo.get_by_id(candidate_id)
            if not candidate:
                return HTMLResponse(
                    content='<tr><td colspan="6">Candidate not found</td></tr>',
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            candidate_data = {
                "id": candidate.id,
                "symbol": candidate.symbol,
                "action": candidate.action,
                "confidence": candidate.confidence,
                "trigger_id": candidate.trigger_id,
                "created_at": candidate.created_at,
                "metadata": candidate.candidate_metadata,
            }
            
            context = {"candidate": candidate_data}
            return render_template("partials/candidate_row.html", context)
            
    except Exception as e:
        logger.error(f"Error getting candidate row {candidate_id}: {e}", exc_info=True)
        return HTMLResponse(
            content=f'<tr><td colspan="6">Error: {str(e)}</td></tr>',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )











