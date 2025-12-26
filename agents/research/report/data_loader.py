"""
Data Loader for Report Generation - Handles Multiple Data Sources.

Loads scenario results from:
1. war_games_results.json (primary source)
2. research_results/scenario_*.json (research loop outputs)
3. Future: run_id-based iteration snapshots
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from agents.research.report.data_models import (
    ScenarioResult,
    ScenarioIdentity,
    ScenarioMetricSet,
    ResearchIterationSnapshot,
    OverallStats,
    RegimeStats,
    SymbolStats,
    ParamSetStats,
    ReportDataError
)
from agents.research.regime_ontology import get_regime_ontology

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads and normalizes scenario results from various sources.
    """
    
    def __init__(self, data_root: Optional[Path] = None):
        """
        Initialize data loader.
        
        Args:
            data_root: Root directory for data files (default: project_root/data)
        """
        if data_root is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_root = project_root / "data"
        
        self.data_root = Path(data_root)
        self.regime_ontology = get_regime_ontology()
        
        logger.info(f"DataLoader initialized (data_root: {self.data_root})")
    
    def load_from_war_games_results(
        self,
        run_id: Optional[str] = None
    ) -> ResearchIterationSnapshot:
        """
        Load scenario results from war_games_results.json.
        
        Args:
            run_id: Optional run ID to filter (if None, uses latest)
        
        Returns:
            ResearchIterationSnapshot with normalized data
        
        Raises:
            ReportDataError if file doesn't exist or is invalid
        """
        war_games_file = self.data_root / "war_games_results.json"
        
        if not war_games_file.exists():
            raise ReportDataError(
                f"war_games_results.json not found",
                expected_location=str(war_games_file),
                suggestion="Run: python daemon/simulator/war_games_runner.py"
            )
        
        try:
            with open(war_games_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            raise ReportDataError(
                f"Failed to parse war_games_results.json: {e}",
                expected_location=str(war_games_file)
            )
        
        # Validate structure
        if "results" not in data:
            raise ReportDataError(
                "war_games_results.json missing 'results' field",
                expected_location=str(war_games_file)
            )
        
        results_raw = data.get("results", [])
        if not results_raw:
            raise ReportDataError(
                "war_games_results.json contains no scenario results",
                expected_location=str(war_games_file),
                suggestion="Run: python daemon/simulator/war_games_runner.py"
            )
        
        # Convert to normalized format
        scenario_results = []
        for idx, result_raw in enumerate(results_raw):
            try:
                scenario_result = self._normalize_war_games_result(result_raw, data, idx)
                scenario_results.append(scenario_result)
            except Exception as e:
                logger.warning(f"Failed to normalize result {idx}: {e}")
                continue
        
        if not scenario_results:
            raise ReportDataError(
                "No valid scenario results could be normalized from war_games_results.json",
                expected_location=str(war_games_file)
            )
        
        # Generate run_id from timestamp if not provided
        run_timestamp = data.get("run_timestamp", datetime.now().isoformat())
        if not run_id:
            run_id = run_timestamp.replace(":", "-").replace(".", "-")[:19]  # Simplified run_id
        
        # Aggregate statistics
        overall_stats = self._aggregate_overall(scenario_results)
        regime_stats = self._aggregate_by_regime(scenario_results)
        symbol_stats = self._aggregate_by_symbol(scenario_results)
        param_stats = self._aggregate_by_param(scenario_results)
        
        return ResearchIterationSnapshot(
            iteration_id=run_id,
            run_id=run_id,
            generated_at=run_timestamp,
            scenario_results=scenario_results,
            overall_stats=overall_stats,
            regime_stats=regime_stats,
            symbol_stats=symbol_stats,
            param_stats=param_stats,
            data_source=str(war_games_file)
        )
    
    def _normalize_war_games_result(
        self,
        result_raw: Dict[str, Any],
        metadata: Dict[str, Any],
        index: int
    ) -> ScenarioResult:
        """Convert war_games result format to normalized ScenarioResult."""
        # Extract scenario info from campaign_name
        campaign_name = result_raw.get("campaign_name", f"campaign_{index}")
        
        # Parse campaign_name: "Bull Run (2021) - BTC-USD - Aggressive"
        parts = campaign_name.split(" - ")
        scenario_name = parts[0] if len(parts) > 0 else "Unknown"
        symbol = result_raw.get("symbol", parts[1] if len(parts) > 1 else "UNKNOWN")
        param_set_name = parts[2] if len(parts) > 2 else "Unknown"
        
        # Find matching scenario in metadata
        scenario_desc = None
        start_date = result_raw.get("start_date", "")
        end_date = result_raw.get("end_date", "")
        
        for scenario in metadata.get("scenarios", []):
            if scenario.get("name") == scenario_name:
                scenario_desc = scenario.get("description")
                break
        
        # Classify regime
        regime_id = None
        if start_date:
            regime = self.regime_ontology.classify_scenario(
                scenario_name,
                start_date,
                end_date,
                scenario_desc
            )
            regime_id = regime.regime_id()
        
        # Create parameter set ID from params
        params = result_raw.get("params", {})
        param_hash = self._hash_params(params)
        
        # Generate scenario_id deterministically
        scenario_id = f"{symbol}_{param_hash}_{start_date}_{end_date}"
        
        # Build identity
        identity = ScenarioIdentity(
            scenario_id=scenario_id,
            campaign_name=campaign_name,
            symbol=symbol,
            param_set_id=param_hash,
            regime_id=regime_id,
            time_range_start=start_date,
            time_range_end=end_date,
            scenario_description=scenario_desc
        )
        
        # Build metrics
        metrics = ScenarioMetricSet(
            total_return_pct=result_raw.get("total_return_pct", 0.0),
            sharpe_ratio=result_raw.get("sharpe_ratio", 0.0),
            max_drawdown_pct=result_raw.get("max_drawdown_pct", 0.0),
            win_rate=result_raw.get("win_rate", 0.0),
            trades_count=result_raw.get("total_trades", 0),
            profit_factor=result_raw.get("profit_factor"),
            total_bars=None  # Not in war_games format
        )
        
        return ScenarioResult(
            identity=identity,
            metrics=metrics,
            raw_data_pointer=f"war_games_results.json:results[{index}]"
        )
    
    def _hash_params(self, params: Dict[str, Any]) -> str:
        """Generate deterministic hash from parameter dict."""
        import hashlib
        # Sort params for deterministic hashing
        sorted_params = json.dumps(params, sort_keys=True)
        return hashlib.sha256(sorted_params.encode()).hexdigest()[:12]
    
    def _aggregate_overall(self, scenarios: List[ScenarioResult]) -> OverallStats:
        """Aggregate overall statistics."""
        if not scenarios:
            raise ValueError("Cannot aggregate empty scenario list")
        
        returns = [s.metrics.total_return_pct for s in scenarios]
        returns_sorted = sorted(returns)
        n = len(returns)
        
        dates_start = [s.identity.time_range_start for s in scenarios if s.identity.time_range_start]
        dates_end = [s.identity.time_range_end for s in scenarios if s.identity.time_range_end]
        
        return OverallStats(
            total_scenarios=n,
            avg_return_pct=sum(returns) / n,
            median_return_pct=returns_sorted[n // 2] if n > 0 else 0.0,
            p10_return_pct=returns_sorted[int(n * 0.1)] if n >= 10 else returns_sorted[0] if n > 0 else 0.0,
            p90_return_pct=returns_sorted[int(n * 0.9)] if n >= 10 else returns_sorted[-1] if n > 0 else 0.0,
            avg_sharpe_ratio=sum(s.metrics.sharpe_ratio for s in scenarios) / n,
            avg_max_drawdown_pct=sum(s.metrics.max_drawdown_pct for s in scenarios) / n,
            avg_win_rate=sum(s.metrics.win_rate for s in scenarios) / n,
            total_trades=sum(s.metrics.trades_count for s in scenarios),
            min_return_pct=min(returns),
            max_return_pct=max(returns),
            date_range_start=min(dates_start) if dates_start else None,
            date_range_end=max(dates_end) if dates_end else None
        )
    
    def _aggregate_by_regime(self, scenarios: List[ScenarioResult]) -> Dict[str, RegimeStats]:
        """Aggregate statistics by regime."""
        regime_groups: Dict[str, List[ScenarioResult]] = {}
        
        for scenario in scenarios:
            regime_id = scenario.identity.regime_id or "unknown"
            if regime_id not in regime_groups:
                regime_groups[regime_id] = []
            regime_groups[regime_id].append(scenario)
        
        regime_stats = {}
        for regime_id, group in regime_groups.items():
            returns = [s.metrics.total_return_pct for s in group]
            returns_sorted = sorted(returns)
            n = len(group)
            
            # Get regime description
            regime_desc = "Unknown regime"
            if regime_id != "unknown":
                # Try to find in ontology
                all_regimes = self.regime_ontology.get_all_regime_combinations()
                for r in all_regimes:
                    if r.regime_id() == regime_id:
                        regime_desc = r.description
                        break
            
            regime_stats[regime_id] = RegimeStats(
                regime_id=regime_id,
                regime_description=regime_desc,
                scenario_count=n,
                avg_return_pct=sum(returns) / n,
                median_return_pct=returns_sorted[n // 2] if n > 0 else 0.0,
                avg_drawdown_pct=sum(s.metrics.max_drawdown_pct for s in group) / n,
                avg_win_rate=sum(s.metrics.win_rate for s in group) / n,
                min_return_pct=min(returns),
                max_return_pct=max(returns)
            )
        
        return regime_stats
    
    def _aggregate_by_symbol(self, scenarios: List[ScenarioResult]) -> Dict[str, SymbolStats]:
        """Aggregate statistics by symbol."""
        symbol_groups: Dict[str, List[ScenarioResult]] = {}
        
        for scenario in scenarios:
            symbol = scenario.identity.symbol
            if symbol not in symbol_groups:
                symbol_groups[symbol] = []
            symbol_groups[symbol].append(scenario)
        
        symbol_stats = {}
        for symbol, group in symbol_groups.items():
            returns = [s.metrics.total_return_pct for s in group]
            returns_sorted = sorted(returns)
            n = len(group)
            
            symbol_stats[symbol] = SymbolStats(
                symbol=symbol,
                scenario_count=n,
                avg_return_pct=sum(returns) / n,
                median_return_pct=returns_sorted[n // 2] if n > 0 else 0.0,
                avg_drawdown_pct=sum(s.metrics.max_drawdown_pct for s in group) / n,
                avg_win_rate=sum(s.metrics.win_rate for s in group) / n,
                min_return_pct=min(returns),
                max_return_pct=max(returns)
            )
        
        return symbol_stats
    
    def _aggregate_by_param(self, scenarios: List[ScenarioResult]) -> Dict[str, ParamSetStats]:
        """Aggregate statistics by parameter set."""
        param_groups: Dict[str, List[ScenarioResult]] = {}
        
        for scenario in scenarios:
            param_id = scenario.identity.param_set_id
            if param_id not in param_groups:
                param_groups[param_id] = []
            param_groups[param_id].append(scenario)
        
        param_stats = {}
        for param_id, group in param_groups.items():
            returns = [s.metrics.total_return_pct for s in group]
            returns_sorted = sorted(returns)
            n = len(group)
            
            param_stats[param_id] = ParamSetStats(
                param_set_id=param_id,
                scenario_count=n,
                avg_return_pct=sum(returns) / n,
                median_return_pct=returns_sorted[n // 2] if n > 0 else 0.0,
                avg_drawdown_pct=sum(s.metrics.max_drawdown_pct for s in group) / n,
                avg_win_rate=sum(s.metrics.win_rate for s in group) / n
            )
        
        return param_stats
    
    def load_latest_iteration(self) -> ResearchIterationSnapshot:
        """
        Load latest iteration (currently from war_games_results.json).
        
        Returns:
            ResearchIterationSnapshot
        
        Raises:
            ReportDataError if no data found
        """
        return self.load_from_war_games_results()
    
    def load_iteration_by_id(self, run_id: str) -> ResearchIterationSnapshot:
        """
        Load specific iteration by run_id.
        
        Currently only supports war_games_results.json (all runs use same file).
        Future: support iteration-specific files.
        
        Args:
            run_id: Run identifier
        
        Returns:
            ResearchIterationSnapshot
        """
        # For now, just load war_games_results and set the run_id
        snapshot = self.load_from_war_games_results()
        snapshot.run_id = run_id
        snapshot.iteration_id = run_id
        return snapshot

