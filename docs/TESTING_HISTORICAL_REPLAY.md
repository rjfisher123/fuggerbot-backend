# Agents.md — Scenario A Testing Prompt
## Historical Replay (Deterministic, Automated A2A Emission)

**Version:** v1.1  
**Status:** Authoritative · Diagnostic-Only · Non-Mutating  
**Applies To:** ai_inbox_digest v1.1 → FuggerBot v1.1  
**Scenario:** A — Historical Replay

---

## Purpose

Historical Replay exists to:

1. Evaluate signal detection quality using historical inbox data with hindsight.
2. Validate temporal handling (decay, prioritization) under simulated time.
3. Verify end-to-end A2A contract compliance and ingestion.
4. Assess strategic interpretation correctness without live system mutation.

Historical Replay does **not** exist to:
- Tune thresholds
- Adapt models
- Modify memory
- Generate capital actions
- Learn from outcomes

---

## Global Testing Invariants (HARD RULES)

The following **MUST** hold. Violation invalidates the test:

- `TEST_MODE=true` SHALL be enabled
- Deterministic `Test*Agent` substitutions SHALL be enforced
- No LLM / OpenAI clients SHALL be instantiated
- No memory writes or adaptive behavior SHALL occur
- Outputs MUST be reproducible across runs
- Emission is allowed **only** via explicit opt-in

---

## Entry Conditions

### ai_inbox_digest v1.1 (Sensor Layer)

- Core agents frozen (Agents 11–13)
- Deterministic Test Agents available
- Historical normalization layer enabled
- Replay harness (`replay.py`) available
- A2A emission disabled by default

### FuggerBot v1.1 (Strategic Reasoner)

- API running and reachable
- `/api/a2a/ingest` endpoint operational
- `test_mode=True` enforced
- No execution or memory mutation enabled

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

## A2A Emission Mechanism

### Emission Control

Historical replay **MAY** emit A2A signals **only** when explicitly invoked with `--emit-a2a`.

Without this flag, replay **SHALL** produce outputs **only** for local analysis (logs, artifacts, JSON files).

### Signal Validation Requirements

Before emission, each signal **MUST** satisfy:

- Valid `A2ASignal` schema (v1.1)
- Complete `signal_lineage` with `upstream_message_ids`
- Valid `decay_annotation` and `corroboration_annotation`
- Non-null `signal_id`, `signal_class`, `summary`, `created_at`
- `effective_priority` and `corroboration_score` within [0.0, 1.0]

Any signal failing validation **SHALL** be logged and **SHALL NOT** be emitted.

### Emission Behavior

- **Chronological Ordering**: Signals **SHALL** be emitted in strict chronological order based on `created_at` timestamps
- **Rate Limiting**: Default 10 signals/second (configurable via `--a2a-rate-limit`)
- **Error Handling**: Log failures, continue with next signal, emit completion summary

---

## Authoritative Initiation Prompt

> **Initiate a deterministic historical replay of archived inbox messages using ai_inbox_digest v1.1 in test mode. Normalize historical inputs to the v1.1 Message schema, simulate relative time, evaluate routing criteria, and—only for qualifying signals—emit fully validated A2A signals to FuggerBot v1.1 for strategic interpretation. The process SHALL be diagnostic, non-mutating, and reproducible.**

---

## Reference Invocation (Authoritative)

### ai_inbox_digest — Replay + A2A Emission

```bash
TEST_MODE=true \
A2A_TRANSPORT=http \
A2A_ENDPOINT=http://localhost:8000/api/a2a/ingest \
python replay.py \
  --source history/2019_emails.json \
  --emit-a2a
```

### Local Analysis Only (No Emission)

```bash
TEST_MODE=true python replay.py --source history/2019_emails.json
```

### FuggerBot (Strategic Reasoner)

FuggerBot processes incoming A2A signals automatically via `/api/a2a/ingest` endpoint with `test_mode=True`.

---

## Expected Outputs

### From ai_inbox_digest

- Routed A2ASignal payloads (v1.1 schema) - if `--emit-a2a` enabled
- Rejected signals with rejection reasons
- Signal lineage records
- Decay annotations (historical timestamps)
- Corroboration scores
- Audit artifacts (false negatives)
- Emission logs (if `--emit-a2a` enabled)
- Replay summary with statistics

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

3. **A2A Contract Compliance**
   - Were all emitted signals valid v1.1 schema?
   - Was lineage complete and accurate?
   - Did emission respect chronological ordering?

4. **Strategic Interpretation**
   - Did interpretations align with contemporaneous market context?
   - Were regime effects correctly identified?
   - Were scenarios coherent and explainable?

5. **Reproducibility**
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
- Emitting signals without `--emit-a2a` flag

---

## Success Criteria

Historical Replay is successful when:

- All signals processed deterministically
- Outputs are reproducible across runs
- Human reviewers can assess signal quality and interpretation correctness
- False negatives are identified and categorized
- No system state has been mutated
- All artifacts are preserved for review
- A2A emissions (if enabled) complete successfully with full validation

---

## Authority Boundary

- **ai_inbox_digest**: Detects, normalizes, and emits historical signals via A2A contract
- **FuggerBot**: Interprets signals in historical regime context (test mode)
- **Humans**: Evaluate quality and correctness

No agent may make capital decisions or recommendations.

---

## Related Documentation

- [Testing & Evaluation Initiation Prompts](./TESTING_EVALUATION_INITIATION.md) - General testing framework
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed procedures
- [Scenario A Extension (Deprecated)](./TESTING_HISTORICAL_REPLAY_A2A_EXTENSION.md) - Previously separate extension, now consolidated
- [Agents.md](../Agents.md) - Core system specification

---

**End of Historical Replay Testing Prompt**
