"""
Report Diff Schema - Semantic Diff Structure.

Defines the structure of semantic diffs between research reports.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class InsightChange(BaseModel):
    """Change to an individual insight."""
    insight_id: str = Field(..., description="Insight identifier")
    change_type: str = Field(..., description="new, removed, confidence_changed")
    old_confidence: Optional[float] = Field(default=None, description="Previous confidence (if changed)")
    new_confidence: Optional[float] = Field(default=None, description="New confidence (if changed)")
    confidence_delta: Optional[float] = Field(default=None, description="Change in confidence")
    description: str = Field(..., description="Human-readable description of change")


class RegimeCoverageChange(BaseModel):
    """Change in regime coverage."""
    regime_id: str = Field(..., description="Regime identifier")
    regime_description: str = Field(..., description="Regime description")
    old_coverage_pct: float = Field(..., ge=0.0, le=100.0, description="Previous coverage percentage")
    new_coverage_pct: float = Field(..., ge=0.0, le=100.0, description="New coverage percentage")
    coverage_delta: float = Field(..., description="Change in coverage percentage")
    old_scenario_count: int = Field(..., ge=0, description="Previous scenario count")
    new_scenario_count: int = Field(..., ge=0, description="New scenario count")


class FailureBoundaryChange(BaseModel):
    """Change in failure boundaries."""
    parameter_name: str = Field(..., description="Parameter name")
    change_type: str = Field(..., description="new_boundary, removed_boundary, boundary_changed")
    boundary_type: Optional[str] = Field(default=None, description="Type of boundary")
    description: str = Field(..., description="Human-readable description of change")


class ProposalRankingChange(BaseModel):
    """Change in proposal ranking."""
    proposal_id: str = Field(..., description="Proposal identifier")
    old_rank: Optional[int] = Field(default=None, description="Previous rank (1-indexed)")
    new_rank: Optional[int] = Field(default=None, description="New rank (1-indexed)")
    old_info_gain: Optional[float] = Field(default=None, description="Previous expected info gain")
    new_info_gain: Optional[float] = Field(default=None, description="New expected info gain")
    description: str = Field(..., description="Human-readable description of change")


class ReportDiff(BaseModel):
    """Complete semantic diff between two reports."""
    base_report_id: str = Field(..., description="Base report identifier")
    compare_report_id: str = Field(..., description="Compare report identifier")
    base_generated_at: str = Field(..., description="Base report generation timestamp")
    compare_generated_at: str = Field(..., description="Compare report generation timestamp")
    
    # Insight changes
    new_insights: List[InsightChange] = Field(default_factory=list, description="New insights")
    removed_insights: List[InsightChange] = Field(default_factory=list, description="Removed insights")
    confidence_changes: List[InsightChange] = Field(default_factory=list, description="Confidence changes")
    
    # Regime coverage changes
    regime_coverage_changes: List[RegimeCoverageChange] = Field(default_factory=list, description="Regime coverage changes")
    
    # Failure boundary changes
    new_failure_boundaries: List[FailureBoundaryChange] = Field(default_factory=list, description="New failure boundaries")
    removed_failure_boundaries: List[FailureBoundaryChange] = Field(default_factory=list, description="Removed failure boundaries")
    
    # Proposal ranking changes
    proposal_ranking_changes: List[ProposalRankingChange] = Field(default_factory=list, description="Proposal ranking changes")
    
    # Metadata
    total_insight_changes: int = Field(..., ge=0, description="Total number of insight changes")
    total_coverage_changes: int = Field(..., ge=0, description="Total number of coverage changes")
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Diff generation timestamp")

