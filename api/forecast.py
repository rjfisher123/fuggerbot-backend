"""
Forecast API endpoints.

Provides REST API for creating and retrieving forecasts.
"""
from fastapi import APIRouter, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse
from jinja2 import Template, Environment, FileSystemLoader
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.forecast_service import create_forecast, get_forecast
from domain.forecast import Forecast
from dash.utils.forecast_helper import get_historical_prices
from core.logger import logger

# Setup templates
templates_dir = project_root / "ui" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)

router = APIRouter(prefix="/api/forecast", tags=["forecast"])
dashboard_router = APIRouter(tags=["dashboard"])


# Request/Response models
class CreateForecastRequest(BaseModel):
    """Request model for creating a forecast."""
    
    symbol: str = Field(..., description="Trading symbol", min_length=1, max_length=10)
    historical_prices: List[float] = Field(..., description="Historical price series", min_length=20)
    forecast_horizon: int = Field(default=30, description="Number of days to forecast", ge=1, le=365)
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional forecast options: context_length, historical_period, strict_mode, min_trust_score, deterministic_mode, model_name"
    )


class ForecastResponse(BaseModel):
    """Response model for forecast data."""
    
    forecast_id: str
    symbol: str
    created_at: str
    forecast_horizon: int
    model_name: str
    params: Dict[str, Any]
    trust_score: float
    fqs_score: Optional[float] = None
    regime: Optional[Dict[str, Any]] = None
    frs_score: Optional[float] = None
    coherence: Optional[Dict[str, Any]] = None
    recommendation: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


@router.post("", response_model=ForecastResponse, status_code=status.HTTP_201_CREATED)
async def create_forecast_endpoint(request: CreateForecastRequest) -> ForecastResponse:
    """
    Create a new forecast.
    
    Args:
        request: Forecast creation request with symbol, historical prices, and options
    
    Returns:
        ForecastResponse with created forecast data
    
    Raises:
        HTTPException: If forecast creation fails
    """
    try:
        logger.info(f"Creating forecast for {request.symbol} via API")
        
        # Create forecast using service
        forecast = create_forecast(
            symbol=request.symbol,
            historical_prices=request.historical_prices,
            forecast_horizon=request.forecast_horizon,
            options=request.options
        )
        
        # Convert to response model
        response = ForecastResponse(
            forecast_id=forecast.forecast_id,
            symbol=forecast.symbol,
            created_at=forecast.created_at.isoformat(),
            forecast_horizon=forecast.forecast_horizon,
            model_name=forecast.model_name,
            params=forecast.params,
            trust_score=forecast.trust_score,
            fqs_score=forecast.fqs_score,
            regime=forecast.regime,
            frs_score=forecast.frs_score,
            coherence=forecast.coherence,
            recommendation=forecast.recommendation,
            metadata=forecast.metadata
        )
        
        logger.info(f"Forecast {forecast.forecast_id} created successfully via API")
        return response
        
    except ValueError as e:
        logger.error(f"Invalid forecast request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating forecast: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create forecast: {str(e)}"
        )


