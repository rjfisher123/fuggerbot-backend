# Research Reports System

## Overview

The Research Reports system provides deterministic, append-only research artifacts that document strategy performance, insights, and recommendations. Reports are read-only and cannot influence simulation, scoring, or execution.

---

## CLI Usage

### Generate Report

```bash
# Basic usage
python -m agents.research.report --output reports/my_report.md

# With specific run ID
python -m agents.research.report \
  --output reports/FRR-2025-01-15.md \
  --run-id latest \
  --strategy-version 1.0.0 \
  --simulator-hash $(git rev-parse HEAD)

# Save JSON for diffing
python -m agents.research.report \
  --output reports/report.md \
  --json-output reports/json/report.json
```

### Output Structure

Reports are saved with append-only semantics:

```
reports/
  ├── my_report.md          # Markdown report (canonical)
  ├── my_report.meta.json  # Metadata (append-only)
  └── my_report.json       # JSON format (optional, for diffing)
```

**meta.json** contains:
```json
{
  "report_id": "my_report",
  "generated_at": "2025-01-15T10:30:00",
  "strategy_version": "1.0.0",
  "research_loop_version": "2.0",
  "data_fingerprint": "abc123...",
  "scenario_count": 36,
  "insight_count": 5,
  "simulator_commit_hash": "abc123..."
}
```

---

## Web UI

### Access Reports

Navigate to: `http://localhost:3000/reports`

**Features:**
- List all available reports (sorted by date)
- View report metadata (scenarios, insights, fingerprint)
- Display full report content (Markdown)
- Search reports semantically (if vector logging enabled)

### Report Detail View

- **Executive Summary**: High-level findings
- **Performance Overview**: Metrics, top/bottom scenarios, per-symbol/per-regime stats
- **Confirmed Insights**: Evidence-qualified insights
- **Preliminary Insights**: Insufficient evidence insights
- **Failure Boundaries**: Performance cliffs detected
- **Regime Coverage**: Coverage analysis
- **Recommended Experiments**: Top 3 proposals
- **Historical Context**: Historonics hypotheses (if present)

---

## API Endpoints

### List Reports

```http
GET /api/reports/
```

**Response:**
```json
[
  {
    "report_id": "final_hardened",
    "generated_at": "2025-01-15T10:30:00",
    "strategy_version": "1.0.0",
    "scenario_count": 36,
    "insight_count": 5,
    "data_fingerprint": "abc123...",
    "markdown_path": "reports/final_hardened.md"
  }
]
```

### Get Report

```http
GET /api/reports/{report_id}?format=markdown
GET /api/reports/{report_id}?format=html
GET /api/reports/{report_id}?format=json
GET /api/reports/{report_id}?format=meta
```

**Formats:**
- `markdown`: Raw Markdown (default)
- `html`: Rendered HTML
- `json`: Full report JSON
- `meta`: Metadata only

### Semantic Search

```http
GET /api/reports/search?query=drawdown+failures&limit=10&section=confirmed_insights
```

**Response:**
```json
{
  "query": "drawdown failures",
  "results": [
    {
      "id": "report_id_confirmed_insights",
      "content": "Section content...",
      "metadata": {
        "report_id": "report_id",
        "section": "confirmed_insights",
        "generated_at": "2025-01-15T10:30:00"
      },
      "distance": 0.23
    }
  ],
  "count": 1
}
```

---

## Vector Logging (Optional)

### Purpose

Enable semantic search over historical research outputs:
- "Show reports mentioning drawdown failures"
- "When did trust thresholds first appear as a risk?"
- "Find all reports with regime transition hypotheses"

### Setup

Install ChromaDB (optional dependency):
```bash
pip install chromadb
```

### Automatic Indexing

Reports are automatically indexed when generated via CLI (if ChromaDB is available).

**Indexed Sections:**
- Executive Summary
- Confirmed Insights
- Preliminary Insights
- Failure Boundaries
- Historical Context (if present)
- Recommended Experiments

