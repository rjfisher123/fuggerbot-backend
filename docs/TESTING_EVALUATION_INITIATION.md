# Agents.md — Testing & Evaluation Initiation Prompts  
**Applies to:**  
- ai_inbox_digest v1.1 (Sensor Layer)  
- FuggerBot v1.1 (Strategic Reasoner)  

**Status:** Authoritative  
**Mode:** Diagnostic / Test-Only  
**Effective Immediately**

---

## 1. Purpose of Testing

The purpose of testing is to **evaluate signal quality, timing, and strategic interpretability** using historical and shadow data **without mutating live system state**.

Testing is **diagnostic**, not evolutionary.

No system may adapt, learn, tune, or optimize during testing.

---

## 2. Global Testing Invariants (Hard Rules)

During all testing:

- `test_mode = True` **must** be enabled
- No memory writes are permitted
- No decay parameters may be updated
- No thresholds may be tuned
- No learning or pattern inference may occur
- Outputs must be deterministic and reproducible
- Human authority remains final

Violation of any invariant invalidates test results.

---

## 3. Testing Entry Conditions

### ai_inbox_digest (Sensor Layer)
Testing may begin only if:

- Agents 1–13 are frozen at v1.1
- A2ASignal schema validation passes
- Shadow Replay mode is enabled
- Lineage, decay, and corroboration annotations are attached to every signal
- Adaptive Decay is disabled in test mode

### FuggerBot (Strategic Reasoner)
Testing may begin only if:

- StrategicReasonerAgent initialized with `test_mode=True`
- Memory access is read-only
- No pattern learning or persistence is active
- RegimeContextProvider is enabled
- A2A feedback emission is enabled

---

## 4. Authorized Testing Scenarios

### Scenario A — Historical Replay
**Objective:** Evaluate signal surfacing and strategic interpretation using past data.

- Input: Historical emails with timestamps
- Mode: Deterministic replay
- Output:
  - Routed vs rejected signals
  - Strategic interpretations
  - Scenario probabilities
  - Regime context annotations
  - A2A feedback records

No live market action is implied.

---

### Scenario B — Shadow Evaluation
**Objective:** Compare interpretation quality without affecting production logic.

- Input: Live or recent signals
- Mode: Shadow (non-mutating)
- Output:
  - Parallel interpretations
  - No routing side effects
  - No decay or feedback influence

Used to detect drift and blind spots.

---

### Scenario C — Backtesting Strategic Logic
**Objective:** Validate reasoning quality under known market outcomes.

- Input: Curated historical signals
- Mode: Fully offline
- Output:
  - Interpretation correctness
  - Regime sensitivity
  - Timing adequacy

No capital framing may be evaluated as "correct" or "incorrect" based on P&L.

---

## 5. Required Outputs (Both Systems)

Each test run **must produce**:

### From ai_inbox_digest
- A2ASignal payloads
- Lineage records
- Base priority
- Decay annotations
- Corroboration scores
- Routing decision (routed / rejected)

### From FuggerBot
- Strategic interpretation text
- Regime context
- Scenario framing (base / bull / bear)
- Probability distribution
- Second-order implications
- A2AFeedback record

All outputs must be timestamped and traceable.

---

## 6. Evaluation Criteria (Human-Led)

Testing success is evaluated **only by human review** using the following questions:

1. Was the signal worth attention?
2. Was it surfaced early enough?
3. Did the strategic interpretation add insight?
4. Was regime context relevant?
5. Was noise appropriately ignored?

No automated scoring replaces human judgment.

---

## 7. Prohibited Activities During Testing

The following are explicitly forbidden:

- Trade execution
- Capital allocation advice
- Portfolio recommendations
- Strategy optimization
- Threshold tuning
- Memory updates
- Feedback-driven adaptation

Testing results **may inform future versions**, but **may not change v1.1 behavior**.

---

## 8. Exit Criteria for Testing Phase

Testing may conclude when:

- Sufficient historical coverage is evaluated
- Failure modes are identified and categorized
- Human confidence is established (or not)
- A conscious decision is made to:
  - Proceed to v1.2
  - Adjust scope
  - Halt further development

No automatic progression is permitted.

---

## 9. Authority Boundary Reminder

- ai_inbox_digest detects and refines signals
- FuggerBot interprets meaning and context
- Humans decide action

This boundary is inviolable.

---

## Related Documentation

- [Agents.md](../Agents.md) - Core system specification
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed testing procedures
- [A2A Integration Test Guide](./A2A_INTEGRATION_TEST.md) - Integration testing

