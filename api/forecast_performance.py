"""
Forecast Performance Analytics API.

Provides analytics dashboard for forecast performance metrics.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import sys
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.forecast_metadata import ForecastMetadata
from services.backtest_service import get_backtest_service
from persistence.db import SessionLocal
from persistence.repositories_backtest import BacktestRepository
from core.logger import logger

dashboard_router = APIRouter(tags=["dashboard"])

templates_dir = project_root / "ui" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

# Add JSON filter to Jinja2
def tojson_filter(obj):
    """Convert Python object to JSON string."""
    return json.dumps(obj)

jinja_env.filters['tojson'] = tojson_filter


def render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)


def list_forecast_snapshots(limit: int = 100) -> List[Dict[str, Any]]:
    """
    List forecast snapshots from filesystem.
    
    Args:
        limit: Maximum number of forecasts to return
    
    Returns:
        List of forecast snapshot dicts
    """
    metadata_manager = ForecastMetadata()
    forecasts = []
    
    # Get all forecast snapshot files
    snapshot_files = sorted(metadata_manager.storage_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    for filepath in snapshot_files[:limit]:
        try:
            with open(filepath, "r") as f:
                snapshot = json.load(f)
                forecasts.append(snapshot)
        except Exception as e:
            logger.warning(f"Error loading forecast snapshot {filepath}: {e}")
            continue
    
    return forecasts


def calculate_rolling_metrics(backtests: List[Dict[str, Any]], window: int = 10) -> Dict[str, List[float]]:
    """
    Calculate rolling MAPE and directional accuracy.
    
    Args:
        backtests: List of backtest dicts with metrics
        window: Rolling window size
    
    Returns:
        Dict with 'dates', 'rolling_mape', 'rolling_directional_accuracy'
    """
    if not backtests:
        return {
            "dates": [],
            "rolling_mape": [],
            "rolling_directional_accuracy": []
        }
    
    # Sort by date
    sorted_backtests = sorted(backtests, key=lambda x: x.get("created_at", ""))
    
    dates = []
    rolling_mape = []
    rolling_directional = []
    
    for i in range(len(sorted_backtests)):
        window_start = max(0, i - window + 1)
        window_backtests = sorted_backtests[window_start:i+1]
        
        if window_backtests:
            mape_values = [bt["metrics"]["mape"] for bt in window_backtests if "metrics" in bt and "mape" in bt["metrics"]]
            directional_values = [bt["metrics"]["directional_accuracy"] for bt in window_backtests if "metrics" in bt and "directional_accuracy" in bt["metrics"]]
            
            avg_mape = sum(mape_values) / len(mape_values) if mape_values else 0.0
            avg_directional = sum(directional_values) / len(directional_values) if directional_values else 0.0
            
            dates.append(window_backtests[-1].get("created_at", ""))
            rolling_mape.append(avg_mape)
            rolling_directional.append(avg_directional)
    
    return {
        "dates": dates,
        "rolling_mape": rolling_mape,
        "rolling_directional_accuracy": rolling_directional
    }


@dashboard_router.get("/forecast/performance", response_class=HTMLResponse)
async def forecast_performance_dashboard(request: Request):
    """Render the forecast performance analytics dashboard."""
    try:
        # Get forecast snapshots
        forecast_snapshots = list_forecast_snapshots(limit=100)
        logger.info(f"Found {len(forecast_snapshots)} forecast snapshots")
        
        # Get all backtests from database
        backtest_service = get_backtest_service()
        all_backtests = backtest_service.list_backtests(limit=1000)
        
        # Group backtests by forecast_id
        backtests_by_forecast = defaultdict(list)
        for bt in all_backtests:
            backtests_by_forecast[bt.forecast_id].append({
                "id": bt.id,
                "forecast_id": bt.forecast_id,
                "symbol": bt.symbol,
                "created_at": bt.created_at.isoformat() if bt.created_at else "",
                "metrics": {
                    "mae": bt.metrics.mae,
                    "mape": bt.metrics.mape,
                    "rmse": bt.metrics.rmse,
                    "directional_accuracy": bt.metrics.directional_accuracy,
                    "calibration_coverage": bt.metrics.calibration_coverage,
                    "well_calibrated": bt.metrics.well_calibrated,
                }
            })
        
        # Match forecasts with their backtests
        forecast_performance = []
        for snapshot in forecast_snapshots[:50]:  # Limit to 50 most recent
            forecast_id = snapshot.get("forecast_id")
            backtests = backtests_by_forecast.get(forecast_id, [])
            
            # Calculate average metrics if we have backtests
            avg_metrics = None
            if backtests:
                avg_metrics = {
                    "mae": sum(bt["metrics"]["mae"] for bt in backtests) / len(backtests),
                    "mape": sum(bt["metrics"]["mape"] for bt in backtests) / len(backtests),
                    "rmse": sum(bt["metrics"]["rmse"] for bt in backtests) / len(backtests),
                    "directional_accuracy": sum(bt["metrics"]["directional_accuracy"] for bt in backtests) / len(backtests),
                    "calibration_coverage": sum(bt["metrics"]["calibration_coverage"] for bt in backtests) / len(backtests),
                }
            
            forecast_performance.append({
                "forecast_id": forecast_id,
                "symbol": snapshot.get("symbol", "UNKNOWN"),
                "created_at": snapshot.get("timestamp", ""),
                "backtest_count": len(backtests),
                "avg_metrics": avg_metrics,
                "latest_backtest": backtests[0] if backtests else None,
            })
        
        # Calculate rolling metrics from all backtests
        all_backtest_dicts = []
        for bt in all_backtests:
            all_backtest_dicts.append({
                "created_at": bt.created_at.isoformat() if bt.created_at else "",
                "metrics": {
                    "mape": bt.metrics.mape,
                    "directional_accuracy": bt.metrics.directional_accuracy,
                }
            })
        
        rolling_metrics = calculate_rolling_metrics(all_backtest_dicts, window=10)
        
        # Generate Plotly charts (as JSON for embedding)
        charts = {}
        
        # Rolling MAPE chart
        if rolling_metrics["dates"]:
            charts["rolling_mape"] = {
                "data": [
                    {
                        "x": rolling_metrics["dates"],
                        "y": rolling_metrics["rolling_mape"],
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "Rolling MAPE (%)",
                        "line": {"color": "#1f77b4"}
                    }
                ],
                "layout": {
                    "title": "Rolling MAPE (10-backtest window)",
                    "xaxis": {"title": "Date"},
                    "yaxis": {"title": "MAPE (%)"},
                    "hovermode": "closest"
                }
            }
        
        # Rolling Directional Accuracy chart
        if rolling_metrics["dates"]:
            charts["rolling_directional"] = {
                "data": [
                    {
                        "x": rolling_metrics["dates"],
                        "y": rolling_metrics["rolling_directional_accuracy"],
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "Rolling Directional Accuracy (%)",
                        "line": {"color": "#2ca02c"}
                    }
                ],
                "layout": {
                    "title": "Rolling Directional Accuracy (10-backtest window)",
                    "xaxis": {"title": "Date"},
                    "yaxis": {"title": "Directional Accuracy (%)"},
                    "hovermode": "closest"
                }
            }
        
        # Overall statistics
        if all_backtests:
            overall_stats = {
                "total_backtests": len(all_backtests),
                "avg_mape": sum(bt.metrics.mape for bt in all_backtests) / len(all_backtests),
                "avg_directional_accuracy": sum(bt.metrics.directional_accuracy for bt in all_backtests) / len(all_backtests),
                "avg_mae": sum(bt.metrics.mae for bt in all_backtests) / len(all_backtests),
                "avg_rmse": sum(bt.metrics.rmse for bt in all_backtests) / len(all_backtests),
            }
        else:
            overall_stats = {
                "total_backtests": 0,
                "avg_mape": 0.0,
                "avg_directional_accuracy": 0.0,
                "avg_mae": 0.0,
                "avg_rmse": 0.0,
            }
        
        context = {
            "forecast_performance": forecast_performance,
            "rolling_metrics": rolling_metrics,
            "charts": charts,
            "overall_stats": overall_stats,
            "total_forecasts": len(forecast_snapshots),
        }
        
        return render_template("forecast_performance.html", context)
        
    except Exception as e:
        logger.error(f"Error rendering forecast performance dashboard: {e}", exc_info=True)
        context = {
            "forecast_performance": [],
            "rolling_metrics": {"dates": [], "rolling_mape": [], "rolling_directional_accuracy": []},
            "charts": {},
            "overall_stats": {
                "total_backtests": 0,
                "avg_mape": 0.0,
                "avg_directional_accuracy": 0.0,
                "avg_mae": 0.0,
                "avg_rmse": 0.0,
            },
            "total_forecasts": 0,
            "error_message": f"Error loading performance data: {str(e)}"
        }
        return render_template("forecast_performance.html", context)

