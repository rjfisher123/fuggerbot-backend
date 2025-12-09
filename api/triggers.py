"""
Triggers API endpoints.

Provides REST API and dashboard for managing price triggers.
"""
from fastapi import APIRouter, HTTPException, status, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.trigger_service import get_trigger_service
from core.logger import logger
from core.auth import require_auth

router = APIRouter(prefix="/api/triggers", tags=["triggers"])
dashboard_router = APIRouter(tags=["dashboard"])

# Setup templates
templates_dir = project_root / "ui" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)


# Dashboard endpoints
@dashboard_router.get("/triggers", response_class=HTMLResponse)
async def triggers_dashboard(request: Request):
    """
    Render the triggers dashboard page.
    
    Args:
        request: FastAPI request object
    
    Returns:
        HTML response with triggers list and create form
    """
    try:
        trigger_service = get_trigger_service()
        triggers = trigger_service.load_triggers()
        
        # Add last_fired timestamp to each trigger
        for trigger in triggers:
            last_fired = trigger_service.get_last_fired_timestamp(trigger)
            trigger["last_fired"] = last_fired
        
        html_content = render_template(
            "triggers.html",
            {
                "triggers": triggers,
                "error": None,
                "success_message": None
            }
        )
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error loading triggers dashboard: {e}", exc_info=True)
        html_content = render_template(
            "triggers.html",
            {
                "triggers": [],
                "error": f"Error loading triggers: {str(e)}",
                "success_message": None
            }
        )
        return HTMLResponse(content=html_content)


@dashboard_router.post("/triggers", response_class=HTMLResponse)
async def create_trigger(
    request: Request,
    symbol: str = Form(...),
    condition: str = Form(...),
    value: float = Form(...),
    action: str = Form(...),
    enabled: Optional[str] = Form(None),
    current_user: dict = Depends(require_auth)
):
    """
    Create a new trigger.
    
    Args:
        request: FastAPI request object
        symbol: Trading symbol
        condition: Trigger condition ("<", ">", "drop_pct", "rise_pct")
        value: Trigger value/threshold
        action: Action to take ("notify", "buy", "sell", "layer_in")
        enabled: Whether trigger is enabled
    
    Returns:
        HTML response with updated triggers list
    """
    error = None
    success_message = None
    
    try:
        # Handle checkbox - if present and value is "on", it's checked (enabled=True), otherwise False
        enabled_bool = enabled is not None and str(enabled).lower() in ['true', 'on', '1', 'yes']
        
        # Validate inputs
        symbol = symbol.upper().strip()
        if not symbol or len(symbol) > 10:
            error = "Invalid symbol. Must be 1-10 uppercase letters."
        elif condition not in ["<", ">", "drop_pct", "rise_pct"]:
            error = f"Invalid condition: {condition}. Must be one of: <, >, drop_pct, rise_pct"
        elif action not in ["notify", "buy", "sell", "layer_in"]:
            error = f"Invalid action: {action}. Must be one of: notify, buy, sell, layer_in"
        elif value < 0:
            error = "Value must be non-negative."
        else:
            # Create trigger
            trigger_service = get_trigger_service()
            trigger = trigger_service.create_trigger(
                symbol=symbol,
                condition=condition,
                value=value,
                action=action,
                enabled=enabled_bool
            )
            success_message = f"✅ Trigger created: {symbol} {condition} ${value:.2f} → {action}"
            logger.info(f"Trigger created via dashboard: {symbol} {condition} {value} → {action}")
    
    except ValueError as e:
        error = f"Invalid input: {str(e)}"
        logger.error(f"Error creating trigger: {e}")
    except Exception as e:
        error = f"Error creating trigger: {str(e)}"
        logger.error(f"Error creating trigger: {e}", exc_info=True)
        # Log full traceback for debugging
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
    
    # Reload triggers and render page
    try:
        trigger_service = get_trigger_service()
        triggers = trigger_service.load_triggers()
        # Add last_fired timestamp to each trigger
        for trigger in triggers:
            last_fired = trigger_service.get_last_fired_timestamp(trigger)
            trigger["last_fired"] = last_fired
    except Exception as e:
        logger.error(f"Error loading triggers for display: {e}", exc_info=True)
        triggers = []
        if not error:  # Only set error if we don't already have one
            error = f"Error loading triggers: {str(e)}"
    
    try:
        html_content = render_template(
            "triggers.html",
            {
                "triggers": triggers,
                "error": error,
                "success_message": success_message,
                "symbol": symbol if 'symbol' in locals() else None,
                "condition": condition if 'condition' in locals() else None,
                "value": value if 'value' in locals() else None,
                "action": action if 'action' in locals() else None,
                "enabled": enabled_bool if 'enabled_bool' in locals() else True
            }
        )
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error rendering template: {e}", exc_info=True)
        # Return a simple error page
        return HTMLResponse(
            content=f"<h1>Error</h1><p>Error rendering page: {str(e)}</p><p>Check server logs for details.</p>",
            status_code=500
        )