@router.get("/{forecast_id}", response_model=ForecastResponse)
async def get_forecast_endpoint(forecast_id: str) -> ForecastResponse:
    """
    Retrieve a forecast by ID.
    
    Args:
        forecast_id: Forecast ID to retrieve
    
    Returns:
        ForecastResponse with forecast data
    
    Raises:
        HTTPException: If forecast not found
    """
    try:
        logger.info(f"Retrieving forecast {forecast_id} via API")
        
        # Get forecast using service
        forecast = get_forecast(forecast_id)
        
        if not forecast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forecast {forecast_id} not found"
            )
        
        # Convert to response model
        response = ForecastResponse(
            forecast_id=forecast.forecast_id,
            symbol=forecast.symbol,
            created_at=forecast.created_at.isoformat(),
            forecast_horizon=forecast.forecast_horizon,
            model_name=forecast.model_name,
            params=forecast.params,
            trust_score=forecast.trust_score,
            fqs_score=forecast.fqs_score,
            regime=forecast.regime,
            frs_score=forecast.frs_score,
            coherence=forecast.coherence,
            recommendation=forecast.recommendation,
            metadata=forecast.metadata
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving forecast {forecast_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve forecast: {str(e)}"
        )


# Dashboard endpoints
@dashboard_router.get("/forecast", response_class=HTMLResponse)
async def forecast_dashboard(request: Request):
    """
    Render the forecast dashboard form.
    
    Args:
        request: FastAPI request object
    
    Returns:
        HTML response with forecast form
    """
    html_content = render_template(
        "forecast.html",
        {
            "symbol": None,
            "forecast_horizon": 30,
            "historical_period": 252,
            "context_length": None,
            "strict_mode": False,
            "deterministic_mode": False,
            "min_trust_score": 0.5,
            "forecast_result": None,
            "error": None
        }
    )
    return HTMLResponse(content=html_content)


@dashboard_router.post("/forecast", response_class=HTMLResponse)
async def forecast_dashboard_submit(
    request: Request,
    symbol: str = Form(...),
    forecast_horizon: int = Form(30),
    historical_period: Optional[int] = Form(None),
    context_length: Optional[int] = Form(None),
    strict_mode: bool = Form(False),
    deterministic_mode: bool = Form(False),
    min_trust_score: float = Form(0.5)
):
    """
    Handle forecast form submission.
    
    Args:
        request: FastAPI request object
        symbol: Trading symbol
        forecast_horizon: Forecast horizon in days
        historical_period: Historical period in days (optional)
        context_length: Context length (optional)
        strict_mode: Enable strict mode
        deterministic_mode: Enable deterministic mode
        min_trust_score: Minimum trust score
    
    Returns:
        HTML response with forecast result or error
    """
    error = None
    forecast_result = None
    
    try:
        # Validate symbol
        symbol = symbol.upper().strip()
        if not symbol or len(symbol) > 10:
            error = "Invalid symbol. Must be 1-10 characters."
            html_content = render_template(
                "forecast.html",
                {
                    "symbol": symbol,
                    "forecast_horizon": forecast_horizon,
                    "historical_period": historical_period or 252,
                    "context_length": context_length,
                    "strict_mode": strict_mode,
                    "deterministic_mode": deterministic_mode,
                    "min_trust_score": min_trust_score,
                    "forecast_result": None,
                    "error": error
                }
            )
            return HTMLResponse(content=html_content)
        
        # Fetch historical prices
        logger.info(f"Fetching historical prices for {symbol}...")
        
        # Calculate period string from historical_period
        if historical_period:
            if historical_period <= 5:
                period = "5d"
            elif historical_period <= 30:
                period = "1mo"
            elif historical_period <= 90:
                period = "3mo"
            elif historical_period <= 180:
                period = "6mo"
            elif historical_period <= 365:
                period = "1y"
            elif historical_period <= 730:
                period = "2y"
            else:
                period = "5y"
        else:
            period = "1y"
        
        historical_prices = get_historical_prices(symbol, period=period)
        
        if not historical_prices or len(historical_prices) < 20:
            error = f"Could not fetch sufficient historical data for {symbol}. Please check the symbol is valid."
            html_content = render_template(
                "forecast.html",
                {
                    "symbol": symbol,
                    "forecast_horizon": forecast_horizon,
                    "historical_period": historical_period or 252,
                    "context_length": context_length,
                    "strict_mode": strict_mode,
                    "deterministic_mode": deterministic_mode,
                    "min_trust_score": min_trust_score,
                    "forecast_result": None,
                    "error": error
                }
            )
            return HTMLResponse(content=html_content)
        
        # Build options dict
        options = {}
        if context_length:
            options["context_length"] = context_length
        if historical_period:
            options["historical_period"] = historical_period
        if strict_mode:
            options["strict_mode"] = True
        if deterministic_mode:
            options["deterministic_mode"] = True
        if min_trust_score:
            options["min_trust_score"] = min_trust_score
        
        # Create forecast
        logger.info(f"Creating forecast for {symbol} with horizon {forecast_horizon}...")
        forecast = create_forecast(
            symbol=symbol,
            historical_prices=historical_prices,
            forecast_horizon=forecast_horizon,
            options=options if options else None
        )
        
        # Convert to response format for template
        forecast_result = {
            "forecast_id": forecast.forecast_id,
            "symbol": forecast.symbol,
            "forecast_horizon": forecast.forecast_horizon,
            "trust_score": forecast.trust_score,
            "fqs_score": forecast.fqs_score,
            "regime": forecast.regime,
            "frs_score": forecast.frs_score,
            "coherence": forecast.coherence,
            "recommendation": forecast.recommendation,
            "created_at": forecast.created_at.isoformat()
        }
        
        logger.info(f"Forecast {forecast.forecast_id} created successfully via dashboard")
        
    except ValueError as e:
        error = f"Invalid input: {str(e)}"
        logger.error(f"Forecast dashboard error: {e}")
    except Exception as e:
        error = f"Error creating forecast: {str(e)}"
        logger.error(f"Forecast dashboard error: {e}", exc_info=True)
    
    html_content = render_template(
        "forecast.html",
        {
            "symbol": symbol if 'symbol' in locals() else None,
            "forecast_horizon": forecast_horizon,
            "historical_period": historical_period or 252,
            "context_length": context_length,
            "strict_mode": strict_mode,
            "deterministic_mode": deterministic_mode,
            "min_trust_score": min_trust_score,
            "forecast_result": forecast_result,
            "error": error
        }
    )
    return HTMLResponse(content=html_content)

