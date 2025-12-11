"""
Adaptive tuning daemon.

Automatically adjusts trading thresholds based on observed Hit Rate and Regret.
"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure project root is on sys.path when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.adaptive_loader import AdaptiveParamLoader
from research.profiler import SymbolProfiler
from daemon.tuning_log import TuningEvent, log_tuning_event
from context.tracker import RegimeTracker

logger = logging.getLogger(__name__)

# Tuning constants
REGRET_THRESHOLD = 0.40
HIT_LOW = 0.40
HIT_HIGH = 0.70

TRUST_STEP = 0.05
CONF_STEP_UP = 0.05
CONF_STEP_DOWN = 0.03

TRUST_MIN = 0.50
CONF_MIN = 0.50
CONF_MAX = 0.95


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def run_tuning_cycle(
    memory_path: Optional[Path] = None,
    params_path: Optional[Path] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Execute one tuning pass over all symbols based on recent performance.
    
    Now regime-aware (v1.5): Tunes parameters per regime.

    Args:
        memory_path: Optional path to trade_memory.json (defaults used by SymbolProfiler).
        params_path: Optional path to adaptive params file (defaults used by AdaptiveParamLoader).

    Returns:
        Dict keyed by symbol describing applied parameter changes.
    """
    profiler = SymbolProfiler(memory_path)
    
    # Get current regime for regime-aware tuning
    regime_tracker = RegimeTracker()
    current_regime = regime_tracker.get_current_regime()
    regime_id = current_regime.id if hasattr(current_regime, 'id') else str(current_regime)
    
    logger.info(f"🌍 Tuning for regime: {regime_id} ({current_regime.name if hasattr(current_regime, 'name') else 'UNKNOWN'})")
    
    # Use regime-specific params file if it exists, otherwise use default
    if params_path is None:
        regime_params_path = Path(f"data/adaptive_params_{regime_id}.json")
        if regime_params_path.exists():
            params_path = regime_params_path
            logger.info(f"📁 Using regime-specific params: {regime_params_path}")
        else:
            params_path = Path("data/adaptive_params.json")
    
    loader = AdaptiveParamLoader(params_path)

    profiles = profiler.generate_profiles()
    if not profiles:
        logger.info("No profiles generated; nothing to tune.")
        return {}

    applied_changes: Dict[str, Dict[str, Any]] = {}

    for symbol, metrics in profiles.items():
        current = loader.get_params(symbol)
        updates: Dict[str, Any] = {}

        hit_rate = metrics.get("hit_rate", 0.0) or 0.0
        regret_rate = metrics.get("regret_rate", 0.0) or 0.0

        # Case A: High regret -> too strict -> decrease trust threshold
        if regret_rate > REGRET_THRESHOLD:
            prev = current.get("trust_threshold", TRUST_MIN)
            new_val = _clamp(prev - TRUST_STEP, TRUST_MIN, 1.0)
            if new_val != prev:
                reason = f"High Regret {regret_rate:.1%} > {REGRET_THRESHOLD:.0%}"
                _apply_update(
                    loader,
                    symbol,
                    "trust_threshold",
                    prev,
                    new_val,
                    reason,
                    hit_rate,
                    regret_rate,
                    updates,
                    regime_id,
                )

        # Case B: Low hit rate -> increase min confidence
        if hit_rate < HIT_LOW:
            prev = current.get("min_confidence", CONF_MIN)
            new_val = _clamp(prev + CONF_STEP_UP, CONF_MIN, CONF_MAX)
            if new_val != prev:
                reason = f"Low Hit Rate {hit_rate:.1%} < {HIT_LOW:.0%}"
                _apply_update(
                    loader,
                    symbol,
                    "min_confidence",
                    prev,
                    new_val,
                    reason,
                    hit_rate,
                    regret_rate,
                    updates,
                    regime_id,
                )

        # Case C: High hit rate -> loosen min confidence slightly
        elif hit_rate > HIT_HIGH:
            prev = current.get("min_confidence", CONF_MIN)
            new_val = _clamp(prev - CONF_STEP_DOWN, CONF_MIN, CONF_MAX)
            if new_val != prev:
                reason = f"High Hit Rate {hit_rate:.1%} > {HIT_HIGH:.0%}"
                _apply_update(
                    loader,
                    symbol,
                    "min_confidence",
                    prev,
                    new_val,
                    reason,
                    hit_rate,
                    regret_rate,
                    updates,
                    regime_id,
                )

        if updates:
            applied_changes[symbol] = updates
        else:
            logger.debug(f"No tuning adjustments needed for {symbol}")

    return applied_changes


def _apply_update(
    loader: AdaptiveParamLoader,
    symbol: str,
    param_name: str,
    prev: float,
    new_val: float,
    reason: str,
    hit_rate: float,
    regret_rate: float,
    updates: Dict[str, Any],
    regime_id: str,
) -> None:
    """
    Apply a single parameter update, persist to regime-specific file, and log the tuning event.
    
    v1.5: Saves to regime-specific params file.
    """
    logger.info(
        f"🔧 Tuning {symbol} for regime {regime_id}: {param_name} {prev:.2f} -> {new_val:.2f} ({reason})"
    )

    # Save to regime-specific file
    regime_params_path = Path(f"data/adaptive_params_{regime_id}.json")
    regime_loader = AdaptiveParamLoader(regime_params_path)
    regime_loader.update_params(symbol, {param_name: new_val})
    
    # Also update the main loader (for backward compatibility)
    loader.update_params(symbol, {param_name: new_val})
    
    updates[param_name] = new_val

    event = TuningEvent(
        symbol=symbol,
        param_name=param_name,
        old_value=prev,
        new_value=new_val,
        reason=reason,
        hit_rate=hit_rate,
        regret_rate=regret_rate,
    )
    log_tuning_event(event)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    changes = run_tuning_cycle()
    if changes:
        logger.info("Tuning applied:")
        for sym, upd in changes.items():
            logger.info(f"  {sym}: {upd}")
    else:
        logger.info("No tuning changes were applied.")

