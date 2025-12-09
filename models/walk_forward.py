"""
Walk-Forward Optimization for Strategy Parameters.

Implements rolling and expanding window optimization.
"""
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """Performs walk-forward optimization on strategy parameters."""
    
    def __init__(
        self,
        optimization_window_days: int = 90,
        test_window_days: int = 30,
        step_size_days: int = 7
    ):
        """
        Initialize walk-forward optimizer.
        
        Args:
            optimization_window_days: Days in optimization window
            test_window_days: Days in test/out-of-sample window
            step_size_days: Days to step forward each iteration
        """
        self.optimization_window_days = optimization_window_days
        self.test_window_days = test_window_days
        self.step_size_days = step_size_days
    
    def rolling_window_optimization(
        self,
        historical_data: List[Dict[str, Any]],
        parameter_ranges: Dict[str, List[float]],
        objective_function: callable
    ) -> List[Dict[str, Any]]:
        """
        Perform rolling window optimization.
        
        Args:
            historical_data: List of historical forecast/trade data
            parameter_ranges: Dict of parameter -> list of values to test
            objective_function: Function to optimize (returns score)
            
        Returns:
            List of optimization results for each window
        """
        results = []
        
        # Sort data by date
        sorted_data = sorted(historical_data, key=lambda x: x.get("timestamp", ""))
        
        if len(sorted_data) < self.optimization_window_days + self.test_window_days:
            logger.warning("Insufficient data for walk-forward optimization")
            return results
        
        # Rolling windows
        start_idx = 0
        while start_idx + self.optimization_window_days + self.test_window_days <= len(sorted_data):
            # Split into optimization and test sets
            opt_data = sorted_data[start_idx:start_idx + self.optimization_window_days]
            test_data = sorted_data[
                start_idx + self.optimization_window_days:
                start_idx + self.optimization_window_days + self.test_window_days
            ]
            
            # Optimize on optimization set
            best_params, best_score = self._optimize_parameters(
                opt_data, parameter_ranges, objective_function
            )
            
            # Test on out-of-sample set
            test_score = objective_function(test_data, best_params)
            
            results.append({
                "window_start": start_idx,
                "window_end": start_idx + self.optimization_window_days + self.test_window_days,
                "best_parameters": best_params,
                "optimization_score": best_score,
                "test_score": test_score,
                "overfitting_ratio": best_score / (test_score + 1e-10)
            })
            
            # Step forward
            start_idx += self.step_size_days
        
        return results
    
    def expanding_window_optimization(
        self,
        historical_data: List[Dict[str, Any]],
        parameter_ranges: Dict[str, List[float]],
        objective_function: callable,
        initial_window_days: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Perform expanding window optimization.
        
        Args:
            historical_data: List of historical forecast/trade data
            parameter_ranges: Dict of parameter -> list of values to test
            objective_function: Function to optimize
            initial_window_days: Initial window size
            
        Returns:
            List of optimization results
        """
        results = []
        
        sorted_data = sorted(historical_data, key=lambda x: x.get("timestamp", ""))
        
        if len(sorted_data) < initial_window_days + self.test_window_days:
            logger.warning("Insufficient data for expanding window optimization")
            return results
        
        # Expanding windows
        window_size = initial_window_days
        start_idx = 0
        
        while start_idx + window_size + self.test_window_days <= len(sorted_data):
            # Split into optimization and test sets
            opt_data = sorted_data[start_idx:start_idx + window_size]
            test_data = sorted_data[
                start_idx + window_size:
                start_idx + window_size + self.test_window_days
            ]
            
            # Optimize
            best_params, best_score = self._optimize_parameters(
                opt_data, parameter_ranges, objective_function
            )
            
            # Test
            test_score = objective_function(test_data, best_params)
            
            results.append({
                "window_size": window_size,
                "window_start": start_idx,
                "window_end": start_idx + window_size + self.test_window_days,
                "best_parameters": best_params,
                "optimization_score": best_score,
                "test_score": test_score,
                "overfitting_ratio": best_score / (test_score + 1e-10)
            })
            
            # Expand window
            window_size += self.step_size_days
            start_idx += self.step_size_days
        
        return results
    
    def _optimize_parameters(
        self,
        data: List[Dict[str, Any]],
        parameter_ranges: Dict[str, List[float]],
        objective_function: callable
    ) -> Tuple[Dict[str, float], float]:
        """
        Optimize parameters using grid search.
        
        Args:
            data: Optimization data
            parameter_ranges: Parameter ranges to test
            objective_function: Objective function
            
        Returns:
            Tuple of (best_parameters, best_score)
        """
        best_params = {}
        best_score = float('-inf')
        
        # Generate parameter combinations (simplified grid search)
        param_names = list(parameter_ranges.keys())
        param_values = [parameter_ranges[name] for name in param_names]
        
        # Iterate through combinations
        from itertools import product
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            score = objective_function(data, params)
            
            if score > best_score:
                best_score = score
                best_params = params
        
        return best_params, best_score
    
    def dynamic_threshold_learning(
        self,
        historical_data: List[Dict[str, Any]],
        metric_name: str = "fqs_score"
    ) -> Dict[str, float]:
        """
        Learn optimal thresholds dynamically from historical data.
        
        Args:
            historical_data: Historical forecast data
            metric_name: Metric to learn thresholds for
            
        Returns:
            Dict with learned thresholds
        """
        if not historical_data:
            return {}
        
        # Extract metric values and outcomes
        metric_values = []
        outcomes = []  # 1 = profitable, 0 = not profitable
        
        for data_point in historical_data:
            metric_value = data_point.get(metric_name, 0)
            # Would need actual trade outcomes here
            # For now, use expected return as proxy
            expected_return = data_point.get("recommendation", {}).get("expected_return_pct", 0)
            outcome = 1 if expected_return > 0 else 0
            
            metric_values.append(metric_value)
            outcomes.append(outcome)
        
        if not metric_values:
            return {}
        
        # Find optimal threshold using ROC curve approach
        sorted_pairs = sorted(zip(metric_values, outcomes), key=lambda x: x[0])
        
        best_threshold = 0.5
        best_accuracy = 0.0
        
        for i in range(len(sorted_pairs)):
            threshold = sorted_pairs[i][0]
            
            # Calculate accuracy at this threshold
            true_positives = sum(1 for m, o in sorted_pairs if m >= threshold and o == 1)
            true_negatives = sum(1 for m, o in sorted_pairs if m < threshold and o == 0)
            accuracy = (true_positives + true_negatives) / len(sorted_pairs)
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold
        
        return {
            f"{metric_name}_threshold": best_threshold,
            "accuracy": best_accuracy
        }




