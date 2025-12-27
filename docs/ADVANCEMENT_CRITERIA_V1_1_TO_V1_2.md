# Advancement Criteria — v1.1 → v1.2

## Purpose

Define the **explicit, testable conditions** under which the system may advance from  
**v1.1 (Frozen / Diagnostic)** to **v1.2 (Selective Production Enablement)**.

Advancement is **not automatic** and **not model-driven**.  
It requires **evidence**, **human review**, and **documented boundary behavior**.

---

## New Signal Class: `monitor_only`

### Definition

`monitor_only` is a **non-authoritative signal classification** indicating:

- The input contains **potentially relevant information**
- Confidence or corroboration is **insufficient for strategic routing**
- The signal **must not influence portfolio decisions**
- The signal is preserved **only for visibility, trend detection, or follow-up**

This class exists to **absorb ambiguity without escalation**.

---

### Monitor-Only Routing Rules

A signal **MUST** be classified as `monitor_only` if **any** of the following hold:

- `corroboration_score < 0.6`
- Sender authority is **non-primary** (e.g., non-IR, non-regulatory) AND content is speculative
- Hedging language detected (`may`, `could`, `sources say`, `unclear`)
- Conflicting sentiment within the same message
- Earnings-related content without verified figures or guidance

---

### Monitor-Only Invariants

Monitor-only signals:

- ❌ MUST NOT be routed to FuggerBot strategic evaluation
- ❌ MUST NOT generate A2AFeedback with `high_interest`
- ❌ MUST NOT influence adaptive decay or learning mechanisms
- ✅ MAY be logged, surfaced, and reviewed by humans
- ✅ MAY be promoted later if corroboration increases (future scenario)

---

### Monitor-Only A2A Handling

If emitted, the payload **MUST** include:

```json
{
  "signal_class": "monitor_only",
  "routing": "non_strategic",
  "strategic_relevance": null
}
```

---

## Advancement Criteria (v1.1 → v1.2)

### Evidence Requirements

Before advancing to v1.2, the following evidence **MUST** be documented:

1. **Historical Replay (Scenario A) Evidence**
   - At least 100 historical signals processed deterministically
   - Classification accuracy ≥ 85% for earnings, policy, and geopolitical signals
   - False positive rate ≤ 15% for strategic routing
   - False negative rate ≤ 10% for high-priority signals
   - Reproducibility: Same inputs → same outputs (100% match)

2. **Shadow Evaluation (Scenario B) Evidence**
   - At least 50 signals processed in parallel (primary vs shadow)
   - Divergence analysis documented with explainable differences
   - Shadow configuration validated as stable and deterministic
   - No production behavior contamination

3. **Earnings Stress Test Evidence**
   - At least 20 earnings signals processed deterministically
   - Material earnings correctly classified and routed
   - Earnings noise correctly filtered (monitor_only classification appropriate)
   - Priority and corroboration scores within test mode caps

4. **Monitor-Only Classification Evidence**
   - Monitor-only rules applied correctly (corroboration < 0.6, hedging language, etc.)
   - No monitor-only signals routed to strategic evaluation
   - Monitor-only signals logged and visible for human review
   - Zero instances of monitor-only signals generating `high_interest` feedback

5. **A2A Contract Compliance Evidence**
   - All emitted signals valid v1.1 schema
   - Complete signal lineage for all routed signals
   - Chronological ordering preserved in emissions
   - Strategic interpretations generated for all routed signals

6. **Reproducibility Evidence**
   - All test runs produce identical outputs given same inputs
   - No non-deterministic behavior observed
   - All artifacts preserved and auditable

---

## Human Review Requirements

Before advancement, **human reviewers MUST**:

1. Review all evidence artifacts (logs, summaries, comparison reports)
2. Validate classification accuracy against known ground truth
3. Assess strategic interpretation quality and relevance
4. Verify no production behavior mutation occurred
5. Confirm all invariants were preserved
6. Document approval or rejection with rationale

---

## Boundary Behavior Documentation

Before advancement, the following boundary behaviors **MUST** be documented:

1. **Edge Cases**
   - How ambiguous signals are classified (monitor_only vs routed)
   - How conflicting signals are handled
   - How time-sensitive signals are prioritized
   - How low-confidence but high-relevance signals are handled

2. **Failure Modes**
   - What happens when A2A endpoint is unreachable
   - What happens when signal validation fails
   - What happens when downstream processing errors occur
   - How partial or corrupted signals are handled

3. **Monitor-Only Behavior**
   - How monitor-only signals are stored and retrieved
   - How monitor-only signals can be promoted (future)
   - How monitor-only signals are surfaced to humans
   - How monitor-only signals are excluded from analytics

---

## Advancement Decision Process

1. **Evidence Collection Phase**
   - Execute Scenario A (Historical Replay) with required evidence
   - Execute Scenario B (Shadow Evaluation) with required evidence
   - Execute Earnings Stress Test
   - Collect all artifacts and logs

2. **Human Review Phase**
   - Human reviewers assess all evidence
   - Validate against advancement criteria
   - Document findings and recommendations

3. **Decision Phase**
   - Go/No-Go decision based on evidence and review
   - If Go: Document boundary behaviors, update version, enable selective production
   - If No-Go: Document gaps, return to evidence collection

---

## Post-Advancement Requirements (v1.2)

Once advanced to v1.2, the system **MUST**:

1. Maintain all v1.1 invariants (test_mode capabilities preserved)
2. Support selective production enablement (configurable)
3. Preserve monitor_only classification and routing rules
4. Continue to support Historical Replay and Shadow Evaluation
5. Maintain A2A contract compliance
6. Preserve all diagnostic and audit capabilities

---

## Prohibited Advancements

The system **MUST NOT** advance to v1.2 if:

- Any evidence requirements are not met
- Human review identifies critical gaps
- Reproducibility is not demonstrated
- Production behavior mutation occurred during testing
- Monitor-only invariants were violated
- A2A contract compliance was not demonstrated

---

## Related Documentation

- [Historical Replay Testing Prompt](./TESTING_HISTORICAL_REPLAY.md) - Scenario A
- [Scenario B Shadow Evaluation](./TESTING_SCENARIO_B_SHADOW_EVALUATION.md) - Scenario B
- [Earnings Stress Test](./TESTING_EARNINGS_STRESS_TEST.md) - Earnings extension
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - General testing procedures
- [Agents.md](../Agents.md) - Core system specification

---

**End of Advancement Criteria v1.1 → v1.2**

