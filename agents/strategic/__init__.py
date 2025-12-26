"""
Strategic Reasoner Agents for FuggerBot.

FuggerBot Strategic Reasoner (v1.0):
- Consumes curated signals from ai_inbox_digest v1.0 (via A2A protocol)
- Provides strategic interpretation and capital framing (non-executable)
- Emits feedback to upstream systems
- Maintains strict separation: Sensor → Strategy → Human Authority
"""
from agents.strategic.a2a_schema import (
    A2ASignal,
    A2AFeedback,
    SignalClass,
    FeedbackType,
    SignalLineage,
    DecayAnnotation,
    CorroborationAnnotation,
)
from agents.strategic.a2a_adapter import A2AAdapter, get_a2a_adapter
from agents.strategic.strategic_reasoner_agent import (
    StrategicReasonerAgent,
    StrategicInterpretation,
    ConfidenceLevel,
    TimeHorizon,
    get_strategic_reasoner,
)

__all__ = [
    "A2ASignal",
    "A2AFeedback",
    "SignalClass",
    "FeedbackType",
    "SignalLineage",
    "DecayAnnotation",
    "CorroborationAnnotation",
    "A2AAdapter",
    "get_a2a_adapter",
    "StrategicReasonerAgent",
    "StrategicInterpretation",
    "ConfidenceLevel",
    "TimeHorizon",
    "get_strategic_reasoner",
]

