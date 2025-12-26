"""
Daily Rebalance Logic.

FRS-weighted, decay-adjusted, and risk parity rebalancing.
"""
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RebalancingEngine:
    """Handles portfolio rebalancing logic."""
    
    def __init__(
        self,
        rebalance_frequency_days: int = 1,
        rebalance_threshold: float = 0.05  # 5% drift triggers rebalance
    ):
        """
        Initialize rebalancing engine.
        
        Args:
            rebalance_frequency_days: Days between rebalances
            rebalance_threshold: Threshold for triggering rebalance
        """
        self.rebalance_frequency_days = rebalance_frequency_days
        self.rebalance_threshold = rebalance_threshold
    
    def frs_weighted_rebalance(
        self,
        current_positions: Dict[str, float],
        new_forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Rebalance using FRS-weighted allocations.
        
        Args:
            current_positions: Current position values
            new_forecasts: New forecast data
            portfolio_value: Current portfolio value
            
        Returns:
            New target allocations
        """
        if not new_forecasts:
            return current_positions
        
        # Calculate FRS-weighted target allocations
        frs_weights = {}
        total_frs_weight = 0.0
        
        for symbol, forecast in new_forecasts.items():
            frs = forecast.get("frs", {}).get("frs_score", 0)
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            
            if frs >= 0.6 and expected_return > 0:
                # Weight by FRS * expected return
                frs_weights[symbol] = frs * expected_return
                total_frs_weight += frs_weights[symbol]
        
        if total_frs_weight == 0:
            return current_positions
        
        # Normalize to portfolio value
        target_allocations = {}
        for symbol, weight in frs_weights.items():
            normalized_weight = weight / total_frs_weight
            target_allocations[symbol] = portfolio_value * normalized_weight
        
        return target_allocations
    
    def decay_adjusted_rebalance(
        self,
        current_positions: Dict[str, float],
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float,
        decay_threshold_hours: float = 24.0
    ) -> Dict[str, float]:
        """
        Rebalance with decay adjustment (reduce positions with old forecasts).
        
        Args:
            current_positions: Current position values
            forecasts: Forecast data with timestamps
            portfolio_value: Current portfolio value
            decay_threshold_hours: Hours before forecast is considered stale
            
        Returns:
            Decay-adjusted allocations
        """
        if not forecasts:
            return current_positions
        
        # Check forecast age
        current_time = datetime.now()
        decay_adjusted_weights = {}
        
        for symbol, forecast in forecasts.items():
            # Get forecast timestamp
            timestamp_str = forecast.get("timestamp", "")
            if not timestamp_str:
                # No timestamp - assume fresh
                age_hours = 0.0
            else:
                try:
                    forecast_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    age_hours = (current_time - forecast_time.replace(tzinfo=None)).total_seconds() / 3600
                except:
                    age_hours = 0.0
            
            # Decay factor: 1.0 if fresh, decreases with age
            if age_hours < decay_threshold_hours:
                decay_factor = 1.0
            else:
                # Exponential decay
                decay_factor = np.exp(-(age_hours - decay_threshold_hours) / decay_threshold_hours)
            
            # Get base allocation
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            frs = forecast.get("frs", {}).get("frs_score", 0)
            
            if expected_return > 0 and frs >= 0.6:
                base_weight = frs * expected_return
                decay_adjusted_weights[symbol] = base_weight * decay_factor
        
        # Normalize
        total_weight = sum(decay_adjusted_weights.values())
        if total_weight > 0:
            allocations = {}
            for symbol, weight in decay_adjusted_weights.items():
                normalized_weight = weight / total_weight
                allocations[symbol] = portfolio_value * normalized_weight
            return allocations
        
        return current_positions
    
    def risk_parity_rebalance(
        self,
        current_positions: Dict[str, float],
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Rebalance using risk parity (equal risk contribution).
        
        Args:
            current_positions: Current position values
            forecasts: Forecast data
            portfolio_value: Current portfolio value
            
        Returns:
            Risk parity allocations
        """
        if not forecasts:
            return current_positions
        
        # Extract risks
        symbol_risks = {}
        for symbol, forecast in forecasts.items():
            rec = forecast.get("recommendation", {})
            risk_pct = rec.get("risk_pct", 0) / 100.0  # Convert to fraction
            frs = forecast.get("frs", {}).get("frs_score", 0)
            
            if risk_pct > 0 and frs >= 0.6:
                symbol_risks[symbol] = risk_pct
        
        if not symbol_risks:
            return current_positions
        
        # Risk parity: weight inversely proportional to risk
        # Each position contributes equal risk
        inv_risk_weights = {sym: 1.0 / risk for sym, risk in symbol_risks.items()}
        
        # Normalize
        total_inv_risk = sum(inv_risk_weights.values())
        if total_inv_risk > 0:
            allocations = {}
            for symbol, inv_risk in inv_risk_weights.items():
                normalized_weight = inv_risk / total_inv_risk
                allocations[symbol] = portfolio_value * normalized_weight
            return allocations
        
        return current_positions
    
    def should_rebalance(
        self,
        current_positions: Dict[str, float],
        target_allocations: Dict[str, float],
        last_rebalance_date: Optional[datetime] = None
    ) -> bool:
        """
        Determine if rebalancing is needed.
        
        Args:
            current_positions: Current position values
            target_allocations: Target allocations
            last_rebalance_date: Last rebalance date
            
        Returns:
            True if rebalancing needed
        """
        # Check time-based rebalancing
        if last_rebalance_date:
            days_since = (datetime.now() - last_rebalance_date).days
            if days_since >= self.rebalance_frequency_days:
                return True
        
        # Check drift-based rebalancing
        total_current = sum(current_positions.values())
        total_target = sum(target_allocations.values())
        
        if total_current == 0 or total_target == 0:
            return True
        
        # Calculate drift for each position
        max_drift = 0.0
        for symbol in set(list(current_positions.keys()) + list(target_allocations.keys())):
            current_weight = current_positions.get(symbol, 0) / total_current
            target_weight = target_allocations.get(symbol, 0) / total_target
            
            drift = abs(current_weight - target_weight)
            max_drift = max(max_drift, drift)
        
        return max_drift >= self.rebalance_threshold
    
    def calculate_rebalance_trades(
        self,
        current_positions: Dict[str, float],
        target_allocations: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate trades needed for rebalancing.
        
        Args:
            current_positions: Current position values
            target_allocations: Target allocations
            current_prices: Current prices
            
        Returns:
            List of trade instructions
        """
        trades = []
        
        all_symbols = set(list(current_positions.keys()) + list(target_allocations.keys()))
        
        for symbol in all_symbols:
            current_value = current_positions.get(symbol, 0)
            target_value = target_allocations.get(symbol, 0)
            
            if symbol not in current_prices or current_prices[symbol] <= 0:
                continue
            
            current_price = current_prices[symbol]
            current_shares = current_value / current_price if current_value > 0 else 0
            target_shares = target_value / current_price
            
            shares_to_trade = target_shares - current_shares
            
            if abs(shares_to_trade) > 0.01:  # Minimum trade size
                trades.append({
                    "symbol": symbol,
                    "action": "BUY" if shares_to_trade > 0 else "SELL",
                    "shares": abs(shares_to_trade),
                    "value": abs(target_value - current_value),
                    "current_value": current_value,
                    "target_value": target_value
                })
        
        return trades











