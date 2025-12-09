"""
Backtest API endpoints.

Provides REST API for evaluating forecasts against actual outcomes.
"""
from fastapi import APIRouter, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.backtest_service import evaluate_forecast_by_id, get_backtest_service
from domain.backtest import BacktestResult, BacktestMetrics
from core.logger import logger

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
dashboard_router = APIRouter(tags=["dashboard"])

# Setup templates
templates_dir = project_root / "ui" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)

# Backtest storage is now in database via BacktestService


# Request/Response models
class EvaluateBacktestRequest(BaseModel):
    """Request model for evaluating a forecast."""
    
    realised_prices: List[float] = Field(
        ...,
        description="Actual prices that occurred (must match forecast horizon length)",
        min_length=1
    )


class BacktestMetricsResponse(BaseModel):
    """Response model for backtest metrics."""
    
    mae: float
    mape: float
    rmse: float
    directional_accuracy: float
    calibration_coverage: float
    well_calibrated: bool
    directional_correct: int | None = None
    directional_total: int | None = None
    calibration_expected: float | None = None
    calibration_error: float | None = None


class BacktestResultResponse(BaseModel):
    """Response model for backtest result."""
    
    id: str
    forecast_id: str
    symbol: str
    created_at: str
    horizon: int
    realised_series: List[float]
    metrics: BacktestMetricsResponse
    metadata: Dict[str, Any]
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


@router.post("/{forecast_id}", response_model=BacktestResultResponse, status_code=status.HTTP_201_CREATED)
async def evaluate_backtest_endpoint(
    forecast_id: str,
    request: EvaluateBacktestRequest
) -> BacktestResultResponse:
    """
    Evaluate a forecast against actual outcomes.
    
    Args:
        forecast_id: Forecast ID to evaluate
        request: Request body with realised prices
    
    Returns:
        BacktestResultResponse with evaluation metrics
    
    Raises:
        HTTPException: If forecast not found or evaluation fails
    """
    try:
        logger.info(f"Evaluating forecast {forecast_id} via API with {len(request.realised_prices)} actual prices")
        
        # Evaluate forecast using service (automatically saves to DB)
        backtest_result = evaluate_forecast_by_id(
            forecast_id=forecast_id,
            realised=request.realised_prices
        )
        
        # Convert to response model
        response = BacktestResultResponse(
            id=backtest_result.id,
            forecast_id=backtest_result.forecast_id,
            symbol=backtest_result.symbol,
            created_at=backtest_result.created_at.isoformat(),
            horizon=backtest_result.horizon,
            realised_series=backtest_result.realised_series,
            metrics=BacktestMetricsResponse(
                mae=backtest_result.metrics.mae,
                mape=backtest_result.metrics.mape,
                rmse=backtest_result.metrics.rmse,
                directional_accuracy=backtest_result.metrics.directional_accuracy,
                calibration_coverage=backtest_result.metrics.calibration_coverage,
                well_calibrated=backtest_result.metrics.well_calibrated,
                directional_correct=backtest_result.metrics.directional_correct,
                directional_total=backtest_result.metrics.directional_total,
                calibration_expected=backtest_result.metrics.calibration_expected,
                calibration_error=backtest_result.metrics.calibration_error,
            ),
            metadata=backtest_result.metadata
        )
        
        logger.info(f"Backtest {backtest_result.id} completed successfully via API")
        return response
        
    except ValueError as e:
        logger.error(f"Invalid backtest request for {forecast_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error evaluating backtest for {forecast_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate backtest: {str(e)}"
        )


