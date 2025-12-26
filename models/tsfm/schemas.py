"""Pydantic schemas for TSFM input/output data contracts."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np


class ForecastInput(BaseModel):
    """Input schema for time series forecasting."""
    
    series: List[float] = Field(
        ...,
        description="Historical time series values (univariate)",
        min_length=1,
        max_length=10000
    )
    
    forecast_horizon: int = Field(
        ...,
        description="Number of future time steps to forecast",
        ge=1,
        le=1000
    )
    
    context_length: Optional[int] = Field(
        None,
        description="Number of historical points to use as context. If None, uses full series.",
        ge=1,
        le=10000
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata (symbol, frequency, etc.)"
    )
    
    @field_validator('series')
    @classmethod
    def validate_series(cls, v: List[float]) -> List[float]:
        """Validate series contains valid numeric values."""
        if not v:
            raise ValueError("Series cannot be empty")
        if any(not isinstance(x, (int, float)) or np.isnan(x) or np.isinf(x) for x in v):
            raise ValueError("Series must contain only finite numeric values")
        return v
    
    @field_validator('forecast_horizon')
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        """Validate forecast horizon is reasonable."""
        if v <= 0:
            raise ValueError("Forecast horizon must be positive")
        return v


class ForecastOutput(BaseModel):
    """Output schema for probabilistic forecasts."""
    
    point_forecast: List[float] = Field(
        ...,
        description="Point estimates (median/mean) for each forecast step"
    )
    
    lower_bound: List[float] = Field(
        ...,
        description="Lower bound of prediction interval (e.g., 5th percentile)"
    )
    
    upper_bound: List[float] = Field(
        ...,
        description="Upper bound of prediction interval (e.g., 95th percentile)"
    )
    
    quantiles: Optional[Dict[str, List[float]]] = Field(
        None,
        description="Additional quantiles (e.g., {'q10': [...], 'q90': [...]})"
    )
    
    forecast_horizon: int = Field(
        ...,
        description="Number of forecast steps (should match input)"
    )
    
    model_name: str = Field(
        ...,
        description="Name/version of the model used"
    )
    
    inference_time_ms: float = Field(
        ...,
        description="Time taken for inference in milliseconds"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata from input or model"
    )
    
    @field_validator('point_forecast', 'lower_bound', 'upper_bound')
    @classmethod
    def validate_forecast_lengths(cls, v: List[float], info) -> List[float]:
        """Validate all forecast arrays have same length."""
        if not v:
            raise ValueError("Forecast arrays cannot be empty")
        if any(not isinstance(x, (int, float)) or np.isnan(x) or np.isinf(x) for x in v):
            raise ValueError("Forecast arrays must contain only finite numeric values")
        return v
    
    def model_post_init(self, __context: Any) -> None:
        """Validate that all forecast arrays have matching lengths."""
        lengths = {
            'point_forecast': len(self.point_forecast),
            'lower_bound': len(self.lower_bound),
            'upper_bound': len(self.upper_bound)
        }
        
        if len(set(lengths.values())) > 1:
            raise ValueError(
                f"All forecast arrays must have same length. Got: {lengths}"
            )
        
        if lengths['point_forecast'] != self.forecast_horizon:
            raise ValueError(
                f"Forecast length ({lengths['point_forecast']}) must match "
                f"forecast_horizon ({self.forecast_horizon})"
            )
        
        # Validate bounds are ordered correctly
        for i in range(len(self.point_forecast)):
            if self.lower_bound[i] > self.upper_bound[i]:
                raise ValueError(
                    f"Lower bound ({self.lower_bound[i]}) must be <= "
                    f"upper bound ({self.upper_bound[i]}) at index {i}"
                )


class BatchForecastInput(BaseModel):
    """Input schema for batch forecasting (multiple series)."""
    
    series_list: List[List[float]] = Field(
        ...,
        description="List of historical time series",
        min_length=1
    )
    
    forecast_horizon: int = Field(
        ...,
        description="Number of future time steps to forecast for all series",
        ge=1,
        le=1000
    )
    
    context_length: Optional[int] = Field(
        None,
        description="Number of historical points to use as context"
    )
    
    metadata_list: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional metadata for each series"
    )


class BatchForecastOutput(BaseModel):
    """Output schema for batch forecasts."""
    
    forecasts: List[ForecastOutput] = Field(
        ...,
        description="List of forecast outputs, one per input series"
    )
    
    total_inference_time_ms: float = Field(
        ...,
        description="Total time for batch inference in milliseconds"
    )












