"""
Autonomous Execution Service.

Unified service for automated trade execution with safety constraints.
"""
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from models.execution_layer import ExecutionLayer, IBKRAdapter
from models.autonomous_execution import AutonomousExecutionEngine
from models.safety_constraints import SafetyConstraintsEngine
from core.ibkr_trader import get_ibkr_trader, get_paper_trading_trader
from core.logger import logger


def _load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    project_root = Path(__file__).parent.parent
    config_file = project_root / "config" / "config.yaml"
    
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
                return config or {}
        except Exception as e:
            logger.warning(f"Error loading config from {config_file}: {e}")
            return {}
    return {}


def _get_execution_config() -> Dict[str, Any]:
    """Get execution configuration from config.yaml."""
    config = _load_config()
    execution_config = config.get("execution", {})
    
    # Defaults
    defaults = {
        "automated": True,
        "safety": {
            "drift_halt_threshold": 0.8,
            "volatility_flat_threshold": 0.35,
            "coherence_break_threshold": 0.5,
            "min_frs_score": 0.4,
            "min_meta_reliability": 0.4
        }
    }
    
    # Merge with defaults
    result = defaults.copy()
    if execution_config:
        result["automated"] = execution_config.get("automated", defaults["automated"])
        if "safety" in execution_config:
            result["safety"].update(execution_config["safety"])
    
    return result


class AutonomousExecutionService:
    """
    Unified service for autonomous trade execution with safety constraints.
    
    This service combines:
    - Safety constraint evaluation
    - Autonomous execution engine
    - Broker execution layer
    - Configuration management
    """
    
    def __init__(
        self,
        paper_trading: bool = False,
        require_human_approval: Optional[bool] = None,
        safety_engine: Optional[SafetyConstraintsEngine] = None
    ):
        """
        Initialize autonomous execution service.
        
        Args:
            paper_trading: If True, use paper trading account
            require_human_approval: If True, require human approval. If None, loads from config.
            safety_engine: Optional custom SafetyConstraintsEngine
        """
        self.paper_trading = paper_trading
        
        # Load configuration
        exec_config = _get_execution_config()
        
        # Determine approval requirement (config takes precedence, then parameter, then default)
        if require_human_approval is None:
            require_human_approval = not exec_config.get("automated", True)
        self.require_human_approval = require_human_approval
        
        # Initialize broker adapter
        if paper_trading:
            ibkr_trader = get_paper_trading_trader()
        else:
            ibkr_trader = get_ibkr_trader()
        
        broker_adapter = IBKRAdapter(ibkr_trader)
        execution_layer = ExecutionLayer(broker_adapter)
        
        # Initialize safety engine with config thresholds
        safety_config = exec_config.get("safety", {})
        if safety_engine is None:
            self.safety_engine = SafetyConstraintsEngine(
                drift_halt_threshold=safety_config.get("drift_halt_threshold", 0.8),
                volatility_flat_threshold=safety_config.get("volatility_flat_threshold", 0.35),
                coherence_break_threshold=safety_config.get("coherence_break_threshold", 0.5)
            )
        else:
            self.safety_engine = safety_engine
        
        # Initialize autonomous execution engine
        self.execution_engine = AutonomousExecutionEngine(
            broker_execution_layer=execution_layer,
            require_human_approval=require_human_approval,
            safety_engine=self.safety_engine
        )
        
        logger.info(
            f"AutonomousExecutionService initialized - "
            f"paper_trading={paper_trading}, "
            f"require_human_approval={require_human_approval} "
            f"(from config: automated={exec_config.get('automated', True)})"
        )
    
    def execute_with_safety_checks(
        self,
        symbol: str,
        action: str,
        position_size_pct: float,
        forecast_id: str,
        drift_score: Optional[float] = None,
        volatility: Optional[float] = None,
        coherence_score: Optional[float] = None,
        frs_score: Optional[float] = None,
        meta_reliability: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute trade with automatic safety constraint evaluation.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            position_size_pct: Position size as percentage of portfolio
            forecast_id: Forecast ID for tracking
            drift_score: Optional drift score (defaults to 0.0 if not provided)
            volatility: Optional volatility (defaults to 0.0 if not provided)
            coherence_score: Optional coherence score (defaults to 1.0 if not provided)
            frs_score: Optional FRS score (defaults to 0.5 if not provided)
            meta_reliability: Optional meta reliability (defaults to 0.5 if not provided)
        
        Returns:
            Dict with execution result including safety check information
        """
        logger.info(
            f"Executing trade with safety checks: {symbol} {action} "
            f"({position_size_pct}% position, forecast_id={forecast_id})"
        )
        
        # Execute through autonomous execution engine
        result = self.execution_engine.execute_trade(
            symbol=symbol,
            action=action,
            position_size_pct=position_size_pct,
            forecast_id=forecast_id,
            drift_score=drift_score,
            volatility=volatility,
            coherence_score=coherence_score,
            frs_score=frs_score,
            meta_reliability=meta_reliability
        )
        
        # Add service metadata
        result["service"] = "AutonomousExecutionService"
        result["paper_trading"] = self.paper_trading
        result["automated"] = not self.require_human_approval
        result["timestamp"] = datetime.now().isoformat()
        
        return result
    
    def toggle_approval_mode(self, require_approval: bool) -> None:
        """
        Toggle between automated and approval-required modes.
        
        Args:
            require_approval: If True, require human approval; if False, automated execution
        """
        self.require_human_approval = require_approval
        self.execution_engine.toggle_approval(require_approval)
        logger.info(f"Execution mode changed to: {'Approval Required' if require_approval else 'Automated'}")
    
    def get_execution_log(self) -> list:
        """Get execution log from autonomous execution engine."""
        return self.execution_engine.execution_log
    
    def get_safety_engine(self) -> SafetyConstraintsEngine:
        """Get the safety constraints engine instance."""
        return self.safety_engine


# Global service instances
_live_execution_service: Optional[AutonomousExecutionService] = None
_paper_execution_service: Optional[AutonomousExecutionService] = None


def get_autonomous_execution_service(
    paper_trading: bool = False,
    require_human_approval: Optional[bool] = None
) -> AutonomousExecutionService:
    """
    Get or create autonomous execution service instance.
    
    Args:
        paper_trading: If True, return paper trading service
        require_human_approval: Override approval requirement (None = use config/default)
    
    Returns:
        AutonomousExecutionService instance
    """
    global _live_execution_service, _paper_execution_service
    
    if paper_trading:
        if _paper_execution_service is None:
            _paper_execution_service = AutonomousExecutionService(
                paper_trading=True,
                require_human_approval=require_human_approval
            )
        return _paper_execution_service
    else:
        if _live_execution_service is None:
            _live_execution_service = AutonomousExecutionService(
                paper_trading=False,
                require_human_approval=require_human_approval
            )
        return _live_execution_service

