"""
Reasoning schemas for trade decision-making.

Defines Pydantic V2 models for trade context and AI reasoning responses.
"""
from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel, Field


class ReasoningDecision(str, Enum):
    """Decision types for trade reasoning."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    WAIT = "WAIT"


class TradeContext(BaseModel):
    """Context information for trade decision-making."""
    
    symbol: str = Field(..., description="Trading symbol (e.g., 'AAPL')")
    price: float = Field(..., gt=0, description="Current market price")
    forecast_target: float = Field(..., description="Forecast target price")
    
    forecast_confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Forecast confidence score (0.0 to 1.0)"
    )
    trust_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Trust score for the forecast (0.0 to 1.0)"
    )
    
    volatility_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Volatility metrics dictionary (e.g., {'current': 0.15, 'historical': 0.12})"
    )
    memory_summary: str = Field(
        default="",
        description="Summary of relevant historical context or memory"
    )
    
    class Config:
        """Pydantic V2 configuration."""
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "price": 175.50,
                "forecast_target": 185.00,
                "forecast_confidence": 0.85,
                "trust_score": 0.78,
                "volatility_metrics": {
                    "current": 0.15,
                    "historical": 0.12,
                    "regime": "normal"
                },
                "memory_summary": "Strong bullish trend over past 30 days"
            }
        }


class DeepSeekResponse(BaseModel):
    """Response from DeepSeek AI reasoning engine."""
    
    decision: ReasoningDecision = Field(
        ..., 
        description="The reasoning decision: APPROVE, REJECT, or WAIT"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence in the decision (0.0 to 1.0)"
    )
    risk_analysis: str = Field(
        ..., 
        description="Detailed risk analysis of the trade"
    )
    rationale: str = Field(
        ..., 
        description="Explanation of the reasoning behind the decision"
    )
    
    def is_actionable(self, threshold: float = 0.75) -> bool:
        """
        Check if the decision is actionable (approved with high confidence).
        
        Args:
            threshold: Minimum confidence threshold (default: 0.75)
        
        Returns:
            True if decision is APPROVE and confidence >= threshold, False otherwise
        """
        return (
            self.decision == ReasoningDecision.APPROVE 
            and self.confidence >= threshold
        )
    
    class Config:
        """Pydantic V2 configuration."""
        json_schema_extra = {
            "example": {
                "decision": "APPROVE",
                "confidence": 0.82,
                "risk_analysis": "Moderate risk with strong bullish signal. Volatility within acceptable range.",
                "rationale": "Forecast shows 5.4% upside potential with high confidence (0.85). Trust score (0.78) indicates reliable signal. Historical context supports bullish trend."
            }
        }

