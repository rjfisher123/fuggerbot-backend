# Agents.md — Testing & Evaluation Initiation Prompts (v1.1)

**Status:** Authoritative · Diagnostic-Only · Non-Mutating

**Applies to:**
- ai_inbox_digest v1.1 (Sensor Layer)
- FuggerBot v1.1 (Strategic Reasoner)

---

## 1. Purpose of Testing

Testing is observational and evaluative only.

Testing exists to:
- Validate signal quality, routing, and explainability
- Evaluate strategic interpretation and regime sensitivity
- Detect false negatives and boundary failures
- Build human confidence prior to live use

Testing does not exist to:
- Improve models automatically
- Tune thresholds
- Adapt behavior
- Execute trades
- Recommend capital actions

---

## 2. Global Testing Invariants (Hard Rules)

These rules are non-negotiable.
- `test_mode = True` MUST be enabled
- No memory writes
- No learning, tuning, or adaptation
- Deterministic, reproducible outputs
- Advisory outputs only
- Human authority remains final

Violation of any invariant invalidates the test.

---

## 3. Testing Entry Conditions

### ai_inbox_digest MUST:
- Run with `TEST_MODE=true`
- Emit full A2ASignal v1.1 payloads
- Attach lineage, decay, corroboration metadata
- Persist evaluation artifacts (JSONL)

### FuggerBot MUST:
- Run with `test_mode=True`
- Accept A2A signals via ingest endpoint
- Produce deterministic interpretations
- Emit structured A2A feedback
- Perform no memory mutation

---

## 4. Authorized Testing Scenarios

### Scenario A — Historical Replay

**Prompt:**

> "Replay historical email signals using preserved timestamps.
> Evaluate whether ai_inbox_digest would have surfaced the signal and how FuggerBot interprets it given historical regime context.
> No state mutation permitted."

**Invocation Pattern:**
- Source: historical email dataset
- Mode: historical
- Time-aligned with known market events

---

### Scenario B — Shadow Evaluation

**Prompt:**

> "Process signals in parallel with live logic, but in test_mode.
> Compare routed vs ignored signals without influencing the live system."

**Invocation Pattern:**
- Source: recent emails
- Mode: shadow
- Outputs written to test artifacts only

---

### Scenario C — Backtesting Strategic Logic

**Prompt:**

> "Evaluate FuggerBot's strategic interpretations against known macro outcomes.
> Assess scenario framing, regime sensitivity, and feedback discipline.
> No capital advice permitted."

**Invocation Pattern:**
- Source: curated historical signals
- Mode: backtest
- Human-led evaluation

---

## 5. Required Outputs (Evidence)

### From ai_inbox_digest
- Routed and rejected signals
- Signal lineage records
- Base priority and decay annotations
- Corroboration scores
- Audit reports (false negatives)

### From FuggerBot
- Strategic interpretations
- Regime context annotations
- Scenario probability breakdowns
- A2A feedback records

All outputs must be inspectable and reproducible.

---

## 6. Evaluation (Human-Led)

Human reviewers must answer:
1. Was the signal detected appropriately?
2. Was decay behavior reasonable?
3. Was corroboration adequate?
4. Did regime context materially affect interpretation?
5. Was feedback disciplined and proportional?

No automated score replaces human judgment.

---

## 7. Prohibited Activities During Testing

Explicitly forbidden:
- Trade execution
- Capital allocation advice
- Memory updates
- Threshold tuning
- Self-improvement
- Strategy evolution

Testing is diagnostic, not evolutionary.

---

## 8. Testing Exit Criteria

Testing may conclude when:
- All scenarios complete
- Artifacts reviewed
- Human confidence achieved

Testing does not auto-advance system versions.

---

## 9. Authority Boundary Reminder
- ai_inbox_digest → Detects and refines signals
- FuggerBot → Interprets meaning and context
- Humans → Decide action

No agent holds authority over capital.

---

## Core Principle

Testing observes reality. It does not change it.

---

## Related Documentation

- [Agents.md](../Agents.md) - Core system specification
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed testing procedures
- [A2A Integration Test Guide](./A2A_INTEGRATION_TEST.md) - Integration testing
