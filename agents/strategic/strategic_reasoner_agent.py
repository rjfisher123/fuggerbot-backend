"""
Strategic Reasoner Agent for FuggerBot v1.0.

FuggerBot is a capital-allocation strategic reasoner that evaluates high-signal inputs
and advises on investment posture, risk framing, and follow-up actions.

FuggerBot does not ingest raw data, scrape, fetch, or filter noise.
FuggerBot reasons only over curated, explainable signals provided by upstream systems.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from agents.strategic.a2a_schema import (
    A2ASignal,
    A2AFeedback,
    FeedbackType,
    SignalClass,
)
from agents.strategic.a2a_adapter import A2AAdapter
from agents.strategic.regime_context import (
    RegimeContextProvider,
    RegimeContext,
    ScenarioFraming,
    MarketRegime,
    MacroRegime,
    get_regime_context_provider,
)

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence levels for strategic interpretation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimeHorizon(str, Enum):
    """Time horizons for strategic impact."""
    DAYS = "days"
    QUARTERS = "quarters"
    YEARS = "years"


class StrategicInterpretation(BaseModel):
    """
    Strategic interpretation of a signal.
    
    Produced by FuggerBot for each signal.
    """
    signal_id: str = Field(..., description="Signal ID")
    strategic_summary: str = Field(..., description="Plain language summary")
    why_it_matters: str = Field(..., description="Why it matters (or doesn't)")
    time_horizon: TimeHorizon = Field(..., description="Time horizon affected")
    follow_up_suggestions: List[str] = Field(default_factory=list, description="Optional follow-up suggestions")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level")
    strategic_relevance: float = Field(..., ge=0.0, le=1.0, description="Strategic relevance score (0-1)")
    
    # Regime interaction (v1.1)
    regime_interaction: Optional[str] = Field(default=None, description="Macro, liquidity, tech cycle, geopolitics")
    second_order_implications: Optional[str] = Field(default=None, description="Second-order implications")
    regime_context: Optional[Dict[str, Any]] = Field(default=None, description="Current regime context (v1.1)")
    scenario_framing: Optional[Dict[str, Any]] = Field(default=None, description="Base/bull/bear scenario framing (v1.1)")
    
    # Capital framing (non-executable)
    exposed_asset_classes: List[str] = Field(default_factory=list, description="Exposed asset classes")
    exposed_sectors: List[str] = Field(default_factory=list, description="Exposed sectors")
    watchlist_suggestions: List[str] = Field(default_factory=list, description="Watchlist suggestions")
    
    # Memory context (if used)
    memory_drawn: bool = Field(default=False, description="Explicitly state when drawing from memory")
    inference_vs_fact: str = Field(default="fact", description="'fact' or 'inference'")
    
    interpreted_at: datetime = Field(default_factory=datetime.now, description="When interpretation was created")
    
    class Config:
        """Pydantic config."""
        use_enum_values = True


class StrategicReasonerAgent:
    """
    Strategic Reasoner Agent - FuggerBot v1.0.
    
    Mental Model: A family office CIO reading a perfectly filtered intelligence brief,
    not a trader staring at a ticker. Reasons slowly, conservatively, and contextually.
    
    Core Responsibilities:
    1. Strategic Interpretation
    2. Capital Framing (Non-Executable)
    3. A2A Feedback Emission
    """
    
    def __init__(
        self,
        a2a_adapter: Optional[A2AAdapter] = None,
        memory_store: Optional[Any] = None,  # TODO: Type this properly when memory is integrated
        regime_tracker: Optional[Any] = None  # Optional RegimeTracker instance
    ):
        """
        Initialize Strategic Reasoner Agent.
        
        Args:
            a2a_adapter: A2A adapter for signal ingestion and feedback emission
            memory_store: Optional memory store for historical context
            regime_tracker: Optional regime tracker for regime-aware interpretation (v1.1)
        """
        self.a2a_adapter = a2a_adapter or A2AAdapter()
        self.memory_store = memory_store
        self.regime_context_provider = get_regime_context_provider(regime_tracker=regime_tracker)
        logger.info("Strategic Reasoner Agent initialized (v1.1)")
    
    def process_signal(self, signal: A2ASignal) -> StrategicInterpretation:
        """
        Process a signal and produce strategic interpretation.
        
        Args:
            signal: A2A signal from ai_inbox_digest v1.0
        
        Returns:
            StrategicInterpretation object
        """
        logger.info(f"Processing signal: {signal.signal_id} (class={signal.signal_class})")
        
        # Step 1: Strategic Interpretation
        interpretation = self._interpret_strategically(signal)
        
        # Step 2: Emit A2A Feedback
        self._emit_feedback(signal, interpretation)
        
        return interpretation
    
    def _interpret_strategically(self, signal: A2ASignal) -> StrategicInterpretation:
        """
        Perform strategic interpretation of a signal.
        
        This is where the core reasoning logic lives.
        For now, this is a placeholder that will be extended with:
        - Regime interaction analysis
        - Historical analog matching
        - Second-order implication reasoning
        - LLM-based strategic analysis (if needed)
        
        Args:
            signal: A2A signal to interpret
        
        Returns:
            StrategicInterpretation object
        """
        # Determine strategic relevance
        # Higher effective_priority and corroboration_score -> higher relevance
        strategic_relevance = (signal.effective_priority + signal.corroboration_score) / 2.0
        
        # Determine time horizon based on signal class
        time_horizon = self._infer_time_horizon(signal)
        
        # Determine confidence level
        confidence_level = self._determine_confidence(signal)
        
        # Generate strategic summary (placeholder - will be enhanced with LLM/rule-based logic)
        strategic_summary = self._generate_strategic_summary(signal)
        why_it_matters = self._generate_why_it_matters(signal, strategic_relevance)
        
        # Capital framing (non-executable suggestions)
        exposed_asset_classes, exposed_sectors, watchlist = self._frame_capital(signal)
        
        # v1.1: Regime-aware interpretation
        regime_context_obj = self.regime_context_provider.get_current_regime_context()
        regime_interaction_str = self._analyze_regime_interaction(signal, regime_context_obj)
        second_order_implications_str = self._analyze_second_order_implications(signal, regime_context_obj)
        
        # v1.1: Scenario framing (base/bull/bear)
        scenario_framing_obj = self.regime_context_provider.frame_scenarios(
            signal_class=signal.signal_class.value,
            signal_summary=signal.summary,
            regime_context=regime_context_obj,
            strategic_relevance=strategic_relevance
        )
        
        # Check if we're drawing from memory
        memory_drawn = False
        if self.memory_store:
            # TODO: Check memory for similar signals/patterns
            memory_drawn = False  # Placeholder
        
        interpretation = StrategicInterpretation(
            signal_id=signal.signal_id,
            strategic_summary=strategic_summary,
            why_it_matters=why_it_matters,
            time_horizon=time_horizon,
            follow_up_suggestions=[],  # TODO: Generate based on signal
            confidence_level=confidence_level,
            strategic_relevance=strategic_relevance,
            regime_interaction=regime_interaction_str,
            second_order_implications=second_order_implications_str,
            regime_context=regime_context_obj.model_dump(mode='json') if regime_context_obj else None,
            scenario_framing=scenario_framing_obj.model_dump(mode='json') if scenario_framing_obj else None,
            exposed_asset_classes=exposed_asset_classes,
            exposed_sectors=exposed_sectors,
            watchlist_suggestions=watchlist,
            memory_drawn=memory_drawn,
            inference_vs_fact="inference",  # Most interpretations are inferences
            interpreted_at=datetime.now()
        )
        
        return interpretation
    
    def _infer_time_horizon(self, signal: A2ASignal) -> TimeHorizon:
        """Infer time horizon from signal class and content."""
        # Policy and geopolitical signals tend to have longer horizons
        if signal.signal_class in [SignalClass.POLICY, SignalClass.GEOPOLITICS]:
            return TimeHorizon.QUARTERS
        # Earnings and market news are shorter-term
        elif signal.signal_class in [SignalClass.EARNINGS, SignalClass.MARKET_NEWS]:
            return TimeHorizon.DAYS
        # Economic data can vary
        else:
            return TimeHorizon.QUARTERS
    
    def _determine_confidence(self, signal: A2ASignal) -> ConfidenceLevel:
        """Determine confidence level based on signal quality."""
        # Higher corroboration and priority -> higher confidence
        score = (signal.corroboration_score + signal.effective_priority) / 2.0
        
        if score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.4:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_strategic_summary(self, signal: A2ASignal) -> str:
        """Generate strategic summary (placeholder - will be enhanced)."""
        return f"{signal.signal_class.value.replace('_', ' ').title()}: {signal.summary}"
    
    def _generate_why_it_matters(self, signal: A2ASignal, relevance: float) -> str:
        """Generate 'why it matters' explanation (placeholder - will be enhanced)."""
        if relevance >= 0.7:
            return f"High strategic relevance ({relevance:.2f}). Requires portfolio review and positioning consideration."
        elif relevance >= 0.4:
            return f"Moderate strategic relevance ({relevance:.2f}). Monitor for developments."
        else:
            return f"Lower strategic relevance ({relevance:.2f}). Background context only."
    
    def _frame_capital(
        self, signal: A2ASignal
    ) -> tuple[List[str], List[str], List[str]]:
        """
        Frame capital exposure (non-executable).
        
        Returns:
            Tuple of (exposed_asset_classes, exposed_sectors, watchlist_suggestions)
        """
        # Placeholder - will be enhanced with:
        # - Signal class -> asset class mapping
        # - Sector analysis
        # - Watchlist recommendations
        
        exposed_asset_classes = []
        exposed_sectors = []
        watchlist = []
        
        # Example: Policy signals often affect all asset classes
        if signal.signal_class == SignalClass.POLICY:
            exposed_asset_classes = ["equities", "bonds", "commodities"]
        
        return exposed_asset_classes, exposed_sectors, watchlist
    
    def _analyze_regime_interaction(self, signal: A2ASignal, regime_context: RegimeContext) -> str:
        """
        Analyze how signal interacts with current regime (v1.1).
        
        Args:
            signal: A2A signal
            regime_context: Current regime context
        
        Returns:
            Human-readable regime interaction analysis
        """
        interactions = []
        
        # Market regime interaction
        if regime_context.market_regime == MarketRegime.BULL:
            interactions.append("Signal aligns with bullish market sentiment, potentially amplifying positive momentum.")
        elif regime_context.market_regime == MarketRegime.BEAR:
            interactions.append("Signal may conflict with bearish market sentiment, requiring careful risk assessment.")
        elif regime_context.market_regime == MarketRegime.VOLATILE:
            interactions.append("Signal arrives during volatile regime - potential for amplified market reactions.")
        
        # Macro regime interaction
        if regime_context.macro_regime == MacroRegime.TIGHTENING and signal.signal_class == SignalClass.POLICY:
            interactions.append("Policy signal during monetary tightening - heightened sensitivity to rate changes.")
        elif regime_context.macro_regime == MacroRegime.EASING:
            interactions.append("Signal during monetary easing - supportive macro backdrop may enhance positive outcomes.")
        
        # Volatility interaction
        if regime_context.volatility_regime == "high":
            interactions.append("High volatility regime - signal may trigger larger-than-normal market moves.")
        
        if not interactions:
            return "Signal interacts neutrally with current regime conditions."
        
        return " ".join(interactions)
    
    def _analyze_second_order_implications(self, signal: A2ASignal, regime_context: RegimeContext) -> str:
        """
        Analyze second-order implications of signal (v1.1).
        
        Args:
            signal: A2A signal
            regime_context: Current regime context
        
        Returns:
            Human-readable second-order implications
        """
        implications = []
        
        # Policy signals often have second-order effects
        if signal.signal_class == SignalClass.POLICY:
            implications.append("Policy changes may cascade through asset classes - equities, bonds, and currencies all affected.")
        
        # Geopolitical signals have broader implications
        if signal.signal_class == SignalClass.GEOPOLITICS:
            implications.append("Geopolitical events may trigger supply chain disruptions, commodity price shocks, or currency volatility.")
        
        # Earnings signals during volatile regimes
        if signal.signal_class == SignalClass.EARNINGS and regime_context.volatility_regime == "high":
            implications.append("Earnings surprises during high volatility may trigger outsized sector rotation.")
        
        if not implications:
            return "Second-order implications are unclear - monitor for cascading effects."
        
        return " ".join(implications)
    
    def _emit_feedback(
        self, signal: A2ASignal, interpretation: StrategicInterpretation
    ) -> A2AFeedback:
        """Emit A2A feedback based on interpretation."""
        # Determine feedback type based on strategic relevance
        if interpretation.strategic_relevance >= 0.7:
            feedback_type = FeedbackType.HIGH_INTEREST
        elif interpretation.strategic_relevance <= 0.3:
            feedback_type = FeedbackType.LOW_INTEREST
        else:
            feedback_type = FeedbackType.FOLLOW_UP_REQUIRED
        
        # Generate feedback
        feedback = self.a2a_adapter.emit_feedback(
            signal_id=signal.signal_id,
            feedback_type=feedback_type,
            summary=interpretation.strategic_summary,
            reasoning=interpretation.why_it_matters,
            strategic_relevance=interpretation.strategic_relevance,
            time_horizon=interpretation.time_horizon,  # Already a string due to use_enum_values
            context={
                "confidence_level": interpretation.confidence_level,  # Already a string due to use_enum_values
                "exposed_asset_classes": interpretation.exposed_asset_classes,
                "memory_drawn": interpretation.memory_drawn,
            }
        )
        
        return feedback


def get_strategic_reasoner(
    a2a_adapter: Optional[A2AAdapter] = None,
    memory_store: Optional[Any] = None,
    regime_tracker: Optional[Any] = None
) -> StrategicReasonerAgent:
    """
    Factory function to get a Strategic Reasoner Agent instance.
    
    Args:
        a2a_adapter: Optional A2A adapter instance
        memory_store: Optional memory store instance
        regime_tracker: Optional regime tracker instance (v1.1)
    
    Returns:
        StrategicReasonerAgent instance
    """
    return StrategicReasonerAgent(a2a_adapter=a2a_adapter, memory_store=memory_store, regime_tracker=regime_tracker)

