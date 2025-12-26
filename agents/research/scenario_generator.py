"""
Scenario Generator Agent - Research Loop Component.

Generates new parameter sets and scenario definitions with versioning.
All variations are explicit, parameterized, and logged.

Core Principle: No randomness in execution. All variation is declarative.
"""
import logging
import hashlib
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from dataclasses import dataclass, asdict

from agents.research.regime_ontology import get_regime_ontology

logger = logging.getLogger(__name__)


@dataclass
class TradingParams:
    """Trading strategy parameters (replicated from war_games_runner for independence)."""
    trust_threshold: float = 0.65
    min_confidence: float = 0.75
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss: float = 0.05  # 5% stop loss
    take_profit: float = 0.15  # 15% take profit
    cooldown_days: int = 2  # Days to wait after a trade
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScenarioDefinition(BaseModel):
    """
    Complete scenario definition with versioning and regime classification.
    """
    scenario_id: str = Field(..., description="Unique hash identifier for this scenario")
    scenario_name: str = Field(..., description="Human-readable scenario name")
    
    # Temporal bounds
    start_date: str = Field(..., description="Scenario start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Scenario end date (YYYY-MM-DD)")
    description: str = Field(..., description="Scenario description (regime, volatility, etc.)")
    
    # Regime classification (explicit, deterministic)
    regime_classification: Optional[Dict[str, str]] = Field(default=None, description="Explicit regime classification")
    
    # Symbols to test
    symbols: List[str] = Field(..., description="List of symbols to test in this scenario")
    
    # Parameter sets
    param_sets: Dict[str, Dict[str, Any]] = Field(..., description="Parameter sets to test (name -> params dict)")
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now, description="When this scenario was generated")
    generator_version: str = Field(default="1.0.0", description="Version of scenario generator")
    parent_scenario_id: Optional[str] = Field(default=None, description="Parent scenario if this is a variant")
    
    def compute_id(self) -> str:
        """Compute deterministic scenario ID from parameters."""
        # Create hash from all scenario parameters (including regime classification)
        hash_data = {
            "name": self.scenario_name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "symbols": sorted(self.symbols),
            "param_sets": {k: sorted(v.items()) for k, v in sorted(self.param_sets.items())},
            "generator_version": self.generator_version
        }
        
        # Include regime classification in hash if present
        if self.regime_classification:
            hash_data["regime"] = sorted(self.regime_classification.items())
        
        hash_input = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def model_post_init(self, __context: Any) -> None:
        """Compute scenario_id after model initialization."""
        if not self.scenario_id or self.scenario_id == "":
            # Compute and set scenario_id
            computed_id = self.compute_id()
            object.__setattr__(self, 'scenario_id', computed_id)


