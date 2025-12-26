"""
Signal Decay Modeling and Visualization.

Estimates forecast half-life and signal persistence.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from models.forecast_metadata import ForecastMetadata

logger = logging.getLogger(__name__)


class SignalDecayModel:
    """Models signal decay and persistence."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize signal decay model.
        
        Args:
            storage_dir: Directory with forecast snapshots
        """
        self.metadata = ForecastMetadata(storage_dir)
    
    def calculate_half_life(
        self,
        symbol: str,
        forecast_history: List[Dict[str, Any]],
        stability_threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Calculate forecast half-life based on stability.
        
        Args:
            symbol: Trading symbol
            forecast_history: List of historical forecasts with timestamps
            stability_threshold: Threshold for considering forecast stable
            
        Returns:
            Dict with half-life estimate
        """
        if len(forecast_history) < 2:
            return {
                "half_life_hours": None,
                "reason": "Insufficient forecast history"
            }
        
        # Extract expected returns over time
        expected_returns = []
        timestamps = []
        
        for forecast in forecast_history:
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            timestamp_str = forecast.get("timestamp", "")
            
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    expected_returns.append(expected_return)
                    timestamps.append(timestamp)
                except:
                    continue
        
        if len(expected_returns) < 2:
            return {
                "half_life_hours": None,
                "reason": "Insufficient valid timestamps"
            }
        
        # Calculate variance in expected returns
        return_variance = np.var(expected_returns)
        return_std = np.std(expected_returns)
        mean_return = np.mean(np.abs(expected_returns))
        
        # Estimate half-life based on stability
        # More stable forecasts (lower variance) have longer half-life
        if mean_return > 0:
            stability_ratio = 1.0 - min(1.0, return_std / (mean_return + 1e-10))
        else:
            stability_ratio = 0.5
        
        # Half-life in hours (base 24 hours, adjusted by stability)
        # Very stable: 48-72 hours
        # Moderate: 24-48 hours
        # Unstable: 6-24 hours
        base_half_life = 24.0
        half_life_hours = base_half_life * (1.0 + stability_ratio * 2.0)
        
        # Clamp to reasonable range
        half_life_hours = max(6.0, min(72.0, half_life_hours))
        
        return {
            "half_life_hours": float(half_life_hours),
            "stability_ratio": float(stability_ratio),
            "return_variance": float(return_variance),
            "mean_return": float(mean_return),
            "forecast_count": len(expected_returns)
        }
    
    def calculate_signal_persistence(
        self,
        symbol: str,
        forecast_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate signal persistence score.
        
        Args:
            symbol: Trading symbol
            forecast_history: List of historical forecasts
            
        Returns:
            Dict with persistence metrics
        """
        if len(forecast_history) < 2:
            return {
                "persistence_score": 0.5,
                "reason": "Insufficient history"
            }
        
        # Extract actions and expected returns
        actions = []
        expected_returns = []
        
        for forecast in forecast_history:
            rec = forecast.get("recommendation", {})
            actions.append(rec.get("action", "HOLD"))
            expected_returns.append(rec.get("expected_return_pct", 0))
        
        # Action consistency
        action_consistency = sum(1 for i in range(len(actions)-1) if actions[i] == actions[i+1]) / max(1, len(actions)-1)
        
        # Return stability
        return_stability = 1.0 - min(1.0, np.std(expected_returns) / (np.mean(np.abs(expected_returns)) + 1e-10))
        
        # Combined persistence score
        persistence_score = (action_consistency * 0.6 + return_stability * 0.4)
        
        return {
            "persistence_score": float(persistence_score),
            "action_consistency": float(action_consistency),
            "return_stability": float(return_stability),
            "signal_stable": persistence_score > 0.7
        }
    
    def generate_decay_heatmap_data(
        self,
        symbols: List[str],
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Generate data for signal decay heatmap.
        
        Args:
            symbols: List of symbols to analyze
            days_back: Number of days to look back
            
        Returns:
            Dict with heatmap data
        """
        heatmap_data = {}
        
        for symbol in symbols:
            # Load recent forecasts for this symbol
            # In production, would query forecast snapshots
            # For now, return structure
            heatmap_data[symbol] = {
                "expected_return_trend": [],  # Would populate from actual data
                "confidence_trend": [],
                "fqs_trend": [],
                "half_life_hours": None,
                "persistence_score": None
            }
        
        return heatmap_data











