"""
Portfolio Construction Layer.

Multi-symbol allocation with MCR, correlation awareness, volatility scaling, and capital constraints.
"""
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class PortfolioConstructor:
    """Constructs optimal portfolios with risk management."""
    
    def __init__(
        self,
        max_position_size: float = 0.10,  # 10% max per position
        max_portfolio_risk: float = 0.20,  # 20% max portfolio risk
        correlation_threshold: float = 0.7  # High correlation threshold
    ):
        """
        Initialize portfolio constructor.
        
        Args:
            max_position_size: Maximum position size as fraction
            max_portfolio_risk: Maximum portfolio risk
            correlation_threshold: Correlation threshold for diversification
        """
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.correlation_threshold = correlation_threshold
    
    def calculate_marginal_contribution_to_risk(
        self,
        symbol: str,
        portfolio_weights: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        volatilities: Dict[str, float]
    ) -> float:
        """
        Calculate Marginal Contribution to Risk (MCR) for a symbol.
        
        Args:
            symbol: Trading symbol
            portfolio_weights: Current portfolio weights
            covariance_matrix: Symbol covariance matrix
            volatilities: Symbol volatilities
            
        Returns:
            MCR value
        """
        if symbol not in portfolio_weights or portfolio_weights[symbol] == 0:
            return 0.0
        
        # Calculate portfolio variance
        portfolio_variance = 0.0
        for sym1, w1 in portfolio_weights.items():
            for sym2, w2 in portfolio_weights.items():
                if sym1 in covariance_matrix and sym2 in covariance_matrix[sym1]:
                    portfolio_variance += w1 * w2 * covariance_matrix[sym1][sym2]
        
        if portfolio_variance <= 0:
            return 0.0
        
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Calculate MCR: partial derivative of portfolio risk w.r.t. symbol weight
        mcr_numerator = 0.0
        for sym, w in portfolio_weights.items():
            if sym in covariance_matrix and symbol in covariance_matrix[sym]:
                mcr_numerator += w * covariance_matrix[sym][symbol]
        
        mcr = (mcr_numerator / portfolio_volatility) if portfolio_volatility > 0 else 0.0
        
        return float(mcr)
    
    def build_correlation_aware_portfolio(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        portfolio_value: float = 100000.0
    ) -> Dict[str, float]:
        """
        Build portfolio with correlation awareness.
        
        Args:
            forecasts: Dict of symbol -> forecast data
            correlation_matrix: Optional correlation matrix
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        if not forecasts:
            return {}
        
        # Filter symbols by quality
        candidate_symbols = []
        for symbol, forecast in forecasts.items():
            frs = forecast.get("frs", {}).get("frs_score", 0)
            rec = forecast.get("recommendation", {})
            expected_return = rec.get("expected_return_pct", 0)
            
            if frs >= 0.6 and expected_return > 0:
                candidate_symbols.append(symbol)
        
        if not candidate_symbols:
            return {}
        
        # If no correlation matrix, use simple diversification
        if not correlation_matrix:
            return self._simple_equal_weight(candidate_symbols, forecasts, portfolio_value)
        
        # Build portfolio avoiding high correlations
        selected_symbols = []
        allocations = {}
        
        for symbol in candidate_symbols:
            # Check correlation with already selected symbols
            is_diversified = True
            
            for selected_symbol in selected_symbols:
                if (selected_symbol in correlation_matrix and 
                    symbol in correlation_matrix[selected_symbol]):
                    correlation = correlation_matrix[selected_symbol][symbol]
                    if abs(correlation) > self.correlation_threshold:
                        is_diversified = False
                        break
            
            if is_diversified:
                selected_symbols.append(symbol)
                # Allocate based on expected return and risk
                rec = forecasts[symbol].get("recommendation", {})
                expected_return = rec.get("expected_return_pct", 0)
                risk = rec.get("risk_pct", 1.0)
                
                # Weight by Sharpe-like ratio
                sharpe_ratio = expected_return / risk if risk > 0 else 0
                allocations[symbol] = sharpe_ratio
        
        # Normalize and apply position size limits
        total_weight = sum(allocations.values())
        if total_weight > 0:
            final_allocations = {}
            for symbol, weight in allocations.items():
                normalized_weight = weight / total_weight
                # Apply max position size constraint
                normalized_weight = min(normalized_weight, self.max_position_size)
                final_allocations[symbol] = portfolio_value * normalized_weight
            return final_allocations
        
        return {}
    
    def volatility_scaled_allocation(
        self,
        forecasts: Dict[str, Dict[str, Any]],
        target_volatility: float = 0.15,  # 15% target portfolio volatility
        portfolio_value: float = 100000.0
    ) -> Dict[str, float]:
        """
        Allocate with volatility scaling to target portfolio volatility.
        
        Args:
            forecasts: Dict of symbol -> forecast data
            target_volatility: Target portfolio volatility
            portfolio_value: Total portfolio value
            
        Returns:
            Dict of symbol -> position value
        """
        if not forecasts:
            return {}
        
        # Extract volatilities and expected returns
        symbol_data = {}
        for symbol, forecast in forecasts.items():
            rec = forecast.get("recommendation", {})
            risk_pct = rec.get("risk_pct", 0) / 100.0  # Convert to fraction
            expected_return = rec.get("expected_return_pct", 0)
            frs = forecast.get("frs", {}).get("fqs_score", 0)
            
            if risk_pct > 0 and expected_return > 0 and frs >= 0.6:
                symbol_data[symbol] = {
                    "volatility": risk_pct,
                    "expected_return": expected_return,
                    "frs": frs
                }
        
        if not symbol_data:
            return {}
        
        # Calculate inverse volatility weights (lower vol = higher weight)
        inv_vol_weights = {}
        for symbol, data in symbol_data.items():
            inv_vol_weights[symbol] = (1.0 / data["volatility"]) * data["frs"]
        
        # Normalize
        total_inv_vol = sum(inv_vol_weights.values())
        if total_inv_vol > 0:
            normalized_weights = {
                sym: w / total_inv_vol for sym, w in inv_vol_weights.items()
            }
        else:
            return {}
        
        # Scale to target volatility
        # Calculate current portfolio volatility
        portfolio_vol = np.sqrt(
            sum(w**2 * symbol_data[sym]["volatility"]**2 
                for sym, w in normalized_weights.items())
        )
        
        if portfolio_vol > 0:
            scale_factor = target_volatility / portfolio_vol
        else:
            scale_factor = 1.0
        
        # Apply scaling and position size limits
        allocations = {}
        for symbol, weight in normalized_weights.items():
            scaled_weight = weight * scale_factor
            # Apply max position size
            scaled_weight = min(scaled_weight, self.max_position_size)
            allocations[symbol] = portfolio_value * scaled_weight
        
        return allocations
    
    def apply_capital_constraints(
        self,
        allocations: Dict[str, float],
        available_capital: float,
        min_position_size: float = 100.0
    ) -> Dict[str, float]:
        """
        Apply capital constraints to allocations.
        
        Args:
            allocations: Proposed allocations
            available_capital: Available capital
            min_position_size: Minimum position size
            
        Returns:
            Constrained allocations
        """
        if not allocations:
            return {}
        
        total_requested = sum(allocations.values())
        
        if total_requested <= available_capital:
            # All allocations fit
            return allocations
        
        # Scale down proportionally
        scale_factor = available_capital / total_requested
        
        constrained = {}
        for symbol, allocation in allocations.items():
            scaled_allocation = allocation * scale_factor
            if scaled_allocation >= min_position_size:
                constrained[symbol] = scaled_allocation
        
        return constrained
    
    def _simple_equal_weight(
        self,
        symbols: List[str],
        forecasts: Dict[str, Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Simple equal-weight allocation."""
        if not symbols:
            return {}
        
        weight_per_symbol = 1.0 / len(symbols)
        weight_per_symbol = min(weight_per_symbol, self.max_position_size)
        
        allocations = {}
        for symbol in symbols:
            allocations[symbol] = portfolio_value * weight_per_symbol
        
        return allocations











