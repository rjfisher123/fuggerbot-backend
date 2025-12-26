# Agents.md — Testing Initiation Prompt
## Scenario A: Historical Replay (Deterministic)

**Version:** v1.1  
**Status:** Authoritative · Diagnostic-Only · Non-Mutating

---

## Purpose

Historical Replay exists to evaluate, with hindsight:

1. Signal detection quality (what was surfaced vs missed)
2. Temporal handling (decay, lag, corroboration timing)
3. Strategic interpretation correctness under known outcomes
4. Evidence quality and explainability (lineage, annotations, feedback)

Historical Replay does **NOT** exist to:
- Improve models or thresholds
- Tune decay, scoring, or regimes
- Modify memory or behavior
- Produce capital allocation or trade advice
- Influence live system behavior

---

## Global Testing Invariants (Hard Rules)

The following **MUST** hold for the test to be valid:

- `test_mode = True` **SHALL** be enabled
- All memory access is **read-only**
- **No OpenAI / LLM clients** may be instantiated
- Deterministic `Test*Agent` implementations **MUST** be used
- No adaptive behavior, learning, or persistence is permitted
- Outputs **MUST** be reproducible across runs

Violation of any invariant **invalidates the test**.

---

## System Entry Conditions

### ai_inbox_digest v1.1
- Agents 11–13 active and frozen
- Shadow Replay (`test_mode=True`) enabled
- Deterministic Test Agents in place for all AI-backed stages
- A2A contract v1.1 enforced

### FuggerBot v1.1
- Strategic Reasoner only (advisory)
- Regime context enabled
- `test_mode=True`
- Memory and learning disabled
- A2A ingest and feedback endpoints active

---

## Authoritative Initiation Prompt

> **Initiate a deterministic historical replay using archived email data.**  
> The system SHALL process historical messages in chronological order, emit v1.1-compliant A2A signals with full lineage and audit annotations, route them to FuggerBot for strategic interpretation, and collect structured feedback.  
> No system state, memory, thresholds, or adaptive parameters may be modified.

---

## Reference Invocation Pattern

### ai_inbox_digest (Sensor Layer)
```bash
TEST_MODE=true python replay.py --source history/2019_emails.json
```

### FuggerBot (Strategic Reasoner)
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
