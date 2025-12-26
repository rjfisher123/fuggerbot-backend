"""
Memory & Insight Agent - Research Loop Component.

Accumulates learning over time. Persists winning parameter archetypes,
losing configurations, and regime-specific heuristics.

Key Rule: Memory informs future scenario generation, never past execution.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class InsightConfidence(BaseModel):
    """
    Confidence metadata for an insight.
    """
    num_supporting_scenarios: int = Field(default=1, ge=1, description="Number of scenarios supporting this insight")
    regime_coverage: List[str] = Field(default_factory=list, description="List of regime IDs where this holds")
    parameter_robustness: float = Field(default=0.5, ge=0.0, le=1.0, description="Does it hold under small parameter perturbations?")
    has_been_contradicted: bool = Field(default=False, description="Has any scenario contradicted this insight?")
    contradiction_count: int = Field(default=0, ge=0, description="Number of times contradicted")
    last_contradiction_at: Optional[datetime] = Field(default=None, description="When last contradicted")
    
    def compute_overall_confidence(self) -> float:
        """
        Compute overall confidence score from components.
        
        Higher confidence when:
        - More supporting scenarios
        - Better regime coverage
        - Higher parameter robustness
        - No contradictions
        
        Returns:
            Confidence score (0-1)
        """
        base_confidence = min(1.0, 0.3 + (self.num_supporting_scenarios * 0.1))
        
        # Regime coverage bonus
        regime_bonus = min(0.2, len(self.regime_coverage) * 0.05)
        
        # Parameter robustness bonus
        robustness_bonus = self.parameter_robustness * 0.2
        
        # Contradiction penalty
        contradiction_penalty = min(0.3, self.contradiction_count * 0.1)
        
        confidence = base_confidence + regime_bonus + robustness_bonus - contradiction_penalty
        return max(0.0, min(1.0, confidence))


class StrategyInsight(BaseModel):
    """
    A learned insight about strategy performance with confidence scoring.
    """
    insight_id: str = Field(..., description="Unique identifier for this insight")
    insight_type: str = Field(..., description="Type: 'winning_pattern', 'failure_mode', 'regime_heuristic'")
    description: str = Field(..., description="Human-readable insight description")
    
    # Context
    scenario_ids: List[str] = Field(default_factory=list, description="Scenario IDs that contributed to this insight")
    regimes: List[str] = Field(default_factory=list, description="Regimes where this insight applies")
    
    # Evidence
    evidence_metrics: Dict[str, float] = Field(default_factory=dict, description="Supporting metrics")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in this insight")
    
    # Enhanced confidence metadata
    confidence_metadata: InsightConfidence = Field(default_factory=InsightConfidence, description="Detailed confidence scoring")
    
    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    use_count: int = Field(default=0, description="How many times this insight has been used")
    is_weak: bool = Field(default=False, description="Flag for weak support insights")
    
    def update_confidence(self) -> None:
        """Update confidence score from metadata."""
        self.confidence = self.confidence_metadata.compute_overall_confidence()
        self.is_weak = self.confidence < 0.5


class StrategyMemory(BaseModel):
    """
    Complete strategy memory store.
    """
    winning_archetypes: List[StrategyInsight] = Field(default_factory=list)
    failure_modes: List[StrategyInsight] = Field(default_factory=list)
    regime_heuristics: List[StrategyInsight] = Field(default_factory=list)
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    total_insights: int = Field(default=0)
    version: str = Field(default="1.0.0")


    def update_insight_confidence(
        self,
        insight_id: str,
        scenario_id: Optional[str] = None,
        regime_id: Optional[str] = None,
        contradicts: bool = False,
        parameter_robustness: Optional[float] = None
    ) -> Optional[StrategyInsight]:
        """
        Update insight confidence metadata based on new evidence.
        
        Args:
            insight_id: ID of insight to update
            scenario_id: New scenario ID that supports/contradicts
            regime_id: Regime ID where this was observed
            contradicts: True if this scenario contradicts the insight
            parameter_robustness: Updated robustness score (0-1)
        
        Returns:
            Updated insight or None if not found
        """
        # Find insight
        insight = None
        for category in ['winning_archetypes', 'failure_modes', 'regime_heuristics']:
            insights_list = getattr(self.memory, category)
            for i in insights_list:
                if i.insight_id == insight_id:
                    insight = i
                    break
            if insight:
                break
        
        if not insight:
            logger.warning(f"Insight {insight_id} not found for confidence update")
            return None
        
        # Update confidence metadata
        if contradicts:
            insight.confidence_metadata.has_been_contradicted = True
            insight.confidence_metadata.contradiction_count += 1
            insight.confidence_metadata.last_contradiction_at = datetime.now()
        else:
            if scenario_id and scenario_id not in insight.scenario_ids:
                insight.scenario_ids.append(scenario_id)
                insight.confidence_metadata.num_supporting_scenarios += 1
            
            if regime_id and regime_id not in insight.confidence_metadata.regime_coverage:
                insight.confidence_metadata.regime_coverage.append(regime_id)
        
        if parameter_robustness is not None:
            insight.confidence_metadata.parameter_robustness = parameter_robustness
        
        # Recompute confidence
        insight.update_confidence()
        insight.last_updated = datetime.now()
        
        # Persist
        self._save_memory()
        
        logger.info(f"Updated insight {insight_id} confidence: {insight.confidence:.2f}")
        return insight


class MemoryAgent:
    """
    Manages strategy memory and insights.
    
    Maintains an append-only strategy memory store.
    """
    
    def __init__(self, memory_store_path: Optional[str] = None):
        """
        Initialize memory agent.
        
        Args:
            memory_store_path: Path to memory store JSON file
        """
        if memory_store_path is None:
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent.parent
            memory_store_path = project_root / "data" / "strategy_memory.json"
        
        self.memory_store_path = Path(memory_store_path)
        self.memory_store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing memory
        self.memory = self._load_memory()
        logger.info(f"MemoryAgent initialized (store: {self.memory_store_path}, {self.memory.total_insights} insights)")
    
    def add_insight(
        self,
        insight_type: str,
        description: str,
        scenario_ids: List[str],
        regimes: List[str],
        evidence_metrics: Dict[str, float],
        confidence: Optional[float] = None,
        confidence_metadata: Optional[InsightConfidence] = None
    ) -> StrategyInsight:
        """
        Add a new insight to memory.
        
        Args:
            insight_type: Type of insight ('winning_pattern', 'failure_mode', 'regime_heuristic')
            description: Human-readable description
            scenario_ids: Scenario IDs that support this insight
            regimes: Regimes where this applies
            evidence_metrics: Supporting metrics
            confidence: Confidence level (0-1)
        
        Returns:
            Created StrategyInsight
        """
        insight_id = f"{insight_type}_{datetime.now().timestamp()}"
        
        # Create or use provided confidence metadata
        if confidence_metadata is None:
            confidence_metadata = InsightConfidence(
                num_supporting_scenarios=len(scenario_ids),
                regime_coverage=regimes,
                parameter_robustness=0.5  # Default, can be updated later
            )
        
        # Compute confidence if not provided
        if confidence is None:
            confidence = confidence_metadata.compute_overall_confidence()
        
        insight = StrategyInsight(
            insight_id=insight_id,
            insight_type=insight_type,
            description=description,
            scenario_ids=scenario_ids,
            regimes=regimes,
            evidence_metrics=evidence_metrics,
            confidence=confidence,
            confidence_metadata=confidence_metadata
        )
        
        # Update confidence from metadata
        insight.update_confidence()
        
        # Add to appropriate category
        if insight_type == "winning_pattern":
            self.memory.winning_archetypes.append(insight)
        elif insight_type == "failure_mode":
            self.memory.failure_modes.append(insight)
        elif insight_type == "regime_heuristic":
            self.memory.regime_heuristics.append(insight)
        
        self.memory.total_insights += 1
        self.memory.last_updated = datetime.now()
        
        # Persist
        self._save_memory()
        
        logger.info(f"Added insight: {description[:50]}... (confidence: {confidence:.2f})")
        return insight
    
    def get_insights_for_scenario_generation(self) -> Dict[str, Any]:
        """
        Get insights formatted for scenario generation.
        
        Returns:
            Dict with insights organized by type
        """
        return {
            "winning_patterns": [
                {
                    "description": i.description,
                    "confidence": i.confidence,
                    "regimes": i.regimes,
                    "metrics": i.evidence_metrics
                }
                for i in self.memory.winning_archetypes
                if i.confidence > 0.6  # Only high-confidence insights
            ],
            "failure_modes": [
                {
                    "description": i.description,
                    "regimes": i.regimes,
                    "metrics": i.evidence_metrics
                }
                for i in self.memory.failure_modes
            ],
            "regime_heuristics": [
                {
                    "description": i.description,
                    "regimes": i.regimes,
                    "confidence": i.confidence
                }
                for i in self.memory.regime_heuristics
            ]
        }
    
    def extract_insights_from_comparison(
        self,
        comparison: Any,  # ScenarioComparison from meta_evaluator
        scenario_a_id: str,
        scenario_b_id: str
    ) -> List[StrategyInsight]:
        """
        Extract insights from a scenario comparison.
        
        Args:
            comparison: ScenarioComparison object
            scenario_a_id: First scenario ID
            scenario_b_id: Second scenario ID
        
        Returns:
            List of extracted insights
        """
        insights = []
        
        # Extract insights from comparison
        for insight_text in comparison.insights:
            # Determine insight type from content
            if "performs" in insight_text.lower() and "better" in insight_text.lower():
                insight_type = "winning_pattern"
                confidence = 0.7
            elif "fails" in insight_text.lower() or "collapse" in insight_text.lower():
                insight_type = "failure_mode"
                confidence = 0.8
            else:
                insight_type = "regime_heuristic"
                confidence = 0.6
            
            insight = self.add_insight(
                insight_type=insight_type,
                description=insight_text,
                scenario_ids=[scenario_a_id, scenario_b_id],
                regimes=[comparison.regime_dependency] if comparison.regime_dependency else [],
                evidence_metrics={
                    "return_delta": comparison.return_delta,
                    "sharpe_delta": comparison.sharpe_delta,
                    "drawdown_delta": comparison.drawdown_delta
                },
                confidence=confidence
            )
            insights.append(insight)
        
        return insights
    
    def _load_memory(self) -> StrategyMemory:
        """Load memory from disk."""
        if not self.memory_store_path.exists():
            return StrategyMemory()
        
        try:
            with open(self.memory_store_path, 'r') as f:
                data = json.load(f)
            
            # Convert timestamps
            for category in ['winning_archetypes', 'failure_modes', 'regime_heuristics']:
                for item in data.get(category, []):
                    if 'discovered_at' in item:
                        item['discovered_at'] = datetime.fromisoformat(item['discovered_at'])
                    if 'last_updated' in item:
                        item['last_updated'] = datetime.fromisoformat(item['last_updated'])
            
            if 'last_updated' in data:
                data['last_updated'] = datetime.fromisoformat(data['last_updated'])
            
            return StrategyMemory(**data)
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return StrategyMemory()
    
    def _save_memory(self) -> None:
        """Save memory to disk."""
        try:
            # Convert to dict and handle datetime serialization
            data = self.memory.model_dump(mode='json')
            
            with open(self.memory_store_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Memory saved to {self.memory_store_path}")
        except Exception as e:
            logger.error(f"Error saving memory: {e}")


# Singleton instance
_memory_agent: Optional[MemoryAgent] = None


def get_memory_agent(memory_store_path: Optional[str] = None) -> MemoryAgent:
    """Get or create memory agent instance."""
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent(memory_store_path)
    return _memory_agent

