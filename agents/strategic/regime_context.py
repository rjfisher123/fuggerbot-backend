"""
Regime Context Module for FuggerBot Strategic Reasoner v1.1.

Provides regime-aware interpretation capabilities:
- Current market regime detection
- Macro context overlays
- Scenario framing (base/bull/bear)
"""
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """Market regime classifications."""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    UNCERTAIN = "uncertain"


class MacroRegime(str, Enum):
    """Macroeconomic regime classifications."""
    EASING = "easing"
    TIGHTENING = "tightening"
    NEUTRAL = "neutral"
    CRISIS = "crisis"
    RECOVERY = "recovery"


class ScenarioFrame(str, Enum):
    """Scenario framing for strategic interpretation."""
    BASE = "base"
    BULL = "bull"
    BEAR = "bear"


class RegimeContext(BaseModel):
    """Current market and macro regime context."""
    market_regime: MarketRegime = Field(..., description="Current market regime")
    macro_regime: MacroRegime = Field(..., description="Current macro regime")
    volatility_regime: str = Field(..., description="Volatility regime (low/medium/high)")
    liquidity_regime: str = Field(..., description="Liquidity regime (normal/stressed)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in regime classification")
    detected_at: datetime = Field(default_factory=datetime.now, description="When regime was detected")
    regime_indicators: Dict[str, Any] = Field(default_factory=dict, description="Supporting indicators")


class ScenarioFraming(BaseModel):
    """Scenario framing for strategic interpretation."""
    base_scenario: str = Field(..., description="Base case scenario description")
    bull_scenario: str = Field(..., description="Bull case scenario description")
    bear_scenario: str = Field(..., description="Bear case scenario description")
    base_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of base scenario")
    bull_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of bull scenario")
    bear_probability: float = Field(..., ge=0.0, le=1.0, description="Probability of bear scenario")
    framing_reasoning: str = Field(..., description="Reasoning for scenario probabilities")


