"""
Risk Policy Agent - Level 4 Policy Layer.

The final gatekeeper with veto power.
Applies hard rules based on news, memory, and critic findings.
"""
import logging
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

from agents.trm.news_digest_agent import NewsDigest, NewsImpact, NewsSentiment
from agents.trm.memory_summarizer import MemoryNarrative
from reasoning.schemas import ReasoningDecision

logger = logging.getLogger(__name__)


class VetoReason(str, Enum):
    """Reasons for veto decisions."""
    NEWS_CRITICAL_EVENT = "NEWS_CRITICAL_EVENT"
    NEWS_REGULATORY_ACTION = "NEWS_REGULATORY_ACTION"
    MEMORY_HIGH_HALLUCINATION = "MEMORY_HIGH_HALLUCINATION"
    MEMORY_LOW_WIN_RATE = "MEMORY_LOW_WIN_RATE"
    CRITIC_OVERWHELMING_FLAWS = "CRITIC_OVERWHELMING_FLAWS"
    NO_VETO = "NO_VETO"


class TRMInput(BaseModel):
    """
    Input for Risk Policy Agent decision-making.
    """
    symbol: str = Field(..., description="Trading symbol")
    forecast_confidence: float = Field(..., ge=0.0, le=1.0, description="Forecast confidence")
    trust_score: float = Field(..., ge=0.0, le=1.0, description="Trust score")
    news_digest: NewsDigest = Field(..., description="Processed news summary")
    memory_narrative: MemoryNarrative = Field(..., description="Historical performance narrative")
    llm_decision: ReasoningDecision = Field(..., description="LLM's proposed decision")
    llm_confidence: float = Field(..., ge=0.0, le=1.0, description="LLM's confidence")
    critique_flaws_count: Optional[int] = Field(default=None, ge=0, description="Number of flaws found by critic")


class FinalVerdict(BaseModel):
    """
    Final decision from Risk Policy Agent.
    """
    decision: ReasoningDecision = Field(..., description="Final decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Adjusted confidence")
    original_confidence: float = Field(..., ge=0.0, le=1.0, description="Original LLM confidence")
    confidence_adjustment: float = Field(..., description="Change in confidence")
    veto_applied: bool = Field(..., description="Whether a veto was applied")
    veto_reason: VetoReason = Field(..., description="Reason for veto (if any)")
    override_reason: str = Field(..., description="Human-readable explanation")
    timestamp: datetime = Field(default_factory=datetime.now, description="Decision timestamp")
    
    def to_prompt_string(self) -> str:
        """
        Format verdict for logging/debugging.
        
        Returns:
            Formatted string
        """
        if self.veto_applied:
            icon = "🛑"
            status = "VETOED"
        elif self.confidence_adjustment < -0.1:
            icon = "⚠️"
            status = "ADJUSTED DOWN"
        elif self.confidence_adjustment > 0.1:
            icon = "✅"
            status = "ADJUSTED UP"
        else:
            icon = "➡️"
            status = "PASSED THROUGH"
        
        return (
            f"{icon} RISK POLICY: {status}\n"
            f"Decision: {self.decision.value}\n"
            f"Confidence: {self.original_confidence:.2f} → {self.confidence:.2f} ({self.confidence_adjustment:+.2f})\n"
            f"Reason: {self.override_reason}"
        )


