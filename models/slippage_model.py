"""
Slippage Modeling.

Estimates execution costs based on bid-ask spread, market volatility, and symbol liquidity.
"""
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SlippageModel:
    """Models execution slippage."""
    
    def __init__(
        self,
        base_slippage_bps: float = 5.0  # 5 basis points base slippage
    ):
        """
        Initialize slippage model.
        
        Args:
            base_slippage_bps: Base slippage in basis points
        """
        self.base_slippage_bps = base_slippage_bps
    
    def estimate_slippage(
        self,
        symbol: str,
        order_size: float,
        current_price: float,
        bid_ask_spread: Optional[float] = None,
        market_volatility: Optional[float] = None,
        liquidity_score: Optional[float] = None,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """
        Estimate slippage for an order.
        
        Args:
            symbol: Trading symbol
            order_size: Order size in shares
            current_price: Current market price
            bid_ask_spread: Bid-ask spread (as fraction, e.g., 0.001 = 0.1%)
            market_volatility: Market volatility (annualized, e.g., 0.20 = 20%)
            liquidity_score: Liquidity score (0-1, higher = more liquid)
            order_type: Order type (MARKET, LIMIT, etc.)
            
        Returns:
            Dict with slippage estimates
        """
        # Base slippage
        base_slippage = self.base_slippage_bps / 10000.0  # Convert bps to fraction
        
        # Bid-ask spread component (half spread for market orders)
        if bid_ask_spread is None:
            # Estimate from symbol characteristics
            bid_ask_spread = self._estimate_spread(symbol, current_price)
        
        spread_slippage = bid_ask_spread / 2.0 if order_type == "MARKET" else 0.0
        
        # Volatility component (higher vol = more slippage)
        if market_volatility is None:
            market_volatility = 0.20  # Default 20% annualized
        
        # Convert to daily volatility
        daily_vol = market_volatility / np.sqrt(252)
        volatility_slippage = daily_vol * 0.5  # Scale factor
        
        # Liquidity component (lower liquidity = more slippage)
        if liquidity_score is None:
            liquidity_score = self._estimate_liquidity(symbol, order_size, current_price)
        
        # Inverse liquidity: lower score = higher slippage
        liquidity_slippage = (1.0 - liquidity_score) * 0.002  # Max 20 bps
        
        # Size impact (larger orders = more slippage)
        order_value = order_size * current_price
        size_impact = self._calculate_size_impact(order_value, symbol)
        
        # Total slippage
        total_slippage = (
            base_slippage +
            spread_slippage +
            volatility_slippage +
            liquidity_slippage +
            size_impact
        )
        
        # Clamp to reasonable range (0-2%)
        total_slippage = min(0.02, max(0.0, total_slippage))
        
        # Calculate expected execution price
        if order_type == "MARKET":
            # Market orders: pay slippage
            execution_price = current_price * (1.0 + total_slippage)
        else:
            # Limit orders: no slippage if filled
            execution_price = current_price
        
        # Estimate execution cost
        execution_cost = order_size * current_price * total_slippage
        
        return {
            "slippage_bps": float(total_slippage * 10000),
            "slippage_pct": float(total_slippage * 100),
            "execution_price": float(execution_price),
            "execution_cost": float(execution_cost),
            "components": {
                "base_slippage": float(base_slippage * 10000),
                "spread_slippage": float(spread_slippage * 10000),
                "volatility_slippage": float(volatility_slippage * 10000),
                "liquidity_slippage": float(liquidity_slippage * 10000),
                "size_impact": float(size_impact * 10000)
            },
            "order_type": order_type
        }
    
    def _estimate_spread(self, symbol: str, price: float) -> float:
        """
        Estimate bid-ask spread for a symbol.
        
        Args:
            symbol: Trading symbol
            price: Current price
            
        Returns:
            Estimated spread as fraction
        """
        # Simplified estimation based on price level
        # Higher priced stocks typically have tighter spreads
        if price > 100:
            return 0.0005  # 5 bps for high-priced stocks
        elif price > 10:
            return 0.001  # 10 bps for mid-priced stocks
        else:
            return 0.002  # 20 bps for low-priced stocks
    
    def _estimate_liquidity(
        self,
        symbol: str,
        order_size: float,
        current_price: float
    ) -> float:
        """
        Estimate liquidity score for a symbol.
        
        Args:
            symbol: Trading symbol
            order_size: Order size in shares
            current_price: Current price
            
        Returns:
            Liquidity score (0-1)
        """
        # Simplified liquidity estimation
        # In production, would use actual volume/ADV data
        
        order_value = order_size * current_price
        
        # Large cap stocks (assumed from symbol patterns)
        large_caps = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA"]
        if symbol in large_caps:
            base_liquidity = 0.9
        else:
            base_liquidity = 0.7
        
        # Adjust for order size (larger orders = lower liquidity score)
        if order_value > 100000:
            size_penalty = 0.1
        elif order_value > 50000:
            size_penalty = 0.05
        else:
            size_penalty = 0.0
        
        liquidity_score = max(0.0, min(1.0, base_liquidity - size_penalty))
        
        return liquidity_score
    
    def _calculate_size_impact(self, order_value: float, symbol: str) -> float:
        """
        Calculate size impact on slippage.
        
        Args:
            order_value: Order value in dollars
            symbol: Trading symbol
            
        Returns:
            Size impact as fraction
        """
        # Simplified size impact model
        # Larger orders have more impact
        
        if order_value < 10000:
            return 0.0
        elif order_value < 50000:
            return 0.0001  # 1 bp
        elif order_value < 100000:
            return 0.0002  # 2 bps
        elif order_value < 500000:
            return 0.0005  # 5 bps
        else:
            return 0.001  # 10 bps


class SlippageAwareExecution:
    """Execution logic with slippage awareness."""
    
    def __init__(self, slippage_model: Optional[SlippageModel] = None):
        """
        Initialize slippage-aware execution.
        
        Args:
            slippage_model: Optional slippage model
        """
        self.slippage_model = slippage_model or SlippageModel()
    
    def adjust_order_for_slippage(
        self,
        symbol: str,
        target_shares: float,
        current_price: float,
        order_type: str = "MARKET"
    ) -> Dict[str, Any]:
        """
        Adjust order size/price for expected slippage.
        
        Args:
            symbol: Trading symbol
            target_shares: Target number of shares
            current_price: Current market price
            order_type: Order type
            
        Returns:
            Dict with adjusted order parameters
        """
        # Estimate slippage
        slippage_estimate = self.slippage_model.estimate_slippage(
            symbol=symbol,
            order_size=target_shares,
            current_price=current_price,
            order_type=order_type
        )
        
        # Adjust order if slippage is high
        if slippage_estimate["slippage_pct"] > 0.5:  # > 50 bps
            # Consider splitting order or using limit order
            recommended_order_type = "LIMIT"
            limit_price = current_price * 1.001  # 10 bps above market
        else:
            recommended_order_type = order_type
            limit_price = None
        
        return {
            "original_shares": target_shares,
            "adjusted_shares": target_shares,  # Could reduce for large orders
            "recommended_order_type": recommended_order_type,
            "limit_price": limit_price,
            "expected_slippage": slippage_estimate,
            "total_cost": target_shares * current_price + slippage_estimate["execution_cost"]
        }










