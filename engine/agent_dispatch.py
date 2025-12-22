"""
Agent Dispatcher for FuggerBot v1.5.

Multi-agent architecture for routing tasks to specialized agents.
"""
import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Task types for agent routing."""
    MACRO_SCAN = "MACRO_SCAN"
    TRADE_VALIDATION = "TRADE_VALIDATION"
    RISK_AUDIT = "RISK_AUDIT"
    POLICY_UPDATE = "POLICY_UPDATE"


class Task(BaseModel):
    """Task model for agent dispatch."""
    task_type: TaskType = Field(..., description="Type of task to execute")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload data")
    task_id: Optional[str] = Field(default=None, description="Optional task identifier")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=highest, 10=lowest)")


class Result(BaseModel):
    """Result model from agent execution."""
    task_id: Optional[str] = Field(default=None, description="Task identifier")
    success: bool = Field(..., description="Whether task completed successfully")
    data: Dict[str, Any] = Field(default_factory=dict, description="Result data")
    error: Optional[str] = Field(default=None, description="Error message if task failed")
    execution_time: float = Field(default=0.0, description="Execution time in seconds")


class AgentRouter:
    """
    Multi-agent router for FuggerBot v1.5.
    
    Routes tasks to specialized agents based on task type.
    """
    
    def __init__(self):
        """Initialize the agent router."""
        self._agents = {}
        self._initialize_agents()
        logger.info("AgentRouter initialized")
    
    def _initialize_agents(self):
        """Initialize agent connections (lazy imports to avoid circular dependencies)."""
        # Agents will be imported on-demand to avoid circular dependencies
        self._agents = {
            TaskType.MACRO_SCAN: None,
            TaskType.TRADE_VALIDATION: None,
            TaskType.RISK_AUDIT: None,
            TaskType.POLICY_UPDATE: None,
        }
    
    async def dispatch(self, task: Task, payload: Optional[Dict[str, Any]] = None) -> Result:
        """
        Dispatch a task to the appropriate agent.
        
        Args:
            task: Task object with task_type and payload
            payload: Optional override payload (if None, uses task.payload)
        
        Returns:
            Result object with execution results
        """
        import time
        start_time = time.time()
        
        if payload is None:
            payload = task.payload
        
        logger.info(f"📤 Dispatching task: {task.task_type.value} (priority: {task.priority})")
        
        try:
            if task.task_type == TaskType.MACRO_SCAN:
                result_data = await self._handle_macro_scan(payload)
            elif task.task_type == TaskType.TRADE_VALIDATION:
                result_data = await self._handle_trade_validation(payload)
            elif task.task_type == TaskType.RISK_AUDIT:
                result_data = await self._handle_risk_audit(payload)
            elif task.task_type == TaskType.POLICY_UPDATE:
                result_data = await self._handle_policy_update(payload)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            execution_time = time.time() - start_time
            logger.info(f"✅ Task completed: {task.task_type.value} ({execution_time:.2f}s)")
            
            return Result(
                task_id=task.task_id,
                success=True,
                data=result_data,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task failed: {task.task_type.value} - {e}", exc_info=True)
            
            return Result(
                task_id=task.task_id,
                success=False,
                data={},
                error=str(e),
                execution_time=execution_time
            )
    
    async def _handle_macro_scan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route MACRO_SCAN task to daemon.watcher.
        
        Args:
            payload: Payload containing macro scan parameters
        
        Returns:
            Result data from macro watcher
        """
        try:
            from daemon.watcher import MacroDaemon
            
            # Initialize watcher if needed
            if self._agents[TaskType.MACRO_SCAN] is None:
                self._agents[TaskType.MACRO_SCAN] = MacroDaemon()
            
            watcher = self._agents[TaskType.MACRO_SCAN]
            
            # Run a single cycle
            result = watcher.run_cycle()
            
            return {
                "regime_detected": result.get("regime_id") if isinstance(result, dict) else None,
                "confidence": result.get("confidence", 0.0) if isinstance(result, dict) else 0.0,
                "signals_analyzed": result.get("signals_count", 0) if isinstance(result, dict) else 0,
            }
        except Exception as e:
            logger.error(f"Error in macro scan: {e}", exc_info=True)
            raise
    
    async def _handle_trade_validation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route TRADE_VALIDATION task to reasoning.engine.
        
        Args:
            payload: Payload containing TradeContext and validation parameters
        
        Returns:
            Result data from trade validation
        """
        try:
            from reasoning.engine import DeepSeekEngine
            from reasoning.schemas import TradeContext
            from config.settings import get_settings
            
            settings = get_settings()
            
            # Initialize engine if needed
            if self._agents[TaskType.TRADE_VALIDATION] is None:
                self._agents[TaskType.TRADE_VALIDATION] = DeepSeekEngine(
                    api_key=settings.openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                    model=settings.deepseek_model
                )
            
            engine = self._agents[TaskType.TRADE_VALIDATION]
            
            # Extract TradeContext from payload
            if "context" in payload:
                context = payload["context"]
                if isinstance(context, dict):
                    context = TradeContext(**context)
                elif not isinstance(context, TradeContext):
                    raise ValueError("Invalid context type in payload")
            else:
                raise ValueError("Missing 'context' in payload")
            
            red_team_mode = payload.get("red_team_mode", False)
            
            # Run validation
            response = engine.analyze_trade(context, red_team_mode=red_team_mode)
            
            if response:
                return {
                    "decision": response.decision.value,
                    "confidence": response.confidence,
                    "rationale": response.rationale,
                    "risk_analysis": response.risk_analysis,
                    "proposer_confidence": getattr(response, "proposer_confidence", None),
                    "final_confidence": response.confidence,
                }
            else:
                return {
                    "decision": "REJECT",
                    "confidence": 0.0,
                    "rationale": "Validation failed",
                    "error": "Engine returned None"
                }
        except Exception as e:
            logger.error(f"Error in trade validation: {e}", exc_info=True)
            raise
    
    async def _handle_risk_audit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route RISK_AUDIT task to engine.postmortem.
        
        Args:
            payload: Payload containing trade data for audit
        
        Returns:
            Result data from risk audit
        """
        try:
            from engine.postmortem import TradeCoroner
            
            # Initialize coroner if needed
            if self._agents[TaskType.RISK_AUDIT] is None:
                self._agents[TaskType.RISK_AUDIT] = TradeCoroner()
            
            coroner = self._agents[TaskType.RISK_AUDIT]
            
            # Extract trade data from payload
            if "trade_data" not in payload:
                raise ValueError("Missing 'trade_data' in payload")
            
            trade_data = payload["trade_data"]
            
            # Run audit
            report = coroner.conduct_review(trade_data)
            
            if report:
                return {
                    "outcome_category": report.outcome_category.value,
                    "root_cause": report.root_cause,
                    "lesson_learned": report.lesson_learned,
                    "adjusted_confidence": report.adjusted_confidence,
                    "actual_outcome": report.actual_outcome,
                }
            else:
                return {
                    "outcome_category": "MODEL_HALLUCINATION",
                    "root_cause": "Audit failed",
                    "error": "Coroner returned None"
                }
        except Exception as e:
            logger.error(f"Error in risk audit: {e}", exc_info=True)
            raise
    
    async def _handle_policy_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route POLICY_UPDATE task to policy update handler.
        
        Args:
            payload: Payload containing policy update parameters
        
        Returns:
            Result data from policy update
        """
        try:
            from config.adaptive_loader import AdaptiveParamLoader
            
            symbol = payload.get("symbol")
            new_params = payload.get("params", {})
            
            if not symbol:
                raise ValueError("Missing 'symbol' in payload")
            
            loader = AdaptiveParamLoader()
            success = loader.update_params(symbol, new_params)
            
            return {
                "symbol": symbol,
                "params_updated": new_params,
                "success": success,
            }
        except Exception as e:
            logger.error(f"Error in policy update: {e}", exc_info=True)
            raise


# Singleton instance
_router_instance: Optional[AgentRouter] = None


def get_router() -> AgentRouter:
    """Get or create the singleton AgentRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = AgentRouter()
    return _router_instance







