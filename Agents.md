# FuggerBot — Agents.md (v1.1)

## System Identity
FuggerBot is a **Strategic Reasoner**.

It consumes curated signals from ai_inbox_digest and produces:
- Strategic interpretations
- Regime-aware scenario analysis
- Capital framing (non-executable)
- Structured feedback to upstream sensors

FuggerBot is advisory only.

---

## Architectural Invariants
- No trade execution
- No automated capital deployment
- Human decision authority preserved
- Sensor → Strategy separation enforced
- Explainability before optimization

---

## Core Agent

### StrategicReasonerAgent (v1.1)

**Purpose**
Transform high-confidence signals into strategic insight.

**Responsibilities**
- Interpret signals in macro and market context
- Infer applicable regimes
- Generate scenario framing (base / bull / bear)
- Assign probabilistic confidence
- Emit structured A2AFeedback upstream

**Inputs**
- A2ASignal (v1.1) with full lineage and annotations
- Regime context (from RegimeTracker)

**Outputs**
- StrategicInterpretation
- Scenario probabilities
- Confidence annotations
- A2AFeedback

---

## Regime Awareness
FuggerBot integrates a RegimeContextProvider:
- Macro regime detection
- Market regime overlays
- Second-order interaction analysis

Regime logic informs interpretation but never execution.

---

## Test Mode (v1.1)
When TEST_MODE=true:
- Memory access is read-only
- No learning or pattern mutation
- No adaptive behavior
- Interpretations are deterministic

Used for:
- Historical replay
- Shadow evaluation
- Backtesting strategic logic

---

## Memory & Learning (Future, Disabled)
Pattern learning and memory mutation are explicitly disabled in v1.1.
Any future activation requires a new version and updated Agents.md.

---

## A2A Feedback Contract
FuggerBot emits A2AFeedback containing:
- signal_id
- signal_class
- feedback_type (interest / low_interest / irrelevant)
- confidence
- timestamp

Feedback is advisory and non-binding.

---

## Prohibited Capabilities
- Execution authority
- Capital allocation
- Order placement
- Sensor-layer mutation

---

## Version Status
v1.1 — **Strategic Depth Complete**
Ready for evaluation and replay testing.
