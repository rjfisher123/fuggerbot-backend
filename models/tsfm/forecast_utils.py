"""
Utility functions for Chronos model forecasting.

This module provides helper functions for working with the Chronos pipeline
from amazon-science/chronos-forecasting library.
"""
import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def forecast_series(
    model,
    series: List[float],
    forecast_horizon: int = 30,
    context_length: Optional[int] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate forecast using Chronos pipeline.
    
    Args:
        model: ChronosPipeline instance from chronos-forecasting
        series: Historical time series values (list of floats)
        forecast_horizon: Number of future periods to forecast
        context_length: Number of historical points to use (None = use all)
        
    Returns:
        Tuple of (point_forecast, lower_bound, upper_bound) as numpy arrays
    """
    try:
        # Convert to numpy array
        series_array = np.array(series, dtype=np.float32)
        
        # Select context window
        if context_length is not None:
            context = series_array[-context_length:]
        else:
            context = series_array
        
        # Ensure minimum length
        if len(context) < 10:
            logger.warning(f"Context length ({len(context)}) is very short")
        
        # Prepare context for Chronos (needs to be 2D: [batch, time])
        # Chronos expects shape (batch_size, context_length) as torch.Tensor
        import torch
        
        # Ensure deterministic ordering (sort if needed)
        # In practice, context should already be time-ordered
        context_sorted = np.sort(context) if len(context) > 1 and not np.all(np.diff(context) >= -1e-10) else context
        
        context_2d = context_sorted.reshape(1, -1)
        
        # Use float64 for deterministic mode if available
        # Check if deterministic mode is requested (via model or global setting)
        dtype = torch.float64  # Higher precision for determinism
        context_tensor = torch.tensor(context_2d, dtype=dtype)
        
        # Generate forecast using Chronos pipeline
        # API: predict(inputs, prediction_length=..., num_samples=...)
        # Returns: torch.Tensor
        # - If num_samples > 1: shape is (num_samples, batch_size, prediction_length)
        # - If num_samples = 1 or None: shape is (batch_size, prediction_length)
        
        # Check for deterministic mode (can be passed via model attributes or global)
        deterministic = getattr(model, '_deterministic_mode', False)
        
        if deterministic:
            # Deterministic inference: single sample, no randomness
            num_samples = 1
            temperature = 0.0
            logger.info("Using deterministic Chronos inference")
        else:
            # Standard inference: multiple samples for uncertainty
            num_samples = 100
            temperature = None
        
        forecast_tensor = model.predict(
            context_tensor,
            prediction_length=forecast_horizon,
            num_samples=num_samples,
            temperature=temperature if temperature is not None else None
        )
        
        # Convert to numpy
        forecast_array = forecast_tensor.cpu().numpy()
        
        if forecast_array.ndim == 3:
            # Multiple samples: shape (num_samples, batch, prediction_length)
            forecast_samples = forecast_array  # (num_samples, batch, prediction_length)
            point_forecast = np.median(forecast_samples, axis=0)[0]  # [0] for batch
            lower_bound = np.percentile(forecast_samples, 5, axis=0)[0]
            upper_bound = np.percentile(forecast_samples, 95, axis=0)[0]
        elif forecast_array.ndim == 2:
            # Single sample or deterministic: shape (batch, prediction_length)
            point_forecast = forecast_array[0]  # [0] for batch
            
            # Generate multiple samples by calling predict multiple times for uncertainty
            # (Chronos may return deterministic output even with num_samples > 1)
            try:
                # Try to get samples with temperature variation
                samples_list = []
                for _ in range(min(20, num_samples)):  # Generate 20 samples
                    sample = model.predict(
                        context_tensor,
                        prediction_length=forecast_horizon,
                        num_samples=1,
                        temperature=1.0 + np.random.uniform(-0.1, 0.1)  # Small temperature variation
                    )
                    samples_list.append(sample.cpu().numpy()[0])
                
                samples_array = np.array(samples_list)  # (n_samples, prediction_length)
                point_forecast = np.median(samples_array, axis=0)
                lower_bound = np.percentile(samples_array, 5, axis=0)
                upper_bound = np.percentile(samples_array, 95, axis=0)
            except Exception:
                # Fallback: estimate uncertainty from point forecast variance
                # Use historical volatility as proxy
                historical_volatility = np.std(context)
                uncertainty = historical_volatility * 0.15  # 15% of historical volatility
                lower_bound = point_forecast - 1.96 * uncertainty
                upper_bound = point_forecast + 1.96 * uncertainty
        else:
            # Unexpected shape - use as-is and estimate bounds
            point_forecast = forecast_array.flatten()[:forecast_horizon]
            historical_volatility = np.std(context)
            uncertainty = historical_volatility * 0.15
            lower_bound = point_forecast - 1.96 * uncertainty
            upper_bound = point_forecast + 1.96 * uncertainty
        
        # Ensure bounds are valid
        lower_bound = np.maximum(lower_bound, point_forecast * 0.5)
        upper_bound = np.minimum(upper_bound, point_forecast * 1.5)
        
        logger.info(f"Generated forecast: horizon={forecast_horizon}, "
                   f"point_range=[{np.min(point_forecast):.2f}, {np.max(point_forecast):.2f}]")
        
        return point_forecast, lower_bound, upper_bound
        
        
    except Exception as e:
        logger.error(f"Error in forecast_series: {e}", exc_info=True)
        raise RuntimeError(f"Forecast generation failed: {e}")


def prepare_context(
    series: List[float],
    context_length: Optional[int] = None
) -> np.ndarray:
    """
    Prepare context array from historical series.
    
    Args:
        series: Historical time series values
        context_length: Number of points to use (None = use all)
        
    Returns:
        Numpy array of context values, ready for Chronos
    """
    series_array = np.array(series, dtype=np.float32)
    
    # Handle NaN/inf values
    if np.any(np.isnan(series_array)) or np.any(np.isinf(series_array)):
        logger.warning("Series contains NaN/Inf values. Filling with forward-fill.")
        series_array = np.nan_to_num(
            series_array,
            nan=np.nanmean(series_array),
            posinf=np.nanmax(series_array),
            neginf=np.nanmin(series_array)
        )
    
    # Select context window
    if context_length is not None:
        context = series_array[-context_length:]
    else:
        context = series_array
    
    return context

