"""
Autonomous Execution Engine.

Handles approval-optional trade flow with safety checks.
"""
from typing import Dict, Any, Optional
import logging

from models.safety_constraints import SafetyConstraintsEngine

logger = logging.getLogger(__name__)


class AutonomousExecutionEngine:
    """Manages autonomous execution with optional approvals and safety constraints."""

    def __init__(
        self,
        broker_execution_layer,
        require_human_approval: bool = False,
        safety_engine: Optional[SafetyConstraintsEngine] = None
    ):
        """
        Initialize autonomous execution engine.

        Args:
            broker_execution_layer: ExecutionLayer instance
            require_human_approval: Whether approval is required (default: False for automated mode)
            safety_engine: Optional SafetyConstraintsEngine instance
        """
        self.broker_execution_layer = broker_execution_layer
        self.require_human_approval = require_human_approval
        self.safety_engine = safety_engine or SafetyConstraintsEngine()
        self.execution_log = []
        
        # Set execution layer approval requirement based on our setting
        if broker_execution_layer:
            broker_execution_layer.set_approval_required(require_human_approval)

    def toggle_approval(self, required: bool) -> None:
        """Toggle approval requirement."""
        self.require_human_approval = required
        logger.info(f"Autonomous execution approval requirement set to {required}")

    def execute_trade(
        self,
        symbol: str,
        action: str,
        position_size_pct: float,
        forecast_id: str,
        safety_checks: Optional[Dict[str, Any]] = None,
        drift_score: Optional[float] = None,
        volatility: Optional[float] = None,
        coherence_score: Optional[float] = None,
        frs_score: Optional[float] = None,
        meta_reliability: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute trade with safety checks.

        Args:
            symbol: Trading symbol
            action: BUY/SELL
            position_size_pct: Position size percent
            forecast_id: Forecast ID
            safety_checks: Pre-computed safety check results (optional)
            drift_score: Drift score for safety evaluation (if safety_checks not provided)
            volatility: Volatility for safety evaluation (if safety_checks not provided)
            coherence_score: Coherence score for safety evaluation (if safety_checks not provided)
            frs_score: FRS score for safety evaluation (if safety_checks not provided)
            meta_reliability: Meta reliability score for safety evaluation (if safety_checks not provided)

        Returns:
            Execution result
        """
        # Evaluate safety constraints if not provided
        if safety_checks is None:
            # Use provided metrics or defaults
            drift_score = drift_score if drift_score is not None else 0.0
            volatility = volatility if volatility is not None else 0.0
            coherence_score = coherence_score if coherence_score is not None else 1.0
            frs_score = frs_score if frs_score is not None else 0.5
            meta_reliability = meta_reliability if meta_reliability is not None else 0.5
            
            safety_checks = self.safety_engine.evaluate(
                drift_score=drift_score,
                volatility=volatility,
                coherence_score=coherence_score,
                frs_score=frs_score,
                meta_reliability=meta_reliability
            )
        
        # Ensure safety checks passed
        if not safety_checks.get("all_clear", False):
            reason = safety_checks.get("blocking_reason", "Safety check failed")
            logger.warning(f"Trade blocked for {symbol}: {reason} - Issues: {safety_checks.get('issues', [])}")
            return {
                "success": False,
                "reason": reason,
                "blocked": True,
                "safety_checks": safety_checks,
                "action": safety_checks.get("action")
            }

        # Update execution layer approval requirement based on current setting
        if self.broker_execution_layer:
            self.broker_execution_layer.set_approval_required(self.require_human_approval)

        result = self.broker_execution_layer.execute_signal(
            symbol=symbol,
            action=action,
            position_size_pct=position_size_pct,
            forecast_id=forecast_id
        )

        # Log execution
        log_entry = {
            "symbol": symbol,
            "action": action,
            "position_size_pct": position_size_pct,
            "forecast_id": forecast_id,
            "result": result,
            "safety_checks": safety_checks,
            "automated": not self.require_human_approval
        }
        self.execution_log.append(log_entry)
        
        logger.info(f"Trade executed for {symbol} {action} - Automated: {not self.require_human_approval}, Safety: {safety_checks.get('all_clear', False)}")

        return result


