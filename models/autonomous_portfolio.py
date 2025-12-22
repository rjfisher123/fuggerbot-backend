"""
Autonomous Portfolio Rotation.

Automatically rebalances portfolio based on signals.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from models.rebalancing import RebalancingEngine
from models.portfolio_construction import PortfolioConstructor

logger = logging.getLogger(__name__)


class AutonomousPortfolioManager:
    """Manages autonomous portfolio rotation."""

    def __init__(
        self,
        rebalance_engine: Optional[RebalancingEngine] = None,
        constructor: Optional[PortfolioConstructor] = None
    ):
        self.rebalance_engine = rebalance_engine or RebalancingEngine()
        self.constructor = constructor or PortfolioConstructor()
        self.current_positions: Dict[str, float] = {}
        self.last_rebalance_date: Optional[datetime] = None

    def update_positions(self, positions: Dict[str, float]) -> None:
        """Update current positions."""
        self.current_positions = positions

    def rotate_portfolio(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float,
        current_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Rotate portfolio based on new forecasts.

        Args:
            forecasts: Forecast data
            portfolio_value: Current portfolio value
            current_prices: Current market prices

        Returns:
            Dict with rebalance plan
        """
        # Build target allocations
        target_allocations = self.constructor.volatility_scaled_allocation(
            forecasts=forecasts,
            portfolio_value=portfolio_value
        )

        # Check if rebalance needed
        should_rebalance = self.rebalance_engine.should_rebalance(
            current_positions=self.current_positions,
            target_allocations=target_allocations,
            last_rebalance_date=self.last_rebalance_date
        )

        if not should_rebalance:
            return {
                "should_rebalance": False,
                "reason": "Within drift threshold",
                "target_allocations": target_allocations
            }

        # Calculate trades
        trades = self.rebalance_engine.calculate_rebalance_trades(
            current_positions=self.current_positions,
            target_allocations=target_allocations,
            current_prices=current_prices
        )

        self.last_rebalance_date = datetime.now()

        return {
            "should_rebalance": True,
            "target_allocations": target_allocations,
            "trades": trades,
            "timestamp": self.last_rebalance_date.isoformat()
        }










