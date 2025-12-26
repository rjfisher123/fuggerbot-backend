"""
Portfolio Backtesting.

Equity curve, drawdown, Sharpe/Sortino, turnover metrics.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PortfolioBacktester:
    """Backtests portfolio strategies."""
    
    def __init__(self, initial_capital: float = 100000.0):
        """
        Initialize portfolio backtester.
        
        Args:
            initial_capital: Starting capital
        """
        self.initial_capital = initial_capital
    
    def run_backtest(
        self,
        trades: List[Dict[str, Any]],
        prices: Dict[str, List[Dict[str, Any]]],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Run portfolio backtest.
        
        Args:
            trades: List of trade records
            prices: Dict of symbol -> price history
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Backtest results
        """
        # Initialize portfolio
        portfolio_value = self.initial_capital
        positions: Dict[str, float] = {}  # symbol -> shares
        cash = self.initial_capital
        
        # Track equity curve
        equity_curve = []
        dates = []
        
        # Process trades chronologically
        sorted_trades = sorted(trades, key=lambda x: x.get("timestamp", ""))
        
        current_date = start_date
        trade_idx = 0
        
        while current_date <= end_date:
            # Execute trades for this date
            while (trade_idx < len(sorted_trades) and 
                   datetime.fromisoformat(sorted_trades[trade_idx].get("timestamp", "")) <= current_date):
                trade = sorted_trades[trade_idx]
                symbol = trade.get("symbol")
                action = trade.get("action")
                shares = trade.get("shares", 0)
                price = trade.get("price", 0)
                
                if symbol and price > 0:
                    if action == "BUY":
                        cost = shares * price
                        if cost <= cash:
                            cash -= cost
                            positions[symbol] = positions.get(symbol, 0) + shares
                    elif action == "SELL":
                        if symbol in positions and positions[symbol] >= shares:
                            proceeds = shares * price
                            cash += proceeds
                            positions[symbol] -= shares
                            if positions[symbol] <= 0:
                                del positions[symbol]
                
                trade_idx += 1
            
            # Calculate portfolio value
            portfolio_value = cash
            for symbol, shares in positions.items():
                if symbol in prices:
                    # Get price for this date
                    price = self._get_price_for_date(prices[symbol], current_date)
                    if price:
                        portfolio_value += shares * price
            
            equity_curve.append(portfolio_value)
            dates.append(current_date)
            
            # Move to next day
            current_date += timedelta(days=1)
        
        # Calculate metrics
        equity_array = np.array(equity_curve)
        returns = np.diff(equity_array) / equity_array[:-1]
        
        results = {
            "equity_curve": equity_curve,
            "dates": [d.isoformat() for d in dates],
            "final_value": float(equity_curve[-1]) if equity_curve else self.initial_capital,
            "total_return": float((equity_curve[-1] - self.initial_capital) / self.initial_capital * 100) if equity_curve else 0.0,
            "sharpe_ratio": self._calculate_sharpe(returns),
            "sortino_ratio": self._calculate_sortino(returns),
            "max_drawdown": self._calculate_max_drawdown(equity_curve),
            "drawdown_curve": self._calculate_drawdown_curve(equity_curve),
            "turnover": self._calculate_turnover(trades, start_date, end_date),
            "win_rate": self._calculate_win_rate(trades),
            "average_win": self._calculate_average_win(trades),
            "average_loss": self._calculate_average_loss(trades)
        }
        
        return results
    
    def _get_price_for_date(
        self,
        price_history: List[Dict[str, Any]],
        target_date: datetime
    ) -> Optional[float]:
        """Get price for a specific date."""
        # Find closest price before or on target date
        best_price = None
        best_date_diff = None
        
        for price_point in price_history:
            price_date_str = price_point.get("date", "")
            if not price_date_str:
                continue
            
            try:
                price_date = datetime.fromisoformat(price_date_str.replace("Z", "+00:00"))
                date_diff = abs((target_date - price_date.replace(tzinfo=None)).days)
                
                if price_date <= target_date.replace(tzinfo=None):
                    if best_date_diff is None or date_diff < best_date_diff:
                        best_date_diff = date_diff
                        best_price = price_point.get("price")
            except:
                continue
        
        return best_price
    
    def _calculate_sharpe(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        if np.std(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        return float(sharpe)
    
    def _calculate_sortino(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio (downside deviation only)."""
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)
        return float(sortino)
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown."""
        if not equity_curve:
            return 0.0
        
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = abs(np.min(drawdown)) * 100  # As percentage
        
        return float(max_drawdown)
    
    def _calculate_drawdown_curve(self, equity_curve: List[float]) -> List[float]:
        """Calculate drawdown curve."""
        if not equity_curve:
            return []
        
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = ((equity_array - running_max) / running_max) * 100
        
        return drawdown.tolist()
    
    def _calculate_turnover(
        self,
        trades: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate portfolio turnover."""
        if not trades:
            return 0.0
        
        total_trade_value = sum(abs(t.get("value", 0)) for t in trades)
        days = (end_date - start_date).days
        
        if days == 0:
            return 0.0
        
        # Annualized turnover
        daily_turnover = total_trade_value / (self.initial_capital * days)
        annualized_turnover = daily_turnover * 252
        
        return float(annualized_turnover)
    
    def _calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate win rate from trades."""
        if not trades:
            return 0.0
        
        # Would need P/L data from trades
        # For now, use entry/exit price difference as proxy
        profitable_trades = 0
        total_trades = 0
        
        for trade in trades:
            if "entry_price" in trade and "exit_price" in trade:
                total_trades += 1
                if trade["exit_price"] > trade["entry_price"]:
                    profitable_trades += 1
        
        if total_trades == 0:
            return 0.0
        
        return float(profitable_trades / total_trades * 100)
    
    def _calculate_average_win(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average winning trade."""
        wins = []
        
        for trade in trades:
            if "entry_price" in trade and "exit_price" in trade:
                pnl_pct = ((trade["exit_price"] - trade["entry_price"]) / trade["entry_price"]) * 100
                if pnl_pct > 0:
                    wins.append(pnl_pct)
        
        return float(np.mean(wins)) if wins else 0.0
    
    def _calculate_average_loss(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average losing trade."""
        losses = []
        
        for trade in trades:
            if "entry_price" in trade and "exit_price" in trade:
                pnl_pct = ((trade["exit_price"] - trade["entry_price"]) / trade["entry_price"]) * 100
                if pnl_pct < 0:
                    losses.append(pnl_pct)
        
        return float(np.mean(losses)) if losses else 0.0
    
    def generate_equity_curve_plot(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data for equity curve plot."""
        return {
            "dates": results.get("dates", []),
            "equity": results.get("equity_curve", []),
            "drawdown": results.get("drawdown_curve", [])
        }











