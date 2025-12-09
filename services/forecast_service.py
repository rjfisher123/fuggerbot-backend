"""
Forecast service for creating and managing forecasts.

This service encapsulates all forecast generation logic, including:
- Forecast generation using Chronos
- Trust evaluation
- Quality scoring (FQS)
- Regime classification
- FRS calculation
- Cross-asset coherence
- Forecast metadata management
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from models.forecast_trader import ForecastTrader
from models.trust.schemas import TrustFilterConfig
from models.forecast_metadata import ForecastMetadata
from models.forecast_quality import ForecastQualityScorer
from models.regime_classifier import RegimeClassifier
from models.frs_engine import FRSEngine
from models.cross_asset_coherence import CrossAssetCoherence
from models.tsfm.inference import ChronosInferenceEngine
from domain.forecast import Forecast
from core.logger import logger
from core.logging import log_forecast_creation


class ForecastService:
    """Service for creating and managing forecasts."""
    
    def __init__(self):
        """Initialize forecast service."""
        self.metadata_manager = ForecastMetadata()
        self.quality_scorer = ForecastQualityScorer()
        self.regime_classifier = RegimeClassifier()
        self.frs_engine = FRSEngine()
        self.coherence_engine = CrossAssetCoherence()
        logger.info("ForecastService initialized")
    
    def create_forecast(
        self,
        symbol: str,
        historical_prices: List[float],
        forecast_horizon: int = 30,
        options: Optional[Dict[str, Any]] = None
    ) -> Forecast:
        """
        Create a complete forecast with all analysis.
        
        Args:
            symbol: Trading symbol
            historical_prices: Historical price series
            forecast_horizon: Number of days to forecast
            options: Optional dict with:
                - context_length: Context window size (None = use all)
                - historical_period: Period string (e.g., "1y")
                - strict_mode: Enable strict trust mode
                - min_trust_score: Minimum trust score threshold
                - deterministic_mode: Use deterministic inference
                - model_name: Model name to use
        
        Returns:
            Forecast domain object with all analysis
        """
        if options is None:
            options = {}
        
        # Extract options
        context_length = options.get("context_length")
        historical_period = options.get("historical_period", "1y")
        strict_mode = options.get("strict_mode", False)
        min_trust_score = options.get("min_trust_score", 0.6)
        deterministic_mode = options.get("deterministic_mode", True)
        model_name = options.get("model_name", "amazon/chronos-t5-tiny")
        
        # Build parameters dict for forecast ID generation
        parameters = {
            "context_length": context_length,
            "historical_period": historical_period,
            "strict_mode": strict_mode,
            "min_trust_score": min_trust_score,
            "forecast_horizon": forecast_horizon
        }
        
        # Generate forecast ID
        forecast_id = self.metadata_manager.generate_forecast_id(symbol, parameters)
        
        logger.info(f"Creating forecast {forecast_id} for {symbol}")
        
        # Create forecast trader
        forecast_trader = ForecastTrader(model_name=model_name)
        
        # Configure trust filter
        trust_config = TrustFilterConfig(
            min_trust_score=min_trust_score,
            enable_strict_mode=strict_mode
        )
        forecast_trader.trust_filter.config = trust_config
        
        # Use deterministic engine if enabled
        if deterministic_mode:
            engine = ChronosInferenceEngine(deterministic_mode=True)
            forecast_trader.forecast_engine = engine
        
        # Generate forecast and evaluate trust
        result = forecast_trader.analyze_symbol(
            symbol=symbol,
            historical_prices=historical_prices,
            forecast_horizon=forecast_horizon,
            context_length=context_length
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Forecast generation failed for {symbol}: {error_msg}")
            raise ValueError(f"Forecast generation failed: {error_msg}")
        
        forecast_output = result["forecast"]
        trust_eval = result["trust_evaluation"]
        recommendation = result["recommendation"]
        
        # Calculate FQS
        fqs = self.quality_scorer.calculate_fqs(forecast_output, trust_eval, historical_prices)
        
        # Classify regime
        regime = self.regime_classifier.classify_regime(forecast_output, trust_eval, historical_prices)
        
        # Calculate FRS (FuggerBot Reliability Score)
        frs = self.frs_engine.calculate_frs(
            forecast=forecast_output,
            trust_eval=trust_eval,
            fqs=fqs,
            regime=regime,
            historical_series=historical_prices
        )
        
        # Check cross-asset coherence
        coherence = self.coherence_engine.check_coherence(
            symbol=symbol,
            symbol_regime=regime["regime"],
            symbol_action=recommendation.get("action", "HOLD"),
            symbol_expected_return=recommendation.get("expected_return_pct", 0)
        )
        
        # Save snapshot
        snapshot_path = self.metadata_manager.save_forecast_snapshot(
            forecast_id, symbol, parameters, result
        )
        
        logger.info(f"Forecast {forecast_id} created and saved to {snapshot_path}")
        
        # Create domain model
        forecast = Forecast(
            forecast_id=forecast_id,
            symbol=symbol,
            created_at=datetime.now(),
            forecast_horizon=forecast_horizon,
            model_name=model_name,
            params=parameters,
            predicted_series=forecast_output,
            trust_score=trust_eval.metrics.overall_trust_score,
            trust_evaluation=trust_eval,
            fqs_score=fqs['fqs_score'],
            regime=regime,
            frs_score=frs['frs_score'],
            coherence=coherence,
            recommendation=recommendation,
            metadata={
                "snapshot_path": str(snapshot_path),
                "inference_time_ms": forecast_output.inference_time_ms,
                "fqs_interpretation": fqs.get('interpretation'),
                "frs_reliability_level": frs.get('reliability_level'),
                "frs_is_reliable": frs.get('is_reliable'),
            }
        )
        
        return forecast
    
    def get_forecast(self, forecast_id: str) -> Optional[Forecast]:
        """
        Retrieve a forecast by ID.
        
        Args:
            forecast_id: Forecast ID to retrieve
        
        Returns:
            Forecast domain object or None if not found
        """
        snapshot = self.metadata_manager.load_forecast_snapshot(forecast_id)
        
        if not snapshot:
            logger.warning(f"Forecast {forecast_id} not found")
            return None
        
        # Reconstruct Forecast from snapshot
        # Note: This is a simplified reconstruction - full reconstruction would
        # require deserializing ForecastOutput and TrustEvaluation objects
        try:
            from models.tsfm.schemas import ForecastOutput
            from models.trust.schemas import TrustEvaluation, TrustMetrics
            
            # Reconstruct forecast output
            forecast_data = snapshot.get("forecast", {})
            forecast_output = ForecastOutput(
                point_forecast=forecast_data.get("point_forecast", []),
                lower_bound=forecast_data.get("lower_bound", []),
                upper_bound=forecast_data.get("upper_bound", []),
                forecast_horizon=forecast_data.get("forecast_horizon", 30),
                model_name=snapshot.get("model_name", "amazon/chronos-t5-tiny"),
                inference_time_ms=snapshot.get("inference_time_ms", 0.0)
            )
            
            # Reconstruct trust evaluation (simplified)
            trust_data = snapshot.get("trust_evaluation", {})
            trust_metrics = TrustMetrics(
                overall_trust_score=trust_data.get("overall_trust_score", 0.0),
                confidence_level=trust_data.get("confidence_level", "low"),
                uncertainty_score=0.0,  # Not stored in snapshot
                consistency_score=0.0,
                data_quality_score=0.0
            )
            trust_eval = TrustEvaluation(
                is_trusted=trust_data.get("is_trusted", False),
                metrics=trust_metrics
            )
            
            forecast = Forecast(
                forecast_id=snapshot.get("forecast_id", forecast_id),
                symbol=snapshot.get("symbol", "UNKNOWN"),
                created_at=datetime.fromisoformat(snapshot.get("timestamp", datetime.now().isoformat())),
                forecast_horizon=snapshot.get("parameters", {}).get("forecast_horizon", 30),
                model_name=snapshot.get("model_name", "amazon/chronos-t5-tiny"),
                params=snapshot.get("parameters", {}),
                predicted_series=forecast_output,
                trust_score=trust_data.get("overall_trust_score", 0.0),
                trust_evaluation=trust_eval,
                recommendation=snapshot.get("recommendation", {})
            )
            
            return forecast
            
        except Exception as e:
            logger.error(f"Error reconstructing forecast {forecast_id}: {e}", exc_info=True)
            return None


# Global service instance
_forecast_service: Optional[ForecastService] = None


def get_forecast_service() -> ForecastService:
    """
    Get or create the global forecast service instance.
    
    Returns:
        ForecastService instance
    """
    global _forecast_service
    if _forecast_service is None:
        _forecast_service = ForecastService()
    return _forecast_service


# Convenience functions for direct use
def create_forecast(
    symbol: str,
    historical_prices: List[float],
    forecast_horizon: int = 30,
    options: Optional[Dict[str, Any]] = None
) -> Forecast:
    """
    Create a forecast (convenience function).
    
    Args:
        symbol: Trading symbol
        historical_prices: Historical price series
        forecast_horizon: Number of days to forecast
        options: Optional forecast options
    
    Returns:
        Forecast domain object
    """
    service = get_forecast_service()
    return service.create_forecast(symbol, historical_prices, forecast_horizon, options)


def get_forecast(forecast_id: str) -> Optional[Forecast]:
    """
    Get a forecast by ID (convenience function).
    
    Args:
        forecast_id: Forecast ID
    
    Returns:
        Forecast domain object or None
    """
    service = get_forecast_service()
    return service.get_forecast(forecast_id)

