# Automated Execution with Safety Constraints

## Overview

The system has been updated to support **automated execution with safety constraints** instead of requiring human approval for every trade. Trades are now automatically executed when safety checks pass, with hard safety rails to prevent risky trades.

## Key Changes

### 1. ExecutionLayer (`models/execution_layer.py`)
- **Changed default**: `approval_required` now defaults to `False` (automated execution)
- Trades execute directly when `approval_required=False`
- Can still be toggled to require approval via `set_approval_required(True)`

### 2. AutonomousExecutionEngine (`models/autonomous_execution.py`)
- **Changed default**: `require_human_approval` now defaults to `False` (automated mode)
- **Integrated SafetyConstraintsEngine**: Automatically evaluates safety constraints before execution
- **Enhanced execute_trade()**: Now accepts safety metrics (drift_score, volatility, coherence_score, frs_score, meta_reliability) or pre-computed safety_checks
- Automatically blocks trades if safety checks fail

### 3. New AutonomousExecutionService (`services/autonomous_execution_service.py`)
- **Unified service** that combines:
  - Safety constraint evaluation
  - Autonomous execution engine
  - Broker execution layer
  - Configuration management
- **Main method**: `execute_with_safety_checks()` - executes trades with automatic safety evaluation
- **Configuration-aware**: Reads from `config/config.yaml` for execution settings

### 4. Configuration (`config/config.yaml`)
- Added `execution` section with:
  - `automated`: Boolean flag (default: `true`) - enables automated execution
  - `safety`: Safety constraint thresholds:
    - `drift_halt_threshold`: 0.8 (drift >= 0.8 → halt trading)
    - `volatility_flat_threshold`: 0.35 (volatility >= 35% → flatten positions)
    - `coherence_break_threshold`: 0.5 (coherence <= 0.5 → stop new trades)
    - `min_frs_score`: 0.4 (FRS < 0.4 → wait for confirmation)
    - `min_meta_reliability`: 0.4 (Meta reliability < 0.4 → wait for confirmation)

## Safety Constraints

The system enforces hard safety rails before executing any trade:

1. **Drift Spike Detection**: If drift score >= 0.8, trading is halted
2. **High Volatility**: If volatility >= 35%, positions are flattened
3. **Coherence Break**: If coherence score <= 0.5, new trades are blocked
4. **Low Confidence**: If FRS score < 0.4 or meta reliability < 0.4, execution waits for confirmation

## Usage

### Basic Usage

```python
from services.autonomous_execution_service import get_autonomous_execution_service

# Get service (defaults to automated mode from config)
service = get_autonomous_execution_service(paper_trading=False)

# Execute trade with safety checks
result = service.execute_with_safety_checks(
    symbol="AAPL",
    action="BUY",
    position_size_pct=3.0,
    forecast_id="forecast_123",
    drift_score=0.2,
    volatility=0.15,
    coherence_score=0.8,
    frs_score=0.75,
    meta_reliability=0.70
)

if result.get("success"):
    print(f"Trade executed: {result}")
elif result.get("blocked"):
    print(f"Trade blocked: {result.get('reason')}")
```

### Toggle Between Modes

```python
# Switch to approval-required mode
service.toggle_approval_mode(require_approval=True)

# Switch back to automated mode
service.toggle_approval_mode(require_approval=False)
```

### Using Pre-computed Safety Checks

```python
from models.safety_constraints import SafetyConstraintsEngine

safety_engine = SafetyConstraintsEngine()
safety_checks = safety_engine.evaluate(
    drift_score=0.3,
    volatility=0.20,
    coherence_score=0.85,
    frs_score=0.80,
    meta_reliability=0.75
)

# Use pre-computed checks
result = service.execution_engine.execute_trade(
    symbol="AAPL",
    action="BUY",
    position_size_pct=3.0,
    forecast_id="forecast_123",
    safety_checks=safety_checks
)
```

## Configuration

Edit `config/config.yaml` to control execution behavior:

```yaml
execution:
  automated: true  # Set to false to require human approval
  
  safety:
    drift_halt_threshold: 0.8
    volatility_flat_threshold: 0.35
    coherence_break_threshold: 0.5
    min_frs_score: 0.4
    min_meta_reliability: 0.4
```

## Migration Notes

- **Default behavior changed**: System now defaults to automated execution
- **Safety-first**: All trades must pass safety constraints before execution
- **Backward compatible**: Can still enable approval mode via configuration or code
- **Logging**: All executions are logged with safety check context

## Safety Guarantees

1. **No trades execute if safety checks fail** - trades are blocked with clear reasons
2. **Hard thresholds** - cannot be bypassed without code changes
3. **Comprehensive logging** - all execution attempts (successful and blocked) are logged
4. **Configurable thresholds** - adjust safety limits via config file

## Example Execution Flow

1. Trade signal generated (e.g., from forecast)
2. Safety metrics collected (drift, volatility, coherence, FRS, meta reliability)
3. SafetyConstraintsEngine evaluates constraints
4. If `all_clear=True`: Trade executes automatically
5. If `all_clear=False`: Trade is blocked with reason logged
6. Execution result logged with full context

## Dependencies

- Added `pyyaml>=6.0` to `requirements.txt` for configuration file parsing



