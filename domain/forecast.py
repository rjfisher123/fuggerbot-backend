"""
Forecast domain model.

Represents a complete forecast with all associated metadata and analysis.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from models.tsfm.schemas import ForecastOutput
from models.trust.schemas import TrustEvaluation


class Forecast(BaseModel):
    """
    Domain model representing a complete forecast with all analysis.
    
    This aggregates the raw forecast output, trust evaluation, and all
    derived metrics (FQS, regime, FRS, etc.) into a single domain entity.
    """
    
    # Core identifiers
    forecast_id: str = Field(..., description="Unique forecast identifier")
    symbol: str = Field(..., description="Trading symbol")
    created_at: datetime = Field(default_factory=datetime.now, description="Forecast creation timestamp")
    
    # Forecast parameters
    forecast_horizon: int = Field(..., description="Number of days forecasted", ge=1)
    model_name: str = Field(default="amazon/chronos-t5-tiny", description="Model used for forecasting")
    params: Dict[str, Any] = Field(default_factory=dict, description="Forecast parameters (context_length, historical_period, etc.)")
    
    # Raw forecast output
    predicted_series: ForecastOutput = Field(..., description="Raw forecast output from model")
    
    # Trust and quality metrics
    trust_score: float = Field(..., description="Overall trust score (0-1)", ge=0.0, le=1.0)
    trust_evaluation: TrustEvaluation = Field(..., description="Complete trust evaluation")
    
    # Derived metrics (optional - populated by service layer)
    fqs_score: Optional[float] = Field(None, description="Forecast Quality Score (0-1)")
    regime: Optional[Dict[str, Any]] = Field(None, description="Confidence regime classification")
    frs_score: Optional[float] = Field(None, description="FuggerBot Reliability Score (0-1)")
    coherence: Optional[Dict[str, Any]] = Field(None, description="Cross-asset coherence analysis")
    
    # Trading recommendation
    recommendation: Optional[Dict[str, Any]] = Field(None, description="Trading recommendation")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True  # Allow ForecastOutput and TrustEvaluation
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert forecast to dictionary for serialization."""
        return {
            "forecast_id": self.forecast_id,
            "symbol": self.symbol,
            "created_at": self.created_at.isoformat(),
            "forecast_horizon": self.forecast_horizon,
            "model_name": self.model_name,
            "params": self.params,
            "trust_score": self.trust_score,
            "fqs_score": self.fqs_score,
            "regime": self.regime,
            "frs_score": self.frs_score,
            "coherence": self.coherence,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }










