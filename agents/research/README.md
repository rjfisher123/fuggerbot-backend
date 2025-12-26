# FuggerBot Research Loop System

## Overview

The Research Loop transforms FuggerBot from a deterministic backtesting engine into a cumulative research system that explains why results occur, when strategies break, and what to test next — **without introducing randomness or retroactive modification of results**.

**Core Principle**: All execution remains fully deterministic and reproducible. Learning occurs through comparison, aggregation, and memory — never through stochastic processes.

---

## Architecture

### Component Flow

```
[Scenario Generator] → [Deterministic Simulator] → [Meta-Evaluator] → 
[Memory & Insight Store] → [Proposal Agent] → (loop)
```

Each iteration increases **knowledge**, not randomness.

---

## Components

### 1. Explicit Regime Ontology (`regime_ontology.py`)

Provides a **fixed, explicit taxonomy** for market regimes.

**Regime Dimensions:**
- **Volatility**: `low` / `medium` / `high`
- **Trend**: `up` / `sideways` / `down`
- **Liquidity**: `normal` / `stressed`
- **Macro**: `easing` / `tightening` / `neutral`

**Key Features:**
- Regimes are **labels**, not inferred during execution
- Each scenario is tagged with regime metadata
- Classification is **deterministic and documented**
- Supports coverage analysis (identify unexplored regimes)

**Usage:**
```python
from agents.research.regime_ontology import get_regime_ontology

ontology = get_regime_ontology()
regime = ontology.classify_scenario("Bull Run 2021", "2021-01-01", "2021-12-31")
# Returns: RegimeClassification with explicit labels
```

---

### 2. Scenario Generator (`scenario_generator.py`)

Generates parameterized scenario definitions with **deterministic IDs**.

**Features:**
- All scenarios have stable, hash-based IDs
- Scenarios include regime classification metadata
- Supports baseline, regime-focused, and parameter sweep variants
- **No randomness** — all variations are explicit

**Enhanced in v2.0:**
- Scenarios now include `regime_classification` field
- Regime classification is included in scenario ID hash (ensures determinism)

---

### 3. Meta-Evaluator (`meta_evaluator.py`)

Compares scenario outcomes and identifies patterns.

**Core Methods:**
- `compare_scenarios()`: Compare two scenario results
- `evaluate_parameter_sensitivity()`: Measure parameter impact on outcomes
- `identify_failure_modes()`: Find scenarios with large losses

**Enhanced in v2.0:**
- `detect_failure_boundaries()`: Identify performance cliffs and failure thresholds
- `analyze_sensitivity_landscape()`: Comprehensive sensitivity analysis with regime patterns

**Example:**
```python
# Detect where strategy breaks
boundary = meta_evaluator.detect_failure_boundaries(results, "trust_threshold")
# Returns: Dict with performance cliffs and failure thresholds

# Analyze sensitivity
sensitivity = meta_evaluator.analyze_sensitivity_landscape(results)
# Returns: High-sensitivity params, regime failure patterns, sensitivity summary
```

---

### 4. Memory Agent (`memory_agent.py`)

Manages strategy memory and insights with **confidence scoring**.

**Core Data Structures:**
- `StrategyInsight`: Learned insight about strategy performance
- `InsightConfidence`: Detailed confidence metadata

**Confidence Components:**
- Number of supporting scenarios
- Regime coverage (list of regime IDs where insight holds)
- Parameter robustness (does it hold under small perturbations?)
- Contradiction tracking (has any scenario contradicted this?)

**Confidence Calculation:**
```python
confidence = base_confidence + regime_bonus + robustness_bonus - contradiction_penalty
```

**Enhanced in v2.0:**
- `InsightConfidence` model with detailed metadata
- `update_insight_confidence()`: Update confidence based on new evidence
- Weak insight flagging (`is_weak` when confidence < 0.5)

