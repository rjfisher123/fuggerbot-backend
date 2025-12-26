# Testing Initiation Prompt — Option A: Historical Replay (Deterministic)

## Status
**Authoritative · Diagnostic-Only · Non-Mutating · v1.1**

This prompt initiates a fully deterministic, non-mutating historical replay across
**ai_inbox_digest v1.1** (Sensor Layer) and **FuggerBot v1.1** (Strategic Reasoner).

---

## Purpose

Historical Replay exists to:

- Evaluate **signal detection quality** using real historical inputs
- Observe **temporal behavior** (decay, corroboration, routing)
- Assess **strategic interpretation correctness** with hindsight
- Identify **false negatives** and **missed signal classes**

This mode **does not exist** to:
- Tune thresholds
- Modify decay behavior
- Update memory or patterns
- Improve models automatically
- Produce capital or trade decisions

> **Testing observes reality. It does not change it.**

---

## Global Testing Invariants (Hard Rules)

The following rules are mandatory. Violation invalidates the test.

- `test_mode = True` MUST be enabled
- No OpenAI / LLM clients may be instantiated
- All AI agents MUST be deterministic test agents
- No memory writes
- No adaptive decay updates
- No feedback-driven tuning
- Outputs MUST be reproducible from identical inputs

---

## System Entry Conditions

### ai_inbox_digest v1.1
- Orchestrator initialized with `test_mode=True`
- All AI agents swapped for deterministic `Test*` agents
- Full evaluation artifacts persisted (lineage, decay, corroboration)
- A2A payload includes full v1.1 schema

### FuggerBot v1.1
- StrategicReasoner initialized with `test_mode=True`
- Memory access is read-only
- No learning or pattern updates
- Regime context allowed (read-only)
- A2A feedback emission enabled

---

## Initiation Prompt (Authoritative)

> **Initiate Historical Replay (Deterministic) using archived historical inputs.  
> Replay must proceed with test_mode=True across all agents.  
> No adaptive, stochastic, or learning behavior is permitted.  
> All outputs must be diagnostic, explainable, and reproducible.**

---

## Reference Invocation Pattern

### ai_inbox_digest
```bash
export TEST_MODE=true
python replay.py --source history/2019_emails.json --mode historical
```

### FuggerBot
```python
from agents.strategic import get_strategic_reasoner

reasoner = get_strategic_reasoner(test_mode=True)

# Process historical signals in chronological order
for signal in historical_signals:
    interpretation = reasoner.process_signal(signal)
    # Log interpretation (no mutation)
```

---

## Expected Outputs

### From ai_inbox_digest
- Routed A2ASignal payloads (v1.1 schema)
- Rejected signals with rejection reasons
- Signal lineage records
- Decay annotations (historical timestamps)
- Corroboration scores
- Audit artifacts (false negatives)

### From FuggerBot
- Strategic interpretations for each signal
- Regime context annotations (historical regime state)
- Scenario probability breakdowns (base/bull/bear)
- A2A feedback records
- Interpretation timestamps aligned with signal timestamps

---

## Evaluation Criteria (Human-Led)

After replay, human reviewers assess:

1. **Signal Detection Quality**
   - Were important signals surfaced?
   - Were false positives minimized?
   - Were false negatives identified and documented?

2. **Temporal Behavior**
   - Was decay behavior reasonable given time elapsed?
   - Did corroboration scores reflect signal quality?
   - Were routing decisions consistent?

3. **Strategic Interpretation**
   - Did interpretations align with contemporaneous market context?
   - Were regime effects correctly identified?
   - Were scenarios coherent and explainable?

4. **Reproducibility**
   - Same inputs → same outputs?
   - Are all outputs timestamped and traceable?
   - Can replay be rerun with identical results?

---

## Prohibited Behaviors

During Historical Replay, the following are explicitly forbidden:

- Accessing LLM APIs (OpenAI, Anthropic, etc.)
- Mutating memory or learning patterns
- Tuning thresholds based on outcomes
- Adaptive decay parameter changes
- Feedback-driven behavior modification
- Trade or capital allocation advice
- Any form of self-improvement

---

## Success Criteria

Historical Replay is successful when:

- All signals processed deterministically
- Outputs are reproducible across runs
- Human reviewers can assess signal quality and interpretation correctness
- False negatives are identified and categorized
- No system state has been mutated
- All artifacts are preserved for review

---

## Authority Boundary

- **ai_inbox_digest**: Detects and refines historical signals
- **FuggerBot**: Interprets signals in historical regime context
- **Humans**: Evaluate quality and correctness

No agent may make capital decisions or recommendations.

---

## Related Documentation

- [Testing & Evaluation Initiation Prompts](./TESTING_EVALUATION_INITIATION.md) - General testing framework
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed procedures
- [Agents.md](../Agents.md) - Core system specification

---

**End of Historical Replay Testing Prompt**