class RiskPolicyAgent:
    """
    Risk Policy Agent - The Compliance Officer.
    
    Final gatekeeper that applies hard rules and has veto power.
    """
    
    # Policy thresholds
    CRITICAL_NEWS_VETO = True  # Veto on critical news
    HIGH_HALLUCINATION_THRESHOLD = 0.5  # Veto if hallucination rate > 50%
    LOW_WIN_RATE_THRESHOLD = 0.35  # Penalize if win rate < 35%
    MEMORY_CONFIDENCE_PENALTY = 0.2  # Confidence penalty for poor memory
    CRITIQUE_FLAW_PENALTY = 0.05  # Penalty per flaw found
    MAX_CRITIQUE_PENALTY = 0.3  # Max penalty from critique
    
    def __init__(self):
        """Initialize the risk policy agent."""
        logger.info("RiskPolicyAgent initialized")
    
    def _apply_news_policy(self, trm_input: TRMInput, confidence: float) -> tuple[bool, float, VetoReason, str]:
        """
        Apply news-based policy rules.
        
        Args:
            trm_input: TRM input data
            confidence: Current confidence level
        
        Returns:
            Tuple of (veto_applied, adjusted_confidence, veto_reason, explanation)
        """
        news = trm_input.news_digest
        
        # Rule 1: Veto on CRITICAL regulatory news
        if news.impact_level == NewsImpact.CRITICAL:
            # Check for regulatory keywords
            regulatory_keywords = {"sec", "lawsuit", "investigation", "fraud"}
            if any(kw in news.triggered_keywords for kw in regulatory_keywords):
                if self.CRITICAL_NEWS_VETO:
                    return (
                        True,
                        0.0,
                        VetoReason.NEWS_REGULATORY_ACTION,
                        f"VETO: Critical regulatory event detected - {', '.join(news.triggered_keywords[:2])}"
                    )
        
        # Rule 2: Confidence penalty for CRITICAL news (if not veto)
        if news.impact_level == NewsImpact.CRITICAL:
            adjustment = -0.3
            reason = f"Critical event penalty: {news.summary[:50]}"
            return (False, max(0.0, confidence + adjustment), VetoReason.NEWS_CRITICAL_EVENT, reason)
        
        # Rule 3: Confidence penalty for HIGH impact bearish news
        if news.impact_level == NewsImpact.HIGH and news.sentiment in [NewsSentiment.BEARISH, NewsSentiment.FEAR]:
            adjustment = -0.15
            reason = f"High impact bearish news penalty: {news.sentiment.value}"
            return (False, max(0.0, confidence + adjustment), VetoReason.NO_VETO, reason)
        
        # Rule 4: Confidence boost for HIGH impact bullish news
        if news.impact_level == NewsImpact.HIGH and news.sentiment == NewsSentiment.BULLISH:
            adjustment = +0.10
            reason = f"High impact bullish news boost"
            return (False, min(1.0, confidence + adjustment), VetoReason.NO_VETO, reason)
        
        return (False, confidence, VetoReason.NO_VETO, "No news policy triggered")
    
    def _apply_memory_policy(self, trm_input: TRMInput, confidence: float) -> tuple[bool, float, VetoReason, str]:
        """
        Apply memory-based policy rules.
        
        Args:
            trm_input: TRM input data
            confidence: Current confidence level
        
        Returns:
            Tuple of (veto_applied, adjusted_confidence, veto_reason, explanation)
        """
        memory = trm_input.memory_narrative
        
        # Rule 1: Veto if hallucination rate is extremely high
        if memory.hallucination_rate > self.HIGH_HALLUCINATION_THRESHOLD:
            return (
                True,
                0.0,
                VetoReason.MEMORY_HIGH_HALLUCINATION,
                f"VETO: Hallucination rate too high ({memory.hallucination_rate:.1%})"
            )
        
        # Rule 2: Confidence penalty for low win rate
        if memory.regime_win_rate < self.LOW_WIN_RATE_THRESHOLD:
            adjustment = -self.MEMORY_CONFIDENCE_PENALTY
            reason = f"Low win rate penalty ({memory.regime_win_rate:.1%} in regime)"
            return (False, max(0.0, confidence + adjustment), VetoReason.MEMORY_LOW_WIN_RATE, reason)
        
        # Rule 3: Smaller penalty for moderate hallucination rate
        if memory.hallucination_rate > 0.3:
            adjustment = -0.1
            reason = f"Moderate hallucination penalty ({memory.hallucination_rate:.1%})"
            return (False, max(0.0, confidence + adjustment), VetoReason.NO_VETO, reason)
        
        return (False, confidence, VetoReason.NO_VETO, "No memory policy triggered")
    
    def _apply_critique_policy(self, trm_input: TRMInput, confidence: float) -> tuple[bool, float, VetoReason, str]:
        """
        Apply critique-based policy rules.
        
        Args:
            trm_input: TRM input data
            confidence: Current confidence level
        
        Returns:
            Tuple of (veto_applied, adjusted_confidence, veto_reason, explanation)
        """
        if trm_input.critique_flaws_count is None:
            return (False, confidence, VetoReason.NO_VETO, "No critique data")
        
        # Rule 1: Veto if critic found overwhelming flaws (5+)
        if trm_input.critique_flaws_count >= 5:
            return (
                True,
                0.0,
                VetoReason.CRITIC_OVERWHELMING_FLAWS,
                f"VETO: Critic found {trm_input.critique_flaws_count} major flaws"
            )
        
        # Rule 2: Confidence penalty based on flaw count
        if trm_input.critique_flaws_count > 0:
            adjustment = -min(
                trm_input.critique_flaws_count * self.CRITIQUE_FLAW_PENALTY,
                self.MAX_CRITIQUE_PENALTY
            )
            reason = f"Critique penalty: {trm_input.critique_flaws_count} flaws found"
            return (False, max(0.0, confidence + adjustment), VetoReason.NO_VETO, reason)
        
        return (False, confidence, VetoReason.NO_VETO, "No critique policy triggered")
    
    def decide(self, trm_input: TRMInput) -> FinalVerdict:
        """
        Make final decision with policy enforcement.
        
        Args:
            trm_input: Complete TRM input with all context
        
        Returns:
            FinalVerdict with final decision and adjustments
        """
        original_confidence = trm_input.llm_confidence
        adjusted_confidence = original_confidence
        veto_applied = False
        veto_reason = VetoReason.NO_VETO
        override_explanations = []
        
        logger.info(f"Risk policy evaluation for {trm_input.symbol}: LLM={trm_input.llm_decision.value} @ {original_confidence:.2f}")
        
        # Apply policies in order (news, memory, critique)
        # Each policy can veto or adjust confidence
        
        # 1. News Policy
        news_veto, adjusted_confidence, news_veto_reason, news_explanation = self._apply_news_policy(trm_input, adjusted_confidence)
        if news_veto:
            veto_applied = True
            veto_reason = news_veto_reason
        override_explanations.append(news_explanation)
        
        # 2. Memory Policy (only if not already vetoed)
        if not veto_applied:
            mem_veto, adjusted_confidence, mem_veto_reason, mem_explanation = self._apply_memory_policy(trm_input, adjusted_confidence)
            if mem_veto:
                veto_applied = True
                veto_reason = mem_veto_reason
            override_explanations.append(mem_explanation)
        
        # 3. Critique Policy (only if not already vetoed)
        if not veto_applied:
            crit_veto, adjusted_confidence, crit_veto_reason, crit_explanation = self._apply_critique_policy(trm_input, adjusted_confidence)
            if crit_veto:
                veto_applied = True
                veto_reason = crit_veto_reason
            override_explanations.append(crit_explanation)
        
        # Determine final decision
        if veto_applied:
            final_decision = ReasoningDecision.REJECT
            adjusted_confidence = 0.0  # Veto means zero confidence
        else:
            # Keep LLM's decision but with adjusted confidence
            final_decision = trm_input.llm_decision
        
        # Compile override reason
        override_reason = " | ".join([exp for exp in override_explanations if exp != "No news policy triggered" and exp != "No memory policy triggered" and exp != "No critique policy triggered"])
        if not override_reason:
            override_reason = "All policies passed"
        
        confidence_adjustment = adjusted_confidence - original_confidence
        
        logger.info(
            f"Risk policy result: {final_decision.value} @ {adjusted_confidence:.2f} "
            f"(Δ{confidence_adjustment:+.2f}) - Veto: {veto_applied}"
        )
        
        return FinalVerdict(
            decision=final_decision,
            confidence=adjusted_confidence,
            original_confidence=original_confidence,
            confidence_adjustment=confidence_adjustment,
            veto_applied=veto_applied,
            veto_reason=veto_reason,
            override_reason=override_reason
        )


