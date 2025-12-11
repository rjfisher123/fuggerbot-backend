"""
Backtest service for evaluating forecasts against actual outcomes.

This service encapsulates all backtesting logic, including:
- Loading forecasts
- Calculating evaluation metrics (MAE, MAPE, RMSE, directional accuracy, calibration)
- Creating BacktestResult domain objects
- Persisting results to database
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import numpy as np
import json

from models.backtesting import ForecastBacktester
from domain.forecast import Forecast
from domain.backtest import BacktestResult, BacktestMetrics
from services.forecast_service import get_forecast
from persistence.db import SessionLocal
from persistence.repositories_backtest import BacktestRepository
from core.logger import logger
from core.logger import log_backtest_result


class BacktestService:
    """Service for evaluating forecasts against actual outcomes."""
    
    def __init__(self):
        """Initialize backtest service."""
        self.backtester = ForecastBacktester()
        logger.info("BacktestService initialized")
    
    def evaluate_forecast(
        self,
        forecast: Forecast,
        realised: List[float]
    ) -> BacktestResult:
        """
        Evaluate a forecast against actual outcomes.
        
        Args:
            forecast: Forecast domain object to evaluate
            realised: Actual prices that occurred (list of floats)
        
        Returns:
            BacktestResult domain object with evaluation metrics
        
        Raises:
            ValueError: If forecast or realised data is invalid
        """
        if not realised or len(realised) == 0:
            raise ValueError("Realised prices list cannot be empty")
        
        logger.info(f"Evaluating forecast {forecast.forecast_id} with {len(realised)} actual prices")
        
        # Extract forecast data
        point_forecast = forecast.predicted_series.point_forecast
        lower_bound = forecast.predicted_series.lower_bound
        upper_bound = forecast.predicted_series.upper_bound
        
        if not point_forecast:
            raise ValueError("Forecast has no point predictions")
        
        # Align lengths (use minimum length)
        min_len = min(len(point_forecast), len(realised))
        point_forecast = point_forecast[:min_len]
        lower_bound = lower_bound[:min_len]
        upper_bound = upper_bound[:min_len]
        realised = realised[:min_len]
        
        # Calculate metrics using existing backtester
        mae = self.backtester.calculate_mae(point_forecast, realised)
        mape = self.backtester.calculate_mape(point_forecast, realised)
        directional = self.backtester.calculate_directional_accuracy(point_forecast, realised)
        calibration = self.backtester.calculate_calibration(lower_bound, upper_bound, realised)
        
        # Calculate RMSE (not in existing backtester, so we add it here)
        rmse = self._calculate_rmse(point_forecast, realised)
        
        # Create metrics
        metrics = BacktestMetrics(
            mae=mae,
            mape=mape,
            rmse=rmse,
            directional_accuracy=directional.get("accuracy", 0.0),
            calibration_coverage=calibration.get("coverage", 0.0),
            well_calibrated=calibration.get("well_calibrated", False),
            directional_correct=directional.get("correct"),
            directional_total=directional.get("total"),
            calibration_expected=calibration.get("expected_coverage"),
            calibration_error=calibration.get("calibration_error")
        )
        
        # Create backtest result
        result = BacktestResult(
            forecast_id=forecast.forecast_id,
            symbol=forecast.symbol,
            horizon=forecast.forecast_horizon,
            realised_series=realised,
            metrics=metrics,
            metadata={
                "evaluation_date": datetime.now().isoformat(),
                "forecast_created_at": forecast.created_at.isoformat(),
                "model_name": forecast.model_name,
            }
        )
        
        logger.info(
            f"Backtest {result.id} completed: "
            f"MAE=${mae:.2f}, MAPE={mape:.2f}%, "
            f"Directional={metrics.directional_accuracy:.1f}%"
        )
        
        # Save to database
        self._save_to_db(result)
        
        # Log backtest result
        log_backtest_result(
            backtest_id=result.id,
            forecast_id=forecast.forecast_id,
            symbol=forecast.symbol,
            mae=metrics.mae,
            mape=metrics.mape,
            directional_accuracy=metrics.directional_accuracy,
            rmse=metrics.rmse,
            calibration_coverage=metrics.calibration_coverage,
            well_calibrated=metrics.well_calibrated
        )
        
        return result
    
    def _save_to_db(self, result: BacktestResult) -> None:
        """
        Save backtest result to database.
        
        Args:
            result: BacktestResult domain object to save
        """
        try:
            with SessionLocal() as session:
                repo = BacktestRepository(session)
                
                # Convert metrics to dict
                metrics_dict = {
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
                
                repo.add_backtest(
                    backtest_id=result.id,
                    forecast_id=result.forecast_id,
                    symbol=result.symbol,
                    horizon=result.horizon,
                    realised_series=result.realised_series,
                    metrics=metrics_dict,
                    metadata=result.metadata
                )
                
                logger.info(f"Saved backtest {result.id} to database")
        except Exception as e:
            logger.error(f"Error saving backtest to database: {e}", exc_info=True)
            # Don't raise - allow service to continue even if DB save fails
    
    def evaluate_forecast_by_id(
        self,
        forecast_id: str,
        realised: List[float]
    ) -> BacktestResult:
        """
        Evaluate a forecast by ID against actual outcomes.
        
        Args:
            forecast_id: Forecast ID to evaluate
            realised: Actual prices that occurred
        
        Returns:
            BacktestResult domain object
        
        Raises:
            ValueError: If forecast not found or data is invalid
        """
        # Load forecast using service
        forecast = get_forecast(forecast_id)
        
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")
        
        return self.evaluate_forecast(forecast, realised)
    
    def _calculate_rmse(
        self,
        predicted: List[float],
        actual: List[float]
    ) -> float:
        """
        Calculate Root Mean Squared Error.
        
        Args:
            predicted: Predicted values
            actual: Actual values
        
        Returns:
            RMSE value
        """
        if len(predicted) != len(actual):
            min_len = min(len(predicted), len(actual))
            predicted = predicted[:min_len]
            actual = actual[:min_len]
        
        mse = np.mean((np.array(predicted) - np.array(actual)) ** 2)
        rmse = np.sqrt(mse)
        
        return float(rmse)
    
    def list_backtests(
        self,
        limit: int = 100,
        symbol: Optional[str] = None,
        forecast_id: Optional[str] = None
    ) -> List[BacktestResult]:
        """
        List backtest results from database.
        
        Args:
            limit: Maximum number of results to return
            symbol: Optional filter by symbol
            forecast_id: Optional filter by forecast ID
        
        Returns:
            List of BacktestResult domain objects
        """
        try:
            with SessionLocal() as session:
                repo = BacktestRepository(session)
                
                if forecast_id:
                    backtests = repo.get_by_forecast_id(forecast_id, limit=limit)
                elif symbol:
                    backtests = repo.list_by_symbol(symbol, limit=limit)
                else:
                    backtests = repo.list_recent(limit=limit)
                
                # Convert to domain objects
                results = []
                for bt in backtests:
                    try:
                        # Parse JSON fields
                        realised_series = json.loads(bt.realised_series)
                        metrics_dict = json.loads(bt.metrics)
                        backtest_metadata = json.loads(bt.backtest_metadata) if bt.backtest_metadata else {}
                        metadata = backtest_metadata
                        
                        # Create metrics object
                        metrics = BacktestMetrics(**metrics_dict)
                        
                        # Create result object
                        result = BacktestResult(
                            id=bt.backtest_id,
                            forecast_id=bt.forecast_id,
                            symbol=bt.symbol,
                            horizon=bt.horizon,
                            realised_series=realised_series,
                            metrics=metrics,
                            metadata=metadata,
                            created_at=bt.created_at
                        )
                        results.append(result)
                    except Exception as e:
                        logger.warning(f"Error converting backtest {bt.backtest_id} to domain object: {e}")
                        continue
                
                return results
        except Exception as e:
            logger.error(f"Error listing backtests: {e}", exc_info=True)
            return []
    
    def get_backtest(self, backtest_id: str) -> Optional[BacktestResult]:
        """
        Get a backtest result by ID.
        
        Args:
            backtest_id: Backtest ID
        
        Returns:
            BacktestResult domain object or None if not found
        """
        try:
            with SessionLocal() as session:
                repo = BacktestRepository(session)
                
                bt = repo.get_by_id(backtest_id)
                if not bt:
                    return None
                
                # Parse JSON fields
                realised_series = json.loads(bt.realised_series)
                metrics_dict = json.loads(bt.metrics)
                metadata = json.loads(bt.backtest_metadata) if bt.backtest_metadata else {}
                
                # Create metrics object
                metrics = BacktestMetrics(**metrics_dict)
                
                # Create result object
                result = BacktestResult(
                    id=bt.backtest_id,
                    forecast_id=bt.forecast_id,
                    symbol=bt.symbol,
                    horizon=bt.horizon,
                    realised_series=realised_series,
                    metrics=metrics,
                    metadata=metadata,
                    created_at=bt.created_at
                )
                
                return result
        except Exception as e:
            logger.error(f"Error getting backtest {backtest_id}: {e}", exc_info=True)
            return None


# Global service instance
_backtest_service: Optional[BacktestService] = None


def get_backtest_service() -> BacktestService:
    """
    Get or create the global backtest service instance.
    
    Returns:
        BacktestService instance
    """
    global _backtest_service
    if _backtest_service is None:
        _backtest_service = BacktestService()
    return _backtest_service


# Convenience functions for direct use
def evaluate_forecast(
    forecast: Forecast,
    realised: List[float]
) -> BacktestResult:
    """
    Evaluate a forecast (convenience function).
    
    Args:
        forecast: Forecast domain object
        realised: Actual prices that occurred
    
    Returns:
        BacktestResult domain object
    """
    service = get_backtest_service()
    return service.evaluate_forecast(forecast, realised)


def evaluate_forecast_by_id(
    forecast_id: str,
    realised: List[float]
) -> BacktestResult:
    """
    Evaluate a forecast by ID (convenience function).
    
    Args:
        forecast_id: Forecast ID
        realised: Actual prices that occurred
    
    Returns:
        BacktestResult domain object
    """
    service = get_backtest_service()
    return service.evaluate_forecast_by_id(forecast_id, realised)

