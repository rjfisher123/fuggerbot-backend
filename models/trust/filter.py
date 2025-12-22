"""Trust filter for evaluating and filtering forecasts."""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .schemas import (
    TrustEvaluation,
    TrustMetrics,
    TrustFilterConfig,
    BatchTrustEvaluation
)
from .metrics import TrustMetricsCalculator
from ..tsfm.schemas import ForecastOutput, ForecastInput

logger = logging.getLogger(__name__)


class TrustFilter:
    """
    Trust filter for evaluating forecast reliability and filtering low-confidence forecasts.
    
    This filter evaluates forecasts based on multiple criteria:
    - Uncertainty (tighter bounds = higher trust)
    - Consistency (forecast patterns make sense)
    - Data quality (input data is clean and sufficient)
    - Historical accuracy (if available)
    - Market regime (volatility conditions)
    """
    
    def __init__(self, config: Optional[TrustFilterConfig] = None):
        """
        Initialize trust filter.
        
        Args:
            config: TrustFilterConfig with thresholds and weights. If None, uses defaults.
        """
        self.config = config or TrustFilterConfig()
        self.metrics_calculator = TrustMetricsCalculator()
        
        # Optional: Store historical accuracy data
        self.accuracy_history: Dict[str, float] = {}
        
        logger.info(
            f"TrustFilter initialized with min_trust_score={self.config.min_trust_score}"
        )
    
    def update_accuracy_history(self, symbol: str, accuracy: float) -> None:
        """
        Update historical accuracy for a symbol.
        
        Args:
            symbol: Symbol identifier
            accuracy: Accuracy score (0-1)
        """
        self.accuracy_history[symbol] = accuracy
        logger.debug(f"Updated accuracy history for {symbol}: {accuracy:.3f}")
    
    def evaluate(
        self,
        forecast: ForecastOutput,
        input_data: Optional[ForecastInput] = None,
        symbol: Optional[str] = None,
        current_volatility: Optional[float] = None,
        historical_volatility: Optional[float] = None
    ) -> TrustEvaluation:
        """
        Evaluate trustworthiness of a single forecast.
        
        Args:
            forecast: ForecastOutput to evaluate
            input_data: Original ForecastInput (for data quality assessment)
            symbol: Symbol identifier (for historical accuracy lookup)
            current_volatility: Current market volatility measure
            historical_volatility: Historical average volatility
            
        Returns:
            TrustEvaluation with metrics and pass/fail decision
        """
        # Calculate individual metrics
        uncertainty_score = self.metrics_calculator.calculate_uncertainty_score(forecast)
        
        historical_series = input_data.series if input_data else None
        consistency_score = self.metrics_calculator.calculate_consistency_score(
            forecast,
            historical_series
        )
        
        data_quality_score = self.metrics_calculator.calculate_data_quality_score(
            input_data,
            historical_series
        )
        
        historical_accuracy = self.metrics_calculator.calculate_historical_accuracy(
            symbol,
            self.accuracy_history
        )
        
        market_regime_score = self.metrics_calculator.calculate_market_regime_score(
            current_volatility,
            historical_volatility
        )
        
        # Calculate overall trust score
        overall_trust_score = self.metrics_calculator.calculate_overall_trust_score(
            uncertainty_score=uncertainty_score,
            consistency_score=consistency_score,
            data_quality_score=data_quality_score,
            historical_accuracy=historical_accuracy,
            market_regime_score=market_regime_score,
            weights=self.config.weights
        )
        
        # Classify confidence level
        confidence_level = self.metrics_calculator.classify_confidence_level(
            overall_trust_score
        )
        
        # Collect rejection reasons
        rejection_reasons = []
        
        # Check thresholds
        if overall_trust_score < self.config.min_trust_score:
            rejection_reasons.append(
                f"Overall trust score ({overall_trust_score:.3f}) below threshold "
                f"({self.config.min_trust_score:.3f})"
            )
        
        if uncertainty_score < self.config.min_uncertainty_score:
            rejection_reasons.append(
                f"Uncertainty score ({uncertainty_score:.3f}) below threshold "
                f"({self.config.min_uncertainty_score:.3f})"
            )
        
        if consistency_score < self.config.min_consistency_score:
            rejection_reasons.append(
                f"Consistency score ({consistency_score:.3f}) below threshold "
                f"({self.config.min_consistency_score:.3f})"
            )
        
        if data_quality_score < self.config.min_data_quality_score:
            rejection_reasons.append(
                f"Data quality score ({data_quality_score:.3f}) below threshold "
                f"({self.config.min_data_quality_score:.3f})"
            )
        
        if self.config.require_historical_accuracy:
            if historical_accuracy is None:
                rejection_reasons.append("Historical accuracy required but not available")
            elif historical_accuracy < (self.config.min_historical_accuracy or 0.7):
                rejection_reasons.append(
                    f"Historical accuracy ({historical_accuracy:.3f}) below threshold "
                    f"({self.config.min_historical_accuracy:.3f})"
                )
        
        # Check uncertainty ratio
        import numpy as np
        point_forecast = np.array(forecast.point_forecast)
        uncertainty_ranges = np.array(forecast.upper_bound) - np.array(forecast.lower_bound)
        point_abs = np.abs(point_forecast)
        point_abs = np.where(point_abs < 1e-10, 1.0, point_abs)
        max_ratio = np.max(uncertainty_ranges / point_abs)
        
        if max_ratio > self.config.max_uncertainty_ratio:
            rejection_reasons.append(
                f"Uncertainty ratio ({max_ratio:.3f}) exceeds maximum "
                f"({self.config.max_uncertainty_ratio:.3f})"
            )
        
        # Determine if forecast passes filter
        if self.config.enable_strict_mode:
            # In strict mode, all thresholds must pass
            is_trusted = len(rejection_reasons) == 0
        else:
            # In normal mode, overall score is primary
            is_trusted = overall_trust_score >= self.config.min_trust_score
        
        # Build metrics
        metrics = TrustMetrics(
            uncertainty_score=uncertainty_score,
            consistency_score=consistency_score,
            data_quality_score=data_quality_score,
            historical_accuracy=historical_accuracy,
            market_regime_score=market_regime_score,
            overall_trust_score=overall_trust_score,
            confidence_level=confidence_level,
            rejection_reasons=rejection_reasons if not is_trusted else [],
            metadata={
                "max_uncertainty_ratio": float(max_ratio),
                "config_min_trust_score": self.config.min_trust_score
            }
        )
        
        # Build evaluation
        evaluation = TrustEvaluation(
            forecast=forecast,
            metrics=metrics,
            is_trusted=is_trusted,
            evaluation_timestamp=datetime.now(),
            evaluation_id=str(uuid.uuid4())[:8]
        )
        
        logger.info(
            f"Trust evaluation: score={overall_trust_score:.3f}, "
            f"trusted={is_trusted}, confidence={confidence_level}"
        )
        
        return evaluation
    
    def evaluate_batch(
        self,
        forecasts: List[ForecastOutput],
        input_data_list: Optional[List[ForecastInput]] = None,
        symbols: Optional[List[str]] = None,
        current_volatilities: Optional[List[float]] = None,
        historical_volatilities: Optional[List[float]] = None
    ) -> BatchTrustEvaluation:
        """
        Evaluate trustworthiness of multiple forecasts in batch.
        
        Args:
            forecasts: List of ForecastOutputs to evaluate
            input_data_list: Optional list of original ForecastInputs
            symbols: Optional list of symbol identifiers
            current_volatilities: Optional list of current volatility measures
            historical_volatilities: Optional list of historical volatility measures
            
        Returns:
            BatchTrustEvaluation with results for all forecasts
        """
        evaluations = []
        
        for i, forecast in enumerate(forecasts):
            input_data = input_data_list[i] if input_data_list and i < len(input_data_list) else None
            symbol = symbols[i] if symbols and i < len(symbols) else None
            current_vol = current_volatilities[i] if current_volatilities and i < len(current_volatilities) else None
            hist_vol = historical_volatilities[i] if historical_volatilities and i < len(historical_volatilities) else None
            
            evaluation = self.evaluate(
                forecast=forecast,
                input_data=input_data,
                symbol=symbol,
                current_volatility=current_vol,
                historical_volatility=hist_vol
            )
            evaluations.append(evaluation)
        
        # Calculate batch statistics
        trusted_count = sum(1 for e in evaluations if e.is_trusted)
        rejected_count = len(evaluations) - trusted_count
        average_trust_score = (
            sum(e.metrics.overall_trust_score for e in evaluations) / len(evaluations)
            if evaluations else 0.0
        )
        
        return BatchTrustEvaluation(
            evaluations=evaluations,
            trusted_count=trusted_count,
            rejected_count=rejected_count,
            average_trust_score=average_trust_score,
            evaluation_timestamp=datetime.now()
        )
    
    def filter_trusted(
        self,
        forecasts: List[ForecastOutput],
        input_data_list: Optional[List[ForecastInput]] = None,
        symbols: Optional[List[str]] = None,
        current_volatilities: Optional[List[float]] = None,
        historical_volatilities: Optional[List[float]] = None
    ) -> tuple[List[ForecastOutput], List[TrustEvaluation]]:
        """
        Filter forecasts, returning only those that pass the trust filter.
        
        Args:
            forecasts: List of ForecastOutputs to filter
            input_data_list: Optional list of original ForecastInputs
            symbols: Optional list of symbol identifiers
            current_volatilities: Optional list of current volatility measures
            historical_volatilities: Optional list of historical volatility measures
            
        Returns:
            Tuple of (trusted_forecasts, all_evaluations)
        """
        batch_eval = self.evaluate_batch(
            forecasts=forecasts,
            input_data_list=input_data_list,
            symbols=symbols,
            current_volatilities=current_volatilities,
            historical_volatilities=historical_volatilities
        )
        
        trusted_forecasts = [
            eval.forecast for eval in batch_eval.evaluations if eval.is_trusted
        ]
        
        logger.info(
            f"Filtered {len(forecasts)} forecasts: "
            f"{len(trusted_forecasts)} trusted, {batch_eval.rejected_count} rejected"
        )
        
        return trusted_forecasts, batch_eval.evaluations











