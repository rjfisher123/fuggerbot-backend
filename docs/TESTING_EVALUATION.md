# Agents.md — Testing & Evaluation Extension
## FuggerBot Strategic Reasoner v1.1

## Purpose
This document defines how FuggerBot v1.1 participates in **historical replay, shadow evaluation, and deterministic testing** using upstream A2A signals.

It does NOT authorize execution, learning, or policy mutation.

---

## System Identity (Unchanged)
FuggerBot is a **Strategic Reasoner**.

It:
- Interprets curated signals
- Applies regime-aware strategic framing
- Produces scenario-based, non-executable insights
- Emits structured feedback upstream
- Does NOT trade, optimize, or act autonomously

---

## Testing Mode (Authorized)

### Activation
Testing MUST be conducted with:

```python
from agents.strategic import get_strategic_reasoner

# Enable test mode
reasoner = get_strategic_reasoner(test_mode=True)
```

**test_mode=True enforces:**
- Memory access is **read-only** (no mutation)
- No pattern learning or accumulation
- No adaptive behavior
- Interpretations are **deterministic and reproducible**

### Guarantees
When test_mode is enabled:
- Memory is read-only
- Pattern learning is disabled
- Interpretations are deterministic
- No adaptive or persistent behavior is allowed
- Outputs are reproducible

---

## Authorized Testing Objectives

### Objective 1 — Strategic Interpretation Quality
Evaluate whether interpretations:
- Add insight beyond raw signal summaries
- Reflect appropriate regime context
- Surface second-order implications clearly

### Objective 2 — Regime Sensitivity
Evaluate whether:
- Scenario framing shifts meaningfully across regimes
- Probability weights respond to macro context
- Bull/base/bear narratives are coherent and explainable

### Objective 3 — Feedback Discipline
Evaluate whether A2A feedback:
- Is proportional and well-structured
- Avoids hindsight bias
- Clearly communicates "low interest" vs "missed signal"

---

## Testing Scenarios

### 1. Historical Replay

**Purpose**: Process historical signals deterministically to validate interpretation logic.

**Requirements**:
- Use `test_mode=True`
- Provide historical A2ASignal objects with known timestamps
- Regime context must be frozen at historical point
- No memory mutation allowed

**Example**:
```python
from agents.strategic import get_strategic_reasoner, A2ASignal, SignalClass, SignalLineage
from datetime import datetime

reasoner = get_strategic_reasoner(test_mode=True)

# Historical signal from 2024-01-15
historical_signal = A2ASignal(
    signal_id='hist_20240115_001',
    signal_class=SignalClass.POLICY,
    summary='Fed signals rate cut',
    base_priority=0.8,
    effective_priority=0.75,
    corroboration_score=0.85,
    created_at=datetime(2024, 1, 15, 10, 0, 0),
    signal_lineage=SignalLineage(...)
)

# Process deterministically
interpretation = reasoner.process_signal(historical_signal)
```

**Validation**:
- Same signal → same interpretation (deterministic)
- No memory state changes
- Feedback is emitted but non-binding

---

### 2. Shadow Evaluation

**Purpose**: Compare interpretations from different versions or configurations without affecting production.

**Requirements**:
- Use `test_mode=True` for all shadow instances
- Process identical signals through multiple configurations
- Compare outputs (strategic_relevance, confidence, scenario_framing)
- No production memory mutation

**Example**:
```python
# Version A (current)
reasoner_v1_1 = get_strategic_reasoner(test_mode=True, regime_tracker=tracker_a)

# Version B (experimental)
reasoner_v1_2 = get_strategic_reasoner(test_mode=True, regime_tracker=tracker_b)

# Process same signal
signal = create_test_signal()
interpretation_a = reasoner_v1_1.process_signal(signal)
interpretation_b = reasoner_v1_2.process_signal(signal)

# Compare
compare_interpretations(interpretation_a, interpretation_b)
```

**Validation**:
- Both interpretations are deterministic
- Differences are explainable (regime context, logic changes)
- No production impact

---

### 3. Backtesting Strategic Logic

**Purpose**: Validate strategic reasoning logic against historical outcomes.

**Requirements**:
- Use `test_mode=True`
- Process historical signals in chronological order
- Compare interpretations to actual market outcomes (post-hoc)
- Measure interpretation accuracy and confidence calibration

**Example**:
```python
reasoner = get_strategic_reasoner(test_mode=True)

# Load historical signals
historical_signals = load_signals_from_timeframe('2024-01-01', '2024-12-31')

results = []
for signal in historical_signals:
    interpretation = reasoner.process_signal(signal)
    
    # Compare to actual outcome (post-hoc analysis)
    actual_outcome = get_actual_outcome(signal.signal_id)
    
    results.append({
        'signal_id': signal.signal_id,
        'interpretation': interpretation,
        'actual_outcome': actual_outcome,
        'accuracy': evaluate_interpretation(interpretation, actual_outcome)
    })

analyze_backtest_results(results)
```

**Validation**:
- Strategic relevance correlates with actual impact
- Confidence levels are calibrated
- Scenario framing probabilities are reasonable
- No lookahead bias (test_mode ensures no future information leakage)

---

## Test Mode Constraints

### What Test Mode Enforces

1. **Memory Access**
   - Read-only access to memory store
   - No pattern accumulation
   - No learning from processed signals
   - No mutation of historical memory