class RegimeContextProvider:
    """
    Provides regime context for strategic interpretation.
    
    Integrates with existing FuggerBot regime tracking infrastructure.
    """
    
    def __init__(self, regime_tracker=None):
        """
        Initialize regime context provider.
        
        Args:
            regime_tracker: Optional RegimeTracker instance from context.tracker
        """
        self.regime_tracker = regime_tracker
        logger.info("RegimeContextProvider initialized")
    
    def get_current_regime_context(self) -> RegimeContext:
        """
        Get current market and macro regime context.
        
        Returns:
            RegimeContext object with current regime classifications
        """
        # If we have a regime tracker, use it
        if self.regime_tracker:
            try:
                current_regime = self.regime_tracker.get_current_regime()
                # Map to our regime enums
                market_regime = self._map_to_market_regime(current_regime)
                macro_regime = self._map_to_macro_regime(current_regime)
                
                return RegimeContext(
                    market_regime=market_regime,
                    macro_regime=macro_regime,
                    volatility_regime=self._infer_volatility_regime(current_regime),
                    liquidity_regime=self._infer_liquidity_regime(current_regime),
                    confidence=0.7,  # Placeholder - could be enhanced with actual confidence calculation
                    regime_indicators={"source": "regime_tracker", "regime_id": getattr(current_regime, 'id', 'unknown')}
                )
            except Exception as e:
                logger.warning(f"Failed to get regime from tracker: {e}")
        
        # Default: uncertain/neutral regime
        return RegimeContext(
            market_regime=MarketRegime.UNCERTAIN,
            macro_regime=MacroRegime.NEUTRAL,
            volatility_regime="medium",
            liquidity_regime="normal",
            confidence=0.5,
            regime_indicators={"source": "default", "reason": "no_tracker_available"}
        )
    
    def _map_to_market_regime(self, regime_obj: Any) -> MarketRegime:
        """Map regime tracker output to MarketRegime enum."""
        # Placeholder mapping - enhance based on actual RegimeTracker implementation
        if hasattr(regime_obj, 'trend'):
            trend = regime_obj.trend.lower()
            if 'bull' in trend or 'up' in trend:
                return MarketRegime.BULL
            elif 'bear' in trend or 'down' in trend:
                return MarketRegime.BEAR
            elif 'sideways' in trend:
                return MarketRegime.SIDEWAYS
        
        return MarketRegime.UNCERTAIN
    
    def _map_to_macro_regime(self, regime_obj: Any) -> MacroRegime:
        """Map regime tracker output to MacroRegime enum."""
        # Placeholder mapping - enhance based on actual RegimeTracker implementation
        if hasattr(regime_obj, 'macro'):
            macro = regime_obj.macro.lower()
            if 'easing' in macro:
                return MacroRegime.EASING
            elif 'tightening' in macro:
                return MacroRegime.TIGHTENING
            elif 'crisis' in macro:
                return MacroRegime.CRISIS
            elif 'recovery' in macro:
                return MacroRegime.RECOVERY
        
        return MacroRegime.NEUTRAL
    
    def _infer_volatility_regime(self, regime_obj: Any) -> str:
        """Infer volatility regime from regime tracker."""
        if hasattr(regime_obj, 'volatility'):
            vol = regime_obj.volatility.lower()
            if 'high' in vol:
                return "high"
            elif 'low' in vol:
                return "low"
        return "medium"
    
    def _infer_liquidity_regime(self, regime_obj: Any) -> str:
        """Infer liquidity regime from regime tracker."""
        if hasattr(regime_obj, 'liquidity'):
            liq = regime_obj.liquidity.lower()
            if 'stressed' in liq or 'low' in liq:
                return "stressed"
        return "normal"
    
    def frame_scenarios(
        self,
        signal_class: str,
        signal_summary: str,
        regime_context: RegimeContext,
        strategic_relevance: float
    ) -> ScenarioFraming:
        """
        Frame scenarios (base/bull/bear) based on signal and regime context.
        
        Args:
            signal_class: Signal classification
            signal_summary: Signal summary
            regime_context: Current regime context
            strategic_relevance: Strategic relevance score
        
        Returns:
            ScenarioFraming with base/bull/bear scenarios and probabilities
        """
        # Base scenario probability depends on current regime and signal relevance
        base_prob = 0.5  # Default
        
        # Adjust based on regime stability
        if regime_context.market_regime in [MarketRegime.BULL, MarketRegime.BEAR]:
            base_prob = 0.6  # More certain in clear regimes
        elif regime_context.market_regime == MarketRegime.VOLATILE:
            base_prob = 0.3  # Less certain in volatile regimes
        
        # Adjust based on strategic relevance
        base_prob = base_prob * (0.5 + strategic_relevance * 0.5)
        
        # Bull and bear probabilities
        if regime_context.market_regime == MarketRegime.BULL:
            bull_prob = 0.4
            bear_prob = 0.1
        elif regime_context.market_regime == MarketRegime.BEAR:
            bull_prob = 0.1
            bear_prob = 0.4
        else:
            bull_prob = 0.25
            bear_prob = 0.25
        
        # Normalize probabilities
        total = base_prob + bull_prob + bear_prob
        base_prob = base_prob / total
        bull_prob = bull_prob / total
        bear_prob = bear_prob / total
        
        # Generate scenario descriptions
        base_scenario = f"Signal plays out in a {regime_context.market_regime.value} market regime with {regime_context.macro_regime.value} macro conditions. Moderate impact expected."
        bull_scenario = f"Signal triggers or amplifies positive outcomes. Aligns with supportive {regime_context.macro_regime.value} macro backdrop."
        bear_scenario = f"Signal triggers or amplifies negative outcomes. Conflicts with {regime_context.macro_regime.value} macro backdrop."
        
        reasoning = (
            f"Framing based on current {regime_context.market_regime.value} market regime, "
            f"{regime_context.macro_regime.value} macro regime, and signal relevance of {strategic_relevance:.2f}. "
            f"Regime confidence: {regime_context.confidence:.2f}."
        )
        
        return ScenarioFraming(
            base_scenario=base_scenario,
            bull_scenario=bull_scenario,
            bear_scenario=bear_scenario,
            base_probability=base_prob,
            bull_probability=bull_prob,
            bear_probability=bear_prob,
            framing_reasoning=reasoning
        )


def get_regime_context_provider(regime_tracker=None) -> RegimeContextProvider:
    """Factory function to get RegimeContextProvider instance."""
    return RegimeContextProvider(regime_tracker=regime_tracker)

