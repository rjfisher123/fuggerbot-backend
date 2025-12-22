"""
Backtest domain model.

Represents the result of evaluating a forecast against actual outcomes.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class BacktestMetrics(BaseModel):
    """Metrics for backtest evaluation."""
    
    mae: float = Field(..., description="Mean Absolute Error", ge=0.0)
    mape: float = Field(..., description="Mean Absolute Percentage Error (%)", ge=0.0)
    rmse: float = Field(..., description="Root Mean Squared Error", ge=0.0)
    directional_accuracy: float = Field(..., description="Directional accuracy (%)", ge=0.0, le=100.0)
    calibration_coverage: float = Field(..., description="Calibration coverage (%)", ge=0.0, le=100.0)
    well_calibrated: bool = Field(..., description="Whether forecast is well calibrated")
    
    # Additional detailed metrics
    directional_correct: Optional[int] = Field(None, description="Number of correct directional predictions")
    directional_total: Optional[int] = Field(None, description="Total number of directional predictions")
    calibration_expected: Optional[float] = Field(None, description="Expected calibration coverage (%)")
    calibration_error: Optional[float] = Field(None, description="Calibration error (%)")


class BacktestResult(BaseModel):
    """
    Domain model representing a backtest evaluation result.
    
    Contains the forecast ID, actual outcomes, and evaluation metrics.
    """
    
    # Core identifiers
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique backtest result ID")
    forecast_id: str = Field(..., description="Forecast ID that was evaluated")
    symbol: str = Field(..., description="Trading symbol")
    created_at: datetime = Field(default_factory=datetime.now, description="Backtest creation timestamp")
    
    # Forecast and actual data
    horizon: int = Field(..., description="Forecast horizon (number of periods)", ge=1)
    realised_series: List[float] = Field(..., description="Actual prices that occurred", min_length=1)
    
    # Evaluation metrics
    metrics: BacktestMetrics = Field(..., description="Backtest evaluation metrics")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert backtest result to dictionary for serialization."""
        return {
            "id": self.id,
            "forecast_id": self.forecast_id,
            "symbol": self.symbol,
            "created_at": self.created_at.isoformat(),
            "horizon": self.horizon,
            "realised_series": self.realised_series,
            "metrics": {
                "mae": self.metrics.mae,
                "mape": self.metrics.mape,
                "rmse": self.metrics.rmse,
                "directional_accuracy": self.metrics.directional_accuracy,
                "calibration_coverage": self.metrics.calibration_coverage,
                "well_calibrated": self.metrics.well_calibrated,
                "directional_correct": self.metrics.directional_correct,
                "directional_total": self.metrics.directional_total,
                "calibration_expected": self.metrics.calibration_expected,
                "calibration_error": self.metrics.calibration_error,
            },
            "metadata": self.metadata,
        }
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary format for UI display."""
        return {
            "mean_absolute_error": f"${self.metrics.mae:.2f}",
            "mean_absolute_percentage_error": f"{self.metrics.mape:.2f}%",
            "root_mean_squared_error": f"${self.metrics.rmse:.2f}",
            "directional_accuracy": f"{self.metrics.directional_accuracy:.1f}%",
            "calibration_coverage": (
                f"{self.metrics.calibration_coverage:.1f}% "
                f"(expected {self.metrics.calibration_expected or 95.0:.1f}%)"
            ),
            "well_calibrated": self.metrics.well_calibrated
        }










