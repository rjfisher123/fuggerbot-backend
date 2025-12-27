# Agents.md — Testing Extensions
## Scenario B, Review Artifacts, and Advancement Criteria

**Version:** v1.1  
**Status:** Authoritative · Diagnostic-Only · Non-Mutating  
**Applies To:** ai_inbox_digest v1.1 → FuggerBot v1.1  

---

# Scenario B — Shadow Evaluation (Parallel, Non-Authoritative)

## Purpose

Shadow Evaluation exists to:

1. Compare **current v1.1 behavior** against an alternative configuration, model, or interpretation path.
2. Detect **divergence in strategic interpretation** without affecting production signals.
3. Evaluate robustness across regimes, signal classes, and time horizons.
4. Surface second-order effects and blind spots before formal evolution.

Shadow Evaluation does **not** exist to:
- Replace production outputs
- Override routed signals
- Modify thresholds or decay
- Train memory or models
- Recommend capital action

---

## Global Invariants (HARD RULES)

- `TEST_MODE=true` MUST be enabled
- Shadow outputs MUST NOT influence routing
- No state mutation, learning, or tuning permitted
- Shadow results are **non-authoritative**
- Production and shadow pipelines MUST be isolated

---

## Entry Conditions

### ai_inbox_digest

- v1.1 frozen pipeline
- Shadow mode enabled via configuration
- Dual emission capability (primary + shadow tags)

### FuggerBot

- Shadow reasoner instance enabled
- Distinct interpretation IDs
- Explicit labeling: `evaluation_mode=shadow`

---

## Authoritative Initiation Prompt — Scenario B

> **Initiate a shadow evaluation in parallel with the primary strategic reasoner. All signals SHALL be processed identically at the sensor layer, then evaluated independently by a shadow strategic reasoner whose outputs are logged for comparison only. Shadow outputs SHALL NOT affect routing, feedback, or authority.**

---

## Reference Invocation (Illustrative)

```bash
TEST_MODE=true \
SHADOW_EVAL=true \
python replay.py \
  --source history/2019_emails.json \
  --emit-a2a
```

---

## Expected Outputs

### From Primary Pipeline

- Standard A2ASignal payloads (v1.1 schema)
- Strategic interpretations (authoritative)
- A2A feedback records
- All standard replay artifacts

### From Shadow Pipeline

- Shadow strategic interpretations (non-authoritative)
- Comparison artifacts (divergence analysis)
- Side-by-side interpretation logs
- Divergence metrics (confidence delta, scenario framing delta)

---

## Evaluation Criteria

Human reviewers assess:

1. **Interpretation Divergence**
   - Where do primary and shadow interpretations differ?
   - Are differences explainable (configuration, regime context)?
   - Which interpretation aligns better with known outcomes?

2. **Robustness Assessment**
   - How sensitive are interpretations to configuration changes?
   - Are there signal classes or regimes where divergence is high?
   - Are there consistent blind spots?

3. **Evolution Readiness**
   - Should shadow configuration become primary?
   - Are shadow results consistently better/worse?
   - What risks exist in transitioning?

---

## Prohibited Behaviors

During Shadow Evaluation:

- Shadow outputs affecting production routing
- Modifying primary pipeline based on shadow results
- Cross-contamination between primary and shadow pipelines
- Learning or adaptation from shadow comparisons
- Capital decisions based on shadow outputs

---

## Success Criteria

Shadow Evaluation is successful when:

- Primary and shadow pipelines process signals independently
- Divergence is clearly identified and documented
- Comparison artifacts enable human assessment
- No production behavior is altered
- Shadow results remain non-authoritative

---

## Related Documentation

- [Historical Replay Testing Prompt](./TESTING_HISTORICAL_REPLAY.md) - Scenario A
- [Testing & Evaluation Initiation Prompts](./TESTING_EVALUATION_INITIATION.md) - General testing framework
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed procedures
- [Agents.md](../Agents.md) - Core system specification

---

**End of Scenario B: Shadow Evaluation**

