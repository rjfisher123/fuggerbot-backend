"""Pydantic schemas for trust filter input/output data contracts."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import numpy as np

from ..tsfm.schemas import ForecastOutput


class TrustMetrics(BaseModel):
    """Metrics used to evaluate forecast trustworthiness."""
    
    uncertainty_score: float = Field(
        ...,
        description="Uncertainty-based trust score (0-1, higher = more trustworthy)",
        ge=0.0,
        le=1.0
    )
    
    consistency_score: float = Field(
        ...,
        description="Consistency-based trust score (0-1, higher = more consistent)",
        ge=0.0,
        le=1.0
    )
    
    data_quality_score: float = Field(
        ...,
        description="Input data quality score (0-1, higher = better quality)",
        ge=0.0,
        le=1.0
    )
    
    historical_accuracy: Optional[float] = Field(
        None,
        description="Historical accuracy score if available (0-1, higher = more accurate)",
        ge=0.0,
        le=1.0
    )
    
    market_regime_score: Optional[float] = Field(
        None,
        description="Market regime compatibility score (0-1, higher = better regime)",
        ge=0.0,
        le=1.0
    )
    
    overall_trust_score: float = Field(
        ...,
        description="Weighted overall trust score (0-1, higher = more trustworthy)",
        ge=0.0,
        le=1.0
    )
    
    confidence_level: Literal["low", "medium", "high"] = Field(
        ...,
        description="Confidence level classification"
    )
    
    rejection_reasons: List[str] = Field(
        default_factory=list,
        description="List of reasons why forecast might be rejected (if any)"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional trust evaluation metadata"
    )


class TrustEvaluation(BaseModel):
    """Complete trust evaluation for a forecast."""
    
    forecast: ForecastOutput = Field(
        ...,
        description="The forecast being evaluated"
    )
    
    metrics: TrustMetrics = Field(
        ...,
        description="Trust metrics for this forecast"
    )
    
    is_trusted: bool = Field(
        ...,
        description="Whether this forecast passes the trust filter"
    )
    
    evaluation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this evaluation was performed"
    )
    
    evaluation_id: Optional[str] = Field(
        None,
        description="Unique identifier for this evaluation"
    )


class TrustFilterConfig(BaseModel):
    """Configuration for the trust filter."""
    
    min_trust_score: float = Field(
        0.6,
        description="Minimum overall trust score to pass filter (0-1)",
        ge=0.0,
        le=1.0
    )
    
    min_uncertainty_score: float = Field(
        0.5,
        description="Minimum uncertainty score threshold",
        ge=0.0,
        le=1.0
    )
    
    min_consistency_score: float = Field(
        0.5,
        description="Minimum consistency score threshold",
        ge=0.0,
        le=1.0
    )
    
    min_data_quality_score: float = Field(
        0.6,
        description="Minimum data quality score threshold",
        ge=0.0,
        le=1.0
    )
    
    require_historical_accuracy: bool = Field(
        False,
        description="Whether historical accuracy is required"
    )
    
    min_historical_accuracy: Optional[float] = Field(
        0.7,
        description="Minimum historical accuracy if required",
        ge=0.0,
        le=1.0
    )
    
    max_uncertainty_ratio: float = Field(
        0.5,
        description="Maximum ratio of uncertainty range to point forecast (for rejection)",
        ge=0.0,
        le=1.0
    )
    
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "uncertainty": 0.3,
            "consistency": 0.25,
            "data_quality": 0.25,
            "historical_accuracy": 0.15,
            "market_regime": 0.05
        },
        description="Weights for computing overall trust score"
    )
    
    enable_strict_mode: bool = Field(
        False,
        description="If True, all thresholds must pass. If False, overall score is primary."
    )


class BatchTrustEvaluation(BaseModel):
    """Trust evaluation results for multiple forecasts."""
    
    evaluations: List[TrustEvaluation] = Field(
        ...,
        description="List of trust evaluations"
    )
    
    trusted_count: int = Field(
        ...,
        description="Number of forecasts that passed the trust filter"
    )
    
    rejected_count: int = Field(
        ...,
        description="Number of forecasts that failed the trust filter"
    )
    
    average_trust_score: float = Field(
        ...,
        description="Average overall trust score across all forecasts",
        ge=0.0,
        le=1.0
    )
    
    evaluation_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When batch evaluation was performed"
    )