class ScenarioGenerator:
    """
    Generates new parameter sets and scenario definitions.
    
    All variations are explicit and logged. No randomness during execution.
    """
    
    def __init__(self, memory_store_path: Optional[str] = None):
        """
        Initialize scenario generator.
        
        Args:
            memory_store_path: Path to memory store for learning-informed generation
        """
        if memory_store_path is None:
            from pathlib import Path
            memory_store_path = Path("data/research_memory.json")
        
        self.memory_store_path = memory_store_path
        logger.info(f"ScenarioGenerator initialized (memory: {memory_store_path})")
    
    def generate_baseline_scenario(self) -> ScenarioDefinition:
        """
        Generate the baseline scenario (original 36-campaign setup).
        
        This is deterministic and always produces the same scenario.
        """
        regime_ontology = get_regime_ontology()
        
        # Classify baseline scenario
        baseline_regime = regime_ontology.classify_scenario(
            scenario_name="Baseline Suite",
            start_date="2021-01-01",
            end_date="2023-12-31",
            description="Baseline deterministic scenario suite"
        )
        
        return ScenarioDefinition(
            scenario_id="",  # Will be computed
            scenario_name="Baseline Suite",
            start_date="2021-01-01",  # Will be overridden by individual scenarios
            end_date="2023-12-31",
            description="Baseline deterministic scenario suite",
            regime_classification=baseline_regime.to_dict(),
            symbols=["BTC-USD", "ETH-USD", "NVDA", "MSFT"],
            param_sets={
                "Aggressive": TradingParams(
                    trust_threshold=0.55,
                    min_confidence=0.70,
                    max_position_size=0.15,
                    stop_loss=0.08,
                    take_profit=0.20
                ).to_dict(),
                "Balanced": TradingParams(
                    trust_threshold=0.65,
                    min_confidence=0.75,
                    max_position_size=0.10,
                    stop_loss=0.05,
                    take_profit=0.15
                ).to_dict(),
                "Conservative": TradingParams(
                    trust_threshold=0.75,
                    min_confidence=0.80,
                    max_position_size=0.05,
                    stop_loss=0.03,
                    take_profit=0.10
                ).to_dict()
            }
        )
    
    def generate_scenario_variants(
        self,
        parent_scenario: ScenarioDefinition,
        insight_hints: Optional[Dict[str, Any]] = None
    ) -> List[ScenarioDefinition]:
        """
        Generate variant scenarios based on parent and insights.
        
        Args:
            parent_scenario: The base scenario to vary
            insight_hints: Optional insights from memory (e.g., "trust_threshold > 0.65 helps")
        
        Returns:
            List of new scenario definitions
        """
        variants = []
        
        # Strategy 1: Parameter sweeps (systematic exploration)
        if insight_hints is None:
            # Generate parameter sweep variants
            variants.extend(self._generate_parameter_sweeps(parent_scenario))
        
        # Strategy 2: Regime-focused scenarios
        variants.extend(self._generate_regime_scenarios(parent_scenario))
        
        # Strategy 3: Insight-driven variants (if insights available)
        if insight_hints:
            variants.extend(self._generate_insight_driven_variants(parent_scenario, insight_hints))
        
        logger.info(f"Generated {len(variants)} scenario variants from {parent_scenario.scenario_id}")
        return variants
    
    def _generate_parameter_sweeps(self, parent: ScenarioDefinition) -> List[ScenarioDefinition]:
        """Generate systematic parameter sweep variants with regime classification preserved."""
        variants = []
        
        # Trust threshold sweep
        for threshold in [0.50, 0.60, 0.70, 0.80]:
            new_params = parent.param_sets.copy()
            for param_name in new_params:
                new_params[param_name] = new_params[param_name].copy()
                new_params[param_name]["trust_threshold"] = threshold
            
            variant = ScenarioDefinition(
                scenario_id="",  # Will be computed
                scenario_name=f"{parent.scenario_name} - Trust {threshold}",
                start_date=parent.start_date,
                end_date=parent.end_date,
                description=f"Trust threshold sweep: {threshold}",
                regime_classification=parent.regime_classification,  # Preserve regime classification
                symbols=parent.symbols.copy(),
                param_sets=new_params,
                parent_scenario_id=parent.scenario_id
            )
            variants.append(variant)
        
        return variants
    
    def _generate_regime_scenarios(self, parent: ScenarioDefinition) -> List[ScenarioDefinition]:
        """Generate regime-focused scenario variants with explicit regime classification."""
        variants = []
        regime_ontology = get_regime_ontology()
        
        # Different time periods (different market regimes)
        regimes = [
            ("Bull Run 2021", "2021-01-01", "2021-12-31", "Strong upward trend, low volatility"),
            ("Inflation Shock 2022", "2022-01-01", "2022-12-31", "High volatility, regime shifts"),
            ("Recovery Rally 2023", "2023-01-01", "2023-12-31", "Tech bounce back, choppy markets"),
        ]
        
        for name, start, end, desc in regimes:
            # Classify regime deterministically
            regime = regime_ontology.classify_scenario(name, start, end, desc)
            
            variant = ScenarioDefinition(
                scenario_id="",  # Will be computed
                scenario_name=f"{parent.scenario_name} - {name}",
                start_date=start,
                end_date=end,
                description=desc,
                regime_classification=regime.to_dict(),
                symbols=parent.symbols.copy(),
                param_sets=parent.param_sets.copy(),
                parent_scenario_id=parent.scenario_id
            )
            variants.append(variant)
        
        return variants
    
    def _generate_insight_driven_variants(
        self,
        parent: ScenarioDefinition,
        insights: Dict[str, Any]
    ) -> List[ScenarioDefinition]:
        """Generate variants based on learned insights."""
        variants = []
        
        # Example: If insight says "high trust threshold helps in volatile regimes"
        # Generate variants that test this hypothesis
        
        # This is a placeholder - real implementation would parse insights
        # and generate targeted variants
        
        return variants


# Singleton instance
_scenario_generator: Optional[ScenarioGenerator] = None


def get_scenario_generator() -> ScenarioGenerator:
    """Get or create scenario generator instance."""
    global _scenario_generator
    if _scenario_generator is None:
        _scenario_generator = ScenarioGenerator()
    return _scenario_generator

