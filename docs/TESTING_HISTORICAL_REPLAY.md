# Agents.md — Testing Initiation Prompt
## Scenario A: Historical Replay (Deterministic)

### Status
**Authoritative · Diagnostic-Only · Non-Mutating · v1.1**

---

## Purpose

Historical Replay exists to:
1. Evaluate **signal detection quality** in ai_inbox_digest using hindsight.
2. Evaluate **strategic interpretation correctness** in FuggerBot given historical context.
3. Surface **false negatives and weak signals** without modifying live behavior.
4. Produce **reproducible evidence artifacts** for human review.

Historical Replay does NOT exist to:
- Improve models
- Tune thresholds
- Learn patterns
- Adapt decay
- Influence live routing or strategy

> Testing observes reality. It does not change it.

---

## Global Testing Invariants (Hard Rules)

The following rules are non-negotiable.  
Violation invalidates the test.

- `test_mode = True` MUST be enabled
- NO OpenAI / LLM clients may be instantiated
- ONLY deterministic Test* agents may execute
- NO memory writes (read-only access only)
- NO parameter updates
- Outputs MUST be reproducible across runs

---

## System Entry Conditions

### ai_inbox_digest v1.1
- Frozen agent pipeline (Agents 1–13)
- Deterministic Test Agents enabled
- Shadow Replay (`test_mode=True`) supported
- A2A emission enabled
- Full artifact persistence active

### FuggerBot v1.1
- Strategic Reasoner only (advisory)
- RegimeContextProvider enabled
- Test mode enforced
- No learning, memory mutation, or adaptation

---

## Initiation Prompt (Authoritative)

> Initiate a deterministic Historical Replay using archived email data.
> 
> ai_inbox_digest SHALL replay historical messages through the frozen v1.1
> sensor pipeline with test_mode enabled, emitting A2A signals with full
> lineage and audit annotations.
> 
> FuggerBot SHALL ingest each signal, apply regime-aware strategic interpretation,
> generate scenario framing and probabilities, and emit structured A2A feedback.
> 
> No system behavior may adapt, learn, or mutate as a result of this replay.

---

## Reference Invocation Pattern

### ai_inbox_digest
```bash
TEST_MODE=true python replay.py --source history/2019_emails.json
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
