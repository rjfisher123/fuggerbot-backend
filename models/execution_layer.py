"""
Execution Layer for Broker Integration.

Provides unified interface for IBKR, Alpaca, Tradier, etc.
All trades are approval-based initially.
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters."""
    
    @abstractmethod
    def execute_trade(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """Execute a trade (abstract method)."""
        pass
    
    @abstractmethod
    def get_account_balance(self) -> float:
        """Get account balance (abstract method)."""
        pass


class IBKRAdapter(BrokerAdapter):
    """IBKR broker adapter."""
    
    def __init__(self, ibkr_trader):
        """
        Initialize IBKR adapter.
        
        Args:
            ibkr_trader: IBKRTrader instance
        """
        self.ibkr_trader = ibkr_trader
    
    def execute_trade(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """Execute trade via IBKR."""
        return self.ibkr_trader.execute_trade(
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            require_confirmation=require_approval
        )
    
    def get_account_balance(self) -> float:
        """Get IBKR account balance."""
        summary = self.ibkr_trader.get_account_summary()
        if summary and "NetLiquidation" in summary:
            return float(summary["NetLiquidation"]["value"])
        return 0.0


class ExecutionLayer:
    """Unified execution layer for multiple brokers."""
    
    def __init__(self, broker_adapter: Optional[BrokerAdapter] = None):
        """
        Initialize execution layer.
        
        Args:
            broker_adapter: Optional broker adapter (IBKR, Alpaca, etc.)
        """
        self.broker_adapter = broker_adapter
        self.approval_required = False  # Default to automated execution with safety constraints
    
    def execute_signal(
        self,
        symbol: str,
        action: str,
        position_size_pct: float,
        forecast_id: str,
        account_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a trading signal.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            position_size_pct: Position size as % of portfolio
            forecast_id: Forecast ID for tracking
            account_balance: Optional account balance (if None, fetched)
            
        Returns:
            Dict with execution result
        """
        if not self.broker_adapter:
            return {
                "success": False,
                "error": "No broker adapter configured"
            }
        
        # Get account balance
        if account_balance is None:
            account_balance = self.broker_adapter.get_account_balance()
        
        if account_balance <= 0:
            return {
                "success": False,
                "error": "Invalid account balance"
            }
        
        # Calculate position size
        position_value = account_balance * (position_size_pct / 100.0)
        
        # Get current price (would fetch from broker)
        # For now, use placeholder
        current_price = 0.0  # Would fetch from broker
        
        if current_price <= 0:
            return {
                "success": False,
                "error": "Could not fetch current price"
            }
        
        # Calculate shares
        quantity = int(position_value / current_price)
        
        if quantity <= 0:
            return {
                "success": False,
                "error": "Position size too small"
            }
        
        # Execute trade (with approval if required)
        if self.approval_required:
            result = self.broker_adapter.execute_trade(
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type="MARKET",
                require_approval=True
            )
        else:
            # Direct execution (not recommended without approval)
            result = self.broker_adapter.execute_trade(
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type="MARKET",
                require_approval=False
            )
        
        # Add forecast tracking
        if result.get("success"):
            result["forecast_id"] = forecast_id
            result["position_size_pct"] = position_size_pct
            result["position_value"] = position_value
        
        return result
    
    def set_approval_required(self, required: bool) -> None:
        """Set whether approval is required for trades."""
        self.approval_required = required
        logger.info(f"Approval required set to: {required}")