**Usage:**
```python
# Add insight with confidence metadata
insight = memory_agent.add_insight(
    insight_type="winning_pattern",
    description="High trust threshold works in volatile regimes",
    scenario_ids=["scenario_1", "scenario_2"],
    regimes=["high_vol_up_normal_easing"],
    evidence_metrics={"avg_return": 0.15},
    confidence=None  # Will be computed from metadata
)

# Update confidence when new evidence arrives
memory_agent.update_insight_confidence(
    insight_id=insight.insight_id,
    scenario_id="scenario_3",
    regime_id="high_vol_down_stressed_tightening",
    contradicts=False,
    parameter_robustness=0.8
)
```

---

### 5. Proposal Agent (`proposal_agent.py`)

Suggests future experiments **ranked by information gain** (not returns).

**Proposal Strategies:**
1. **Parameter Gaps**: Unexplored parameter combinations
2. **Regime Tests**: Coverage gaps and failure mode analysis
3. **Hypothesis Tests**: Verify/falsify existing insights
4. **Uncertainty Reduction**: Strengthen weak insights

**Ranking Criteria:**
- Expected reduction in uncertainty
- Coverage of under-explored regimes
- Ability to confirm or falsify existing insights
- **NOT optimization for returns**

**Enhanced in v2.0:**
- `_rank_by_information_gain()`: Rank proposals by learning value
- `_propose_uncertainty_reduction()`: Target weak insights for strengthening
- Regime coverage integration (identify unexplored regimes)

**Usage:**
```python
proposals = proposal_agent.generate_proposals(
    existing_scenarios=["scenario_1", "scenario_2"],
    memory_insights=insights,
    existing_regime_coverage={"regime_1": 3, "regime_2": 0},  # regime_2 unexplored
    limit=5
)
# Returns: Proposals sorted by expected_info_gain (descending)
```

---

### 6. Research Loop Orchestrator (`daemon/research_loop.py`)

Coordinates the complete research cycle.

**Execution Flow:**
1. Generate or select scenario (with regime classification)
2. Run deterministic simulation
3. Meta-evaluate (compare with previous scenarios)
4. Analyze sensitivity and failure boundaries
5. Update memory with insights
6. Generate proposals for next iteration

**Enhanced in v2.0:**
- Regime coverage calculation
- Sensitivity analysis integration
- Failure boundary detection
- Regime classification preserved in results

---

## Design Principles

### Non-Negotiable Invariants

1. **Deterministic Execution**
   - All simulations remain fully deterministic
   - Identical inputs MUST produce identical outputs
   - No stochasticity, RNG, or sampling in execution paths

2. **Explicit Variation Only**
   - All variation must be parameterized and versioned
   - No hidden randomness, heuristics, or adaptive execution logic

3. **Append-Only Learning**
   - Past execution results are immutable
   - Learning occurs only via comparison, aggregation, and memory
   - Memory may influence future experiment generation only

4. **Replayability**
   - Every scenario must be re-runnable via a deterministic ID
   - Scenario IDs must be stable (hash-based)

### Prohibited Actions

The system must **NOT**:
- Introduce stochastic simulations
- Modify past results
- Auto-tune strategy parameters
- Optimize for PnL directly
- Replace human judgment with opaque heuristics

---

## Usage Examples

### Running a Research Loop Iteration

```python
from daemon.research_loop import get_research_loop

loop = get_research_loop()

# Run one iteration (will generate proposals based on memory)
results = loop.run_iteration(max_proposals=5)

# Or run with a specific scenario
from agents.research.scenario_generator import get_scenario_generator
generator = get_scenario_generator()
scenario = generator.generate_baseline_scenario()
results = loop.run_iteration(scenario=scenario)
```

### Analyzing Sensitivity

```python
from agents.research.meta_evaluator import get_meta_evaluator

evaluator = get_meta_evaluator()

# Load all scenario results
all_results = [...]  # List of scenario result dicts

# Analyze sensitivity landscape
sensitivity = evaluator.analyze_sensitivity_landscape(all_results)

# Check high-sensitivity parameters
for param, metrics in sensitivity["high_sensitivity_params"].items():
    print(f"{param}: range={metrics['range']:.2f}%, std={metrics['std']:.2f}")
    
# Check failure boundaries
for param, metrics in sensitivity["high_sensitivity_params"].items():
    boundary = metrics["boundary_analysis"]
    if boundary["boundary_detected"]:
        print(f"Failure boundary detected for {param}")
        print(f"  Performance cliffs: {boundary['performance_cliffs']}")
        print(f"  Failure thresholds: {boundary['failure_thresholds']}")
```

