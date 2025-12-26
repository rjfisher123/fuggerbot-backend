"""
Explicit Regime Ontology - Research Loop Component.

Provides a fixed, explicit taxonomy for market regimes.
All regime classifications are deterministic and documented.

Core Principle: Regimes are labels, not inferred during execution.
"""
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VolatilityRegime(str, Enum):
    """Volatility regime classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrendRegime(str, Enum):
    """Trend regime classification."""
    UP = "up"
    SIDEWAYS = "sideways"
    DOWN = "down"


class LiquidityRegime(str, Enum):
    """Liquidity regime classification."""
    NORMAL = "normal"
    STRESSED = "stressed"


class MacroRegime(str, Enum):
    """Macro regime classification (proxy via Fed policy)."""
    EASING = "easing"
    TIGHTENING = "tightening"
    NEUTRAL = "neutral"


class RegimeClassification(BaseModel):
    """
    Complete regime classification for a scenario.
    
    All classifications are explicit, deterministic labels.
    """
    volatility: VolatilityRegime = Field(..., description="Volatility regime")
    trend: TrendRegime = Field(..., description="Trend regime")
    liquidity: LiquidityRegime = Field(..., description="Liquidity regime")
    macro: MacroRegime = Field(..., description="Macro regime")
    
    # Optional metadata
    description: str = Field(default="", description="Human-readable description")
    classification_method: str = Field(default="explicit", description="How this was classified")
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dict for serialization."""
        return {
            "volatility": self.volatility.value,
            "trend": self.trend.value,
            "liquidity": self.liquidity.value,
            "macro": self.macro.value,
            "description": self.description
        }
    
    def regime_id(self) -> str:
        """Generate deterministic regime identifier."""
        return f"{self.volatility.value}_{self.trend.value}_{self.liquidity.value}_{self.macro.value}"
    
    def is_extreme_regime(self) -> bool:
        """Check if this is an extreme regime (high volatility, stressed liquidity)."""
        return (
            self.volatility == VolatilityRegime.HIGH or
            self.liquidity == LiquidityRegime.STRESSED
        )


class RegimeOntology:
    """
    Provides explicit regime classification.
    
    All classifications are deterministic and documented.
    """
    
    # Pre-defined regime mappings for common scenarios
    REGIME_MAPPINGS = {
        "Bull Run 2021": RegimeClassification(
            volatility=VolatilityRegime.LOW,
            trend=TrendRegime.UP,
            liquidity=LiquidityRegime.NORMAL,
            macro=MacroRegime.EASING,
            description="Strong upward trend, low volatility, accommodative policy"
        ),
        "Inflation Shock 2022": RegimeClassification(
            volatility=VolatilityRegime.HIGH,
            trend=TrendRegime.DOWN,
            liquidity=LiquidityRegime.NORMAL,
            macro=MacroRegime.TIGHTENING,
            description="High volatility, regime shifts, tightening policy"
        ),
        "Recovery Rally 2023": RegimeClassification(
            volatility=VolatilityRegime.MEDIUM,
            trend=TrendRegime.UP,
            liquidity=LiquidityRegime.NORMAL,
            macro=MacroRegime.NEUTRAL,
            description="Tech bounce back, choppy markets, neutral policy"
        ),
    }
    
    def classify_scenario(
        self,
        scenario_name: str,
        start_date: str,
        end_date: str,
        description: Optional[str] = None
    ) -> RegimeClassification:
        """
        Classify a scenario into regime taxonomy.
        
        Args:
            scenario_name: Name of the scenario
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            description: Optional scenario description
        
        Returns:
            RegimeClassification with explicit labels
        
        Note: Classification is deterministic based on scenario name/description.
        """
        # First check explicit mappings
        if scenario_name in self.REGIME_MAPPINGS:
            regime = self.REGIME_MAPPINGS[scenario_name]
            logger.debug(f"Using explicit regime mapping for '{scenario_name}': {regime.regime_id()}")
            return regime
        
        # Default classification based on date ranges (deterministic)
        # This is a simplified version - real implementation would use historical data
        year = int(start_date[:4])
        
        if year == 2021:
            return RegimeClassification(
                volatility=VolatilityRegime.LOW,
                trend=TrendRegime.UP,
                liquidity=LiquidityRegime.NORMAL,
                macro=MacroRegime.EASING,
                description=description or "Bull market period"
            )
        elif year == 2022:
            return RegimeClassification(
                volatility=VolatilityRegime.HIGH,
                trend=TrendRegime.DOWN,
                liquidity=LiquidityRegime.NORMAL,
                macro=MacroRegime.TIGHTENING,
                description=description or "Inflation and tightening period"
            )
        elif year == 2023:
            return RegimeClassification(
                volatility=VolatilityRegime.MEDIUM,
                trend=TrendRegime.UP,
                liquidity=LiquidityRegime.NORMAL,
                macro=MacroRegime.NEUTRAL,
                description=description or "Recovery period"
            )
        else:
            # Default to medium volatility, neutral
            return RegimeClassification(
                volatility=VolatilityRegime.MEDIUM,
                trend=TrendRegime.SIDEWAYS,
                liquidity=LiquidityRegime.NORMAL,
                macro=MacroRegime.NEUTRAL,
                description=description or "Standard market conditions"
            )
    
    def get_all_regime_combinations(self) -> List[RegimeClassification]:
        """Get all possible regime combinations (for coverage analysis)."""
        combinations = []
        
        for vol in VolatilityRegime:
            for trend in TrendRegime:
                for liq in LiquidityRegime:
                    for macro in MacroRegime:
                        combinations.append(RegimeClassification(
                            volatility=vol,
                            trend=trend,
                            liquidity=liq,
                            macro=macro,
                            description=f"{vol.value} vol, {trend.value} trend, {liq.value} liquidity, {macro.value} macro"
                        ))
        
        return combinations
    
    def get_regime_coverage(self, scenarios: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Analyze regime coverage across scenarios.
        
        Args:
            scenarios: List of scenario dicts with regime classifications
        
        Returns:
            Dict mapping regime_id to count of scenarios
        """
        coverage = {}
        
        for scenario in scenarios:
            regime_data = scenario.get("regime_classification")
            if regime_data:
                if isinstance(regime_data, dict):
                    regime = RegimeClassification(**regime_data)
                else:
                    regime = regime_data
                
                regime_id = regime.regime_id()
                coverage[regime_id] = coverage.get(regime_id, 0) + 1
        
        return coverage


# Singleton instance
_regime_ontology: Optional[RegimeOntology] = None


def get_regime_ontology() -> RegimeOntology:
    """Get or create regime ontology instance."""
    global _regime_ontology
    if _regime_ontology is None:
        _regime_ontology = RegimeOntology()
    return _regime_ontology

