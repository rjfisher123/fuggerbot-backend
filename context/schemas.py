"""
Macro Regime data structures.

Defines schemas for tracking macroeconomic regimes and their impact on market behavior.
"""
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RegimeType(str, Enum):
    """Types of macroeconomic regimes."""
    
    INFLATIONARY = "INFLATIONARY"
    DEFLATIONARY = "DEFLATIONARY"
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"
    GOLDILOCKS = "GOLDILOCKS"


class MacroRegime(BaseModel):
    """
    Represents a macroeconomic regime.
    
    Tracks the current market regime state with risk characteristics
    and sentiment indicators.
    """
    
    id: str = Field(..., description="Unique identifier for the regime")
    name: str = Field(..., description="Human-readable name of the regime")
    summary: str = Field(..., description="Brief summary of the regime characteristics")
    risk_on: bool = Field(..., description="Whether the regime is risk-on (True) or risk-off (False)")
    vibe_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Sentiment/vibe score from 0.0 (very negative) to 1.0 (very positive)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when this regime was detected/updated"
    )
    
    class Config:
        """Pydantic V2 configuration."""
        json_schema_extra = {
            "example": {
                "id": "QT_HAWKISH_2024",
                "name": "Quantitative Tightening - Hawkish",
                "summary": "Fed maintaining high rates, QT ongoing, inflation concerns",
                "risk_on": False,
                "vibe_score": 0.3,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
