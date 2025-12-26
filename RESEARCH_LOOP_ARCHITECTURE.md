# FuggerBot Research Loop Architecture

## Overview

The Research Loop transforms FuggerBot's War Games from a purely deterministic backtest into a learning-capable research engine while **preserving determinism**.

## Core Principle

> **Deterministic simulation is the ground truth. Learning happens by comparing many deterministic truths.**

No randomness in execution paths. All variation is explicit, parameterized, and logged.

---

## Agent Architecture

### 1. Scenario Generator Agent
**Location:** `agents/research/scenario_generator.py`

**Purpose:** Generate new parameter sets and scenario definitions with versioning.

**Key Features:**
- Generates baseline scenarios (36-campaign suite)
- Creates variant scenarios through parameter sweeps
- Regime-focused scenario generation
- Insight-driven variant generation (when insights available)
- All scenarios have deterministic `scenario_id` hash

**Example:**
```python
from agents.research.scenario_generator import get_scenario_generator

generator = get_scenario_generator()
baseline = generator.generate_baseline_scenario()
variants = generator.generate_scenario_variants(baseline, insight_hints={...})
```

---

### 2. Deterministic Simulator Agent
**Location:** `daemon/simulator/war_games_runner.py` (existing)

**Purpose:** Execute scenarios deterministically. Unchanged from original.

**Invariant:** `hash(inputs) → identical outputs`

---

### 3. Meta-Evaluator Agent
**Location:** `agents/research/meta_evaluator.py`

**Purpose:** Compare outcomes across Scenario_IDs and identify patterns.

**Key Features:**
- Scenario-to-scenario comparison with delta metrics
- Parameter sensitivity analysis
- Failure mode identification
- Regime-dependent performance analysis
- Generates human-readable insights

**Example Output:**
- "Scenario B performs 2.3% better on average return"
- "Trust threshold >0.65 improves drawdown at cost of convexity"
- "Strategy collapses under gap risk in volatile regimes"

---

### 4. Memory & Insight Agent
**Location:** `agents/research/memory_agent.py`

**Purpose:** Accumulate learning over time in an append-only store.

**Key Features:**
- Persists winning parameter archetypes
- Tracks failure modes
- Stores regime-specific heuristics
- Append-only strategy memory (never modifies past execution)
- Memory informs future scenario generation

**Storage:** `data/strategy_memory.json`

---

### 5. Proposal Agent
**Location:** `agents/research/proposal_agent.py`

**Purpose:** Suggest what to test next based on accumulated learning.

**Key Features:**
- Proposes parameter sweeps
- Suggests regime-focused stress tests
- Generates hypothesis-driven experiments
- Ranks proposals by expected information gain
- Prioritizes high-value experiments

---

## Execution Loop (Canonical)

```
[Scenario Generator]
        ↓
[Deterministic Simulator]
        ↓
[Meta-Evaluator]
        ↓
[Memory & Insight Store]
        ↓
[Proposal Agent]
        ↺
```

Each iteration increases knowledge, not randomness.

---

## Usage

### Basic Usage

```python
from daemon.research_loop import get_research_loop

# Initialize research loop
loop = get_research_loop()

# Run one iteration
results = loop.run_iteration()

# Get accumulated insights
insights = loop.get_current_insights()
print(f"Total insights: {insights['total_insights']}")
print(f"Winning patterns: {insights['winning_patterns']}")
print(f"Failure modes: {insights['failure_modes']}")
```

### Running Multiple Iterations

```python
loop = get_research_loop()

for i in range(5):
    print(f"\n=== Iteration {i+1} ===")
    results = loop.run_iteration()
    
    if results["success"]:
        print(f"Scenarios run: {len(results['scenarios_run'])}")
        print(f"Insights: {sum(len(i) for i in results['insights_generated'])}")
        print(f"Proposals: {len(results['proposals_created'])}")
    else:
        print(f"Error: {results.get('error')}")
```

### Custom Scenario

```python
from agents.research.scenario_generator import ScenarioDefinition

# Create custom scenario
scenario = ScenarioDefinition(
    scenario_name="Custom Test",
    start_date="2022-01-01",
    end_date="2022-12-31",
    description="High volatility regime test",
    symbols=["BTC-USD", "ETH-USD"],
    param_sets={...}
)

# Run iteration with custom scenario
loop = get_research_loop()
results = loop.run_iteration(scenario=scenario)
```

---

## What This Fixes

### ❌ Before (Problems)
- "Average return doesn't change" confusion
- False belief that learning requires stochasticity
- Overfitting masked by randomness
- No systematic exploration

### ✅ After (Solutions)
- Deterministic truth preserved
- Comparative learning across scenarios
- Regime awareness built-in
- Research velocity increased
- Systematic parameter space exploration

---

## Guardrails

1. **No RNG in execution paths** - All randomness is explicit and logged
2. **All variation must be versioned** - Every scenario has a scenario_id
3. **Every run must be replayable** - Deterministic execution
4. **Learning ≠ optimization** - Insights inform future tests, not past execution
5. **Optimization only after insight stabilization** - Don't optimize prematurely

---

## End Goal

Transform FuggerBot from:

> "A backtest that gives the same answer"

into:

> "A system that understands why that answer holds — and when it breaks."

---

## Success Metric

When FuggerBot can answer, unprompted:

> "This strategy earns 0.2% on average — but only because it survives three regimes and dies in one."

At that point, FuggerBot is no longer a simulator.

**It is a research engine.**

---

## Integration Points

### Current System Integration

The Research Loop is designed to work alongside the existing War Games system:

1. **Existing War Games Runner** - Unchanged, used as deterministic simulator
2. **Existing API Endpoints** - Can be extended to support research loop
3. **Existing Frontend** - Can display research insights alongside simulation results

### Future Integration

1. Add research loop API endpoints (`/api/research/run`, `/api/research/insights`)
2. Add research dashboard to frontend
3. Integrate research loop into scheduled jobs
4. Add research loop to War Games UI

---

## File Structure

```
agents/research/
├── __init__.py              # Exports
├── scenario_generator.py    # Scenario generation
├── meta_evaluator.py        # Scenario comparison
├── memory_agent.py          # Insight storage
└── proposal_agent.py        # Next experiment proposals

daemon/
├── research_loop.py         # Main orchestrator
└── simulator/
    └── war_games_runner.py  # Deterministic simulator (existing)

data/
├── strategy_memory.json     # Append-only insight store
└── research_results/        # Scenario result files
    ├── scenario_abc123.json
    ├── scenario_def456.json
    └── ...
```

---

## Next Steps

1. ✅ Core agents implemented
2. ⏳ Integrate with existing War Games API
3. ⏳ Add research loop UI to frontend
4. ⏳ Add proposal-to-scenario conversion logic
5. ⏳ Enhance insight extraction algorithms
6. ⏳ Add research loop scheduling

---

**Status:** Core architecture complete. Ready for integration and testing.