# Singleton instance
_risk_policy_agent: Optional[RiskPolicyAgent] = None


def get_risk_policy_agent() -> RiskPolicyAgent:
    """
    Get or create singleton RiskPolicyAgent instance.
    
    Returns:
        RiskPolicyAgent instance
    """
    global _risk_policy_agent
    
    if _risk_policy_agent is None:
        _risk_policy_agent = RiskPolicyAgent()
    
    return _risk_policy_agent


if __name__ == "__main__":
    # Test the risk policy agent
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    logging.basicConfig(level=logging.INFO)
    
    from agents.trm.news_digest_agent import NewsDigest, NewsImpact, NewsSentiment
    from agents.trm.memory_summarizer import MemoryNarrative
    
    # Create test inputs
    test_news = NewsDigest(
        impact_level=NewsImpact.CRITICAL,
        sentiment=NewsSentiment.FEAR,
        summary="SEC sues major exchange",
        triggered_keywords=["sec", "lawsuit"],
        headline_count=1
    )
    
    test_memory = MemoryNarrative(
        regime_win_rate=0.42,
        total_trades_in_regime=193,
        primary_failure_mode="BAD_TIMING",
        hallucination_rate=0.15,
        confidence_calibration="OVERCONFIDENT",
        narrative="Historical performance: 42% win rate"
    )
    
    test_input = TRMInput(
        symbol="BTC-USD",
        forecast_confidence=0.85,
        trust_score=0.75,
        news_digest=test_news,
        memory_narrative=test_memory,
        llm_decision=ReasoningDecision.APPROVE,
        llm_confidence=0.80,
        critique_flaws_count=2
    )
    
    agent = get_risk_policy_agent()
    verdict = agent.decide(test_input)
    
    print("Risk Policy Verdict Test:")
    print(verdict.to_prompt_string())