### Checking Regime Coverage

```python
from agents.research.regime_ontology import get_regime_ontology

ontology = get_regime_ontology()

# Get all possible regime combinations
all_regimes = ontology.get_all_regime_combinations()
print(f"Total regime combinations: {len(all_regimes)}")

# Check coverage from scenario results
coverage = ontology.get_regime_coverage(scenario_results)
print(f"Covered regimes: {len(coverage)}")
print(f"Unexplored regimes: {len(all_regimes) - len(coverage)}")
```

---

## Data Flow

### Scenario Results Structure

```json
{
  "scenario_id": "abc123...",
  "scenario_name": "Baseline Suite - Bull Run 2021",
  "scenario_description": "Strong upward trend, low volatility",
  "regime_classification": {
    "volatility": "low",
    "trend": "up",
    "liquidity": "normal",
    "macro": "easing"
  },
  "results": [
    {
      "symbol": "BTC-USD",
      "total_return_pct": 0.15,
      "sharpe_ratio": 1.2,
      "max_drawdown_pct": -0.05,
      "win_rate": 0.65,
      "params": {
        "trust_threshold": 0.65,
        "min_confidence": 0.75
      }
    }
  ]
}
```

### Strategy Memory Structure

```json
{
  "winning_archetypes": [
    {
      "insight_id": "winning_pattern_123",
      "insight_type": "winning_pattern",
      "description": "High trust threshold works in volatile regimes",
      "scenario_ids": ["scenario_1", "scenario_2"],
      "regimes": ["high_vol_up_normal_easing"],
      "confidence": 0.75,
      "confidence_metadata": {
        "num_supporting_scenarios": 2,
        "regime_coverage": ["high_vol_up_normal_easing"],
        "parameter_robustness": 0.7,
        "has_been_contradicted": false,
        "contradiction_count": 0
      },
      "is_weak": false
    }
  ],
  "failure_modes": [...],
  "regime_heuristics": [...]
}
```

---

## Upgrade Summary (v2.0)

### What Changed

1. **Explicit Regime Ontology** (NEW)
   - Fixed taxonomy for market regimes
   - Deterministic classification
   - Coverage analysis support

2. **Insight Confidence Scoring** (ENHANCED)
   - Detailed confidence metadata
   - Supports weak insight flagging
   - Contradiction tracking

3. **Sensitivity & Failure Boundary Detection** (ENHANCED)
   - Performance cliff detection
   - Failure threshold identification
   - Comprehensive sensitivity analysis

4. **Proposal Ranking by Information Gain** (ENHANCED)
   - Ranking optimized for learning, not returns
   - Uncertainty reduction proposals
   - Regime coverage integration

### What Stayed the Same

- **All execution remains deterministic**
- **Past results are immutable**
- **No stochastic processes**
- **Scenario IDs are stable (hash-based)**

---

## Future Enhancements

Potential extensions (while preserving invariants):

1. **Regime Transition Analysis**: Understand how strategy performs during regime shifts
2. **Multi-Symbol Correlation**: Analyze strategy behavior across correlated assets
3. **Time Decay Weighting**: Weight recent insights more heavily (without modifying past data)
4. **Interactive Hypothesis Testing**: Allow user to specify hypotheses to test

---

## Files

- `agents/research/regime_ontology.py`: Explicit regime taxonomy
- `agents/research/scenario_generator.py`: Scenario generation with regime tagging
- `agents/research/meta_evaluator.py`: Scenario comparison and sensitivity analysis
- `agents/research/memory_agent.py`: Strategy memory with confidence scoring
- `agents/research/proposal_agent.py`: Experiment proposals ranked by information gain
- `daemon/research_loop.py`: Research loop orchestrator
- `daemon/simulator/war_games_runner.py`: Deterministic simulation engine

---

**Version**: 2.0  
**Last Updated**: December 2024  
**Maintainer**: FuggerBot Team

