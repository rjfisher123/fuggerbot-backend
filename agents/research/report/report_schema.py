"""
Research Report Schema - Deterministic Structure.

Defines the canonical structure of a FuggerBot Research Report.
All fields must be deterministically ordered and stable across runs.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class InsightStrength(str, Enum):
    """Insight confidence strength classification."""
    STRONG = "strong"  # confidence >= 0.7
    MODERATE = "moderate"  # 0.5 <= confidence < 0.7
    WEAK = "weak"  # confidence < 0.5


class InsightEvidenceStatus(str, Enum):
    """Evidence qualification status for insights."""
    STRONG = "strong"  # Meets evidence requirements (>=3 scenarios, >=2 regimes)
    PRELIMINARY = "preliminary"  # Insufficient evidence (but may have high confidence)


class ReportInsight(BaseModel):
    """Single insight entry in report."""
    insight_id: str = Field(..., description="Unique insight identifier")
    insight_type: str = Field(..., description="Type: winning_pattern, failure_mode, regime_heuristic")
    description: str = Field(..., description="Human-readable insight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    strength: InsightStrength = Field(..., description="Confidence strength classification (based on confidence score)")
    evidence_status: InsightEvidenceStatus = Field(..., description="Evidence qualification status (based on supporting data)")
    scenario_count: int = Field(..., ge=0, description="Number of supporting scenarios")
    regime_coverage: List[str] = Field(default_factory=list, description="Regime IDs where this holds")
    regime_coverage_count: int = Field(..., ge=0, description="Number of distinct regimes where this holds")
    discovered_at: str = Field(..., description="ISO timestamp of discovery")
    has_contradictions: bool = Field(default=False, description="Has been contradicted")
    
    def model_post_init(self, __context: Any) -> None:
        """Set strength based on confidence if not provided."""
        if not hasattr(self, 'strength') or self.strength is None:
            if self.confidence >= 0.7:
                object.__setattr__(self, 'strength', InsightStrength.STRONG)
            elif self.confidence >= 0.5:
                object.__setattr__(self, 'strength', InsightStrength.MODERATE)
            else:
                object.__setattr__(self, 'strength', InsightStrength.WEAK)


class FailureBoundary(BaseModel):
    """Failure boundary detection result."""
    parameter_name: str = Field(..., description="Parameter that has a failure boundary")
    boundary_type: str = Field(..., description="performance_cliff or failure_threshold")
    param_value: Optional[float] = Field(default=None, description="Parameter value at boundary")
    return_before: Optional[float] = Field(default=None, description="Return before boundary")
    return_after: Optional[float] = Field(default=None, description="Return after boundary")
    drop_magnitude: Optional[float] = Field(default=None, description="Magnitude of performance drop")
    description: str = Field(..., description="Human-readable boundary description")


class RegimeCoverageEntry(BaseModel):
    """Single regime coverage entry."""
    regime_id: str = Field(..., description="Regime identifier")
    regime_description: str = Field(..., description="Human-readable regime description")
    scenario_count: int = Field(..., ge=0, description="Number of scenarios tested in this regime")
    coverage_percentage: float = Field(..., ge=0.0, le=100.0, description="Coverage percentage")


class RecommendedExperiment(BaseModel):
    """Recommended experiment proposal."""
    proposal_id: str = Field(..., description="Unique proposal identifier")
    proposal_type: str = Field(..., description="parameter_sweep, regime_test, hypothesis_test, uncertainty_reduction")
    title: str = Field(..., description="Proposal title")
    description: str = Field(..., description="Proposal description")
    expected_info_gain: float = Field(..., ge=0.0, le=1.0, description="Expected information gain")
    priority: int = Field(..., ge=0, le=10, description="Priority score")
    reasoning: str = Field(..., description="Reasoning for this proposal")
    based_on_insights: List[str] = Field(default_factory=list, description="Insight IDs that informed this proposal")


class PerformanceMetrics(BaseModel):
    """Aggregate performance metrics."""
    total_scenarios: int = Field(..., ge=0, description="Total number of scenarios tested")
    avg_return_pct: float = Field(..., description="Average return percentage")
    avg_sharpe_ratio: float = Field(..., description="Average Sharpe ratio (valid values only)")
    avg_max_drawdown_pct: float = Field(..., description="Average maximum drawdown percentage")
    avg_win_rate: float = Field(..., ge=0.0, le=1.0, description="Average win rate")
    total_returns: List[float] = Field(default_factory=list, description="All individual returns (for distribution analysis)")
    min_return_pct: float = Field(..., description="Minimum return across scenarios")
    max_return_pct: float = Field(..., description="Maximum return across scenarios")
    
    # Sharpe ratio statistics (valid values only)
    median_sharpe_ratio: Optional[float] = Field(default=None, description="Median Sharpe ratio (valid values only)")
    sharpe_p10: Optional[float] = Field(default=None, description="10th percentile Sharpe ratio")
    sharpe_p90: Optional[float] = Field(default=None, description="90th percentile Sharpe ratio")
    invalid_sharpe_count: int = Field(default=0, ge=0, description="Count of invalid Sharpe values (NaN or ±inf)")


class ReportMetadata(BaseModel):
    """Report metadata."""
    report_id: str = Field(..., description="Unique report identifier (e.g., FRR-2025-02-14)")
    strategy_version: str = Field(..., description="Strategy version identifier")
    research_loop_version: str = Field(default="2.0", description="Research loop version")
    simulator_commit_hash: str = Field(..., description="Simulator commit hash for reproducibility")
    data_fingerprint: str = Field(..., description="Hash of input data for validation")
    generated_at: str = Field(..., description="ISO timestamp of report generation")
    total_insights: int = Field(..., ge=0, description="Total number of insights")
    total_scenarios: int = Field(..., ge=0, description="Total number of scenarios analyzed")


class ResearchReport(BaseModel):
    """Complete research report structure."""
    metadata: ReportMetadata = Field(..., description="Report metadata")
    
    # Executive Summary
    executive_summary: str = Field(..., description="High-level summary of findings")
    
    # Performance Overview
    performance_metrics: PerformanceMetrics = Field(..., description="Aggregate performance metrics")
    
    # Confirmed Insights (sorted by confidence, descending)
    confirmed_insights: List[ReportInsight] = Field(default_factory=list, description="All insights, sorted by confidence")
    
    # Known Unknowns (weak insights and gaps)
    known_unknowns: List[str] = Field(default_factory=list, description="List of unresolved questions or weak insights")
    
    # Failure Boundaries
    failure_boundaries: List[FailureBoundary] = Field(default_factory=list, description="Detected failure boundaries")
    
    # Regime Coverage
    regime_coverage: List[RegimeCoverageEntry] = Field(default_factory=list, description="Regime coverage analysis")
    
    # Recommended Experiments
    recommended_experiments: List[RecommendedExperiment] = Field(default_factory=list, description="Recommended next experiments")
    
    # Appendices
    appendix_scenario_ids: List[str] = Field(default_factory=list, description="All scenario IDs analyzed (for reference)")
    appendix_sensitivity_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Full sensitivity analysis results")
    
    # Rich content (optional - populated from snapshot)
    appendix_top_scenarios: Optional[List[Dict[str, Any]]] = Field(default=None, description="Top 5 scenarios by return")
    appendix_bottom_scenarios: Optional[List[Dict[str, Any]]] = Field(default=None, description="Bottom 5 scenarios by return")
    appendix_symbol_stats: Optional[Dict[str, Dict[str, float]]] = Field(default=None, description="Statistics by symbol")
    appendix_regime_stats: Optional[Dict[str, Dict[str, float]]] = Field(default=None, description="Statistics by regime")
    appendix_metric_definitions: Optional[Dict[str, str]] = Field(default=None, description="Metric definitions and calculation methods")
    appendix_historonics_hypotheses: Optional[List[Dict[str, Any]]] = Field(default=None, description="Historonics Agent hypotheses (advisory only)")
    
    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

