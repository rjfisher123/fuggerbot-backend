"""
Research Report Generator - Deterministic Report Creation.

Generates canonical Markdown research reports from Research Loop outputs.
All outputs are deterministic and stable across runs.
"""
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from agents.research.report.report_schema import (
    ResearchReport,
    ReportMetadata,
    ReportInsight,
    InsightStrength,
    InsightEvidenceStatus,
    FailureBoundary,
    RegimeCoverageEntry,
    RecommendedExperiment,
    PerformanceMetrics
)
from agents.research.report.data_loader import DataLoader, ReportDataError
from agents.research.report.data_models import ResearchIterationSnapshot, ScenarioResult
from agents.research.memory_agent import get_memory_agent
from agents.research.meta_evaluator import get_meta_evaluator
from agents.research.proposal_agent import get_proposal_agent
from agents.research.regime_ontology import get_regime_ontology

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates deterministic research reports from Research Loop outputs.
    """
    
    def __init__(
        self,
        memory_store_path: Optional[str] = None,
        data_root: Optional[str] = None
    ):
        """
        Initialize report generator.
        
        Args:
            memory_store_path: Path to strategy memory store
            data_root: Root directory for data files (default: project_root/data)
        """
        self.memory_agent = get_memory_agent(memory_store_path)
        self.meta_evaluator = get_meta_evaluator()
        self.proposal_agent = get_proposal_agent()
        self.regime_ontology = get_regime_ontology()
        
        if data_root is None:
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent.parent
            data_root = project_root / "data"
        self.data_root = Path(data_root)
        self.data_loader = DataLoader(data_root=self.data_root)
        
        logger.info(f"ReportGenerator initialized (data_root: {self.data_root})")
    
    def generate_report(
        self,
        report_id: str,
        run_id: Optional[str] = None,
        strategy_version: str = "1.0.0",
        simulator_commit_hash: str = "unknown",
        output_path: Optional[Path] = None
    ) -> ResearchReport:
        """
        Generate a complete research report.
        
        Args:
            report_id: Unique report identifier (e.g., "FRR-2025-02-14")
            run_id: Optional run ID (if None, loads latest)
            strategy_version: Strategy version identifier
            simulator_commit_hash: Simulator commit hash for reproducibility
            output_path: Optional path to save report JSON (for validation)
        
        Returns:
            ResearchReport object
        
        Raises:
            ReportDataError if scenario data is missing
        """
        logger.info(f"Generating report: {report_id} (run_id: {run_id or 'latest'})")
        
        # Load iteration snapshot (FAILS LOUDLY if no data)
        try:
            if run_id:
                iteration_snapshot = self.data_loader.load_iteration_by_id(run_id)
            else:
                iteration_snapshot = self.data_loader.load_latest_iteration()
        except ReportDataError as e:
            logger.error(f"Failed to load scenario data: {e}")
            raise
        
        logger.info(f"Loaded {len(iteration_snapshot.scenario_results)} scenarios from {iteration_snapshot.data_source}")
        
        # Get insights directly from memory store (not filtered version)
        memory = self.memory_agent.memory
        memory_insights = {
            "winning_patterns": memory.winning_archetypes,
            "failure_modes": memory.failure_modes,
            "regime_heuristics": memory.regime_heuristics
        }
        
        # Convert normalized scenarios to dict format for meta_evaluator (temporary compatibility)
        scenario_results_dict = [self._scenario_result_to_dict(sr) for sr in iteration_snapshot.scenario_results]
        sensitivity_analysis = self.meta_evaluator.analyze_sensitivity_landscape(scenario_results_dict)
        
        # Generate data fingerprint
        data_fingerprint = self._compute_data_fingerprint_from_snapshot(iteration_snapshot, memory_insights)
        
        # Count total insights
        total_insights = (
            len(memory_insights.get("winning_patterns", [])) +
            len(memory_insights.get("failure_modes", [])) +
            len(memory_insights.get("regime_heuristics", []))
        )
        
        # Build metadata
        metadata = ReportMetadata(
            report_id=report_id,
            strategy_version=strategy_version,
            research_loop_version="2.0",
            simulator_commit_hash=simulator_commit_hash,
            data_fingerprint=data_fingerprint,
            generated_at=datetime.now().isoformat(),
            total_insights=total_insights,
            total_scenarios=len(iteration_snapshot.scenario_results)
        )
        
        # Build performance metrics from snapshot
        performance_metrics = self._compute_performance_metrics_from_snapshot(iteration_snapshot)
        
        # Build confirmed insights (sorted by confidence, descending)
        confirmed_insights = self._build_confirmed_insights(memory_insights)
        
        # Build known unknowns (weak insights and coverage gaps)
        known_unknowns = self._build_known_unknowns_from_snapshot(memory_insights, iteration_snapshot)
        
        # Build failure boundaries
        failure_boundaries = self._build_failure_boundaries(sensitivity_analysis)
        
        # Build regime coverage from snapshot
        regime_coverage = self._build_regime_coverage_from_snapshot(iteration_snapshot)
        
        # Build recommended experiments
        recommended_experiments = self._build_recommended_experiments_from_snapshot(memory_insights, iteration_snapshot)
        
        # Build executive summary
        executive_summary = self._build_executive_summary(
            performance_metrics,
            confirmed_insights,
            failure_boundaries,
            regime_coverage,
            iteration_snapshot
        )
        
        # Build report
        report = ResearchReport(
            metadata=metadata,
            executive_summary=executive_summary,
            performance_metrics=performance_metrics,
            confirmed_insights=confirmed_insights,
            known_unknowns=known_unknowns,
            failure_boundaries=failure_boundaries,
            regime_coverage=regime_coverage,
            recommended_experiments=recommended_experiments,
            appendix_scenario_ids=[sr.identity.scenario_id for sr in iteration_snapshot.scenario_results],
            appendix_sensitivity_analysis=sensitivity_analysis,
            appendix_top_scenarios=self._get_top_scenarios(iteration_snapshot, n=5),
            appendix_bottom_scenarios=self._get_bottom_scenarios(iteration_snapshot, n=5),
            appendix_symbol_stats=self._get_symbol_stats_dict(iteration_snapshot),
            appendix_regime_stats=self._get_regime_stats_dict(iteration_snapshot),
            appendix_metric_definitions=self._get_metric_definitions(),
            appendix_historonics_hypotheses=None  # Can be populated by calling generate_historonics_hypotheses separately
        )
        
        # Save JSON if requested (for validation/diffing)
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(report.model_dump(), f, indent=2, default=str)
            logger.info(f"Report JSON saved to {output_path}")
        
        logger.info(f"Report generated: {report_id} ({len(confirmed_insights)} insights, {len(iteration_snapshot.scenario_results)} scenarios)")
        return report
    
    def _scenario_result_to_dict(self, sr: ScenarioResult) -> Dict[str, Any]:
        """Convert ScenarioResult to dict format for compatibility with meta_evaluator."""
        return {
            "scenario_id": sr.identity.scenario_id,
            "total_return_pct": sr.metrics.total_return_pct,
            "sharpe_ratio": sr.metrics.sharpe_ratio,
            "max_drawdown_pct": sr.metrics.max_drawdown_pct,
            "win_rate": sr.metrics.win_rate,
            "params": {},  # TODO: Extract from param_set_id if needed
            "regime_classification": {"regime_id": sr.identity.regime_id} if sr.identity.regime_id else None,
            "scenario_description": sr.identity.scenario_description
        }
    
    def _compute_data_fingerprint_from_snapshot(
        self,
        snapshot: ResearchIterationSnapshot,
        memory_insights: Dict[str, List[Any]]
    ) -> str:
        """Compute fingerprint from snapshot."""
        scenario_ids = sorted([sr.identity.scenario_id for sr in snapshot.scenario_results])
        insight_ids = []
        for category, insight_list in memory_insights.items():
            for insight_obj in insight_list:
                insight_id = insight_obj.insight_id if hasattr(insight_obj, 'insight_id') else 'unknown'
                insight_ids.append(f"{category}:{insight_id}")
        
        fingerprint_data = {
            "scenario_ids": scenario_ids,
            "insight_ids": sorted(insight_ids),
            "iteration_id": snapshot.iteration_id
        }
        
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_json.encode()).hexdigest()[:16]
    
    def _compute_performance_metrics_from_snapshot(self, snapshot: ResearchIterationSnapshot) -> PerformanceMetrics:
        """Compute performance metrics from snapshot with Sharpe ratio sanity checks."""
        overall = snapshot.overall_stats
        
        # Extract Sharpe ratios and filter invalid values (NaN, ±inf)
        all_sharpes = [sr.metrics.sharpe_ratio for sr in snapshot.scenario_results]
        valid_sharpes = self._filter_valid_sharpe_ratios(all_sharpes)
        invalid_count = len(all_sharpes) - len(valid_sharpes)
        
        # Compute Sharpe statistics (only from valid values)
        median_sharpe = None
        sharpe_p10 = None
        sharpe_p90 = None
        avg_sharpe = 0.0
        
        if valid_sharpes:
            valid_sharpes_sorted = sorted(valid_sharpes)
            n = len(valid_sharpes_sorted)
            avg_sharpe = sum(valid_sharpes_sorted) / n
            median_sharpe = valid_sharpes_sorted[n // 2]
            
            if n >= 10:
                sharpe_p10 = valid_sharpes_sorted[int(n * 0.1)]
                sharpe_p90 = valid_sharpes_sorted[int(n * 0.9)]
            elif n > 0:
                sharpe_p10 = valid_sharpes_sorted[0]
                sharpe_p90 = valid_sharpes_sorted[-1]
        else:
            # If no valid Sharpe values, use overall.avg_sharpe_ratio but flag as potentially invalid
            avg_sharpe = overall.avg_sharpe_ratio
        
        return PerformanceMetrics(
            total_scenarios=overall.total_scenarios,
            avg_return_pct=overall.avg_return_pct,
            avg_sharpe_ratio=avg_sharpe,
            avg_max_drawdown_pct=overall.avg_max_drawdown_pct,
            avg_win_rate=overall.avg_win_rate,
            total_returns=[sr.metrics.total_return_pct for sr in snapshot.scenario_results],
            min_return_pct=overall.min_return_pct,
            max_return_pct=overall.max_return_pct,
            median_sharpe_ratio=median_sharpe,
            sharpe_p10=sharpe_p10,
            sharpe_p90=sharpe_p90,
            invalid_sharpe_count=invalid_count
        )
    
    def _filter_valid_sharpe_ratios(self, sharpe_ratios: List[float]) -> List[float]:
        """
        Filter out invalid Sharpe ratio values (NaN, ±inf).
        
        Invalid values occur when:
        - Standard deviation is zero (no variance in returns)
        - Division by zero
        - Other numerical issues
        
        Args:
            sharpe_ratios: List of Sharpe ratio values
        
        Returns:
            List of valid (finite) Sharpe ratio values
        """
        import math
        valid = []
        for sharpe in sharpe_ratios:
            # Check if finite (not NaN, not ±inf)
            if math.isfinite(sharpe):
                valid.append(sharpe)
        return valid
    
    def _build_known_unknowns_from_snapshot(
        self,
        memory_insights: Dict[str, Any],
        snapshot: ResearchIterationSnapshot
    ) -> List[str]:
        """Build known unknowns from snapshot."""
        unknowns = []
        
        # Weak insights
        insight_lists = {
            "winning_pattern": memory_insights.get("winning_patterns", []),
            "failure_mode": memory_insights.get("failure_modes", []),
            "regime_heuristic": memory_insights.get("regime_heuristics", [])
        }
        
        for category, insight_list in insight_lists.items():
            for insight_obj in insight_list:
                confidence = insight_obj.confidence
                description = insight_obj.description
                if confidence < 0.5:
                    unknowns.append(f"Weak insight: {description} (confidence: {confidence:.2f})")
        
        # Coverage gaps (unexplored regimes)
        covered_regimes = set(snapshot.regime_stats.keys())
        all_regimes = self.regime_ontology.get_all_regime_combinations()
        uncovered_regimes = [r for r in all_regimes if r.regime_id() not in covered_regimes and r.regime_id() != "unknown"]
        
        if uncovered_regimes:
            unknowns.append(f"{len(uncovered_regimes)} regime combinations remain unexplored")
        
        return unknowns
    
    def _build_regime_coverage_from_snapshot(self, snapshot: ResearchIterationSnapshot) -> List[RegimeCoverageEntry]:
        """Build regime coverage from snapshot."""
        coverage_entries = []
        total_scenarios = snapshot.overall_stats.total_scenarios
        
        for regime_id, regime_stats in snapshot.regime_stats.items():
            coverage_pct = (regime_stats.scenario_count / total_scenarios * 100) if total_scenarios > 0 else 0.0
            
            entry = RegimeCoverageEntry(
                regime_id=regime_id,
                regime_description=regime_stats.regime_description,
                scenario_count=regime_stats.scenario_count,
                coverage_percentage=coverage_pct
            )
            coverage_entries.append(entry)
        
        # Sort by coverage percentage (descending)
        coverage_entries.sort(key=lambda x: (x.coverage_percentage, x.regime_id), reverse=True)
        
        return coverage_entries
    
    def _build_recommended_experiments_from_snapshot(
        self,
        memory_insights: Dict[str, Any],
        snapshot: ResearchIterationSnapshot
    ) -> List[RecommendedExperiment]:
        """Build recommended experiments from snapshot."""
        existing_scenarios = [sr.identity.scenario_id for sr in snapshot.scenario_results]
        
        # Convert StrategyInsight objects to dict format for proposal agent
        insights_for_proposals = {
            "winning_patterns": [
                {
                    "description": i.description,
                    "confidence": i.confidence,
                    "regimes": i.regimes,
                    "insight_id": i.insight_id,
                    "metrics": i.evidence_metrics
                }
                for i in memory_insights.get("winning_patterns", [])
            ],
            "failure_modes": [
                {
                    "description": i.description,
                    "regimes": i.regimes,
                    "insight_id": i.insight_id,
                    "metrics": i.evidence_metrics
                }
                for i in memory_insights.get("failure_modes", [])
            ],
            "regime_heuristics": [
                {
                    "description": i.description,
                    "regimes": i.regimes,
                    "confidence": i.confidence,
                    "insight_id": i.insight_id
                }
                for i in memory_insights.get("regime_heuristics", [])
            ]
        }
        
        # Build regime coverage dict
        regime_coverage = {regime_id: stats.scenario_count for regime_id, stats in snapshot.regime_stats.items()}
        
        proposals = self.proposal_agent.generate_proposals(
            existing_scenarios=existing_scenarios,
            memory_insights=insights_for_proposals,
            existing_regime_coverage=regime_coverage,
            limit=10
        )
        
        experiments = []
        for proposal in proposals:
            experiment = RecommendedExperiment(
                proposal_id=proposal.proposal_id,
                proposal_type=proposal.proposal_type,
                title=proposal.title,
                description=proposal.description,
                expected_info_gain=proposal.expected_info_gain,
                priority=proposal.priority,
                reasoning=proposal.reasoning,
                based_on_insights=proposal.based_on_insights
            )
            experiments.append(experiment)
        
        return experiments
    
    def _get_top_scenarios(self, snapshot: ResearchIterationSnapshot, n: int = 5) -> List[Dict[str, Any]]:
        """Get top N scenarios by return."""
        sorted_scenarios = sorted(snapshot.scenario_results, key=lambda x: x.sort_key())
        top = sorted_scenarios[:n]
        
        return [{
            "scenario_id": sr.identity.scenario_id,
            "campaign_name": sr.identity.campaign_name,
            "symbol": sr.identity.symbol,
            "return_pct": sr.metrics.total_return_pct,
            "sharpe_ratio": sr.metrics.sharpe_ratio,
            "drawdown_pct": sr.metrics.max_drawdown_pct,
            "win_rate": sr.metrics.win_rate,
            "trades_count": sr.metrics.trades_count
        } for sr in top]
    
    def _get_bottom_scenarios(self, snapshot: ResearchIterationSnapshot, n: int = 5) -> List[Dict[str, Any]]:
        """Get bottom N scenarios by return."""
        sorted_scenarios = sorted(snapshot.scenario_results, key=lambda x: x.sort_key(), reverse=True)
        bottom = sorted_scenarios[:n]
        
        return [{
            "scenario_id": sr.identity.scenario_id,
            "campaign_name": sr.identity.campaign_name,
            "symbol": sr.identity.symbol,
            "return_pct": sr.metrics.total_return_pct,
            "sharpe_ratio": sr.metrics.sharpe_ratio,
            "drawdown_pct": sr.metrics.max_drawdown_pct,
            "win_rate": sr.metrics.win_rate,
            "trades_count": sr.metrics.trades_count
        } for sr in bottom]
    
    def _get_symbol_stats_dict(self, snapshot: ResearchIterationSnapshot) -> Dict[str, Dict[str, float]]:
        """Convert symbol stats to dict for report."""
        return {
            symbol: {
                "scenario_count": stats.scenario_count,
                "avg_return_pct": stats.avg_return_pct,
                "median_return_pct": stats.median_return_pct,
                "avg_drawdown_pct": stats.avg_drawdown_pct,
                "avg_win_rate": stats.avg_win_rate,
                "min_return_pct": stats.min_return_pct,
                "max_return_pct": stats.max_return_pct
            }
            for symbol, stats in snapshot.symbol_stats.items()
        }
    
    def _get_regime_stats_dict(self, snapshot: ResearchIterationSnapshot) -> Dict[str, Dict[str, float]]:
        """Convert regime stats to dict for report."""
        return {
            regime_id: {
                "scenario_count": stats.scenario_count,
                "avg_return_pct": stats.avg_return_pct,
                "median_return_pct": stats.median_return_pct,
                "avg_drawdown_pct": stats.avg_drawdown_pct,
                "avg_win_rate": stats.avg_win_rate,
                "min_return_pct": stats.min_return_pct,
                "max_return_pct": stats.max_return_pct
            }
            for regime_id, stats in snapshot.regime_stats.items()
        }
    
    def _get_metric_definitions(self) -> Dict[str, str]:
        """Get metric definitions for appendix."""
        return {
            "sharpe_ratio": (
                "Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Standard Deviation\n\n"
                "Calculation Details:\n"
                "- Return periodicity: Daily returns\n"
                "- Annualization factor: Not applied (reported as daily Sharpe)\n"
                "- Risk-free rate assumption: 0% (excess return = raw return)\n"
                "- Invalid values: Scenarios with zero variance (constant returns) produce invalid Sharpe ratios (NaN or ±inf) and are excluded from all statistics\n"
                "- Validity check: Only finite values (not NaN, not ±inf) are included in mean, median, and percentile calculations"
            )
        }
    
    def _load_all_scenario_results(self) -> List[Dict[str, Any]]:
        """Load all scenario results from disk."""
        results = []
        if not self.results_store_path.exists():
            logger.warning(f"Results directory does not exist: {self.results_store_path}")
            return results
        
        for result_file in sorted(self.results_store_path.glob("scenario_*.json")):
            try:
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                    results.append(result_data)
            except Exception as e:
                logger.warning(f"Failed to load scenario result {result_file}: {e}")
        
        return results
    
    def _compute_data_fingerprint(
        self,
        scenario_results: List[Dict[str, Any]],
        memory_insights: Dict[str, List[Any]]
    ) -> str:
        """
        Compute deterministic fingerprint of input data.
        
        Used for validation that reports are generated from same inputs.
        """
        # Create hash of all scenario IDs and insight IDs
        scenario_ids = sorted([r.get("scenario_id", "unknown") for r in scenario_results])
        insight_ids = []
        for category, insights in memory_insights.items():
            for insight in insights:
                # insight is a StrategyInsight object
                insight_id = insight.insight_id if hasattr(insight, 'insight_id') else 'unknown'
                insight_ids.append(f"{category}:{insight_id}")
        
        fingerprint_data = {
            "scenario_ids": scenario_ids,
            "insight_ids": sorted(insight_ids),
            "iteration_id": snapshot.iteration_id
        }
        
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_json.encode()).hexdigest()[:16]
    
    def _compute_performance_metrics(self, scenario_results: List[Dict[str, Any]]) -> PerformanceMetrics:
        """Compute aggregate performance metrics."""
        if not scenario_results:
            return PerformanceMetrics(
                total_scenarios=0,
                avg_return_pct=0.0,
                avg_sharpe_ratio=0.0,
                avg_max_drawdown_pct=0.0,
                avg_win_rate=0.0,
                total_returns=[],
                min_return_pct=0.0,
                max_return_pct=0.0
            )
        
        # Extract all campaign results
        all_returns = []
        all_sharpes = []
        all_drawdowns = []
        all_win_rates = []
        
        for scenario_result in scenario_results:
            campaigns = scenario_result.get("results", [])
            for campaign in campaigns:
                all_returns.append(campaign.get("total_return_pct", 0.0))
                all_sharpes.append(campaign.get("sharpe_ratio", 0.0))
                all_drawdowns.append(campaign.get("max_drawdown_pct", 0.0))
                all_win_rates.append(campaign.get("win_rate", 0.0))
        
        if not all_returns:
            return PerformanceMetrics(
                total_scenarios=len(scenario_results),
                avg_return_pct=0.0,
                avg_sharpe_ratio=0.0,
                avg_max_drawdown_pct=0.0,
                avg_win_rate=0.0,
                total_returns=[],
                min_return_pct=0.0,
                max_return_pct=0.0
            )
        
        return PerformanceMetrics(
            total_scenarios=len(scenario_results),
            avg_return_pct=sum(all_returns) / len(all_returns),
            avg_sharpe_ratio=sum(all_sharpes) / len(all_sharpes) if all_sharpes else 0.0,
            avg_max_drawdown_pct=sum(all_drawdowns) / len(all_drawdowns) if all_drawdowns else 0.0,
            avg_win_rate=sum(all_win_rates) / len(all_win_rates) if all_win_rates else 0.0,
            total_returns=all_returns,
            min_return_pct=min(all_returns),
            max_return_pct=max(all_returns)
        )
    
    def _build_confirmed_insights(self, memory_insights: Dict[str, Any]) -> List[ReportInsight]:
        """Build list of confirmed insights, sorted by confidence (descending)."""
        insights = []
        
        # Extract insights from memory_insights (now StrategyInsight objects)
        # Structure: {"winning_patterns": [StrategyInsight, ...], "failure_modes": [...], "regime_heuristics": [...]}
        insight_lists = {
            "winning_pattern": memory_insights.get("winning_patterns", []),
            "failure_mode": memory_insights.get("failure_modes", []),
            "regime_heuristic": memory_insights.get("regime_heuristics", [])
        }
        
        for category, insight_list in insight_lists.items():
            for insight_obj in insight_list:
                # insight_obj is a StrategyInsight Pydantic model
                confidence_meta = insight_obj.confidence_metadata
                # Determine strength from confidence
                confidence = insight_obj.confidence
                if confidence >= 0.7:
                    strength = InsightStrength.STRONG
                elif confidence >= 0.5:
                    strength = InsightStrength.MODERATE
                else:
                    strength = InsightStrength.WEAK
                
                # Determine evidence status (gating: STRONG requires >=3 scenarios AND >=2 regimes)
                scenario_count = confidence_meta.num_supporting_scenarios
                regime_coverage = confidence_meta.regime_coverage
                regime_count = len(regime_coverage)
                
                if scenario_count >= 3 and regime_count >= 2:
                    evidence_status = InsightEvidenceStatus.STRONG
                else:
                    evidence_status = InsightEvidenceStatus.PRELIMINARY
                
                insight = ReportInsight(
                    insight_id=insight_obj.insight_id,
                    insight_type=insight_obj.insight_type,
                    description=insight_obj.description,
                    confidence=confidence,
                    strength=strength,
                    evidence_status=evidence_status,
                    scenario_count=scenario_count,
                    regime_coverage=regime_coverage,
                    regime_coverage_count=regime_count,
                    discovered_at=insight_obj.discovered_at.isoformat() if hasattr(insight_obj.discovered_at, 'isoformat') else str(insight_obj.discovered_at),
                    has_contradictions=confidence_meta.has_been_contradicted
                )
                insights.append(insight)
        
        # Sort by confidence (descending) for deterministic ordering
        insights.sort(key=lambda x: (x.confidence, x.insight_id), reverse=True)
        
        return insights
    
    def _build_known_unknowns(
        self,
        memory_insights: Dict[str, Any],
        scenario_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Build list of known unknowns (weak insights and coverage gaps)."""
        unknowns = []
        
        # Extract insights from memory_insights dict structure
        insight_lists = {
            "winning_pattern": memory_insights.get("winning_patterns", []),
            "failure_mode": memory_insights.get("failure_modes", []),
            "regime_heuristic": memory_insights.get("regime_heuristics", [])
        }
        
        # Weak insights (low confidence)
        for category, insight_list in insight_lists.items():
            for insight_obj in insight_list:
                # insight_obj is a StrategyInsight Pydantic model
                confidence = insight_obj.confidence
                description = insight_obj.description
                
                if confidence < 0.5:
                    unknowns.append(f"Weak insight: {description} (confidence: {confidence:.2f})")
        
        # Coverage gaps
        coverage = self.regime_ontology.get_regime_coverage(scenario_results)
        all_regimes = self.regime_ontology.get_all_regime_combinations()
        uncovered_regimes = [r for r in all_regimes if r.regime_id() not in coverage]
        
        if uncovered_regimes:
            unknowns.append(f"{len(uncovered_regimes)} regime combinations remain unexplored")
        
        return unknowns
    
    def _build_failure_boundaries(self, sensitivity_analysis: Dict[str, Any]) -> List[FailureBoundary]:
        """Build list of failure boundaries from sensitivity analysis."""
        boundaries = []
        
        high_sensitivity = sensitivity_analysis.get("high_sensitivity_params", {})
        
        for param_name, param_data in high_sensitivity.items():
            boundary_analysis = param_data.get("boundary_analysis", {})
            
            if boundary_analysis.get("boundary_detected", False):
                # Performance cliffs
                for cliff in boundary_analysis.get("performance_cliffs", []):
                    boundary = FailureBoundary(
                        parameter_name=param_name,
                        boundary_type="performance_cliff",
                        param_value=cliff.get("param_value_after"),
                        return_before=cliff.get("return_before"),
                        return_after=cliff.get("return_after"),
                        drop_magnitude=cliff.get("drop_magnitude"),
                        description=f"Performance cliff at {param_name}={cliff.get('param_value_after')}: {cliff.get('drop_magnitude', 0):.1f}% drop"
                    )
                    boundaries.append(boundary)
                
                # Failure thresholds
                for threshold in boundary_analysis.get("failure_thresholds", []):
                    boundary = FailureBoundary(
                        parameter_name=param_name,
                        boundary_type="failure_threshold",
                        param_value=threshold.get("param_value"),
                        return_before=threshold.get("return_before"),
                        return_after=threshold.get("return_after"),
                        description=f"Failure threshold at {param_name}={threshold.get('param_value')}: return crosses into negative"
                    )
                    boundaries.append(boundary)
        
        return boundaries
    
    def _build_regime_coverage(self, scenario_results: List[Dict[str, Any]]) -> List[RegimeCoverageEntry]:
        """Build regime coverage analysis."""
        coverage_dict = self.regime_ontology.get_regime_coverage(scenario_results)
        all_regimes = self.regime_ontology.get_all_regime_combinations()
        
        total_scenarios = len(scenario_results)
        
        coverage_entries = []
        for regime in all_regimes:
            regime_id = regime.regime_id()
            scenario_count = coverage_dict.get(regime_id, 0)
            coverage_pct = (scenario_count / total_scenarios * 100) if total_scenarios > 0 else 0.0
            
            entry = RegimeCoverageEntry(
                regime_id=regime_id,
                regime_description=regime.description,
                scenario_count=scenario_count,
                coverage_percentage=coverage_pct
            )
            coverage_entries.append(entry)
        
        # Sort by coverage percentage (descending) for deterministic ordering
        coverage_entries.sort(key=lambda x: (x.coverage_percentage, x.regime_id), reverse=True)
        
        return coverage_entries
    
    def _build_recommended_experiments(
        self,
        memory_insights: Dict[str, List[Any]],
        scenario_results: List[Dict[str, Any]]
    ) -> List[RecommendedExperiment]:
        """Build recommended experiments from proposal agent."""
        existing_scenarios = [r.get("scenario_id", "") for r in scenario_results]
        insights_for_proposals = self.memory_agent.get_insights_for_scenario_generation()
        regime_coverage = self.regime_ontology.get_regime_coverage(scenario_results)
        
        proposals = self.proposal_agent.generate_proposals(
            existing_scenarios=existing_scenarios,
            memory_insights=insights_for_proposals,
            existing_regime_coverage=regime_coverage,
            limit=10
        )
        
        experiments = []
        for proposal in proposals:
            experiment = RecommendedExperiment(
                proposal_id=proposal.proposal_id,
                proposal_type=proposal.proposal_type,
                title=proposal.title,
                description=proposal.description,
                expected_info_gain=proposal.expected_info_gain,
                priority=proposal.priority,
                reasoning=proposal.reasoning,
                based_on_insights=proposal.based_on_insights
            )
            experiments.append(experiment)
        
        # Already sorted by expected_info_gain (descending) from proposal agent
        return experiments
    
    def _build_executive_summary(
        self,
        performance_metrics: PerformanceMetrics,
        confirmed_insights: List[ReportInsight],
        failure_boundaries: List[FailureBoundary],
        regime_coverage: List[RegimeCoverageEntry],
        iteration_snapshot: Optional[ResearchIterationSnapshot] = None
    ) -> str:
        """Build executive summary text."""
        summary_parts = []
        
        # Performance summary with more detail
        median_return = 0.0
        if performance_metrics.total_returns:
            sorted_returns = sorted(performance_metrics.total_returns)
            median_return = sorted_returns[len(sorted_returns) // 2]
        
        summary_parts.append(
            f"This report analyzes {performance_metrics.total_scenarios} scenarios with an average return of "
            f"{performance_metrics.avg_return_pct:.2f}% (median: {median_return:.2f}%, "
            f"range: {performance_metrics.min_return_pct:.2f}% to {performance_metrics.max_return_pct:.2f}%)."
        )
        
        # Date range if available
        if iteration_snapshot and iteration_snapshot.overall_stats.date_range_start:
            summary_parts.append(
                f"Data covers {iteration_snapshot.overall_stats.date_range_start} to "
                f"{iteration_snapshot.overall_stats.date_range_end}."
            )
        
        # Best/worst scenario
        if iteration_snapshot and iteration_snapshot.scenario_results:
            sorted_scenarios = sorted(iteration_snapshot.scenario_results, key=lambda x: x.sort_key())
            best = sorted_scenarios[0]
            worst = sorted_scenarios[-1]
            summary_parts.append(
                f"Best scenario: {best.identity.symbol} ({best.metrics.total_return_pct:.2f}% return). "
                f"Worst scenario: {worst.identity.symbol} ({worst.metrics.total_return_pct:.2f}% return)."
            )
        
        # Insights summary
        strong_insights = [i for i in confirmed_insights if i.strength == InsightStrength.STRONG]
        summary_parts.append(
            f"Analysis identified {len(confirmed_insights)} total insights, including {len(strong_insights)} "
            f"high-confidence findings."
        )
        
        # Top 3 insights
        if confirmed_insights:
            top_3 = confirmed_insights[:3]
            insights_desc = ", ".join([f"{i.insight_id[:12]}... (conf: {i.confidence:.2f})" for i in top_3])
            summary_parts.append(f"Top insights: {insights_desc}.")
        
        # Biggest uncertainty (weakest insight or largest variance)
        weak_insights = [i for i in confirmed_insights if i.strength == InsightStrength.WEAK]
        if weak_insights:
            weakest = weak_insights[0]  # Already sorted by confidence
            summary_parts.append(
                f"Biggest uncertainty: {weakest.insight_id[:12]}... (confidence: {weakest.confidence:.2f})."
            )
        
        # Failure boundaries summary
        if failure_boundaries:
            summary_parts.append(
                f"Failure boundary analysis detected {len(failure_boundaries)} performance cliffs or failure thresholds."
            )
        
        # Regime coverage summary
        covered_regimes = [r for r in regime_coverage if r.scenario_count > 0]
        summary_parts.append(
            f"Regime coverage: {len(covered_regimes)} of {len(regime_coverage)} regime combinations tested."
        )
        
        return " ".join(summary_parts)


# Singleton instance
_report_generator: Optional[ReportGenerator] = None


def get_report_generator(
    memory_store_path: Optional[str] = None,
    data_root: Optional[str] = None
) -> ReportGenerator:
    """Get or create report generator instance."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator(memory_store_path, data_root)
    return _report_generator

