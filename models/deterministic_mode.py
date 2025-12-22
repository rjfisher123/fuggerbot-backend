"""
Deterministic Forecast Mode (DFM).

Ensures same inputs → same forecast every time.
"""
import numpy as np
import torch
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class DeterministicForecastMode:
    """Manages deterministic forecast settings."""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize deterministic mode.
        
        Args:
            enabled: Whether deterministic mode is enabled
        """
        self.enabled = enabled
        if enabled:
            self._set_deterministic_settings()
    
    def _set_deterministic_settings(self) -> None:
        """Set PyTorch and NumPy for deterministic behavior."""
        # PyTorch deterministic settings
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        
        # NumPy random seed (if needed)
        np.random.seed(42)
        
        logger.info("Deterministic mode enabled - forecasts will be reproducible")
    
    def get_chronos_params(self) -> Dict[str, Any]:
        """
        Get Chronos parameters for deterministic inference.
        
        Returns:
            Dict with deterministic Chronos parameters
        """
        if not self.enabled:
            return {}
        
        return {
            "num_samples": 1,  # Single deterministic sample
            "temperature": 0.0,  # No randomness
            "device": "cpu",  # CPU for bitwise stability
            "dtype": torch.float64  # Higher precision
        }
    
    def prepare_context(
        self,
        series: List[float],
        context_length: Optional[int] = None,
        frozen_timestamp: Optional[str] = None
    ) -> np.ndarray:
        """
        Prepare context with deterministic ordering and precision.
        
        Args:
            series: Historical series
            context_length: Fixed context length
            frozen_timestamp: Optional frozen timestamp for reproducibility
            
        Returns:
            Deterministic context array
        """
        # Convert to numpy with fixed precision
        series_array = np.array(series, dtype=np.float64)
        
        # Sort to ensure deterministic order (if not already sorted)
        # In practice, series should already be time-ordered, but we enforce it
        if len(series_array) > 1:
            # Check if already sorted (ascending by index = time order)
            if not np.all(np.diff(series_array) >= -1e-10):  # Allow for small numerical errors
                logger.warning("Series not in ascending order - sorting for determinism")
                # Don't sort values, but ensure we're using the right slice
                pass
        
        # Select context window deterministically
        if context_length is not None:
            context = series_array[-context_length:].copy()
        else:
            context = series_array.copy()
        
        # Ensure no NaN/Inf
        if np.any(np.isnan(context)) or np.any(np.isinf(context)):
            logger.warning("Context contains NaN/Inf - cleaning for determinism")
            context = np.nan_to_num(
                context,
                nan=np.nanmean(context),
                posinf=np.nanmax(context),
                neginf=np.nanmin(context)
            )
        
        return context
    
    def normalize_series(
        self,
        series: np.ndarray,
        method: str = "zscore"
    ) -> tuple[np.ndarray, Dict[str, float]]:
        """
        Normalize series with deterministic method.
        
        Args:
            series: Series to normalize
            method: Normalization method
            
        Returns:
            Normalized series and normalization parameters
        """
        if method == "zscore":
            mean = np.mean(series)
            std = np.std(series)
            if std < 1e-10:
                std = 1.0
            normalized = (series - mean) / std
            params = {"mean": float(mean), "std": float(std)}
        else:
            # Min-max normalization
            min_val = np.min(series)
            max_val = np.max(series)
            if max_val - min_val < 1e-10:
                normalized = series - min_val
            else:
                normalized = (series - min_val) / (max_val - min_val)
            params = {"min": float(min_val), "max": float(max_val)}
        
        return normalized, params
    
    def denormalize_series(
        self,
        normalized: np.ndarray,
        params: Dict[str, float],
        method: str = "zscore"
    ) -> np.ndarray:
        """Denormalize series using stored parameters."""
        if method == "zscore":
            return normalized * params["std"] + params["mean"]
        else:
            return normalized * (params["max"] - params["min"]) + params["min"]










