# FuggerBot Research Report Guide

## Quick Start

### Generate a Report

```bash
# Basic usage - generates report from current Research Loop data
python -m agents.research.report --output reports/FRR-2025-02-14.md

# With JSON output (needed for diffing later)
python -m agents.research.report \
  --output reports/FRR-2025-02-14.md \
  --json-output reports/json/FRR-2025-02-14.json \
  --report-id FRR-2025-02-14 \
  --strategy-version 1.0.0 \
  --simulator-hash abc123def456
```

### Compare Two Reports (Diff)

```bash
# Compare two reports
python -m agents.diff \
  --base reports/json/FRR-2025-02-01.json \
  --compare reports/json/FRR-2025-02-14.json \
  --output reports/diff-0201-0214.md
```

---

## Detailed Usage

### Report Generation

**Command:**
```bash
python -m agents.research.report [OPTIONS]
```

**Required Arguments:**
- `--output`: Path where the Markdown report will be saved

**Optional Arguments:**
- `--report-id`: Unique report identifier (default: derived from output filename)
- `--strategy-version`: Strategy version identifier (default: "1.0.0")
- `--simulator-hash`: Simulator commit hash for reproducibility (default: "unknown")
- `--json-output`: Path to save report JSON (recommended for diffing)

**What it does:**
1. Loads all scenario results from `data/research_results/`
2. Loads insights from memory agent
3. Computes sensitivity analysis and failure boundaries
4. Generates a structured Markdown report with:
   - Metadata (report ID, versions, data fingerprint)
   - Executive Summary
   - Performance Overview
   - Confirmed Insights (sorted by confidence)
   - Known Unknowns
   - Failure Boundaries
   - Regime Coverage
   - Recommended Experiments
   - Appendices

**Example:**
```bash
python -m agents.research.report \
  --output reports/FRR-2025-02-14.md \
  --json-output reports/json/FRR-2025-02-14.json \
  --report-id FRR-2025-02-14 \
  --strategy-version 2.0.0 \
  --simulator-hash $(git rev-parse HEAD)
```

---

### Report Diffing

**Command:**
```bash
python -m agents.diff [OPTIONS]
```

**Required Arguments:**
- `--base`: Path to base report (JSON format required)
- `--compare`: Path to compare report (JSON format required)
- `--output`: Path where diff Markdown will be saved

**Optional Arguments:**
- `--base-json`: Explicit path to base report JSON (if Markdown provided)
- `--compare-json`: Explicit path to compare report JSON (if Markdown provided)

**What it does:**
1. Loads both reports from JSON files
2. Computes semantic differences:
   - New/removed insights
   - Confidence changes
   - Regime coverage changes
   - Failure boundary changes
   - Proposal ranking changes
3. Generates a structured Markdown diff

**Example:**
```bash
python -m agents.diff \
  --base reports/json/FRR-2025-02-01.json \
  --compare reports/json/FRR-2025-02-14.json \
  --output reports/diff-0201-0214.md
```

**Note:** The diff engine requires JSON files. If you have Markdown reports, ensure you also saved the JSON version when generating the report (using `--json-output`).

---

## Report Structure

The generated Markdown report contains:

1. **Metadata**: Report ID, versions, data fingerprint
2. **Executive Summary**: High-level findings
3. **Performance Overview**: Aggregate metrics (returns, Sharpe, drawdown, win rate)
4. **Confirmed Insights**: 
   - Strong (confidence ≥ 0.7)
   - Moderate (0.5 ≤ confidence < 0.7)
   - Weak (confidence < 0.5)
5. **Known Unknowns**: Weak insights and coverage gaps
6. **Failure Boundaries**: Performance cliffs and failure thresholds
7. **Regime Coverage**: Coverage table across all regime combinations
8. **Recommended Experiments**: Top experiments ranked by information gain
9. **Appendices**: Scenario IDs and sensitivity analysis summary

---

## Diff Structure

The generated diff contains:

1. **Summary**: Total counts of changes
2. **New Insights**: Insights added since base report
3. **Removed Insights**: Insights removed since base report
4. **Confidence Changes**: Insights with significant confidence changes (≥0.05)
5. **Regime Coverage Changes**: Regimes with coverage changes (≥1.0%)
6. **New/Removed Failure Boundaries**: Boundary detection changes
7. **Proposal Ranking Changes**: Changes in experiment recommendations

---

## Best Practices

1. **Always save JSON**: Use `--json-output` when generating reports to enable diffing later
2. **Use descriptive report IDs**: Use dates or version numbers (e.g., `FRR-2025-02-14`)
3. **Include simulator hash**: Capture the exact simulator version for reproducibility
4. **Regular reporting**: Generate reports after significant research loop iterations
5. **Version reports**: Keep reports in a `reports/` directory with clear naming

---

## File Organization

Recommended structure:

```
fuggerbot/
├── data/
│   ├── research_results/          # Scenario results (input)
│   └── strategy_memory.json       # Memory insights (input)
├── reports/
│   ├── FRR-2025-02-01.md          # Markdown report
│   ├── FRR-2025-02-14.md
│   ├── diff-0201-0214.md          # Diff between reports
│   └── json/                       # JSON versions (for diffing)
│       ├── FRR-2025-02-01.json
│       └── FRR-2025-02-14.json
```

---

## Troubleshooting

**Error: "No scenario results found"**
- Ensure you've run the Research Loop and have results in `data/research_results/`
- Check that scenario result JSON files exist

**Error: "No JSON file found for diff"**
- Ensure you saved JSON when generating reports (`--json-output`)
- Or provide explicit JSON paths with `--base-json` and `--compare-json`

**Report seems incomplete**
- Check that memory agent has insights loaded
- Verify scenario results contain the expected data structure

---

## Determinism Guarantee

Reports are **deterministic**: the same inputs will always produce the same output. This is enforced by:
- Stable sorting (by IDs, confidence, etc.)
- Deterministic data fingerprinting
- No randomness in report generation
- Replayable diff computation

To verify determinism, generate the same report twice and compare:
```bash
python -m agents.research.report --output report1.md --json-output report1.json
python -m agents.research.report --output report2.md --json-output report2.json
diff report1.md report2.md  # Should be identical
diff report1.json report2.json  # Should be identical
```