2. **Regime Context**
   - Regime context is frozen at time of signal
   - No adaptive regime detection
   - Historical regime data used as-is

3. **Determinism**
   - Same input → same output
   - No randomness in interpretation
   - Reproducible results across runs

4. **Feedback Emission**
   - Feedback is still emitted (for testing purposes)
   - Feedback does NOT affect upstream systems in test mode
   - Feedback is logged but non-binding

### What Test Mode Does NOT Change

1. **Core Logic**
   - Strategic interpretation algorithms unchanged
   - Regime analysis unchanged
   - Scenario framing unchanged
   - Confidence calculation unchanged

2. **Input/Output Schema**
   - A2ASignal schema unchanged
   - StrategicInterpretation schema unchanged
   - A2AFeedback schema unchanged

3. **Advisory Nature**
   - All outputs remain advisory
   - No execution authority granted
   - Human decision authority preserved

---

## Test Data Requirements

### Historical Signal Data

For historical replay and backtesting, signals must include:

1. **Complete Signal Metadata**
   - `signal_id`: Unique identifier
   - `signal_class`: Classification type
   - `summary`: Signal description
   - `created_at`: Precise timestamp

2. **Priority & Corroboration**
   - `base_priority`: Original priority
   - `effective_priority`: Post-decay priority
   - `corroboration_score`: Corroboration level

3. **Provenance**
   - `signal_lineage`: Upstream processing chain
   - `decay_annotation`: Time-decay metadata
   - `corroboration_annotation`: Corroboration metadata

4. **Regime Context** (if available)
   - Historical regime data
   - Macro indicators at signal time
   - Market conditions

---

## Evaluation Metrics

### Interpretation Quality Metrics

1. **Strategic Relevance Accuracy**
   - How well does strategic_relevance predict actual impact?
   - Correlation between relevance score and outcome magnitude

2. **Confidence Calibration**
   - Are HIGH confidence interpretations actually more accurate?
   - Confidence level vs. actual correctness

3. **Scenario Framing Accuracy**
   - Do scenario probabilities align with actual outcomes?
   - Base/bull/bear probability calibration

4. **Time Horizon Accuracy**
   - Does inferred time_horizon match actual impact timing?

### Feedback Quality Metrics

1. **Feedback Type Accuracy**
   - HIGH_INTEREST signals → actually high impact?
   - LOW_INTEREST signals → actually low impact?

2. **Feedback Consistency**
   - Similar signals → similar feedback?
   - Feedback is reproducible?

---

## Test Execution Guidelines

### Pre-Test Checklist

- [ ] Test mode is enabled (`test_mode=True`)
- [ ] Historical data is validated (complete, timestamped)
- [ ] Regime context is available for test period
- [ ] Expected outcomes are documented (for backtesting)
- [ ] No production memory access

### During Test Execution

- [ ] Monitor for any memory mutation attempts (should be blocked)
- [ ] Verify deterministic outputs (same signal → same result)
- [ ] Log all interpretations and feedback
- [ ] Track performance metrics

### Post-Test Validation

- [ ] Verify no memory state changes
- [ ] Validate determinism (re-run should produce identical results)
- [ ] Analyze interpretation quality metrics
- [ ] Document findings and recommendations

---

## Prohibited Activities During Testing

The following are forbidden:
- Capital allocation advice
- Trade suggestions
- Memory updates
- Threshold tuning based on outcomes
- Any form of self-improvement

Testing is **diagnostic**, not evolutionary.

### Additional Prohibited Behaviors

Even in test mode, FuggerBot MUST NOT:

1. **Execute trades**
   - No order placement
   - No capital deployment
   - No execution authority

2. **Mutate production state**
   - No memory mutation
   - No learning accumulation
   - No adaptive behavior

3. **Access future information**
   - No lookahead bias
   - Regime context frozen at signal time
   - Historical data only up to signal timestamp

4. **Override human authority**
   - All outputs remain advisory
   - No automated decisions
   - Human review required for any action

---

## Integration with CI/CD

### Automated Testing

Test mode enables automated testing of strategic reasoning:

```python
# pytest example
def test_strategic_interpretation_determinism():
    """Test that interpretations are deterministic."""
    reasoner = get_strategic_reasoner(test_mode=True)
    
    signal = create_test_signal()
    
    # Run twice
    interpretation_1 = reasoner.process_signal(signal)
    interpretation_2 = reasoner.process_signal(signal)
    
    # Should be identical
    assert interpretation_1.model_dump() == interpretation_2.model_dump()

def test_test_mode_memory_readonly():
    """Test that test mode prevents memory mutation."""
    reasoner = get_strategic_reasoner(test_mode=True, memory_store=mock_memory)
    
    signal = create_test_signal()
    reasoner.process_signal(signal)
    
    # Verify memory was not mutated
    assert mock_memory.mutation_count == 0
```

---

## Version Status

**v1.1 — Testing & Evaluation Extension**

- Test mode fully implemented
- Historical replay supported
- Shadow evaluation supported
- Backtesting framework ready

---

## Related Documentation

- [Agents.md](../Agents.md) - Core system specification
- [Strategic Reasoner README](../agents/strategic/README.md) - Implementation details
- [A2A Integration Test Guide](./A2A_INTEGRATION_TEST.md) - Integration testing