**Metadata per Chunk:**
- `report_id`: Report identifier
- `section`: Section name
- `generated_at`: ISO timestamp
- `strategy_version`: Strategy version
- `data_fingerprint`: Data hash
- `deterministic`: Always `true`

### Storage

Vector database location: `data/vector_db/`

**Properties:**
- Append-only (no overwrites)
- Immutable embeddings
- Isolated from simulator/proposal logic

---

## Guardrails

### ❌ Reports Cannot:

- Influence proposal ranking
- Modify memory or confidence scores
- Feed back into execution
- Overwrite existing reports (append-only)

### ✅ Reports May:

- Be searched semantically
- Be compared and diffed
- Be read by humans
- Inform future research (advisory only)

---

## Report Structure

1. **Metadata**: Report ID, versions, fingerprint
2. **Executive Summary**: High-level findings
3. **Performance Overview**:
   - Overall statistics
   - Top 5 / Bottom 5 scenarios
   - Per-symbol summary
   - Per-regime summary (top 10)
4. **Confirmed Insights**: Evidence-qualified insights
5. **Preliminary Insights**: Insufficient evidence
6. **Known Unknowns**: Weak insights and gaps
7. **Failure Boundaries**: Performance cliffs
8. **Regime Coverage**: Coverage analysis
9. **Recommended Experiments**: Top 3 proposals
10. **Historical Context**: Historonics hypotheses (if present)
11. **Appendices**: Scenario IDs, sensitivity analysis, metric definitions

---

## Determinism & Reproducibility

**Guarantees:**
- Same inputs → byte-identical reports
- Data fingerprint for validation
- Simulator commit hash for reproducibility
- Append-only storage (no overwrites)

**Validation:**
```bash
# Generate report twice, compare
python -m agents.research.report --output reports/test1.md
python -m agents.research.report --output reports/test2.md

# Should be identical (if same data)
diff reports/test1.md reports/test2.md
```

---

## Examples

### Generate and View Report

```bash
# 1. Generate report
python -m agents.research.report \
  --output reports/FRR-2025-01-15.md \
  --strategy-version 1.0.0 \
  --simulator-hash $(git rev-parse HEAD)

# 2. View in web UI
# Navigate to: http://localhost:3000/reports

# 3. Or via API
curl http://localhost:8000/api/reports/FRR-2025-01-15?format=markdown
```

### Semantic Search

```bash
# Search for reports mentioning drawdown
curl "http://localhost:8000/api/reports/search?query=drawdown+failures&limit=5"

# Search in specific section
curl "http://localhost:8000/api/reports/search?query=trust+thresholds&section=confirmed_insights"
```

---

## Integration with Research Loop

Reports are generated independently of the research loop:

1. **Research Loop** runs simulations and accumulates insights
2. **Report Generator** reads loop outputs and generates reports
3. **Vector Logger** indexes reports for semantic search (optional)

**No feedback loop**: Reports cannot influence the research loop.

---

## Troubleshooting

### No Reports Found

**Check:**
1. Reports directory exists: `reports/`
2. Reports have been generated: `ls reports/*.md`
3. Meta files exist: `ls reports/*.meta.json`

**Generate a report:**
```bash
python -m agents.research.report --output reports/test.md
```

### Vector Search Not Working

**Check:**
1. ChromaDB installed: `pip install chromadb`
2. Vector DB directory exists: `data/vector_db/`
3. Reports have been indexed (check logs)

**Re-index:**
Reports are automatically indexed on generation. If needed, delete `data/vector_db/` and regenerate reports.

### API Errors

**Check:**
1. FastAPI server running: `uvicorn main:app --reload`
2. Reports directory accessible
3. CORS configured (if accessing from frontend)

---

## Files

- **CLI**: `agents/research/report/__main__.py`
- **API**: `api/reports.py`
- **Web UI**: `frontend/app/reports/page.tsx`
- **Vector Logger**: `agents/research/report/vector_logger.py`
- **Documentation**: `docs/reports.md`

---

**Last Updated**: December 2024  
**Version**: v1.0  
**Status**: Production Ready

