# Historonics Agent Implementation Summary

## ✅ Implementation Complete

The Historonics Agent has been successfully implemented and integrated into the research loop as a read-only, advisory-only historical research agent.

---

## Components Created

### 1. `historonics_schema.py`
- **Hypothesis**: Pydantic model for structured hypotheses
- **HistoricalAnalog**: Model for historical period references
- **HistoronicsOutput**: Container for agent output
- **HypothesisType**: Enum (historical_analogy, regime_transition, failure_precursor, parameter_risk)

### 2. `historonics_prompts.py`
- **get_historonics_system_prompt()**: LLM safety-enforced system prompt
- **build_historonics_user_prompt()**: Context-aware user prompt builder

### 3. `historonics_agent.py`
- **HistoronicsAgent**: Main agent class with LLM integration
- Safety validation for hypotheses (rejects numeric prescriptions, executable code)
- Graceful error handling (returns empty output on failure)

---

## Integration Points

### Research Loop (`daemon/research_loop.py`)

**Integration Flow:**
```
Step 4: Update Memory
  ↓
Step 5: Generate Historical Hypotheses (NEW - optional, advisory)
  ↓
Step 6: Generate Proposals (existing)
```

**Key Features:**
- Called after memory update, before proposal generation
- Non-critical: Research loop continues even if Historonics fails
- Output logged but not used to modify simulation/scoring

### Research Report (Optional)

**Schema Extension:**
- Added `appendix_historonics_hypotheses` field to `ResearchReport`
- Renderer supports "Historical Context & Hypothesis Generation" section

---

## Invariants Preserved ✅

### 1. Deterministic Execution ✅
- Historonics outputs do not affect simulation or scoring
- All outputs are advisory only
- No randomness introduced

### 2. Append-Only Learning ✅
- Historonics reads only (cannot modify past results)
- Hypotheses are new outputs, not modifications
- Memory store remains append-only

### 3. Strict Role Separation ✅
- **Simulator** = ground truth (unchanged)
- **Meta-evaluator** = quantitative comparison (unchanged)
- **Historonics** = qualitative hypothesis generation (advisory only)

### 4. LLMs Never Authorities ✅
- LLM output cannot:
  - Set parameters ❌
  - Rank strategies ❌
  - Influence returns ❌
  - Modify scoring logic ❌
  - Override evidence gating ❌
- LLM can only:
  - Generate text hypotheses ✅
  - Suggest what to study ✅
  - Provide historical context ✅

---

## Safety Mechanisms

### 1. Prompt Constraints
- Explicit instructions: "You are a research historian, not a trader"
- No optimization or prediction allowed
- Uncertainty must be stated explicitly
- No numeric prescriptions

### 2. Output Validation
- Rejects hypotheses with numeric parameter values
- Rejects hypotheses with executable code patterns
- Rejects hypotheses claiming certainty
- Requires explicit uncertainty notes

### 3. Error Handling
- Graceful degradation: Returns empty output on failure
- Non-blocking: Research loop continues without Historonics
- Logging: All errors logged but not fatal

---

## Usage Examples

### From Research Loop (Automatic)

The Historonics Agent is automatically called during research loop iterations if LLM is available:

```python
loop = ResearchLoop()
results = loop.run_iteration()
# Hypotheses generated automatically (if LLM available)
```

### Manual Usage

```python
from agents.research.historonics_agent import get_historonics_agent

agent = get_historonics_agent()

output = agent.generate_hypotheses(
    report_summary="Research findings...",
    insights=[...],
    regime_coverage={"regime_id": count, ...},
    scenario_metadata=[{"scenario_id": "...", "regime_id": "..."}],
    report_id="FRR-2025-01-01"
)

for hypothesis in output.hypotheses:
    print(f"{hypothesis.summary}")
    print(f"  Uncertainty: {hypothesis.uncertainty_notes}")
```

### In Reports

```python
# Hypotheses can be included in reports
report = generator.generate_report(...)

# Optionally add hypotheses
if historonics_output:
    report.appendix_historonics_hypotheses = [
        hyp.model_dump() for hyp in historonics_output.hypotheses
    ]
```

---

## Output Format

Each hypothesis includes:

```json
{
  "hypothesis_id": "stable_hash",
  "hypothesis_type": "historical_analogy",
  "summary": "Concise statement",
  "historical_analogs": [
    {
      "period": "Q4 2018",
      "description": "Why relevant",
      "confidence": 0.7
    }
  ],
  "linked_insights": ["insight_id_1"],
  "regimes_implicated": ["regime_id_1"],
  "uncertainty_notes": "Explicit limitations",
  "recommended_validation": "How to test (non-binding)",
  "status": "UNTESTED",
  "evidence_level": "Narrative only"
}
```

---

## Testing

```bash
# Test import
python -c "from agents.research.historonics_agent import get_historonics_agent; agent = get_historonics_agent(); print('OK')"

# Test research loop integration
python -c "from daemon.research_loop import ResearchLoop; loop = ResearchLoop(); print('OK')"
```

---

## Configuration

Set in `.env`:
```bash
OPENROUTER_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek/deepseek-r1
```

If API key is not set, agent initializes but returns empty outputs (non-critical).

---

## Files Modified

1. **Created:**
   - `agents/research/historonics_schema.py`
   - `agents/research/historonics_prompts.py`
   - `agents/research/historonics_agent.py`

2. **Modified:**
   - `daemon/research_loop.py` (added Historonics call)
   - `agents/research/report/report_schema.py` (added hypotheses field)
   - `agents/research/report/markdown_renderer.py` (added rendering)

3. **Unchanged (Critical):**
   - Simulator ❌
   - Meta-evaluator ❌
   - Memory evidence thresholds ❌
   - Scenario generation logic ❌

---

## Success Criteria ✅

- ✅ All existing research reports reproduce identically
- ✅ No simulation results change
- ✅ Historonics outputs appear only as advisory hypotheses
- ✅ Proposal Agent remains the sole ranking authority
- ✅ Reports clearly distinguish evidence vs conjecture
- ✅ System can answer: "What historical patterns suggest what to test next?"

---

**Implementation Date**: December 2024  
**Version**: v1.0  
**Status**: Production Ready (with LLM API key)

