"""
Research Loop Orchestrator - Canonical Execution Loop.

Transforms deterministic backtests into a learning-capable research engine.

Execution Loop:
    [Scenario Generator] → [Deterministic Simulator] → [Meta-Evaluator] → 
    [Memory & Insight Store] → [Proposal Agent] → (loop)

Each iteration increases knowledge, not randomness.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

from agents.research.scenario_generator import ScenarioGenerator, ScenarioDefinition, get_scenario_generator
from agents.research.meta_evaluator import MetaEvaluator, get_meta_evaluator
from agents.research.memory_agent import MemoryAgent, get_memory_agent
from agents.research.proposal_agent import ProposalAgent, get_proposal_agent
from agents.research.historonics_agent import HistoronicsAgent, get_historonics_agent
from agents.research.regime_ontology import get_regime_ontology
from daemon.simulator.war_games_runner import WarGamesRunner

logger = logging.getLogger(__name__)


class ResearchLoop:
    """
    Orchestrates the research loop execution.
    
    Maintains determinism while enabling comparative learning.
    """
    
    def __init__(
        self,
        memory_store_path: Optional[str] = None,
        results_store_path: Optional[str] = None
    ):
        """
        Initialize research loop.
        
        Args:
            memory_store_path: Path to strategy memory store
            results_store_path: Path to store scenario results
        """
        self.scenario_generator = get_scenario_generator()
        self.meta_evaluator = get_meta_evaluator()
        self.memory_agent = get_memory_agent(memory_store_path)
        self.proposal_agent = get_proposal_agent()
        self.historonics_agent = get_historonics_agent()  # Optional - may be None if LLM unavailable
        self.simulator = WarGamesRunner()
        
        if results_store_path is None:
            from pathlib import Path
            project_root = Path(__file__).parent.parent
            results_store_path = project_root / "data" / "research_results"
        self.results_store_path = Path(results_store_path)
        self.results_store_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ResearchLoop initialized (results: {self.results_store_path})")
    
    def run_iteration(
        self,
        scenario: Optional[ScenarioDefinition] = None,
        max_proposals: int = 3
    ) -> Dict[str, Any]:
        """
        Run one iteration of the research loop.
        
        Args:
            scenario: Optional scenario to run (if None, uses proposals)
            max_proposals: Maximum number of proposals to generate/execute
        
        Returns:
            Dict with iteration results
        """
        logger.info("=" * 60)
        logger.info("Starting Research Loop Iteration")
        logger.info("=" * 60)
        
        iteration_results = {
            "iteration_id": f"iter_{datetime.now().timestamp()}",
            "started_at": datetime.now().isoformat(),
            "scenarios_run": [],
            "insights_generated": [],
            "proposals_created": []
        }
        
        try:
            # Step 1: Generate or select scenario
            if scenario is None:
                # Get proposals from proposal agent
                existing_scenarios = self._get_existing_scenario_ids()
                insights = self.memory_agent.get_insights_for_scenario_generation()
                
                # Calculate regime coverage from existing scenarios
                regime_coverage = self._calculate_regime_coverage()
                
                proposals = self.proposal_agent.generate_proposals(
                    existing_scenarios=existing_scenarios,
                    memory_insights=insights,
                    existing_regime_coverage=regime_coverage,
                    limit=max_proposals
                )
                
                if not proposals:
                    # Fallback to baseline
                    logger.info("No proposals available, using baseline scenario")
                    scenario = self.scenario_generator.generate_baseline_scenario()
                else:
                    # Use top proposal (this would need proposal-to-scenario conversion)
                    logger.info(f"Using top proposal: {proposals[0].title}")
                    scenario = self.scenario_generator.generate_baseline_scenario()  # TODO: Convert proposal
            
            iteration_results["scenarios_run"].append(scenario.scenario_id)
            
            # Step 2: Run deterministic simulation
            logger.info(f"Running deterministic simulation for scenario: {scenario.scenario_id}")
            simulation_results = self._run_simulation(scenario)
            
            # Save results with scenario_id
            self._save_scenario_results(scenario.scenario_id, simulation_results)
            
            # Step 3: Meta-evaluation (compare with previous scenarios)
            logger.info("Running meta-evaluation...")
            comparison_results = self._evaluate_scenario(simulation_results)
            iteration_results["insights_generated"] = [c.insights for c in comparison_results]
            
            # Step 4: Update memory
            logger.info("Updating strategy memory...")
            for comparison in comparison_results:
                self.memory_agent.extract_insights_from_comparison(
                    comparison=comparison,
                    scenario_a_id=comparison.scenario_a_id,
                    scenario_b_id=comparison.scenario_b_id
                )
            
            # Step 5: Generate historical hypotheses (optional, advisory only)
            historonics_output = None
            if self.historonics_agent:
                try:
                    logger.info("Generating historical hypotheses...")
                    # Prepare data for Historonics Agent
                    insights_summary = self._prepare_insights_for_historonics()
                    regime_coverage = self._calculate_regime_coverage()
                    scenario_metadata = self._get_scenario_metadata()
                    report_summary = self._generate_simple_report_summary()
                    
                    historonics_output = self.historonics_agent.generate_hypotheses(
                        report_summary=report_summary,
                        insights=insights_summary,
                        regime_coverage=regime_coverage,
                        scenario_metadata=scenario_metadata,
                        iteration_id=iteration_results.get("iteration_id")
                    )
                    iteration_results["historonics_hypotheses"] = len(historonics_output.hypotheses) if historonics_output else 0
                    logger.info(f"Generated {len(historonics_output.hypotheses) if historonics_output else 0} historical hypotheses")
                except Exception as e:
                    logger.warning(f"Historonics Agent failed (non-critical): {e}")
                    # Continue without Historonics output - it's advisory only
            
            # Step 6: Generate next proposals (for next iteration)
            logger.info("Generating next proposals...")
            existing_scenarios = self._get_existing_scenario_ids()
            insights = self.memory_agent.get_insights_for_scenario_generation()
            # Calculate regime coverage from existing scenarios
            regime_coverage = self._calculate_regime_coverage()
            
            proposals = self.proposal_agent.generate_proposals(
                existing_scenarios=existing_scenarios,
                memory_insights=insights,
                existing_regime_coverage=regime_coverage,
                limit=max_proposals
            )
            iteration_results["proposals_created"] = [
                {"title": p.title, "priority": p.priority} for p in proposals
            ]
            
            iteration_results["completed_at"] = datetime.now().isoformat()
            iteration_results["success"] = True
            
            logger.info("=" * 60)
            logger.info("Research Loop Iteration Complete")
            logger.info(f"Scenarios run: {len(iteration_results['scenarios_run'])}")
            logger.info(f"Insights generated: {sum(len(i) for i in iteration_results['insights_generated'])}")
            logger.info(f"Proposals created: {len(iteration_results['proposals_created'])}")
            logger.info("=" * 60)
            
            return iteration_results
            
        except Exception as e:
            logger.error(f"Research loop iteration failed: {e}", exc_info=True)
            iteration_results["success"] = False
            iteration_results["error"] = str(e)
            return iteration_results
    
    def _run_simulation(self, scenario: ScenarioDefinition) -> Dict[str, Any]:
        """
        Run deterministic simulation for a scenario.
        
        Args:
            scenario: Scenario definition
        
        Returns:
            Simulation results dict
        """
        # Convert scenario to WarGamesRunner format
        # This is a simplified version - real implementation would handle all scenario types
        
        # For now, use baseline scenario structure
        # TODO: Full scenario conversion logic
        
        results = self.simulator.run_all_scenarios(
            output_path=self.results_store_path / f"scenario_{scenario.scenario_id}.json"
        )
        
        # Add scenario metadata (including regime classification)
        results["scenario_id"] = scenario.scenario_id
        results["scenario_name"] = scenario.scenario_name
        results["scenario_description"] = scenario.description
        
        # Include regime classification if present
        if scenario.regime_classification:
            results["regime_classification"] = scenario.regime_classification
        
        return results
    
    def _evaluate_scenario(
        self,
        current_results: Dict[str, Any]
    ) -> List[Any]:  # List[ScenarioComparison]
        """
        Evaluate current scenario against previous scenarios.
        
        Args:
            current_results: Current scenario results
        
        Returns:
            List of scenario comparisons
        """
        comparisons = []
        
        # Get previous scenario results
        previous_results = self._load_previous_scenario_results(current_results["scenario_id"])
        
        # Compare with each previous scenario
        for prev_result in previous_results[:5]:  # Compare with top 5 most recent
            comparison = self.meta_evaluator.compare_scenarios(
                scenario_a_results=prev_result,
                scenario_b_results=current_results
            )
            comparisons.append(comparison)
        
        return comparisons
    
    def _save_scenario_results(self, scenario_id: str, results: Dict[str, Any]) -> None:
        """Save scenario results to disk."""
        output_file = self.results_store_path / f"scenario_{scenario_id}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.debug(f"Saved scenario results to {output_file}")
    
    def _load_all_scenario_results(self) -> List[Dict[str, Any]]:
        """Load all scenario results."""
        all_results = []
        for result_file in sorted(self.results_store_path.glob("scenario_*.json"), reverse=True):
            try:
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                    all_results.append(result_data)
            except Exception as e:
                logger.warning(f"Failed to load scenario result {result_file}: {e}")
        return all_results
    
    def _load_previous_scenario_results(self, exclude_id: str) -> List[Dict[str, Any]]:
        """Load previous scenario results (excluding current)."""
        previous = []
        
        for result_file in sorted(self.results_store_path.glob("scenario_*.json"), reverse=True):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    if data.get("scenario_id") != exclude_id:
                        previous.append(data)
            except Exception as e:
                logger.warning(f"Error loading {result_file}: {e}")
        
        return previous
    
    def _get_existing_scenario_ids(self) -> List[str]:
        """Get list of existing scenario IDs."""
        scenario_ids = []
        
        for result_file in self.results_store_path.glob("scenario_*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    if "scenario_id" in data:
                        scenario_ids.append(data["scenario_id"])
            except Exception:
                pass
        
        return scenario_ids
    
    def _calculate_regime_coverage(self) -> Dict[str, int]:
        """
        Calculate regime coverage from existing scenario results.
        
        Returns:
            Dict mapping regime_id to count of scenarios
        """
        regime_ontology = get_regime_ontology()
        
        # Load all scenario results
        all_results = []
        for result_file in self.results_store_path.glob("scenario_*.json"):
            try:
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                    all_results.append(result_data)
            except Exception as e:
                logger.warning(f"Failed to load scenario result {result_file}: {e}")
        
        # Calculate coverage
        coverage = regime_ontology.get_regime_coverage(all_results)
        
        logger.debug(f"Regime coverage: {coverage}")
        return coverage
    
    def get_current_insights(self) -> Dict[str, Any]:
        """
        Get current accumulated insights.
        
        Returns:
            Dict with insights summary
        """
        insights = self.memory_agent.get_insights_for_scenario_generation()
        
        return {
            "total_insights": self.memory_agent.memory.total_insights,
            "winning_patterns": len(insights["winning_patterns"]),
            "failure_modes": len(insights["failure_modes"]),
            "regime_heuristics": len(insights["regime_heuristics"]),
            "insights": insights
        }
    
    def _prepare_insights_for_historonics(self) -> List[Dict[str, Any]]:
        """Prepare insights summary for Historonics Agent."""
        all_insights = self.memory_agent.get_all_insights()
        insights_summary = []
        
        for category in ["winning_patterns", "failure_modes", "regime_heuristics"]:
            for insight in all_insights.get(category, []):
                # Extract confidence metadata safely
                confidence_meta = getattr(insight, 'confidence_metadata', None)
                scenario_count = confidence_meta.num_supporting_scenarios if confidence_meta else 0
                regime_count = len(confidence_meta.regime_coverage) if confidence_meta and hasattr(confidence_meta, 'regime_coverage') else 0
                
                evidence_status = "strong" if (scenario_count >= 3 and regime_count >= 2) else "preliminary"
                
                insights_summary.append({
                    "insight_id": insight.insight_id if hasattr(insight, 'insight_id') else str(insight),
                    "description": insight.description if hasattr(insight, 'description') else "",
                    "confidence": insight.confidence if hasattr(insight, 'confidence') else 0.0,
                    "evidence_status": evidence_status
                })
        
        return insights_summary
    
    def _get_scenario_metadata(self) -> List[Dict[str, str]]:
        """Get scenario metadata (NO METRICS - just IDs and regime info)."""
        metadata = []
        for result_file in sorted(self.results_store_path.glob("scenario_*.json")):
            try:
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                    scenario_id = result_data.get("scenario_id", "unknown")
                    regime_classification = result_data.get("regime_classification", {})
                    regime_id = regime_classification.get("regime_id") if isinstance(regime_classification, dict) else None
                    
                    metadata.append({
                        "scenario_id": scenario_id,
                        "regime_id": regime_id or "unknown"
                    })
            except Exception as e:
                logger.warning(f"Failed to load scenario metadata {result_file}: {e}")
        
        return metadata
    
    def _generate_simple_report_summary(self) -> str:
        """Generate a simple text summary for Historonics Agent."""
        insights = self.memory_agent.get_all_insights()
        total_insights = (
            len(insights.get("winning_patterns", [])) +
            len(insights.get("failure_modes", [])) +
            len(insights.get("regime_heuristics", []))
        )
        
        scenario_count = len(self._get_existing_scenario_ids())
        regime_coverage = self._calculate_regime_coverage()
        covered_regimes = len([r for r in regime_coverage.values() if r > 0])
        
        summary = (
            f"Research summary: {scenario_count} scenarios tested, {total_insights} insights accumulated. "
            f"{covered_regimes} regimes have been explored. "
        )
        
        # Add brief insight highlights
        if insights.get("winning_patterns"):
            summary += f"{len(insights['winning_patterns'])} winning patterns identified. "
        if insights.get("failure_modes"):
            summary += f"{len(insights['failure_modes'])} failure modes documented. "
        
        return summary


# Singleton instance
_research_loop: Optional[ResearchLoop] = None


def get_research_loop(
    memory_store_path: Optional[str] = None,
    results_store_path: Optional[str] = None
) -> ResearchLoop:
    """Get or create research loop instance."""
    global _research_loop
    if _research_loop is None:
        _research_loop = ResearchLoop(memory_store_path, results_store_path)
    return _research_loop

