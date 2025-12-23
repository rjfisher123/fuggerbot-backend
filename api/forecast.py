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


class RichForecastResponse(BaseModel):
    """
    Rich Response model with full context.
    """
    forecast_id: str
    symbol: str
    created_at: str
    
    # Core Data
    price_target: Optional[float] = Field(None, description="Projected price at horizon end")
    confidence: float = Field(..., description="Overall Trust Score (0-1)")
    
    # Rich Context
    technicals: Optional[Dict[str, Any]] = Field(None, description="Technical Indicators (RSI, MACD)")
    regime: Optional[str] = Field(None, description="Market Regime (e.g. Bullish Trending)")
    news_summary: Optional[str] = Field(None, description="Relevant News Headlines")
    reasoning: Optional[str] = Field(None, description="AI Rationale")
    
    # Raw Data (for debugging/charts)
    forecast_horizon: int
    predicted_values: List[float] = Field(default=[], description="Point forecast series")
    lower_bound: List[float] = Field(default=[], description="Lower confidence bound")
    upper_bound: List[float] = Field(default=[], description="Upper confidence bound")
    
    metadata: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

@router.post("", response_model=RichForecastResponse, status_code=status.HTTP_201_CREATED)
async def create_forecast_endpoint(request: CreateForecastRequest) -> RichForecastResponse:
    """
    Create a new forecast with RICH context.
    """
    try:
        logger.info(f"Creating forecast for {request.symbol} via API")
        
        # Create forecast using service
        forecast = await create_forecast(
            symbol=request.symbol,
            historical_prices=request.historical_prices,
            forecast_horizon=request.forecast_horizon,
            options=request.options
        )
        
        # Extract Rich Data
        meta = forecast.metadata or {}
        technicals = meta.get("technicals", {})
        regime_data = forecast.regime or {}
        
        # Get price target (last point of forecast)
        price_target = None
        predicted_values = []
        lower_bound = []
        upper_bound = []
        
        if forecast.predicted_series:
             predicted_values = forecast.predicted_series.point_forecast or []
             lower_bound = forecast.predicted_series.lower_bound or []
             upper_bound = forecast.predicted_series.upper_bound or []
             if predicted_values:
                 price_target = predicted_values[-1]

        # Construct Rich Response
        response = RichForecastResponse(
            forecast_id=forecast.forecast_id,
            symbol=forecast.symbol,
            created_at=forecast.created_at.isoformat(),
            
            price_target=price_target,
            confidence=forecast.trust_score,
            
            technicals=technicals,
            regime=regime_data.get("regime", "Unknown"),
            news_summary=meta.get("news_context", "No news available"),
            reasoning=meta.get("frs_interpretation", "No rationale generated"),
            
            forecast_horizon=forecast.forecast_horizon,
            predicted_values=predicted_values,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            
            metadata=meta
        )
        
        logger.info(f"Forecast {forecast.forecast_id} created successfully via API")
        return response
        
    except ValueError as e:
        logger.error(f"Invalid forecast request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating forecast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create forecast: {str(e)}")


@router.get("/{forecast_id}", response_model=RichForecastResponse)
async def get_forecast_endpoint(forecast_id: str) -> RichForecastResponse:
    """Retrieve a forecast by ID."""
    try:
        forecast = get_forecast(forecast_id)
        if not forecast:
            raise HTTPException(status_code=404, detail="Forecast not found")
            
        # Extract Rich Data (logic duplicated from create, ideally helper function)
        meta = forecast.metadata or {}
        predicted_values = forecast.predicted_series.point_forecast if forecast.predicted_series else []
        price_target = predicted_values[-1] if predicted_values else None
        
        return RichForecastResponse(
            forecast_id=forecast.forecast_id,
            symbol=forecast.symbol,
            created_at=forecast.created_at.isoformat(),
            price_target=price_target,
            confidence=forecast.trust_score,
            technicals=meta.get("technicals", {}),
            regime=forecast.regime.get("regime", "Unknown") if forecast.regime else "Unknown",
            news_summary=meta.get("news_context"),
            reasoning=meta.get("frs_interpretation"),
            forecast_horizon=forecast.forecast_horizon,
            predicted_values=predicted_values,
            lower_bound=forecast.predicted_series.lower_bound if forecast.predicted_series else [],
            upper_bound=forecast.predicted_series.upper_bound if forecast.predicted_series else [],
            metadata=meta
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GenerateForecastRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    forecast_horizon: int = Field(30, ge=1, le=365)
    
@router.post("/generate", response_model=RichForecastResponse)
async def generate_forecast_simple(request: GenerateForecastRequest):
    """
    Generate a forecast by symbol.
    """
    try:
        symbol = request.symbol.upper().strip()
        logger.info(f"Fetching historical prices for {symbol}...")
        historical_prices = get_historical_prices(symbol, period="1y") 
        
        if not historical_prices or len(historical_prices) < 20:
             raise HTTPException(status_code=400, detail=f"Insufficient data for {symbol}")

        logger.info(f"Creating forecast for {symbol}...")
        forecast = await create_forecast(
            symbol=symbol,
            historical_prices=historical_prices,
            forecast_horizon=request.forecast_horizon
        )
        
        # Populate Response
        meta = forecast.metadata or {}
        predicted_values = forecast.predicted_series.point_forecast if forecast.predicted_series else []
        
        return RichForecastResponse(
            forecast_id=forecast.forecast_id,
            symbol=forecast.symbol,
            created_at=forecast.created_at.isoformat(),
            price_target=predicted_values[-1] if predicted_values else None,
            confidence=forecast.trust_score,
            technicals=meta.get("technicals", {}),
            regime=forecast.regime.get("regime", "Unknown") if forecast.regime else "Unknown",
            news_summary=meta.get("news_context"),
            reasoning=meta.get("frs_interpretation"),
            forecast_horizon=forecast.forecast_horizon,
            predicted_values=predicted_values,
            lower_bound=forecast.predicted_series.lower_bound if forecast.predicted_series else [],
            upper_bound=forecast.predicted_series.upper_bound if forecast.predicted_series else [],
            metadata=meta
        )

    except Exception as e:
        logger.error(f"Error generating forecast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


