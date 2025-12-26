"""
Meta-Evaluator Agent - Research Loop Component.

Compares outcomes across Scenario_IDs and identifies patterns.
Learns across simulations, not within them.

Core Principle: Delta-based insights, not averages.
"""
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class ScenarioComparison(BaseModel):
    """
    Comparison between scenarios with delta-based insights.
    """
    scenario_a_id: str = Field(..., description="First scenario ID")
    scenario_b_id: str = Field(..., description="Second scenario ID")
    
    # Performance deltas
    return_delta: float = Field(..., description="Difference in average return (%)")
    sharpe_delta: float = Field(..., description="Difference in average Sharpe ratio")
    drawdown_delta: float = Field(..., description="Difference in max drawdown (%)")
    win_rate_delta: float = Field(..., description="Difference in win rate")
    
    # Parameter differences
    parameter_diffs: Dict[str, Any] = Field(..., description="Key parameter differences")
    
    # Insights
    insights: List[str] = Field(default_factory=list, description="Human-readable insights")
    regime_dependency: Optional[str] = Field(default=None, description="Regime where difference is most pronounced")
    
    timestamp: datetime = Field(default_factory=datetime.now)


class MetaEvaluator:
    """
    Evaluates scenarios comparatively to extract learning.
    
    Identifies:
    - Parameter sensitivity
    - Regime-dependent performance
    - Failure modes vs success modes
    """
    
    def __init__(self):
        """Initialize meta-evaluator."""
        logger.info("MetaEvaluator initialized")
    
    def compare_scenarios(
        self,
        scenario_a_results: Dict[str, Any],
        scenario_b_results: Dict[str, Any]
    ) -> ScenarioComparison:
        """
        Compare two scenario results and extract insights.
        
        Args:
            scenario_a_results: Results dict from first scenario
            scenario_b_results: Results dict from second scenario
        
        Returns:
            ScenarioComparison with insights
        """
        # Extract metrics from results
        results_a = scenario_a_results.get("results", [])
        results_b = scenario_b_results.get("results", [])
        
        # Calculate aggregate metrics
        metrics_a = self._calculate_aggregate_metrics(results_a)
        metrics_b = self._calculate_aggregate_metrics(results_b)
        
        # Calculate deltas
        comparison = ScenarioComparison(
            scenario_a_id=scenario_a_results.get("scenario_id", "unknown"),
            scenario_b_id=scenario_b_results.get("scenario_id", "unknown"),
            return_delta=metrics_b["avg_return"] - metrics_a["avg_return"],
            sharpe_delta=metrics_b["avg_sharpe"] - metrics_a["avg_sharpe"],
            drawdown_delta=metrics_b["avg_drawdown"] - metrics_a["avg_drawdown"],
            win_rate_delta=metrics_b["avg_win_rate"] - metrics_a["avg_win_rate"],
            parameter_diffs=self._extract_parameter_diffs(scenario_a_results, scenario_b_results),
            insights=[]
        )
        
        # Generate insights
        comparison.insights = self._generate_insights(metrics_a, metrics_b, comparison.parameter_diffs)
        
        logger.info(f"Compared scenarios {comparison.scenario_a_id} vs {comparison.scenario_b_id}: {len(comparison.insights)} insights")
        return comparison
    
    def evaluate_parameter_sensitivity(
        self,
        scenario_results: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Evaluate how sensitive performance is to parameter changes.
        
        Args:
            scenario_results: List of scenario result dicts
        
        Returns:
            Dict mapping parameter names to sensitivity metrics
        """
        sensitivity = {}
        
        # Group results by parameter values
        param_groups = {}
        for result in scenario_results:
            params = result.get("params", {})
            for param_name, param_value in params.items():
                if param_name not in param_groups:
                    param_groups[param_name] = {}
                
                key = str(param_value)
                if key not in param_groups[param_name]:
                    param_groups[param_name][key] = []
                
                param_groups[param_name][key].append(result)
        
        # Calculate sensitivity (variance in returns across parameter values)
        for param_name, value_groups in param_groups.items():
            returns_by_value = {}
            for value, results in value_groups.items():
                returns = [r.get("total_return_pct", 0) for r in results]
                returns_by_value[value] = np.mean(returns) if returns else 0
            
            if len(returns_by_value) > 1:
                sensitivity[param_name] = {
                    "range": max(returns_by_value.values()) - min(returns_by_value.values()),
                    "std": np.std(list(returns_by_value.values())),
                    "values": returns_by_value
                }
        
        return sensitivity
    
    def identify_failure_modes(
        self,
        scenario_results: List[Dict[str, Any]],
        threshold: float = -10.0
    ) -> List[Dict[str, Any]]:
        """
        Identify scenarios that failed (large losses).
        
        Args:
            scenario_results: List of scenario result dicts
            threshold: Return threshold below which scenario is considered failed
        
        Returns:
            List of failure mode descriptions
        """
        failures = []
        
        for result in scenario_results:
            if result.get("total_return_pct", 0) < threshold:
                failures.append({
                    "scenario_id": result.get("scenario_id", "unknown"),
                    "return_pct": result.get("total_return_pct", 0),
                    "max_drawdown": result.get("max_drawdown_pct", 0),
                    "params": result.get("params", {}),
                    "regime": result.get("scenario_description", "unknown"),
                    "regime_classification": result.get("regime_classification"),
                    "insight": f"Failed with {result.get('total_return_pct', 0):.1f}% return in {result.get('scenario_description', 'unknown')} regime"
                })
        
        logger.info(f"Identified {len(failures)} failure modes (threshold: {threshold}%)")
        return failures
    
    def detect_failure_boundaries(
        self,
        scenario_results: List[Dict[str, Any]],
        param_name: str
    ) -> Dict[str, Any]:
        """
        Detect performance cliffs or failure boundaries for a parameter.
        
        Identifies where strategy performance sharply degrades as parameter changes.
        
        Args:
            scenario_results: List of scenario result dicts
            param_name: Parameter name to analyze (e.g., 'trust_threshold')
        
        Returns:
            Dict with boundary detection results
        """
        # Group results by parameter value
        param_values = {}
        for result in scenario_results:
            # Extract parameter value (simplified - assumes param is in param_sets)
            params = result.get("params", {})
            param_value = params.get(param_name)
            
            if param_value is not None:
                if param_value not in param_values:
                    param_values[param_value] = []
                param_values[param_value].append(result)
        
        if len(param_values) < 2:
            return {"boundary_detected": False, "reason": "Insufficient parameter variation"}
        
        # Calculate average return for each parameter value
        param_performance = {}
        for value, results in param_values.items():
            returns = [r.get("total_return_pct", 0) for r in results]
            param_performance[value] = np.mean(returns) if returns else 0
        
        # Sort by parameter value
        sorted_values = sorted(param_performance.keys())
        sorted_returns = [param_performance[v] for v in sorted_values]
        
        # Detect sharp drops (performance cliffs)
        boundaries = []
        for i in range(len(sorted_values) - 1):
            return_drop = sorted_returns[i] - sorted_returns[i + 1]
            
            # Threshold for "sharp" drop (e.g., >5% return drop)
            if return_drop > 5.0:
                boundaries.append({
                    "param_value_before": sorted_values[i],
                    "param_value_after": sorted_values[i + 1],
                    "return_before": sorted_returns[i],
                    "return_after": sorted_returns[i + 1],
                    "drop_magnitude": return_drop,
                    "boundary_type": "performance_cliff"
                })
        
        # Detect failure boundaries (crossing into negative territory)
        failure_boundaries = []
        for i in range(len(sorted_values) - 1):
            if sorted_returns[i] > 0 and sorted_returns[i + 1] < 0:
                failure_boundaries.append({
                    "param_value": sorted_values[i + 1],
                    "return_before": sorted_returns[i],
                    "return_after": sorted_returns[i + 1],
                    "boundary_type": "failure_threshold"
                })
        
        return {
            "boundary_detected": len(boundaries) > 0 or len(failure_boundaries) > 0,
            "performance_cliffs": boundaries,
            "failure_thresholds": failure_boundaries,
            "param_name": param_name,
            "param_performance": param_performance
        }
    
    def analyze_sensitivity_landscape(
        self,
        scenario_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze parameter sensitivity landscape.
        
        Identifies which parameters have high outcome sensitivity and where failures occur.
        
        Args:
            scenario_results: List of scenario result dicts
        
        Returns:
            Dict with sensitivity analysis results
        """
        sensitivity_analysis = self.evaluate_parameter_sensitivity(scenario_results)
        
        # Identify highly sensitive parameters
        high_sensitivity = {}
        for param_name, metrics in sensitivity_analysis.items():
            if metrics["range"] > 10.0 or metrics["std"] > 5.0:  # Significant variation
                high_sensitivity[param_name] = {
                    "range": metrics["range"],
                    "std": metrics["std"],
                    "boundary_analysis": self.detect_failure_boundaries(scenario_results, param_name)
                }
        
        # Identify failure patterns by regime
        failures = self.identify_failure_modes(scenario_results)
        regime_failure_patterns = {}
        for failure in failures:
            regime_data = failure.get("regime_classification")
            if regime_data:
                regime_id = regime_data.get("regime_id", "unknown") if isinstance(regime_data, dict) else str(regime_data)
                if regime_id not in regime_failure_patterns:
                    regime_failure_patterns[regime_id] = []
                regime_failure_patterns[regime_id].append(failure)
        
        return {
            "high_sensitivity_params": high_sensitivity,
            "regime_failure_patterns": regime_failure_patterns,
            "total_failures": len(failures),
            "sensitivity_summary": {
                param: {
                    "range": metrics["range"],
                    "std": metrics["std"]
                }
                for param, metrics in sensitivity_analysis.items()
            }
        }
    
    def _calculate_aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate aggregate metrics from a list of campaign results."""
        if not results:
            return {
                "avg_return": 0.0,
                "avg_sharpe": 0.0,
                "avg_drawdown": 0.0,
                "avg_win_rate": 0.0
            }
        
        returns = [r.get("total_return_pct", 0) for r in results]
        sharpes = [r.get("sharpe_ratio", 0) for r in results]
        drawdowns = [r.get("max_drawdown_pct", 0) for r in results]
        win_rates = [r.get("win_rate", 0) for r in results]
        
        return {
            "avg_return": np.mean(returns) if returns else 0.0,
            "avg_sharpe": np.mean(sharpes) if sharpes else 0.0,
            "avg_drawdown": np.mean(drawdowns) if drawdowns else 0.0,
            "avg_win_rate": np.mean(win_rates) if win_rates else 0.0
        }
    
    def _extract_parameter_diffs(
        self,
        scenario_a: Dict[str, Any],
        scenario_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract key parameter differences between scenarios."""
        diffs = {}
        
        # Compare param_sets if available
        params_a = scenario_a.get("param_sets", {})
        params_b = scenario_b.get("param_sets", {})
        
        # Simple comparison - in practice would be more sophisticated
        if params_a and params_b:
            # Compare first param set as example
            first_set_a = next(iter(params_a.values())) if params_a else {}
            first_set_b = next(iter(params_b.values())) if params_b else {}
            
            for key in set(first_set_a.keys()) | set(first_set_b.keys()):
                val_a = first_set_a.get(key)
                val_b = first_set_b.get(key)
                if val_a != val_b:
                    diffs[key] = {"a": val_a, "b": val_b}
        
        return diffs
    
    def _generate_insights(
        self,
        metrics_a: Dict[str, float],
        metrics_b: Dict[str, float],
        param_diffs: Dict[str, Any]
    ) -> List[str]:
        """Generate human-readable insights from comparison."""
        insights = []
        
        # Return comparison
        return_delta = metrics_b["avg_return"] - metrics_a["avg_return"]
        if abs(return_delta) > 1.0:  # Significant difference
            direction = "better" if return_delta > 0 else "worse"
            insights.append(f"Scenario B performs {abs(return_delta):.1f}% {direction} on average return")
        
        # Sharpe comparison
        sharpe_delta = metrics_b["avg_sharpe"] - metrics_a["avg_sharpe"]
        if abs(sharpe_delta) > 0.2:
            direction = "better" if sharpe_delta > 0 else "worse"
            insights.append(f"Scenario B has {abs(sharpe_delta):.2f} {direction} risk-adjusted returns (Sharpe)")
        
        # Drawdown comparison
        dd_delta = metrics_b["avg_drawdown"] - metrics_a["avg_drawdown"]
        if abs(dd_delta) > 2.0:
            if dd_delta < 0:  # B has less drawdown
                insights.append(f"Scenario B reduces max drawdown by {abs(dd_delta):.1f}%")
            else:
                insights.append(f"Scenario B increases max drawdown by {dd_delta:.1f}%")
        
        # Parameter insights
        if "trust_threshold" in param_diffs:
            diff = param_diffs["trust_threshold"]
            insights.append(f"Trust threshold changed from {diff['a']} to {diff['b']}")
        
        return insights


# Singleton instance
_meta_evaluator: Optional[MetaEvaluator] = None


def get_meta_evaluator() -> MetaEvaluator:
    """Get or create meta-evaluator instance."""
    global _meta_evaluator
    if _meta_evaluator is None:
        _meta_evaluator = MetaEvaluator()
    return _meta_evaluator