@dashboard_router.post("/triggers/{trigger_id}/toggle", response_class=HTMLResponse)
async def toggle_trigger(
    request: Request,
    trigger_id: int,
    current_user: dict = Depends(require_auth)
):
    """
    Toggle enable/disable status of a trigger.
    
    Args:
        request: FastAPI request object
        trigger_id: Index of trigger to toggle
    
    Returns:
        HTML response with updated triggers list
    """
    error = None
    success_message = None
    
    try:
        trigger_service = get_trigger_service()
        trigger = trigger_service.toggle_trigger(trigger_id)
        
        if trigger:
            status = "enabled" if trigger["enabled"] else "disabled"
            success_message = f"✅ Trigger {status}: {trigger.get('symbol')} {trigger.get('condition')} ${trigger.get('value', 0):.2f}"
        else:
            error = f"Trigger {trigger_id} not found"
    
    except Exception as e:
        error = f"Error toggling trigger: {str(e)}"
        logger.error(f"Error toggling trigger: {e}", exc_info=True)
    
    # Reload triggers and render page
    trigger_service = get_trigger_service()
    triggers = trigger_service.load_triggers()
    # Add last_fired timestamp to each trigger
    for trigger in triggers:
        last_fired = trigger_service.get_last_fired_timestamp(trigger)
        trigger["last_fired"] = last_fired
    
    html_content = render_template(
        "triggers.html",
        {
            "triggers": triggers,
            "error": error,
            "success_message": success_message
        }
    )
    return HTMLResponse(content=html_content)


@dashboard_router.post("/triggers/{trigger_id}/delete", response_class=HTMLResponse)
async def delete_trigger(
    request: Request,
    trigger_id: int,
    current_user: dict = Depends(require_auth)
):
    """
    Delete a trigger.
    
    Args:
        request: FastAPI request object
        trigger_id: Index of trigger to delete
    
    Returns:
        HTML response with updated triggers list
    """
    error = None
    success_message = None
    
    try:
        trigger_service = get_trigger_service()
        triggers = trigger_service.load_triggers()
        
        if 0 <= trigger_id < len(triggers):
            deleted = triggers[trigger_id]
            if trigger_service.delete_trigger(trigger_id):
                success_message = f"✅ Trigger deleted: {deleted.get('symbol')} {deleted.get('condition')} ${deleted.get('value', 0):.2f}"
            else:
                error = f"Failed to delete trigger {trigger_id}"
        else:
            error = f"Trigger {trigger_id} not found"
    
    except Exception as e:
        error = f"Error deleting trigger: {str(e)}"
        logger.error(f"Error deleting trigger: {e}", exc_info=True)
    
    # Reload triggers and render page
    trigger_service = get_trigger_service()
    triggers = trigger_service.load_triggers()
    # Add last_fired timestamp to each trigger
    for trigger in triggers:
        last_fired = trigger_service.get_last_fired_timestamp(trigger)
        trigger["last_fired"] = last_fired
    
    html_content = render_template(
        "triggers.html",
        {
            "triggers": triggers,
            "error": error,
            "success_message": success_message
        }
    )
    return HTMLResponse(content=html_content)

