# Agents.md — Scenario A Extension  
## Automated Historical Replay → A2A Emission

**Version:** v1.1  
**Status:** Authoritative · Diagnostic-Only · Non-Mutating  
**Applies To:** ai_inbox_digest v1.1 → FuggerBot v1.1  
**Scenario:** A — Historical Replay (Deterministic, Automated)

---

## Purpose

This extension authorizes and defines the **automated emission of historically replayed signals** from `ai_inbox_digest` to downstream A2A consumers (e.g., FuggerBot) **without manual intervention**, while preserving all v1.1 invariants.

This capability exists to:

1. Enable end-to-end forensic testing at scale
2. Remove manual JSON crafting and `curl` steps
3. Guarantee schema fidelity and provenance correctness
4. Support reproducible, audit-ready historical evaluation

This capability does **not** exist to:
- Modify live behavior
- Tune thresholds or decay
- Introduce learning or adaptation
- Influence capital decisions

---

## Global Invariants (Hard Rules)

All automated replay → A2A emission **SHALL** obey the following:

1. `test_mode = True` **MUST** be enabled
2. Deterministic `Test*Agent` substitutions **MUST** be active
3. No LLM clients **MAY** be instantiated
4. No persistent state **MAY** be mutated
5. Only fully validated v1.1 `A2ASignal` objects **MAY** be emitted
6. Rejected or partial signals **MUST NOT** be emitted
7. Emission is forbidden outside Historical Replay

Violation of any rule invalidates the test.

---

## Authorized Mechanism

### Emission Control Flag

Historical replay **MAY** emit A2A signals **only** when explicitly invoked with:

```bash
--emit-a2a
```

Without this flag, replay **SHALL** produce outputs **only** for local analysis (logs, artifacts, JSON files).

### A2A Endpoint Configuration

When `--emit-a2a` is present, the system **SHALL**:

1. Require `--a2a-endpoint <URL>` (e.g., `http://localhost:8000/api/a2a/ingest`)
2. Validate endpoint accessibility before starting replay
3. Emit signals in chronological order (per historical timestamps)
4. Respect rate limits and retry logic (configurable)
5. Log all emission attempts and responses
6. Continue replay even if individual emissions fail (with error logging)

---

## Signal Validation Requirements

Before emission, each signal **MUST** satisfy:

- Valid `A2ASignal` schema (v1.1)
- Complete `signal_lineage` with `upstream_message_ids`
- Valid `decay_annotation` and `corroboration_annotation`
- Non-null `signal_id`, `signal_class`, `summary`, `created_at`
- `effective_priority` and `corroboration_score` within [0.0, 1.0]

Any signal failing validation **SHALL** be logged and **SHALL NOT** be emitted.

---

## Emission Behavior

### Chronological Ordering

Signals **SHALL** be emitted in strict chronological order based on `created_at` timestamps from historical data.

If multiple signals share the same timestamp, order **SHALL** be deterministic (e.g., by `signal_id` lexicographic order).

### Rate Limiting

Emission **SHALL** respect rate limits to avoid overwhelming downstream systems:

- Default: 10 signals per second (configurable via `--a2a-rate-limit`)
- Exponential backoff on 429 (Too Many Requests) responses
- Maximum retry attempts: 3 (configurable)

### Error Handling

On emission failure:

1. Log error with full signal context
2. Record failure in replay artifact (separate from success log)
3. Continue with next signal (do not halt replay)
4. Emit replay completion summary with success/failure counts

---

## Replay Artifacts

Automated A2A emission **SHALL** produce the following artifacts:

1. **Emission Log**: JSONL file with one entry per emission attempt
   - Signal ID, timestamp, HTTP status, response body
   - Success/failure flag, error details (if any)

2. **Replay Summary**: JSON file with aggregate statistics
   - Total signals processed
   - Successfully emitted count
   - Failed emissions count
   - Emission duration
   - Average emission rate

3. **Validation Failures**: JSONL file of signals rejected pre-emission
   - Signal data (sanitized)
   - Validation error details

---

## Reference Invocation

### Basic Usage
```bash
TEST_MODE=true python replay.py \
  --source history/2019_emails.json \
  --emit-a2a \
  --a2a-endpoint http://localhost:8000/api/a2a/ingest
```

### With Rate Limiting
```bash
TEST_MODE=true python replay.py \
  --source history/2019_emails.json \
  --emit-a2a \
  --a2a-endpoint http://localhost:8000/api/a2a/ingest \
  --a2a-rate-limit 5
```

### Without Emission (Local Analysis Only)
```bash
TEST_MODE=true python replay.py \
  --source history/2019_emails.json
```

---

## Downstream Consumer Requirements (FuggerBot)

When receiving historically replayed A2A signals, FuggerBot **SHALL**:

1. Process signals with `test_mode=True`
2. Apply regime context based on historical timestamps
3. Emit A2A feedback as normal (advisory, non-binding)
4. Log interpretations for human review
5. **NOT** mutate memory or adaptive parameters

---

## Success Criteria

Automated A2A emission is successful when:

- All valid signals are emitted in chronological order
- All emissions respect rate limits and error handling
- Complete emission logs and summaries are produced
- Downstream consumers process signals without errors
- No system state mutation occurs
- All artifacts are preserved for audit

---

## Prohibited Behaviors

During automated A2A emission, the following are explicitly forbidden:

- Emitting signals outside Historical Replay context
- Emitting invalid or partial signals
- Modifying signal data during emission
- Bypassing validation or rate limiting
- Mutating downstream system state
- Learning from emission results
- Influencing live system behavior

---

## Authority Boundary

- **ai_inbox_digest**: Emits validated historical signals via A2A contract
- **FuggerBot**: Processes signals in test mode, emits feedback
- **Humans**: Review emission logs and downstream interpretations

No agent may modify system behavior or make capital decisions based on emission results.

---

## Related Documentation

- [Historical Replay Testing Prompt](./TESTING_HISTORICAL_REPLAY.md) - Base scenario A specification
- [Testing & Evaluation Initiation Prompts](./TESTING_EVALUATION_INITIATION.md) - General testing framework
- [Testing & Evaluation Guide](./TESTING_EVALUATION.md) - Detailed procedures
- [Agents.md](../Agents.md) - Core system specification

---

**End of Scenario A Extension: Automated A2A Emission**

