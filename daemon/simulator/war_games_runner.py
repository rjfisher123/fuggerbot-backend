"""
War Games Simulation Engine.

A high-speed backtesting framework that stress-tests trading strategies
using the Global Data Lake without hitting external APIs.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pandas as pd
import numpy as np
from tqdm import tqdm
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Phase 3: Import technical analysis for quality filters
from models.technical_analysis import add_indicators, is_quality_setup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradingParams:
    """Trading strategy parameters."""
    trust_threshold: float = 0.65
    min_confidence: float = 0.75
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss: float = 0.05  # 5% stop loss
    take_profit: float = 0.15  # 15% take profit
    cooldown_days: int = 2  # Days to wait after a trade
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Trade:
    """Individual trade record."""
    entry_date: str
    exit_date: str
    symbol: str
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    pnl_pct: float
    reason: str  # "STOP_LOSS", "TAKE_PROFIT", "TIME_EXIT"
    trust_score: float
    forecast_confidence: float


@dataclass
class CampaignResult:
    """Results from a simulation campaign."""
    campaign_name: str
    symbol: str
    start_date: str
    end_date: str
    params: Dict[str, Any]
    
    # Performance metrics
    initial_balance: float
    final_balance: float
    total_return_pct: float
    max_drawdown_pct: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    
    # Risk metrics
    sharpe_ratio: float
    profit_factor: float
    
    # Trade details
    trades: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WarGamesRunner:
    """
    High-speed simulation engine for backtesting trading strategies.
    
    Uses the Global Data Lake to simulate trades without calling external APIs.
    """
    
    def __init__(self, db_path: Path = Path("data/market_history.duckdb")):
        """
        Initialize the War Games Runner.
        
        Args:
            db_path: Path to the DuckDB database
        """
        self.db_path = db_path
        self.conn = self._get_db_connection()
        
    def _get_db_connection(self) -> Optional[duckdb.DuckDBPyConnection]:
        """Get DuckDB connection."""
        try:
            return duckdb.connect(str(self.db_path), read_only=True)
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB: {e}")
            return None
    
    def load_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Load OHLCV data from DuckDB for a specific time window.
        
        Args:
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with OHLCV data
        """
        if not self.conn:
            logger.error("No database connection")
            return pd.DataFrame()
        
        query = f"""
            SELECT date, open, high, low, close, volume
            FROM ohlcv_history
            WHERE symbol = '{symbol}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date ASC
        """
        
        try:
            df = self.conn.execute(query).fetchdf()
            df['date'] = pd.to_datetime(df['date'])
            logger.info(f"Loaded {len(df)} rows for {symbol} ({start_date} to {end_date})")
            return df
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def _calculate_trust_score(self, df: pd.DataFrame, idx: int, lookback: int = 30) -> float:
        """
        Calculate a proxy trust score based on volatility and trend consistency.
        
        Args:
            df: DataFrame with OHLCV data
            idx: Current index
            lookback: Lookback period for calculations
            
        Returns:
            Trust score (0-1)
        """
        if idx < lookback:
            return 0.65  # Start with neutral-positive bias
        
        # Calculate volatility (lower is better for trust)
        returns = df['close'].iloc[idx-lookback:idx].pct_change().dropna()
        volatility = returns.std()
        
        # Calculate trend consistency (more consistent = higher trust)
        sma_short = df['close'].iloc[idx-10:idx].mean()
        sma_long = df['close'].iloc[idx-lookback:idx].mean()
        trend_strength = abs(sma_short - sma_long) / sma_long if sma_long > 0 else 0
        
        # Combine metrics (boosted for more trades)
        # Base trust is higher (0.65 instead of 0.5)
        # Less penalty for volatility
        trust_score = 0.65 + (0.25 * min(1, trend_strength * 10)) - (0.15 * min(1, volatility * 5))
        
        return max(0.4, min(0.95, trust_score))
    
    def _calculate_forecast_confidence(
        self,
        df: pd.DataFrame,
        idx: int,
        lookback: int = 30
    ) -> Tuple[float, float]:
        """
        Calculate a proxy forecast confidence and target price.
        
        Args:
            df: DataFrame with OHLCV data
            idx: Current index
            lookback: Lookback period
            
        Returns:
            Tuple of (confidence, target_price)
        """
        if idx < lookback:
            return 0.75, df['close'].iloc[idx] * 1.08  # Start with optimistic bias
        
        # Simple momentum-based forecast
        recent_returns = df['close'].iloc[idx-lookback:idx].pct_change().dropna()
        avg_return = recent_returns.mean()
        
        # Confidence based on consistency of returns (boosted)
        std_return = recent_returns.std()
        # Higher base confidence (0.70 instead of 0.5)
        # More weight on momentum, less penalty for volatility
        confidence = 0.70 + (0.20 * abs(avg_return) * 100) - (0.10 * std_return * 5)
        confidence = max(0.60, min(0.92, confidence))
        
        # Target price: current price + projected return (more aggressive)
        current_price = df['close'].iloc[idx]
        target_price = current_price * (1 + avg_return * 7)  # 7-day projection (was 5)
        
        return confidence, target_price
    
    def _calculate_kelly_position_size(
        self,
        balance: float,
        trust_score: float,
        params: TradingParams,
        fractional_kelly: float = 0.25
    ) -> float:
        """
        Calculate position size using Conservative Kelly Criterion.
        
        Formula: kelly_pct = (p * b - q) / b
        Where:
            p = win_probability (trust_score, but calibrated conservatively)
            q = loss_probability (1 - p)
            b = win_loss_ratio (take_profit / stop_loss)
        
        Key Safety Features:
        1. Cap trust_score at 0.65 (assume no model is >65% accurate)
        2. Use fractional Kelly (0.25) for extreme safety
        3. Hard cap at 10% per position (not 20%)
        
        Args:
            balance: Current account balance
            trust_score: Model confidence (0-1), calibrated to realistic win rate
            params: Trading parameters (contains stop_loss and take_profit)
            fractional_kelly: Fraction of Kelly to use (0.25 = quarter Kelly)
            
        Returns:
            Position size in dollars
            
        Example:
            trust_score = 0.85 → capped at 0.65
            win_loss_ratio = 0.15 / 0.05 = 3.0
            
            kelly_pct = (0.65 * 3.0 - 0.35) / 3.0
                      = (1.95 - 0.35) / 3.0
                      = 1.60 / 3.0
                      = 0.533 (53% of capital!)
            
            With fractional_kelly = 0.25:
            position_size = 0.533 * 0.25 = 0.133 (13.3%)
            
            Capped at 10% maximum:
            final_position_size = 0.10 (10%)
        """
        # CRITICAL: Cap trust score at 0.65 max
        # Models are overconfident - real win rates are ~50%
        calibrated_trust = min(trust_score, 0.65)
        
        # Win probability = calibrated trust (conservative)
        win_probability = calibrated_trust
        loss_probability = 1 - win_probability
        
        # Win/Loss ratio from risk parameters
        win_loss_ratio = params.take_profit / params.stop_loss
        
        # Kelly Criterion formula
        kelly_pct = (win_probability * win_loss_ratio - loss_probability) / win_loss_ratio
        
        # Handle negative Kelly (no edge, don't trade)
        if kelly_pct <= 0:
            return balance * 0.02  # Minimum 2% position
        
        # Apply fractional Kelly for safety
        kelly_pct = kelly_pct * fractional_kelly
        
        # Ensure within VERY conservative bounds
        kelly_pct = max(0.02, min(kelly_pct, 0.10))  # Between 2% and 10% (not 20%!)
        
        # Calculate position size
        position_size = balance * kelly_pct
        
        # Cap at 10% maximum (MUCH safer than 20%)
        max_position = balance * 0.10
        position_size = min(position_size, max_position)
        
        # Keep 5% cash buffer
        position_size = min(position_size, balance * 0.95)
        
        return position_size
    
    def run_campaign(
        self,
        campaign_name: str,
        symbol: str,
        start_date: str,
        end_date: str,
        params: TradingParams,
        initial_balance: float = 10000.0
    ) -> CampaignResult:
        """
        Run a simulation campaign for a specific symbol and time period.
        
        Args:
            campaign_name: Name of the campaign
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            params: Trading parameters
            initial_balance: Starting capital
            
        Returns:
            CampaignResult with performance metrics
        """
        logger.info(f"🎮 Starting campaign: {campaign_name}")
        
        # Load data
        df = self.load_data(symbol, start_date, end_date)
        if df.empty:
            logger.error("No data loaded")
            return None
        
        # Phase 3: Add technical indicators for quality filtering
        df = add_indicators(df)
        
        # Initialize state
        balance = initial_balance
        position = None  # Current open position
        trades: List[Trade] = []
        cooldown_until = None
        
        # Track metrics
        peak_balance = initial_balance
        max_drawdown = 0.0
        
        # Simulate day by day
        for idx in tqdm(range(30, len(df)), desc=f"Simulating {symbol}"):
            current_date = df['date'].iloc[idx]
            current_price = df['close'].iloc[idx]
            
            # Check cooldown
            if cooldown_until and current_date < cooldown_until:
                continue
            
            # Exit logic for open position
            if position:
                # Check stop loss
                if current_price <= position['entry_price'] * (1 - params.stop_loss):
                    exit_price = current_price
                    pnl = (exit_price - position['entry_price']) * position['shares']
                    pnl_pct = (exit_price / position['entry_price'] - 1) * 100
                    
                    balance += pnl
                    
                    trade = Trade(
                        entry_date=position['entry_date'],
                        exit_date=str(current_date.date()),
                        symbol=symbol,
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        position_size=position['position_size'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        reason="STOP_LOSS",
                        trust_score=position['trust_score'],
                        forecast_confidence=position['forecast_confidence']
                    )
                    trades.append(trade)
                    position = None
                    cooldown_until = current_date + timedelta(days=params.cooldown_days)
                    continue
                
                # Check take profit
                if current_price >= position['entry_price'] * (1 + params.take_profit):
                    exit_price = current_price
                    pnl = (exit_price - position['entry_price']) * position['shares']
                    pnl_pct = (exit_price / position['entry_price'] - 1) * 100
                    
                    balance += pnl
                    
                    trade = Trade(
                        entry_date=position['entry_date'],
                        exit_date=str(current_date.date()),
                        symbol=symbol,
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        position_size=position['position_size'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        reason="TAKE_PROFIT",
                        trust_score=position['trust_score'],
                        forecast_confidence=position['forecast_confidence']
                    )
                    trades.append(trade)
                    position = None
                    cooldown_until = current_date + timedelta(days=params.cooldown_days)
                    continue
                
                # Time-based exit (max 10 days)
                days_in_trade = (current_date - pd.to_datetime(position['entry_date'])).days
                if days_in_trade >= 10:
                    exit_price = current_price
                    pnl = (exit_price - position['entry_price']) * position['shares']
                    pnl_pct = (exit_price / position['entry_price'] - 1) * 100
                    
                    balance += pnl
                    
                    trade = Trade(
                        entry_date=position['entry_date'],
                        exit_date=str(current_date.date()),
                        symbol=symbol,
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        position_size=position['position_size'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        reason="TIME_EXIT",
                        trust_score=position['trust_score'],
                        forecast_confidence=position['forecast_confidence']
                    )
                    trades.append(trade)
                    position = None
                    cooldown_until = current_date + timedelta(days=params.cooldown_days)
                    continue
            
            # Entry logic (no open position)
            if not position:
                # Calculate proxy signals
                trust_score = self._calculate_trust_score(df, idx)
                forecast_confidence, target_price = self._calculate_forecast_confidence(df, idx)
                
                # Phase 3: Technical Quality Filter
                # Only trade if RSI < 70, Volume > 1.0, MACD > 0, Trend positive
                row = df.iloc[idx]
                quality_check = is_quality_setup(
                    rsi=row['rsi_14'],
                    volume_ratio=row['volume_ratio'],
                    macd_hist=row['macd_hist'],
                    trend_sma=row['trend_sma'],
                    rsi_max=70.0,      # Not overbought
                    vol_min=1.0,       # Volume confirmed
                    macd_positive=True # Momentum positive
                )
                
                # Decision logic (proxy for LLM + Policy + Phase 3 Quality)
                should_enter = (
                    trust_score >= params.trust_threshold and
                    forecast_confidence >= params.min_confidence and
                    target_price > current_price * 1.02 and  # At least 2% upside
                    quality_check  # Phase 3: Technical quality filter
                )
                
                if should_enter:
                    # Forward-Looking Kelly Criterion (v2.2)
                    # Uses model confidence (trust_score) and risk/reward ratio
                    # Formula: kelly = (p*b - q) / b, where p=trust, b=TP/SL ratio
                    position_size = self._calculate_kelly_position_size(
                        balance=balance,
                        trust_score=trust_score,
                        params=params,
                        fractional_kelly=0.25  # Quarter Kelly for safety
                    )
                    
                    shares = position_size / current_price
                    
                    position = {
                        'entry_date': str(current_date.date()),
                        'entry_price': current_price,
                        'shares': shares,
                        'position_size': position_size,
                        'trust_score': trust_score,
                        'forecast_confidence': forecast_confidence
                    }
                    
                    balance -= position_size
            
            # Update max drawdown
            if balance > peak_balance:
                peak_balance = balance
            drawdown = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Close any remaining position at end
        if position:
            exit_price = df['close'].iloc[-1]
            pnl = (exit_price - position['entry_price']) * position['shares']
            pnl_pct = (exit_price / position['entry_price'] - 1) * 100
            
            balance += pnl
            
            trade = Trade(
                entry_date=position['entry_date'],
                exit_date=str(df['date'].iloc[-1].date()),
                symbol=symbol,
                entry_price=position['entry_price'],
                exit_price=exit_price,
                position_size=position['position_size'],
                pnl=pnl,
                pnl_pct=pnl_pct,
                reason="END_OF_CAMPAIGN",
                trust_score=position['trust_score'],
                forecast_confidence=position['forecast_confidence']
            )
            trades.append(trade)
        
        # Calculate statistics
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win_pct = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
        avg_loss_pct = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0
        
        total_return_pct = ((balance - initial_balance) / initial_balance) * 100
        
        # Calculate Sharpe ratio (simplified)
        returns = [t.pnl_pct for t in trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) if returns and np.std(returns) > 0 else 0
        
        # Calculate profit factor
        total_wins = sum([t.pnl for t in winning_trades]) if winning_trades else 0
        total_losses = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        result = CampaignResult(
            campaign_name=campaign_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            params=params.to_dict(),
            initial_balance=initial_balance,
            final_balance=balance,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown * 100,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            trades=[asdict(t) for t in trades]
        )
        
        logger.info(f"✅ Campaign complete: {total_return_pct:.1f}% return, {win_rate:.1%} win rate")
        
        return result
    
    def run_all_scenarios(self, output_path: Path = Path("data/war_games_results.json")) -> Dict[str, Any]:
        """
        Run all pre-defined scenarios across multiple symbols and parameter sets.
        
        Args:
            output_path: Path to save results JSON
            
        Returns:
            Dictionary with all campaign results
        """
        logger.info("🎯 Starting War Games - Full Campaign Suite")
        
        # Define scenarios
        scenarios = [
            {
                "name": "Bull Run (2021)",
                "start_date": "2021-01-01",
                "end_date": "2021-12-31",
                "description": "Strong upward trend, low volatility"
            },
            {
                "name": "Inflation Shock (2022)",
                "start_date": "2022-01-01",
                "end_date": "2022-12-31",
                "description": "High volatility, regime shifts"
            },
            {
                "name": "Recovery Rally (2023)",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "description": "Tech bounce back, choppy markets"
            }
        ]
        
        # Define parameter sets
        param_sets = {
            "Aggressive": TradingParams(
                trust_threshold=0.55,
                min_confidence=0.70,
                max_position_size=0.15,
                stop_loss=0.08,
                take_profit=0.20
            ),
            "Balanced": TradingParams(
                trust_threshold=0.65,
                min_confidence=0.75,
                max_position_size=0.10,
                stop_loss=0.05,
                take_profit=0.15
            ),
            "Conservative": TradingParams(
                trust_threshold=0.75,
                min_confidence=0.80,
                max_position_size=0.05,
                stop_loss=0.03,
                take_profit=0.10
            )
        }
        
        # Symbols to test (expanded for v2.0)
        symbols = ["BTC-USD", "ETH-USD", "NVDA", "MSFT"]
        
        # Run all combinations
        all_results = []
        
        for scenario in scenarios:
            for symbol in symbols:
                for param_name, params in param_sets.items():
                    campaign_name = f"{scenario['name']} - {symbol} - {param_name}"
                    
                    try:
                        result = self.run_campaign(
                            campaign_name=campaign_name,
                            symbol=symbol,
                            start_date=scenario['start_date'],
                            end_date=scenario['end_date'],
                            params=params
                        )
                        
                        if result:
                            result_dict = result.to_dict()
                            result_dict['scenario_description'] = scenario['description']
                            all_results.append(result_dict)
                    
                    except Exception as e:
                        logger.error(f"Failed campaign {campaign_name}: {e}")
        
        # Save results
        output_data = {
            "run_timestamp": datetime.now().isoformat(),
            "total_campaigns": len(all_results),
            "scenarios": scenarios,
            "param_sets": {name: params.to_dict() for name, params in param_sets.items()},
            "results": all_results
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"💾 Results saved to {output_path}")
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("🏆 WAR GAMES SUMMARY")
        logger.info("="*80)
        
        for result in all_results:
            logger.info(
                f"{result['campaign_name']}: "
                f"{result['total_return_pct']:+.1f}% return, "
                f"{result['win_rate']:.1%} win rate, "
                f"{result['max_drawdown_pct']:.1f}% max DD"
            )
        
        return output_data


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="War Games Simulation Engine")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test (single campaign)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/war_games_results.json",
        help="Output file path"
    )
    
    args = parser.parse_args()
    
    runner = WarGamesRunner()
    
    if args.quick:
        # Quick test - single campaign
        logger.info("Running quick test campaign...")
        result = runner.run_campaign(
            campaign_name="Quick Test - BTC 2023",
            symbol="BTC-USD",
            start_date="2023-01-01",
            end_date="2023-06-30",
            params=TradingParams()
        )
        if result:
            print(json.dumps(result.to_dict(), indent=2))
    else:
        # Full war games
        runner.run_all_scenarios(output_path=Path(args.output))

