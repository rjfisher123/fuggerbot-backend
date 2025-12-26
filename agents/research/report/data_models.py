"""
Data Models for Report Generation - Normalized Scenario Metrics.

Defines canonical data structures for scenario results and aggregated statistics.
All models are deterministic and support stable sorting.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime


class ScenarioMetricSet(BaseModel):
    """Normalized performance metrics for a single scenario/campaign."""
    total_return_pct: float = Field(..., description="Total return percentage")
    cagr: Optional[float] = Field(default=None, description="Compound annual growth rate")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown_pct: float = Field(..., description="Maximum drawdown percentage")
    win_rate: float = Field(..., ge=0.0, le=1.0, description="Win rate (0-1)")
    trades_count: int = Field(..., ge=0, description="Total number of trades")
    exposure_avg: Optional[float] = Field(default=None, description="Average position exposure")
    worst_day_pct: Optional[float] = Field(default=None, description="Worst single day return")
    best_day_pct: Optional[float] = Field(default=None, description="Best single day return")
    profit_factor: Optional[float] = Field(default=None, description="Profit factor (gross profit / gross loss)")
    total_bars: Optional[int] = Field(default=None, description="Total bars/periods processed")


class ScenarioIdentity(BaseModel):
    """Identity information for a scenario."""
    scenario_id: str = Field(..., description="Unique scenario identifier")
    campaign_name: str = Field(..., description="Campaign name")
    symbol: str = Field(..., description="Trading symbol")
    param_set_id: str = Field(..., description="Parameter set identifier/hash")
    regime_id: Optional[str] = Field(default=None, description="Regime classification ID")
    time_range_start: str = Field(..., description="Start date (YYYY-MM-DD)")
    time_range_end: str = Field(..., description="End date (YYYY-MM-DD)")
    scenario_description: Optional[str] = Field(default=None, description="Scenario description")


class ScenarioResult(BaseModel):
    """Complete scenario result with identity and metrics."""
    identity: ScenarioIdentity = Field(..., description="Scenario identity")
    metrics: ScenarioMetricSet = Field(..., description="Performance metrics")
    raw_data_pointer: Optional[str] = Field(default=None, description="Pointer to raw result data (file path or ID)")
    
    def sort_key(self) -> tuple:
        """Generate deterministic sort key for stable ordering."""
        return (
            -self.metrics.total_return_pct,  # Descending return
            self.identity.scenario_id  # Tie-break by ID
        )


class OverallStats(BaseModel):
    """Aggregated statistics across all scenarios."""
    total_scenarios: int = Field(..., ge=0, description="Total number of scenarios")
    avg_return_pct: float = Field(..., description="Average return percentage")
    median_return_pct: float = Field(..., description="Median return percentage")
    p10_return_pct: float = Field(..., description="10th percentile return")
    p90_return_pct: float = Field(..., description="90th percentile return")
    avg_sharpe_ratio: float = Field(..., description="Average Sharpe ratio")
    avg_max_drawdown_pct: float = Field(..., description="Average maximum drawdown")
    avg_win_rate: float = Field(..., ge=0.0, le=1.0, description="Average win rate")
    total_trades: int = Field(..., ge=0, description="Total trades across all scenarios")
    min_return_pct: float = Field(..., description="Minimum return")
    max_return_pct: float = Field(..., description="Maximum return")
    date_range_start: Optional[str] = Field(default=None, description="Earliest date in scenarios")
    date_range_end: Optional[str] = Field(default=None, description="Latest date in scenarios")


class RegimeStats(BaseModel):
    """Statistics aggregated by regime."""
    regime_id: str = Field(..., description="Regime identifier")
    regime_description: str = Field(..., description="Regime description")
    scenario_count: int = Field(..., ge=0, description="Number of scenarios in this regime")
    avg_return_pct: float = Field(..., description="Average return in this regime")
    median_return_pct: float = Field(..., description="Median return in this regime")
    avg_drawdown_pct: float = Field(..., description="Average drawdown in this regime")
    avg_win_rate: float = Field(..., ge=0.0, le=1.0, description="Average win rate")
    min_return_pct: float = Field(..., description="Minimum return")
    max_return_pct: float = Field(..., description="Maximum return")


class SymbolStats(BaseModel):
    """Statistics aggregated by trading symbol."""
    symbol: str = Field(..., description="Trading symbol")
    scenario_count: int = Field(..., ge=0, description="Number of scenarios for this symbol")
    avg_return_pct: float = Field(..., description="Average return for this symbol")
    median_return_pct: float = Field(..., description="Median return for this symbol")
    avg_drawdown_pct: float = Field(..., description="Average drawdown")
    avg_win_rate: float = Field(..., ge=0.0, le=1.0, description="Average win rate")
    min_return_pct: float = Field(..., description="Minimum return")
    max_return_pct: float = Field(..., description="Maximum return")


class ParamSetStats(BaseModel):
    """Statistics aggregated by parameter set."""
    param_set_id: str = Field(..., description="Parameter set identifier")
    scenario_count: int = Field(..., ge=0, description="Number of scenarios with these params")
    avg_return_pct: float = Field(..., description="Average return with these params")
    median_return_pct: float = Field(..., description="Median return")
    avg_drawdown_pct: float = Field(..., description="Average drawdown")
    avg_win_rate: float = Field(..., ge=0.0, le=1.0, description="Average win rate")


class ResearchIterationSnapshot(BaseModel):
    """Snapshot of a research loop iteration for report generation."""
    iteration_id: str = Field(..., description="Iteration identifier")
    run_id: Optional[str] = Field(default=None, description="Run identifier (if different from iteration_id)")
    generated_at: str = Field(..., description="ISO timestamp of iteration")
    scenario_results: List[ScenarioResult] = Field(default_factory=list, description="All scenario results")
    overall_stats: Optional[OverallStats] = Field(default=None, description="Aggregated overall statistics")
    regime_stats: Dict[str, RegimeStats] = Field(default_factory=dict, description="Statistics by regime")
    symbol_stats: Dict[str, SymbolStats] = Field(default_factory=dict, description="Statistics by symbol")
    param_stats: Dict[str, ParamSetStats] = Field(default_factory=dict, description="Statistics by parameter set")
    data_source: str = Field(..., description="Source file or location of data")


# Exception for missing data
class ReportDataError(Exception):
    """Raised when required report data is missing."""
    def __init__(self, message: str, expected_location: Optional[str] = None, suggestion: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.expected_location = expected_location
        self.suggestion = suggestion
    
    def __str__(self) -> str:
        msg = self.message
        if self.expected_location:
            msg += f"\n  Expected location: {self.expected_location}"
        if self.suggestion:
            msg += f"\n  Suggestion: {self.suggestion}"
        return msg

