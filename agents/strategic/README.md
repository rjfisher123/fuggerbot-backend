# FuggerBot Strategic Reasoner v1.0

## Overview

The FuggerBot Strategic Reasoner is a capital-allocation strategic reasoner that evaluates high-signal inputs and advises on investment posture, risk framing, and follow-up actions.

**Key Principles:**
- FuggerBot does **not** ingest raw data, scrape, fetch, or filter noise
- FuggerBot reasons **only** over curated, explainable signals provided by upstream systems
- FuggerBot maintains strict separation: **Sensor → Strategy → Human Authority**

---

## Architecture

### Mental Model

> A family office CIO reading a perfectly filtered intelligence brief — not a trader staring at a ticker.

FuggerBot reasons slowly, conservatively, and contextually.

---

## Components

### 1. A2A Schema (`a2a_schema.py`)

Defines Pydantic models for:
- **A2ASignal**: Input signal from ai_inbox_digest v1.0
- **A2AFeedback**: Feedback emitted back to upstream systems
- **SignalLineage**: Provenance tracking
- **DecayAnnotation**: Time-decay metadata (computed upstream)
- **CorroborationAnnotation**: Corroboration metadata (computed upstream)

### 2. A2A Adapter (`a2a_adapter.py`)

Handles bidirectional communication:
- **Signal Ingestion**: Validates and ingests signals from ai_inbox_digest
- **Feedback Emission**: Emits structured feedback back to upstream systems
- **State Management**: Tracks processed signals and feedback history

### 3. Strategic Reasoner Agent (`strategic_reasoner_agent.py`)

Core reasoning engine:
- **Strategic Interpretation**: Analyzes signals for strategic relevance
- **Capital Framing**: Identifies exposed asset classes/sectors (non-executable)
- **Time Horizon Analysis**: Determines impact timeframe (days/quarters/years)
- **Feedback Generation**: Emits A2A feedback based on interpretation

---

## Usage

### Basic Example

```python
from agents.strategic import (
    get_strategic_reasoner,
    get_a2a_adapter,
    SignalClass,
)
from datetime import datetime

# Initialize components
adapter = get_a2a_adapter()
reasoner = get_strategic_reasoner(a2a_adapter=adapter)

# Ingest signal
signal_data = {
    'signal_id': 'sig_001',
    'signal_class': SignalClass.POLICY,
    'summary': 'Fed signals potential rate cut',
    'base_priority': 0.8,
    'effective_priority': 0.75,
    'corroboration_score': 0.85,
    'citations': [],
    'created_at': datetime.now(),
    'signal_lineage': {
        'upstream_message_ids': ['msg_001'],
        'upstream_agents': ['news_filter'],
        'processing_chain': ['news_filter', 'priority_engine']
    }
}

signal = adapter.ingest_signal(signal_data)

# Process signal
interpretation = reasoner.process_signal(signal)

print(f"Strategic Relevance: {interpretation.strategic_relevance:.2f}")
print(f"Confidence: {interpretation.confidence_level}")
print(f"Time Horizon: {interpretation.time_horizon}")
print(f"Summary: {interpretation.strategic_summary}")
```

---

## Safety & Invariants

### Must Obey

- ❌ **No autonomous execution**
- ❌ **No hidden heuristics**
- ❌ **No silent memory mutation**
- ❌ **No upstream override**
- ✅ **Explainable reasoning**
- ✅ **Conservative uncertainty**
- ✅ **Clear separation of sensing vs strategy**
- ✅ **Human-in-the-loop by design**

---

## Feedback Types

FuggerBot can emit the following feedback types:

- **HIGH_INTEREST**: Signal has high strategic relevance (>= 0.7)
- **LOW_INTEREST**: Signal has low strategic relevance (<= 0.3)
- **FOLLOW_UP_REQUIRED**: Moderate relevance, requires monitoring
- **DUPLICATE_SIGNAL**: Signal has been seen before
- **OUT_OF_SCOPE**: Signal is outside FuggerBot's domain

---

## Integration Points

### Future Integration

The Strategic Reasoner Agent can be integrated with:

1. **Memory Store**: Historical context and pattern matching
2. **Regime Tracker**: Current market regime awareness
3. **Research Loop**: Learning from historical patterns
4. **Orchestrator**: Main trading decision flow

---

## Status

**Current Version**: v1.0 (Foundation)

**Implemented**:
- ✅ A2A schema and validation
- ✅ A2A adapter (signal ingestion, feedback emission)
- ✅ Strategic Reasoner Agent (basic interpretation logic)

**Planned Enhancements**:
- 🔄 LLM-based strategic analysis (DeepSeek integration)
- 🔄 Regime interaction analysis
- 🔄 Historical analog matching
- 🔄 Second-order implication reasoning
- 🔄 Memory store integration
- 🔄 Capital framing heuristics refinement

---

## Related Documentation

- [Strategic Reasoner Design Document](../../docs/FUGGERBOT_STRATEGIC_REASONER_V1.md)
- [FuggerBot Master Directives](../../.cursorrules)

