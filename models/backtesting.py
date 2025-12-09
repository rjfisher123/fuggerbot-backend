"""
Forecast backtesting and performance evaluation.

Evaluates forecast accuracy using historical data.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

from models.forecast_metadata import ForecastMetadata


class ForecastBacktester:
    """Backtests forecasts against actual outcomes."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize backtester.
        
        Args:
            storage_dir: Directory for forecast snapshots
        """
        self.metadata = ForecastMetadata(storage_dir)
    
    def calculate_mae(
        self,
        predicted: List[float],
        actual: List[float]
    ) -> float:
        """
        Calculate Mean Absolute Error.
        
        Args:
            predicted: Predicted values
            actual: Actual values
            
        Returns:
            MAE value
        """
        if len(predicted) != len(actual):
            min_len = min(len(predicted), len(actual))
            predicted = predicted[:min_len]
            actual = actual[:min_len]
        
        return float(np.mean(np.abs(np.array(predicted) - np.array(actual))))
    
    def calculate_mape(
        self,
        predicted: List[float],
        actual: List[float]
    ) -> float:
        """
        Calculate Mean Absolute Percentage Error.
        
        Args:
            predicted: Predicted values
            actual: Actual values
            
        Returns:
            MAPE value (as percentage)
        """
        if len(predicted) != len(actual):
            min_len = min(len(predicted), len(actual))
            predicted = predicted[:min_len]
            actual = actual[:min_len]
        
        actual_array = np.array(actual)
        predicted_array = np.array(predicted)
        
        # Avoid division by zero
        mask = actual_array != 0
        if not np.any(mask):
            return float('inf')
        
        mape = np.mean(np.abs((actual_array[mask] - predicted_array[mask]) / actual_array[mask])) * 100
        return float(mape)
    
    def calculate_directional_accuracy(
        self,
        predicted: List[float],
        actual: List[float]
    ) -> Dict[str, float]:
        """
        Calculate directional accuracy (did forecast predict direction correctly?).
        
        Args:
            predicted: Predicted values
            actual: Actual values
            
        Returns:
            Dict with accuracy metrics
        """
        if len(predicted) < 2 or len(actual) < 2:
            return {"accuracy": 0.0, "correct": 0, "total": 0}
        
        # Calculate direction changes
        pred_changes = np.diff(predicted)
        actual_changes = np.diff(actual)
        
        # Determine direction (up/down/flat)
        pred_direction = np.sign(pred_changes)
        actual_direction = np.sign(actual_changes)
        
        # Count matches
        matches = np.sum(pred_direction == actual_direction)
        total = len(pred_direction)
        
        accuracy = (matches / total) * 100 if total > 0 else 0.0
        
        return {
            "accuracy": float(accuracy),
            "correct": int(matches),
            "total": int(total)
        }
    
    def calculate_calibration(
        self,
        predicted_lower: List[float],
        predicted_upper: List[float],
        actual: List[float],
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculate forecast calibration (how often actual falls within predicted bounds).
        
        Args:
            predicted_lower: Lower bound predictions
            predicted_upper: Upper bound predictions
            actual: Actual values
            confidence_level: Expected confidence level (default 0.95 for 95% interval)
            
        Returns:
            Dict with calibration metrics
        """
        if len(predicted_lower) != len(predicted_upper) or len(predicted_lower) != len(actual):
            min_len = min(len(predicted_lower), len(predicted_upper), len(actual))
            predicted_lower = predicted_lower[:min_len]
            predicted_upper = predicted_upper[:min_len]
            actual = actual[:min_len]
        
        actual_array = np.array(actual)
        lower_array = np.array(predicted_lower)
        upper_array = np.array(predicted_upper)
        
        # Count how many actual values fall within bounds
        within_bounds = np.sum((actual_array >= lower_array) & (actual_array <= upper_array))
        total = len(actual_array)
        
        coverage = (within_bounds / total) * 100 if total > 0 else 0.0
        expected_coverage = confidence_level * 100
        
        calibration_error = abs(coverage - expected_coverage)
        
        return {
            "coverage": float(coverage),
            "expected_coverage": float(expected_coverage),
            "calibration_error": float(calibration_error),
            "within_bounds": int(within_bounds),
            "total": int(total),
            "well_calibrated": calibration_error < 5.0  # Within 5% of expected
        }
    
    def evaluate_forecast(
        self,
        forecast_id: str,
        actual_prices: List[float],
        actual_dates: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a forecast against actual outcomes.
        
        Args:
            forecast_id: Forecast ID to evaluate
            actual_prices: Actual prices that occurred
            actual_dates: Optional dates for actual prices
            
        Returns:
            Dict with evaluation metrics
        """
        # Load forecast snapshot
        snapshot = self.metadata.load_forecast_snapshot(forecast_id)
        if not snapshot:
            return {"error": f"Forecast {forecast_id} not found"}
        
        forecast_data = snapshot.get("forecast", {})
        point_forecast = forecast_data.get("point_forecast", [])
        lower_bound = forecast_data.get("lower_bound", [])
        upper_bound = forecast_data.get("upper_bound", [])
        
        if not point_forecast:
            return {"error": "Forecast data not available in snapshot"}
        
        # Calculate metrics
        mae = self.calculate_mae(point_forecast, actual_prices)
        mape = self.calculate_mape(point_forecast, actual_prices)
        directional = self.calculate_directional_accuracy(point_forecast, actual_prices)
        calibration = self.calculate_calibration(lower_bound, upper_bound, actual_prices)
        
        return {
            "forecast_id": forecast_id,
            "symbol": snapshot.get("symbol"),
            "evaluation_date": datetime.now().isoformat(),
            "metrics": {
                "mae": mae,
                "mape": mape,
                "directional_accuracy": directional,
                "calibration": calibration
            },
            "summary": {
                "mean_absolute_error": f"${mae:.2f}",
                "mean_absolute_percentage_error": f"{mape:.2f}%",
                "directional_accuracy": f"{directional['accuracy']:.1f}%",
                "calibration_coverage": f"{calibration['coverage']:.1f}% (expected {calibration['expected_coverage']:.1f}%)",
                "well_calibrated": calibration['well_calibrated']
            }
        }

