"""
Reasoning schemas for trade decision-making.

Defines Pydantic V2 models for trade context and AI reasoning responses.
"""
from enum import Enum
from typing import Dict, Any, Optional
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
    
    # v1.5 Adversarial Critique Metrics (optional, set by engine)
    proposer_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Initial confidence before critique (v1.5)")
    final_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Final confidence after critique (v1.5)")
    critique_flaws_count: Optional[int] = Field(default=None, ge=0, description="Number of flaws found by Red Team (v1.5)")
    critique_summary: Optional[str] = Field(default=None, description="Summary of Red Team critique (v1.5)")
    
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


class AnalysisOutcome(str, Enum):
    """Outcome categorization for post-mortem analysis."""
    VALIDATED_THESIS = "VALIDATED_THESIS"
    BAD_TIMING = "BAD_TIMING"
    UNFORESEEN_EVENT = "UNFORESEEN_EVENT"
    MODEL_HALLUCINATION = "MODEL_HALLUCINATION"
    LUCK = "LUCK"  # Won for the wrong reason


class PostMortemReport(BaseModel):
    """Post-trade analysis report."""

    trade_id: str = Field(..., description="Identifier of the evaluated trade")
    actual_outcome: str = Field(..., description="Actual result (WIN/LOSS)")
    outcome_category: AnalysisOutcome = Field(
        ..., description="Categorized outcome of the trade"
    )
    root_cause: str = Field(..., description="One-sentence root cause explanation")
    lesson_learned: str = Field(..., description="What to do differently next time")
    adjusted_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="In-hindsight confidence level"
    )

