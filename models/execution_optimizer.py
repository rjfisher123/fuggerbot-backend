"""
Execution Optimization.

VWAP/TWAP algorithms and smart order routing.
"""
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class VWAPOptimizer:
    """VWAP (Volume-Weighted Average Price) execution optimizer."""
    
    def __init__(self):
        """Initialize VWAP optimizer."""
        pass
    
    def calculate_vwap(
        self,
        price_volume_data: List[Dict[str, float]]
    ) -> float:
        """
        Calculate VWAP from price/volume data.
        
        Args:
            price_volume_data: List of {price, volume} dicts
            
        Returns:
            VWAP value
        """
        if not price_volume_data:
            return 0.0
        
        total_value = sum(d["price"] * d["volume"] for d in price_volume_data)
        total_volume = sum(d["volume"] for d in price_volume_data)
        
        if total_volume == 0:
            return 0.0
        
        return float(total_value / total_volume)
    
    def generate_vwap_schedule(
        self,
        total_shares: float,
        historical_volume_profile: List[float],
        time_window_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Generate VWAP execution schedule.
        
        Args:
            total_shares: Total shares to execute
            historical_volume_profile: Historical volume by time period
            time_window_minutes: Execution time window
            
        Returns:
            List of execution slices
        """
        if not historical_volume_profile:
            # Equal distribution if no volume profile
            num_slices = int(time_window_minutes / 5)  # 5-minute slices
            shares_per_slice = total_shares / num_slices
            
            return [
                {"slice": i + 1, "shares": shares_per_slice, "time_minutes": i * 5}
                for i in range(num_slices)
            ]
        
        # Weight by volume profile
        total_volume = sum(historical_volume_profile)
        if total_volume == 0:
            total_volume = 1.0
        
        # Normalize volume profile
        volume_weights = [v / total_volume for v in historical_volume_profile]
        
        # Calculate shares per slice
        num_slices = len(historical_volume_profile)
        shares_per_slice = [total_shares * w for w in volume_weights]
        
        # Generate schedule
        schedule = []
        time_per_slice = time_window_minutes / num_slices
        
        for i, shares in enumerate(shares_per_slice):
            schedule.append({
                "slice": i + 1,
                "shares": shares,
                "time_minutes": i * time_per_slice,
                "volume_weight": volume_weights[i]
            })
        
        return schedule


class TWAPOptimizer:
    """TWAP (Time-Weighted Average Price) execution optimizer."""
    
    def __init__(self):
        """Initialize TWAP optimizer."""
        pass
    
    def generate_twap_schedule(
        self,
        total_shares: float,
        time_window_minutes: int = 60,
        slice_duration_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate TWAP execution schedule (equal time slices).
        
        Args:
            total_shares: Total shares to execute
            time_window_minutes: Total execution window
            slice_duration_minutes: Duration of each slice
            
        Returns:
            List of execution slices
        """
        num_slices = int(time_window_minutes / slice_duration_minutes)
        if num_slices == 0:
            num_slices = 1
        
        shares_per_slice = total_shares / num_slices
        
        schedule = []
        for i in range(num_slices):
            schedule.append({
                "slice": i + 1,
                "shares": shares_per_slice,
                "start_minutes": i * slice_duration_minutes,
                "end_minutes": (i + 1) * slice_duration_minutes
            })
        
        return schedule


class SmartOrderRouter:
    """Smart order routing for optimal execution."""
    
    def __init__(self):
        """Initialize smart order router."""
        self.vwap_optimizer = VWAPOptimizer()
        self.twap_optimizer = TWAPOptimizer()
    
    def route_order(
        self,
        symbol: str,
        total_shares: float,
        order_type: str = "MARKET",
        execution_strategy: str = "VWAP",
        time_window_minutes: int = 60,
        historical_volume: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Route order using optimal execution strategy.
        
        Args:
            symbol: Trading symbol
            total_shares: Total shares to execute
            order_type: Order type
            execution_strategy: VWAP, TWAP, or MARKET
            time_window_minutes: Execution window
            historical_volume: Optional historical volume profile
            
        Returns:
            Execution plan
        """
        if execution_strategy == "VWAP" and historical_volume:
            schedule = self.vwap_optimizer.generate_vwap_schedule(
                total_shares=total_shares,
                historical_volume_profile=historical_volume,
                time_window_minutes=time_window_minutes
            )
        elif execution_strategy == "TWAP":
            schedule = self.twap_optimizer.generate_twap_schedule(
                total_shares=total_shares,
                time_window_minutes=time_window_minutes
            )
        else:
            # Market order: execute immediately
            schedule = [{
                "slice": 1,
                "shares": total_shares,
                "time_minutes": 0
            }]
        
        return {
            "symbol": symbol,
            "total_shares": total_shares,
            "execution_strategy": execution_strategy,
            "num_slices": len(schedule),
            "schedule": schedule,
            "estimated_completion_minutes": time_window_minutes
        }
    
    def optimize_execution(
        self,
        symbol: str,
        target_shares: float,
        current_price: float,
        market_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize execution based on market conditions.
        
        Args:
            symbol: Trading symbol
            target_shares: Target shares
            current_price: Current price
            market_conditions: Market condition dict (volatility, liquidity, etc.)
            
        Returns:
            Optimized execution plan
        """
        volatility = market_conditions.get("volatility", 0.20)
        liquidity = market_conditions.get("liquidity_score", 0.7)
        order_value = target_shares * current_price
        
        # Choose strategy based on conditions
        if volatility > 0.30 or liquidity < 0.5:
            # High volatility or low liquidity: use TWAP (time-based)
            strategy = "TWAP"
            time_window = 120  # 2 hours for difficult conditions
        elif order_value > 100000:
            # Large order: use VWAP (volume-based)
            strategy = "VWAP"
            time_window = 60  # 1 hour
        else:
            # Small order, good conditions: market order
            strategy = "MARKET"
            time_window = 1  # Immediate
        
        execution_plan = self.route_order(
            symbol=symbol,
            total_shares=target_shares,
            execution_strategy=strategy,
            time_window_minutes=time_window
        )
        
        return {
            **execution_plan,
            "recommended_strategy": strategy,
            "reasoning": self._get_strategy_reasoning(volatility, liquidity, order_value)
        }
    
    @staticmethod
    def _get_strategy_reasoning(
        volatility: float,
        liquidity: float,
        order_value: float
    ) -> str:
        """Get human-readable reasoning for strategy choice."""
        reasons = []
        
        if volatility > 0.30:
            reasons.append("High volatility")
        if liquidity < 0.5:
            reasons.append("Low liquidity")
        if order_value > 100000:
            reasons.append("Large order size")
        
        if not reasons:
            return "Market conditions favorable for immediate execution"
        
        return f"Strategy chosen due to: {', '.join(reasons)}"











