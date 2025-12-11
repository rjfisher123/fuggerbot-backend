"""
Strategy Templates for FuggerBot.

Provides pre-built strategy logic for different trading approaches.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class StrategyTemplate(ABC):
    """Abstract base class for strategy templates."""
    
    @abstractmethod
    def calculate_allocation(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Calculate position allocations (abstract method)."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name (abstract method)."""
        pass


class MeanVarianceStrategy(StrategyTemplate):
    """Mean-variance optimization strategy."""
    
    def __init__(self, risk_aversion: float = 2.0):
        """
        Initialize mean-variance strategy.
        
        Args:
            risk_aversion: Risk aversion parameter (higher = more risk averse)
        """
        self.risk_aversion = risk_aversion
    
    def get_strategy_name(self) -> str:
        return "Mean-Variance Optimization"
    
    def calculate_allocation(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Calculate allocations using mean-variance optimization.
        
        Args:
            forecasts: Dict of symbol -> forecast data
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        if not forecasts:
            return {}
        
        # Extract expected returns and risks
        symbols = []
        expected_returns = []
        risks = []
        
        for symbol, forecast in forecasts.items():
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            risk = rec.get("risk_pct", 0)
            
            if risk > 0 and expected_return > 0:  # Only positive opportunities
                symbols.append(symbol)
                expected_returns.append(expected_return)
                risks.append(risk)
        
        if not symbols:
            return {}
        
        # Simple mean-variance: weight by (return / risk^2) / risk_aversion
        # Higher return/risk ratio gets more allocation
        weights = []
        for ret, risk in zip(expected_returns, risks):
            # Sharpe-like ratio
            sharpe_ratio = ret / risk if risk > 0 else 0
            weight = sharpe_ratio / self.risk_aversion
            weights.append(max(0, weight))
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            return {}
        
        # Calculate position values
        allocations = {}
        for symbol, weight in zip(symbols, weights):
            allocations[symbol] = portfolio_value * weight
        
        return allocations


class TrendFollowingStrategy(StrategyTemplate):
    """Trend-following strategy based on forecast direction."""
    
    def __init__(self, min_trend_strength: float = 0.6):
        """
        Initialize trend-following strategy.
        
        Args:
            min_trend_strength: Minimum FQS for trend signals
        """
        self.min_trend_strength = min_trend_strength
    
    def get_strategy_name(self) -> str:
        return "Trend Following"
    
    def calculate_allocation(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Calculate allocations for trend-following.
        
        Args:
            forecasts: Dict of symbol -> forecast data
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        if not forecasts:
            return {}
        
        # Filter for strong trends
        trend_signals = {}
        
        for symbol, forecast in forecasts.items():
            rec = forecast.get("recommendation", {})
            action = rec.get("action", "HOLD")
            fqs = forecast.get("fqs", {}).get("fqs_score", 0)
            expected_return = rec.get("expected_return_pct", 0)
            
            # Only BUY signals with strong trend
            if action == "BUY" and fqs >= self.min_trend_strength and expected_return > 0:
                # Weight by expected return
                trend_signals[symbol] = expected_return
        
        if not trend_signals:
            return {}
        
        # Normalize by expected return
        total_signal = sum(trend_signals.values())
        if total_signal > 0:
            allocations = {}
            for symbol, signal in trend_signals.items():
                weight = signal / total_signal
                allocations[symbol] = portfolio_value * weight
            return allocations
        
        return {}


class ReversalStrategy(StrategyTemplate):
    """Reversal/carry hybrid strategy."""
    
    def __init__(self, oversold_threshold: float = -5.0):
        """
        Initialize reversal strategy.
        
        Args:
            oversold_threshold: Expected return threshold for oversold signals
        """
        self.oversold_threshold = oversold_threshold
    
    def get_strategy_name(self) -> str:
        return "Reversal / Carry Hybrid"
    
    def calculate_allocation(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Calculate allocations for reversal strategy.
        
        Args:
            forecasts: Dict of symbol -> forecast data
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        if not forecasts:
            return {}
        
        # Look for oversold conditions (negative expected return that's expected to reverse)
        reversal_signals = {}
        
        for symbol, forecast in forecasts.items():
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            risk = rec.get("risk_pct", 0)
            fqs = forecast.get("fqs", {}).get("fqs_score", 0)
            
            # Oversold: negative return with high uncertainty (potential reversal)
            if expected_return < self.oversold_threshold and risk > 15.0 and fqs > 0.5:
                # Weight by magnitude of oversold condition
                reversal_signals[symbol] = abs(expected_return) * fqs
        
        if not reversal_signals:
            return {}
        
        # Normalize
        total_signal = sum(reversal_signals.values())
        if total_signal > 0:
            allocations = {}
            for symbol, signal in reversal_signals.items():
                weight = signal / total_signal
                allocations[symbol] = portfolio_value * weight
            return allocations
        
        return {}


class DecayAwareStrategy(StrategyTemplate):
    """Decay-aware strategy using signal half-life."""
    
    def __init__(self, min_half_life_hours: float = 12.0):
        """
        Initialize decay-aware strategy.
        
        Args:
            min_half_life_hours: Minimum half-life for signals
        """
        self.min_half_life_hours = min_half_life_hours
    
    def get_strategy_name(self) -> str:
        return "Decay-Aware"
    
    def calculate_allocation(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Calculate allocations weighted by signal decay.
        
        Args:
            forecasts: Dict of symbol -> forecast data
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        if not forecasts:
            return {}
        
        # Weight by half-life (longer half-life = more allocation)
        decay_weighted = {}
        
        for symbol, forecast in forecasts.items():
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            
            # Get half-life from decay analysis (if available)
            half_life = forecast.get("decay", {}).get("half_life_hours", 24.0)
            
            if expected_return > 0 and half_life >= self.min_half_life_hours:
                # Weight by half-life and expected return
                decay_weighted[symbol] = expected_return * (half_life / 24.0)
        
        if not decay_weighted:
            return {}
        
        # Normalize
        total_weight = sum(decay_weighted.values())
        if total_weight > 0:
            allocations = {}
            for symbol, weight in decay_weighted.items():
                norm_weight = weight / total_weight
                allocations[symbol] = portfolio_value * norm_weight
            return allocations
        
        return {}


class FRSWeightedStrategy(StrategyTemplate):
    """FRS-weighted allocation strategy."""
    
    def __init__(self, min_frs: float = 0.6):
        """
        Initialize FRS-weighted strategy.
        
        Args:
            min_frs: Minimum FRS for inclusion
        """
        self.min_frs = min_frs
    
    def get_strategy_name(self) -> str:
        return "FRS-Weighted Allocation"
    
    def calculate_allocation(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Calculate allocations weighted by FRS.
        
        Args:
            forecasts: Dict of symbol -> forecast data
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        if not forecasts:
            return {}
        
        # Filter by FRS and weight by FRS score
        frs_weighted = {}
        
        for symbol, forecast in forecasts.items():
            frs = forecast.get("frs", {}).get("frs_score", 0)
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            
            if frs >= self.min_frs and expected_return > 0:
                # Weight by FRS * expected return
                frs_weighted[symbol] = frs * expected_return
        
        if not frs_weighted:
            return {}
        
        # Normalize
        total_weight = sum(frs_weighted.values())
        if total_weight > 0:
            allocations = {}
            for symbol, weight in frs_weighted.items():
                norm_weight = weight / total_weight
                allocations[symbol] = portfolio_value * norm_weight
            return allocations
        
        return {}


class StrategySelector:
    """Selects and applies strategy templates."""
    
    def __init__(self):
        """Initialize strategy selector."""
        self.strategies = {
            "mean_variance": MeanVarianceStrategy(),
            "trend_following": TrendFollowingStrategy(),
            "reversal": ReversalStrategy(),
            "decay_aware": DecayAwareStrategy(),
            "frs_weighted": FRSWeightedStrategy()
        }
    
    def get_strategy(self, strategy_name: str) -> Optional[StrategyTemplate]:
        """Get strategy by name."""
        return self.strategies.get(strategy_name)
    
    def list_strategies(self) -> List[str]:
        """List available strategies."""
        return list(self.strategies.keys())
    
    def calculate_allocations(
        self,
        strategy_name: str,
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Calculate allocations using specified strategy.
        
        Args:
            strategy_name: Name of strategy to use
            forecasts: Dict of symbol -> forecast data
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            logger.warning(f"Unknown strategy: {strategy_name}")
            return {}
        
        return strategy.calculate_allocation(forecasts, portfolio_value)





