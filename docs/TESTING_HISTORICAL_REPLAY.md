# Agents.md — Scenario A Testing Prompt
## Historical Replay (Deterministic · v1.1)

**Status:** Authoritative · Diagnostic-Only · Non-Mutating  
**Applies To:** ai_inbox_digest v1.1 → FuggerBot v1.1  
**Scenario:** A — Historical Replay

---

## Purpose

Historical Replay exists to:

1. Evaluate historical signal detection quality using hindsight data
2. Validate temporal handling (decay, relevance, corroboration)
3. Assess strategic interpretation correctness downstream
4. Produce explainable, auditable artifacts for human review

Historical Replay does **not** exist to:
- Modify system behavior
- Tune thresholds
- Train agents
- Learn patterns
- Execute or recommend capital actions

---

## Global Invariants (Hard Rules)

During Historical Replay:

- `test_mode = true` **MUST** be enabled
- No LLM clients **MAY** be instantiated
- No memory **MAY** be mutated
- All outputs **MUST** be deterministic and reproducible
- Violating any invariant invalidates the test

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

## Historical Input Normalization (MANDATED)

Historical data **WILL NOT** conform to the v1.1 live `Message` schema.

To preserve strict live contracts, Historical Replay **SHALL** apply a
**deterministic normalization layer** prior to validation.

### Authorized Normalizations (Replay-Only)

| Field | Rule |
|------|-----|
| `id` | Accept `message_id` as alias |
| `to` | If list → join into comma-separated string |
| `timestamp` | Map from `date` / `sent_at` / `created_at` |
| Missing optional fields | Fill explicitly with `null` |

> This normalization **MUST NOT** exist in live ingestion paths.

---

## Initiation Prompt (Authoritative)

> **Initiate Historical Replay using archived communications.**  
>  
> The system SHALL replay historical messages in strict test mode,
> apply deterministic normalization, enforce v1.1 schemas,
> emit A2A signals with full lineage, and prevent all state mutation.  
>  
> Outputs SHALL be produced solely for human evaluation.

---

## Reference Invocation (ai_inbox_digest)

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