@router.get("/{backtest_id}", response_model=BacktestResultResponse)
async def get_backtest_endpoint(backtest_id: str) -> BacktestResultResponse:
    """
    Retrieve a backtest result by ID.
    
    Args:
        backtest_id: Backtest result ID to retrieve
    
    Returns:
        BacktestResultResponse with backtest data
    
    Raises:
        HTTPException: If backtest not found
    """
    try:
        logger.info(f"Retrieving backtest {backtest_id} via API")
        
        # Get from database via service
        service = get_backtest_service()
        backtest_result = service.get_backtest(backtest_id)
        
        if not backtest_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found"
            )
        
        # Convert to response model
        response = BacktestResultResponse(
            id=backtest_result.id,
            forecast_id=backtest_result.forecast_id,
            symbol=backtest_result.symbol,
            created_at=backtest_result.created_at.isoformat(),
            horizon=backtest_result.horizon,
            realised_series=backtest_result.realised_series,
            metrics=BacktestMetricsResponse(
                mae=backtest_result.metrics.mae,
                mape=backtest_result.metrics.mape,
                rmse=backtest_result.metrics.rmse,
                directional_accuracy=backtest_result.metrics.directional_accuracy,
                calibration_coverage=backtest_result.metrics.calibration_coverage,
                well_calibrated=backtest_result.metrics.well_calibrated,
                directional_correct=backtest_result.metrics.directional_correct,
                directional_total=backtest_result.metrics.directional_total,
                calibration_expected=backtest_result.metrics.calibration_expected,
                calibration_error=backtest_result.metrics.calibration_error,
            ),
            metadata=backtest_result.metadata
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving backtest {backtest_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve backtest: {str(e)}"
        )


@router.get("", response_model=List[BacktestResultResponse])
async def list_backtests_endpoint(
    limit: int = 100,
    symbol: Optional[str] = None,
    forecast_id: Optional[str] = None
) -> List[BacktestResultResponse]:
    """
    List backtest results.
    
    Args:
        limit: Maximum number of results to return (default: 100)
        symbol: Optional filter by symbol
        forecast_id: Optional filter by forecast ID
    
    Returns:
        List of BacktestResultResponse objects
    """
    try:
        logger.info(f"Listing backtests via API (limit={limit}, symbol={symbol}, forecast_id={forecast_id})")
        
        service = get_backtest_service()
        backtest_results = service.list_backtests(
            limit=limit,
            symbol=symbol,
            forecast_id=forecast_id
        )
        
        # Convert to response models
        responses = []
        for result in backtest_results:
            responses.append(BacktestResultResponse(
                id=result.id,
                forecast_id=result.forecast_id,
                symbol=result.symbol,
                created_at=result.created_at.isoformat(),
                horizon=result.horizon,
                realised_series=result.realised_series,
                metrics=BacktestMetricsResponse(
                    mae=result.metrics.mae,
                    mape=result.metrics.mape,
                    rmse=result.metrics.rmse,
                    directional_accuracy=result.metrics.directional_accuracy,
                    calibration_coverage=result.metrics.calibration_coverage,
                    well_calibrated=result.metrics.well_calibrated,
                    directional_correct=result.metrics.directional_correct,
                    directional_total=result.metrics.directional_total,
                    calibration_expected=result.metrics.calibration_expected,
                    calibration_error=result.metrics.calibration_error,
                ),
                metadata=result.metadata
            ))
        
        logger.info(f"Returning {len(responses)} backtest results")
        return responses
        
    except Exception as e:
        logger.error(f"Error listing backtests: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backtests: {str(e)}"
        )


# Dashboard endpoints
@dashboard_router.get("/backtest", response_class=HTMLResponse)
async def backtest_dashboard(request: Request):
    """
    Render the backtest dashboard form.
    
    Args:
        request: FastAPI request object
    
    Returns:
        HTML response with backtest form
    """
    html_content = render_template(
        "backtest.html",
        {
            "forecast_id": None,
            "realised_prices": None,
            "backtest_result": None,
            "error": None
        }
    )
    return HTMLResponse(content=html_content)


@dashboard_router.post("/backtest", response_class=HTMLResponse)
async def backtest_dashboard_submit(
    request: Request,
    forecast_id: str = Form(...),
    realised_prices: str = Form(...)
):
    """
    Handle backtest form submission.
    
    Args:
        request: FastAPI request object
        forecast_id: Forecast ID to evaluate
        realised_prices: Comma-separated string of actual prices
    
    Returns:
        HTML response with backtest result or error
    """
    error = None
    backtest_result = None
    
    try:
        # Validate forecast ID
        forecast_id = forecast_id.strip()
        if not forecast_id:
            error = "Forecast ID is required."
            html_content = render_template(
                "backtest.html",
                {
                    "forecast_id": forecast_id,
                    "realised_prices": realised_prices,
                    "backtest_result": None,
                    "error": error
                }
            )
            return HTMLResponse(content=html_content)
        
        # Parse realised prices
        try:
            # Split by comma and clean up
            price_list = [float(p.strip()) for p in realised_prices.split(",") if p.strip()]
            
            if not price_list:
                error = "Please enter at least one realised price."
                html_content = render_template(
                    "backtest.html",
                    {
                        "forecast_id": forecast_id,
                        "realised_prices": realised_prices,
                        "backtest_result": None,
                        "error": error
                    }
                )
                return HTMLResponse(content=html_content)
        except ValueError as e:
            error = f"Invalid price format. Please enter comma-separated numbers. Error: {str(e)}"
            html_content = render_template(
                "backtest.html",
                {
                    "forecast_id": forecast_id,
                    "realised_prices": realised_prices,
                    "backtest_result": None,
                    "error": error
                }
            )
            return HTMLResponse(content=html_content)
        
        # Run backtest evaluation
        logger.info(f"Running backtest for forecast {forecast_id} with {len(price_list)} realised prices")
        result = evaluate_forecast_by_id(
            forecast_id=forecast_id,
            realised=price_list
        )
        
        # Convert to dict for template
        backtest_result = {
            "id": result.id,
            "forecast_id": result.forecast_id,
            "symbol": result.symbol,
            "horizon": result.horizon,
            "realised_series": result.realised_series,
            "created_at": result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": {
                "mae": result.metrics.mae,
                "mape": result.metrics.mape,
                "rmse": result.metrics.rmse,
                "directional_accuracy": result.metrics.directional_accuracy,
                "calibration_coverage": result.metrics.calibration_coverage,
                "well_calibrated": result.metrics.well_calibrated,
                "directional_correct": result.metrics.directional_correct,
                "directional_total": result.metrics.directional_total,
                "calibration_expected": result.metrics.calibration_expected,
                "calibration_error": result.metrics.calibration_error,
            }
        }
        
        logger.info(f"Backtest {result.id} completed successfully via dashboard")
        
    except ValueError as e:
        error = f"Invalid input: {str(e)}"
        logger.error(f"Backtest dashboard error: {e}")
    except Exception as e:
        error = f"Error running backtest: {str(e)}"
        logger.error(f"Backtest dashboard error: {e}", exc_info=True)
    
    html_content = render_template(
        "backtest.html",
        {
            "forecast_id": forecast_id if 'forecast_id' in locals() else None,
            "realised_prices": realised_prices if 'realised_prices' in locals() else None,
            "backtest_result": backtest_result,
            "error": error
        }
    )
    return HTMLResponse(content=html_content)

