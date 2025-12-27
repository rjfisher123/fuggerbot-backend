# Agents.md — Scenario A/B Extension: Earnings Stress Test (Deterministic)

## Status
**Authoritative · Diagnostic-Only · Non-Mutating · v1.1**

Applies to:
- ai_inbox_digest v1.1 (Sensor Layer)
- FuggerBot v1.1 (Strategic Reasoner)

---

## Purpose

This extension defines how **earnings-related signals** SHALL be evaluated during
Scenario A (Historical Replay) and Scenario B (Shadow Evaluation) while operating
in `TEST_MODE=true`.

The objective is to validate that:

1. Earnings signals of **material strategic relevance** are detected.
2. Non-material earnings noise is filtered.
3. Deterministic test behavior remains reproducible.
4. No live-system behavior is altered.

This extension exists to **expand deterministic coverage**, not to evolve strategy.

---

## Global Invariants (Hard Rules)

The following rules SHALL hold. Any violation INVALIDATES the test.

- `TEST_MODE=true` MUST be enabled.
- No LLM or stochastic components may execute.
- No adaptive learning, tuning, or memory writes are permitted.
- Deterministic Test* agents MUST be used.
- Routing decisions MUST be explainable via rules.
- Production routing behavior MUST NOT be affected.

---

## Deterministic Earnings Classification Rules (MANDATED)

When operating in test mode, the following rule set SHALL be applied by
`TestClassificationAgent`, `TestPriorityScoringAgent`, and
`TestCorroborationAgent`.

### Classification: `earnings`

A message SHALL be classified as `earnings` if **any** of the following are true:

- Subject or body contains ≥1 of:
  - `earnings`
  - `revenue`
  - `guidance`
  - `quarter`
  - `fiscal`
  - `year-over-year`
  - `beat`
  - `miss`
- Sender domain matches:
  - `investorrelations@*`
  - `@sec.gov`

Confidence:
- Base confidence = **0.75**
- +0.05 if sender is investor relations
- Cap at 0.90

---

## Deterministic Priority Scoring Rules

For `earnings` classification:

| Condition                               | Base Priority |
|----------------------------------------|---------------|
| Revenue growth > 30%                   | 0.75          |
| Explicit "beat expectations" language  | 0.70          |
| Guidance raise / reaffirmation          | 0.65          |
| Generic earnings announcement           | 0.55          |

Priority MUST NOT exceed **0.80** in test mode.

---

## Deterministic Corroboration Rules

Corroboration score SHALL be assigned as follows:

| Source Signal                           | Score |
|----------------------------------------|-------|
| Investor Relations sender              | 0.60  |
| SEC filing language                    | 0.70  |
| Earnings + quantitative metrics        | +0.10 |
| Third-party analyst reference present  | +0.10 |

Cap corroboration at **0.80**.

---

## Routing Rule (Unchanged)

A signal SHALL route only if:

- `effective_priority ≥ 0.40`
- `corroboration_score ≥ 0.50`

No threshold changes are permitted during testing.

---

## Scenario A: Historical Replay (Earnings)

### Authoritative Initiation Prompt

> "Execute Scenario A Historical Replay on earnings-related historical data
> using deterministic Test* agents only. Normalize historical inputs, evaluate
> classification, priority, decay, and corroboration deterministically, and
> emit A2A signals only if routing criteria are met. No live system behavior
> may be modified."

### Reference Invocation

```bash
TEST_MODE=true \
A2A_TRANSPORT=http \
A2A_ENDPOINT=http://localhost:8000/api/a2a/ingest \
python replay.py \
  --source history/2022_nvda_earnings.json \
  --emit-a2a
```

---

## Scenario B: Shadow Evaluation (Earnings)

### Authoritative Initiation Prompt

> "Execute Scenario B Shadow Evaluation on earnings-related data, comparing
> primary v1.1 routing behavior against shadow configuration using deterministic
> Test* agents. Log divergence and comparison artifacts. No production routing
> behavior may be affected."

### Reference Invocation

```bash
TEST_MODE=true \
SHADOW_EVAL=true \
A2A_TRANSPORT=http \
A2A_ENDPOINT=http://localhost:8000/api/a2a/ingest \
python replay.py \
  --source history/2022_nvda_earnings.json \
  --emit-a2a
```

---

## Expected Outputs

### From ai_inbox_digest (Earnings Classification)

- Earnings signals routed (if criteria met)
- Classification confidence scores (deterministic)
- Priority scores (capped at 0.80)
- Corroboration scores (capped at 0.80)
- Rejected earnings noise (below thresholds)
- Routing decision audit trail

### From FuggerBot (Strategic Interpretation)

- Strategic interpretations for earnings signals
- Regime context annotations
- Scenario probability breakdowns
- Time horizon assessment (typically "quarters" for earnings)
- Capital framing (sector/asset class exposure)

---

## Evaluation Criteria

Human reviewers assess:

1. **Classification Accuracy**
   - Were material earnings signals correctly classified?
   - Was noise filtered appropriately?
   - Did confidence scores align with signal quality?

2. **Priority Scoring Consistency**
   - Were high-impact earnings (e.g., 30%+ revenue growth) prioritized?
   - Were generic announcements scored lower?
   - Did scores remain within test mode caps (0.80)?

3. **Corroboration Reliability**
   - Did official sources (SEC, IR) receive higher scores?
   - Were quantitative metrics recognized?
   - Did scores remain within test mode caps (0.80)?

4. **Routing Discipline**
   - Were signals routed only when criteria met (priority ≥ 0.40, corroboration ≥ 0.50)?
   - Was earnings noise correctly filtered out?
   - Were routing decisions explainable via rules?

5. **Strategic Interpretation Quality**
   - Did interpretations reflect earnings context?
   - Were time horizons appropriate (quarters for earnings)?
   - Was capital framing relevant (sector exposure)?

---

## Prohibited Behaviors

During Earnings Stress Test:

- Modifying classification rules during testing
- Adjusting priority or corroboration thresholds
- Learning from earnings outcomes
- Adapting decay rates based on earnings signals
- Mutating memory or routing logic
- Bypassing deterministic Test* agent requirements

---

## Success Criteria

Earnings Stress Test is successful when:

- Material earnings signals are correctly classified and routed
- Non-material earnings noise is filtered
- All scoring remains within test mode caps
- Routing decisions are explainable via deterministic rules
- Strategic interpretations reflect earnings context appropriately
- No production behavior is altered
- All outputs are reproducible across runs

---

## Related Documentation

- [Historical Replay Testing Prompt](./TESTING_HISTORICAL_REPLAY.md) - Scenario A base specification
- [Scenario B Shadow Evaluation](./TESTING_SCENARIO_B_SHADOW_EVALUATION.md) - Scenario B base specification
- [Testing & Evaluation Initiation Prompts](./TESTING_EVALUATION_INITIATION.md) - General testing framework
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed procedures
- [Agents.md](../Agents.md) - Core system specification

---

**End of Earnings Stress Test Extension**

