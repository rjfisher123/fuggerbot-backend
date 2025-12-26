"""
Proposal Agent - Research Loop Component.

Suggests what to test next based on accumulated learning.
Ranks proposals by expected information gain.
"""
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)


class ExperimentProposal(BaseModel):
    """
    A proposal for a new experiment/scenario to run.
    """
    proposal_id: str = Field(..., description="Unique identifier")
    proposal_type: str = Field(..., description="Type: 'parameter_sweep', 'regime_test', 'hypothesis_test'")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed description")
    
    # Expected information gain
    expected_info_gain: float = Field(..., ge=0.0, description="Expected information gain (0-1)")
    priority: int = Field(..., ge=1, le=10, description="Priority (1-10, 10 = highest)")
    
    # Scenario parameters
    scenario_spec: Dict[str, Any] = Field(..., description="Scenario specification")
    
    # Reasoning
    reasoning: str = Field(..., description="Why this proposal is valuable")
    based_on_insights: List[str] = Field(default_factory=list, description="Insight IDs that informed this")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)


class ProposalAgent:
    """
    Generates experiment proposals based on accumulated learning.
    """
    
    def __init__(self):
        """Initialize proposal agent."""
        logger.info("ProposalAgent initialized")
    
    def generate_proposals(
        self,
        existing_scenarios: List[str],
        memory_insights: Dict[str, Any],
        existing_regime_coverage: Optional[Dict[str, int]] = None,
        limit: int = 5
    ) -> List[ExperimentProposal]:
        """
        Generate experiment proposals ranked by information gain.
        
        Args:
            existing_scenarios: List of scenario IDs already tested
            memory_insights: Insights from memory agent
            existing_regime_coverage: Dict mapping regime_id to count of scenarios
            limit: Maximum number of proposals to generate
        
        Returns:
            List of experiment proposals, sorted by expected information gain
        """
        proposals = []
        
        # Strategy 1: Parameter gaps (unexplored combinations)
        proposals.extend(self._propose_parameter_gaps(existing_scenarios, memory_insights))
        
        # Strategy 2: Regime-focused tests (based on failure modes and coverage gaps)
        proposals.extend(self._propose_regime_tests(memory_insights, existing_regime_coverage))
        
        # Strategy 3: Hypothesis-driven (based on insights)
        proposals.extend(self._propose_hypothesis_tests(memory_insights))
        
        # Strategy 4: Uncertainty reduction (test weak insights)
        proposals.extend(self._propose_uncertainty_reduction(memory_insights))
        
        # Rank by expected information gain (not priority)
        proposals = self._rank_by_information_gain(proposals, memory_insights, existing_regime_coverage)
        
        # Limit results
        proposals = proposals[:limit]
        
        logger.info(f"Generated {len(proposals)} experiment proposals (ranked by information gain)")
        return proposals
    
    def _propose_parameter_gaps(
        self,
        existing_scenarios: List[str],
        insights: Dict[str, Any]
    ) -> List[ExperimentProposal]:
        """Propose experiments to fill parameter space gaps."""
        proposals = []
        
        # Example: If we've tested trust thresholds 0.55-0.75, propose 0.85
        # This is simplified - real implementation would analyze parameter space coverage
        
        proposal = ExperimentProposal(
            proposal_id=f"param_gap_{datetime.now().timestamp()}",
            proposal_type="parameter_sweep",
            title="High Trust Threshold Test",
            description="Test trust_threshold=0.85 to explore conservative parameter space",
            expected_info_gain=0.6,
            priority=7,
            scenario_spec={
                "trust_threshold": 0.85,
                "param_type": "trust_sweep"
            },
            reasoning="Current tests cover 0.55-0.75 range. High threshold may reveal tradeoffs between safety and opportunity.",
            based_on_insights=[]
        )
        proposals.append(proposal)
        
        return proposals
    
    def _propose_regime_tests(
        self,
        insights: Dict[str, Any],
        regime_coverage: Optional[Dict[str, int]] = None
    ) -> List[ExperimentProposal]:
        """Propose regime-specific stress tests based on failures and coverage gaps."""
        proposals = []
        
        # Check for failure modes in specific regimes
        failure_modes = insights.get("failure_modes", [])
        
        for failure in failure_modes:
            regimes = failure.get("regimes", [])
            if regimes:
                # High information gain if we can understand why failures occur
                info_gain = 0.8
                
                proposal = ExperimentProposal(
                    proposal_id=f"regime_test_{datetime.now().timestamp()}",
                    proposal_type="regime_test",
                    title=f"Deep Dive: {regimes[0]}",
                    description=f"Focused test in {regimes[0]} regime where failures occurred",
                    expected_info_gain=info_gain,
                    priority=int(info_gain * 10),
                    scenario_spec={
                        "regime_focus": regimes[0],
                        "test_type": "stress_test"
                    },
                    reasoning=f"Previous failures in {regimes[0]} suggest need for regime-specific understanding",
                    based_on_insights=[failure.get("insight_id", "")]
                )
                proposals.append(proposal)
        
        # Propose tests for under-explored regimes (if regime_coverage provided)
        if regime_coverage:
            from agents.research.regime_ontology import get_regime_ontology
            ontology = get_regime_ontology()
            all_regimes = ontology.get_all_regime_combinations()
            
            for regime in all_regimes:
                regime_id = regime.regime_id()
                coverage_count = regime_coverage.get(regime_id, 0)
                
                # High information gain for unexplored regimes
                if coverage_count == 0:
                    info_gain = 0.7
                    proposal = ExperimentProposal(
                        proposal_id=f"coverage_gap_{datetime.now().timestamp()}",
                        proposal_type="regime_test",
                        title=f"Unexplored Regime: {regime_id}",
                        description=f"Test in unexplored regime: {regime.description}",
                        expected_info_gain=info_gain,
                        priority=int(info_gain * 10),
                        scenario_spec={
                            "regime": regime.to_dict(),
                            "test_type": "coverage_gap"
                        },
                        reasoning=f"Regime {regime_id} has not been tested yet - high information value",
                        based_on_insights=[]
                    )
                    proposals.append(proposal)
        
        return proposals
    
    def _propose_hypothesis_tests(self, insights: Dict[str, Any]) -> List[ExperimentProposal]:
        """Propose hypothesis-driven experiments to confirm/falsify insights."""
        proposals = []
        
        winning_patterns = insights.get("winning_patterns", [])
        failure_modes = insights.get("failure_modes", [])
        
        # Test high-confidence patterns (should be verified)
        for pattern in winning_patterns[:3]:  # Top 3 patterns
            confidence = pattern.get("confidence", 0)
            if confidence > 0.7:
                # Higher confidence = lower info gain (less uncertainty to reduce)
                # But still valuable to verify
                info_gain = 0.6 + (0.2 * (1.0 - confidence))
                
                proposal = ExperimentProposal(
                    proposal_id=f"hypothesis_{datetime.now().timestamp()}",
                    proposal_type="hypothesis_test",
                    title=f"Verify: {pattern.get('description', 'Pattern')[:50]}",
                    description=f"Test to verify/refute the hypothesis: {pattern.get('description', '')}",
                    expected_info_gain=info_gain,
                    priority=int(info_gain * 10),
                    scenario_spec={
                        "hypothesis": pattern.get("description", ""),
                        "test_type": "verification",
                        "target_confidence": confidence
                    },
                    reasoning=f"High-confidence pattern ({confidence:.2f}) should be verified across regimes",
                    based_on_insights=[pattern.get("insight_id", "")]
                )
                proposals.append(proposal)
        
        # Test failure modes (understand why they fail)
        for failure in failure_modes[:2]:  # Top 2 failure modes
            info_gain = 0.85  # High info gain - understanding failures is critical
            
            proposal = ExperimentProposal(
                proposal_id=f"failure_analysis_{datetime.now().timestamp()}",
                proposal_type="hypothesis_test",
                title=f"Understand Failure: {failure.get('description', '')[:50]}",
                description=f"Test to understand why this failure mode occurs: {failure.get('description', '')}",
                expected_info_gain=info_gain,
                priority=int(info_gain * 10),
                scenario_spec={
                    "failure_mode": failure.get("description", ""),
                    "test_type": "failure_analysis"
                },
                reasoning=f"Understanding failure modes reduces future risk",
                based_on_insights=[failure.get("insight_id", "")]
            )
            proposals.append(proposal)
        
        return proposals
    
    def _propose_uncertainty_reduction(self, insights: Dict[str, Any]) -> List[ExperimentProposal]:
        """Propose experiments to reduce uncertainty around weak insights."""
        proposals = []
        
        # Find weak insights (low confidence, few supporting scenarios)
        all_insights = []
        all_insights.extend(insights.get("winning_patterns", []))
        all_insights.extend(insights.get("regime_heuristics", []))
        
        weak_insights = [
            i for i in all_insights
            if i.get("confidence", 1.0) < 0.6 or i.get("is_weak", False)
        ]
        
        for insight in weak_insights[:2]:  # Top 2 weak insights
            confidence = insight.get("confidence", 0.5)
            
            # High information gain - can significantly reduce uncertainty
            info_gain = 0.7 + (0.3 * (0.6 - confidence))  # More uncertain = higher gain
            
            proposal = ExperimentProposal(
                proposal_id=f"uncertainty_{datetime.now().timestamp()}",
                proposal_type="uncertainty_reduction",
                title=f"Strengthen: {insight.get('description', '')[:50]}",
                description=f"Test to strengthen weak insight: {insight.get('description', '')}",
                expected_info_gain=info_gain,
                priority=int(info_gain * 10),
                scenario_spec={
                    "insight_id": insight.get("insight_id", ""),
                    "current_confidence": confidence,
                    "test_type": "uncertainty_reduction"
                },
                reasoning=f"Weak insight (confidence: {confidence:.2f}) needs more evidence",
                based_on_insights=[insight.get("insight_id", "")]
            )
            proposals.append(proposal)
        
        return proposals
    
    def _rank_by_information_gain(
        self,
        proposals: List[ExperimentProposal],
        insights: Dict[str, Any],
        regime_coverage: Optional[Dict[str, int]] = None
    ) -> List[ExperimentProposal]:
        """
        Rank proposals by expected information gain.
        
        Information gain factors:
        - Expected reduction in uncertainty
        - Coverage of under-explored regimes
        - Ability to confirm or falsify existing insights
        - NOT optimization for returns
        
        Args:
            proposals: List of proposals to rank
            insights: Memory insights
            regime_coverage: Current regime coverage
        
        Returns:
            List of proposals sorted by expected_info_gain (descending)
        """
        # Additional ranking factors beyond expected_info_gain
        
        for proposal in proposals:
            # Adjust info gain based on additional factors
            
            # Factor 1: Under-explored regime bonus
            if proposal.proposal_type == "regime_test":
                regime_id = proposal.scenario_spec.get("regime", {}).get("regime_id") or \
                           proposal.scenario_spec.get("regime_focus", "")
                if regime_coverage and regime_coverage.get(regime_id, 0) == 0:
                    proposal.expected_info_gain += 0.1  # Bonus for unexplored
            
            # Factor 2: Weak insight bonus (higher uncertainty reduction)
            if proposal.proposal_type == "uncertainty_reduction":
                current_conf = proposal.scenario_spec.get("current_confidence", 0.5)
                if current_conf < 0.4:
                    proposal.expected_info_gain += 0.15  # Very weak = very high gain
            
            # Factor 3: Failure mode analysis bonus (critical for understanding)
            if "failure" in proposal.title.lower() or "failure" in proposal.scenario_spec.get("test_type", ""):
                proposal.expected_info_gain += 0.1
            
            # Ensure info gain stays in valid range
            proposal.expected_info_gain = max(0.0, min(1.0, proposal.expected_info_gain))
            proposal.priority = int(proposal.expected_info_gain * 10)
        
        # Sort by expected_info_gain (descending)
        proposals.sort(key=lambda p: p.expected_info_gain, reverse=True)
        
        return proposals


# Singleton instance
_proposal_agent: Optional[ProposalAgent] = None


def get_proposal_agent() -> ProposalAgent:
    """Get or create proposal agent instance."""
    global _proposal_agent
    if _proposal_agent is None:
        _proposal_agent = ProposalAgent()
    return _proposal_agent

