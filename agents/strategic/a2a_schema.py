"""
A2A (Agent-to-Agent) Protocol Schemas for FuggerBot Strategic Reasoner.

Defines Pydantic models for signal ingestion from ai_inbox_digest v1.0
and feedback emission back to upstream systems.

All signals are treated as "High-confidence but not authoritative."
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SignalClass(str, Enum):
    """Signal classification types."""
    MARKET_NEWS = "market_news"
    EARNINGS = "earnings"
    POLICY = "policy"
    GEOPOLITICS = "geopolitics"
    ECONOMIC_DATA = "economic_data"
    SECTOR_NEWS = "sector_news"
    OTHER = "other"


class SignalLineage(BaseModel):
    """Provenance information for a signal."""
    upstream_message_ids: List[str] = Field(default_factory=list, description="Upstream message IDs")
    upstream_agents: List[str] = Field(default_factory=list, description="Agent names that processed this signal")
    processing_chain: List[str] = Field(default_factory=list, description="Processing chain (ordered list of agent names)")


class DecayAnnotation(BaseModel):
    """Time-decay annotation (computed upstream, not re-computed by FuggerBot)."""
    original_priority: float = Field(..., description="Original priority before decay")
    decay_factor: float = Field(..., ge=0.0, le=1.0, description="Decay factor applied (1.0 = no decay)")
    decay_reason: str = Field(..., description="Reason for decay (e.g., 'time_elapsed', 'redundancy')")
    decay_applied_at: datetime = Field(default_factory=datetime.now, description="When decay was applied")


class CorroborationAnnotation(BaseModel):
    """Corroboration annotation (computed upstream, not re-computed by FuggerBot)."""
    corroboration_score: float = Field(..., ge=0.0, le=1.0, description="Corroboration score (0 = none, 1 = fully corroborated)")
    corroborating_sources: List[str] = Field(default_factory=list, description="List of source IDs that corroborate this signal")
    corroboration_method: str = Field(..., description="Method used for corroboration (e.g., 'multi_source', 'cross_validation')")
    computed_at: datetime = Field(default_factory=datetime.now, description="When corroboration was computed")


class A2ASignal(BaseModel):
    """
    Input signal from ai_inbox_digest v1.0 via A2A protocol.
    
    FuggerBot must treat all signals as "High-confidence but not authoritative."
    FuggerBot must not re-compute decay or corroboration.
    """
    signal_id: str = Field(..., description="Unique signal identifier")
    signal_class: SignalClass = Field(..., description="Signal classification")
    summary: str = Field(..., min_length=1, description="Concise, factual summary")
    
    # Priority (post-decay)
    base_priority: float = Field(..., ge=0.0, le=1.0, description="Original priority (before decay)")
    effective_priority: float = Field(..., ge=0.0, le=1.0, description="Effective priority (post-decay)")
    
    # Corroboration
    corroboration_score: float = Field(..., ge=0.0, le=1.0, description="Corroboration score (0-1)")
    
    # Citations (optional)
    citations: List[str] = Field(default_factory=list, description="Citation URLs or references")
    
    # Timestamps
    created_at: datetime = Field(..., description="When signal was created")
    received_at: datetime = Field(default_factory=datetime.now, description="When FuggerBot received this signal")
    
    # Provenance & Explainability
    signal_lineage: SignalLineage = Field(..., description="Provenance information")
    decay_annotation: Optional[DecayAnnotation] = Field(default=None, description="Time-decay annotation (if applicable)")
    corroboration_annotation: Optional[CorroborationAnnotation] = Field(default=None, description="Corroboration annotation")
    
    # Additional metadata (optional, for extensibility)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def model_post_init(self, __context: Any) -> None:
        """Validate signal integrity."""
        # Ensure effective_priority <= base_priority (decay should only reduce priority)
        if self.effective_priority > self.base_priority:
            raise ValueError(f"effective_priority ({self.effective_priority}) cannot exceed base_priority ({self.base_priority})")


class FeedbackType(str, Enum):
    """Types of feedback that FuggerBot can emit."""
    HIGH_INTEREST = "high_interest"
    LOW_INTEREST = "low_interest"
    FOLLOW_UP_REQUIRED = "follow_up_required"
    DUPLICATE_SIGNAL = "duplicate_signal"
    OUT_OF_SCOPE = "out_of_scope"


class A2AFeedback(BaseModel):
    """
    Feedback emitted by FuggerBot back to upstream systems via A2A protocol.
    
    Feedback is advisory only and must not alter upstream logic directly.
    """
    feedback_id: str = Field(..., description="Unique feedback identifier")
    signal_id: str = Field(..., description="Signal ID this feedback refers to")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    
    # Feedback details
    summary: str = Field(..., description="Human-readable feedback summary")
    reasoning: str = Field(..., description="Reason for this feedback")
    
    # Context (optional)
    strategic_relevance: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Strategic relevance score (if applicable)")
    time_horizon: Optional[str] = Field(default=None, description="Time horizon affected (e.g., 'days', 'quarters', 'years')")
    
    # Metadata
    emitted_at: datetime = Field(default_factory=datetime.now, description="When feedback was emitted")
    fuggerbot_version: str = Field(default="1.0.0", description="FuggerBot version that generated this feedback")
    
    # Additional context (optional)
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for upstream systems")
    
    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

