# Agents.md — Testing Initiation Prompts (v1.1)

**Status**

Authoritative · Diagnostic-Only · Non-Mutating

**Applies to:**
- ai_inbox_digest v1.1 (Sensor Layer)
- FuggerBot v1.1 (Strategic Reasoner)

This document defines the explicit prompts and procedures used to initiate testing.
Testing is observational and evaluative only. No evolution is permitted.

---

## Global Testing Invariants (Hard Rules)

The following invariants must hold for all tests:
- `test_mode = True`
- No memory writes
- No adaptive decay updates
- No learning or tuning
- Deterministic, reproducible outputs
- No execution, allocation, or trade advice
- Human authority retained at all times

Violation of any invariant invalidates the test.

---

## Testing Entry Conditions

### ai_inbox_digest (Sensor Layer)

Before testing:
- Orchestrator initialized with `test_mode=True`
- A2A signals include full v1.1 payload:
  - SignalLineage
  - base_priority
  - decay_annotation
  - corroboration_score
- No adaptive decay mutations permitted
- Shadow Replay mode enabled

### FuggerBot (Strategic Reasoner)

Before testing:
- StrategicReasonerAgent initialized with `test_mode=True`
- Memory access is read-only
- Pattern learning disabled
- RegimeContextProvider active
- A2A ingest endpoint reachable

---

## Authorized Testing Scenarios

### Scenario A — Historical Replay

**Purpose:**
Evaluate how historical signals would have been interpreted at the time.

**Prompt:**

> "Replay historical signals in test mode.
> Produce strategic interpretations, regime context, and scenario framing.
> Do not mutate memory or adapt behavior."

---

### Scenario B — Shadow Evaluation

**Purpose:**
Compare interpretations across versions or configurations.

**Prompt:**

> "Ingest identical signals in parallel test runs.
> Compare interpretations and scenario probabilities.
> Record differences without ranking or preference."

---

### Scenario C — Backtesting Strategic Logic

**Purpose:**
Assess reasoning quality against known historical outcomes.

**Prompt:**

> "Process historical signals deterministically.
> Emit interpretations and feedback.
> Do not reference outcomes during interpretation."

---

## Required Outputs (Evidence)

### From ai_inbox_digest
- Routed A2A signals (v1.1 schema)
- Lineage records
- Base and effective priorities
- Corroboration scores
- Audit artifacts

### From FuggerBot
- Strategic interpretations
- Regime context annotations
- Scenario probability breakdowns
- A2A feedback records (diagnostic only)

---

## Evaluation (Human-Led)

After testing, humans evaluate:
1. Did interpretations align with contemporaneous context?
2. Were regime effects correctly identified?
3. Were scenarios coherent and explainable?
4. Was feedback disciplined and non-prescriptive?
5. Were all invariants preserved?

No automated score replaces human judgment.

---

## Prohibited Activities During Testing

The following are explicitly forbidden:
- Capital allocation advice
- Trade suggestions
- Memory updates
- Threshold tuning
- Adaptive decay changes
- Any form of self-improvement

Testing informs future versions only.

---

## Testing Exit Criteria

Testing may conclude when:
- All scenarios complete
- Outputs reviewed by humans
- Findings documented externally
- No system state has changed

No automatic progression is allowed.

---

## Authority Boundary Reminder
- ai_inbox_digest detects and refines signals
- FuggerBot interprets meaning and context
- Humans decide actions

This boundary is absolute.

---

## Related Documentation

- [Agents.md](../Agents.md) - Core system specification
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed testing procedures
- [A2A Integration Test Guide](./A2A_INTEGRATION_TEST.md) - Integration testing

---

**End of Testing Initiation Prompts**
