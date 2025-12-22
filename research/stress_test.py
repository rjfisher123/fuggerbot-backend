#!/usr/bin/env python3
"""
High-Speed Backtester for FuggerBot Pipeline.

Simulates the complete FuggerBot trading pipeline over deep historical data
to evaluate performance metrics without making real API calls.
"""
import sys
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.tsfm.inference import ChronosInferenceEngine
from models.tsfm.schemas import ForecastInput
from models.trust.filter import TrustFilter
from engine.orchestrator import TradeOrchestrator
from config.universe import FULL_TEST_SUITE, ASSET_CLASSES

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STRESS_TEST - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StressTester")

# Configuration
WINDOW_SIZE = 64  # hours of context for forecast
STEP_SIZE = 24    # hours between tests (daily)
HORIZON = 24      # hours ahead to check outcome
MIN_DATA_POINTS = 100  # minimum data points required
RESULTS_PATH = "data/stress_test_results.csv"


class StressTester:
    """High-speed backtester for FuggerBot pipeline."""
    
    def __init__(self):
        """Initialize stress tester with TSFM, Trust Filter, and Orchestrator."""
        logger.info("Initializing StressTester...")
        
        # Initialize components
        self.tsfm = ChronosInferenceEngine(model_name="amazon/chronos-t5-tiny")
        self.trust_filter = TrustFilter()
        
        # Initialize orchestrator (for find_precedents logic)
        # Don't initialize broker for backtesting
        self.orchestrator = TradeOrchestrator(
            trust_threshold=0.6
        )
        
        # Results storage
        self.trades = []
        
        logger.info("✅ StressTester initialized")
    
    def _parse_precedent_summary(self, precedent_text: str) -> Dict[str, Any]:
        """
        Parse precedent summary string to extract win rate.
        
        Example: "Found 3 matching setups from 2023: 2 Wins, 1 Loss"
        Returns: {"wins": 2, "losses": 1, "win_rate": 0.667}
        """
        result = {
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "found_precedents": False
        }
        
        if not precedent_text or "No historical precedents" in precedent_text:
            return result
        
        # Extract win/loss counts
        # Pattern: "Found X matching setups from Y: W Wins, L Loss"
        match = re.search(r'(\d+)\s+Wins[,\s]+(\d+)\s+Loss', precedent_text)
        if match:
            wins = int(match.group(1))
            losses = int(match.group(2))
            total = wins + losses
            result = {
                "wins": wins,
                "losses": losses,
                "win_rate": wins / total if total > 0 else 0.0,
                "found_precedents": True
            }
        
        return result
    
    def _proxy_llm_decision(
        self,
        trust_score: float,
        precedent_summary: str
    ) -> bool:
        """
        Proxy LLM logic: Decide if we should trade.
        
        Logic: IF trust_score > 0.8 AND historical_win_rate > 0.55: TRADE = TRUE
        
        Args:
            trust_score: Trust score from trust filter
            precedent_summary: Precedent summary string from find_precedents
        
        Returns:
            True if should trade, False otherwise
        """
        # Parse precedent summary
        precedent_data = self._parse_precedent_summary(precedent_summary)
        historical_win_rate = precedent_data.get("win_rate", 0.0)
        
        # Decision logic
        if trust_score > 0.8 and historical_win_rate > 0.55:
            return True
        
        # Fallback: if no precedents but trust is very high
        if not precedent_data["found_precedents"] and trust_score > 0.9:
            return True
        
        return False
    
    def run_test(
        self,
        symbol: str,
        start_date: str = "2020-01-01"
    ) -> Dict[str, Any]:
        """
        Run stress test for a single symbol.
        
        Args:
            symbol: Trading symbol to test
            start_date: Start date for backtest (default: "2020-01-01")
        
        Returns:
            Dictionary with test results
        """
        logger.info(f"🔍 Running stress test for {symbol} from {start_date}...")
        
        try:
            import yfinance as yf
            
            # Fetch hourly data
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, interval="1h", progress=False)
            
            if df.empty:
                logger.warning(f"⚠️ No data for {symbol}")
                return {
                    "symbol": symbol,
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "error": "No data"
                }
            
            # Clean data
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if 'Close' not in df.columns:
                if 'Adj Close' in df.columns:
                    df['Close'] = df['Adj Close']
                else:
                    logger.error(f"❌ No Close column for {symbol}")
                    return {"symbol": symbol, "error": "No Close column"}
            
            df = df[['Close']].dropna()
            
            if len(df) < MIN_DATA_POINTS + HORIZON:
                logger.warning(f"⚠️ Insufficient data for {symbol}: {len(df)} points")
                return {
                    "symbol": symbol,
                    "total_trades": 0,
                    "error": "Insufficient data"
                }
            
            logger.info(f"✅ Fetched {len(df)} data points for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e)}
        
        # Sliding window through history
        prices = df['Close'].values
        symbol_trades = []
        
        start_idx = WINDOW_SIZE
        end_idx = len(prices) - HORIZON
        
        logger.info(f"🔄 Processing {end_idx - start_idx} time windows for {symbol}...")
        
        for i in tqdm(range(start_idx, end_idx, STEP_SIZE), desc=f"Testing {symbol}"):
            try:
                # Extract window
                window_prices = prices[i - WINDOW_SIZE:i]
                current_price = float(window_prices[-1])
                
                # Check if we have future data
                if i + HORIZON >= len(prices):
                    continue
                
                future_price = float(prices[i + HORIZON])
                
                # Calculate volatility
                returns = np.diff(window_prices) / window_prices[:-1]
                volatility = float(np.std(returns) * np.sqrt(24))  # Annualized
                historical_volatility = float(np.std(returns) * np.sqrt(24)) if len(returns) > 0 else 0.0
                
                # Run forecast (use num_samples=10 for speed)
                try:
                    forecast_input = ForecastInput(
                        series=window_prices.tolist(),
                        forecast_horizon=HORIZON,
                        context_length=None,
                        metadata={"symbol": symbol, "timestamp": df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i])}
                    )
                    
                    forecast_output = self.tsfm.forecast(forecast_input, num_samples=10)
                    
                except Exception as e:
                    logger.debug(f"Forecast failed at index {i} for {symbol}: {e}")
                    continue
                
                # Run trust filter
                try:
                    trust_evaluation = self.trust_filter.evaluate(
                        forecast=forecast_output,
                        input_data=forecast_input,
                        symbol=symbol,
                        current_volatility=volatility,
                        historical_volatility=historical_volatility
                    )
                    
                    trust_score = trust_evaluation.metrics.overall_trust_score
                    
                except Exception as e:
                    logger.debug(f"Trust evaluation failed at index {i} for {symbol}: {e}")
                    continue
                
                # Proxy LLM Logic: Use find_precedents
                try:
                    volatility_state = "High" if volatility > 0.3 else "Normal" if volatility > 0.15 else "Low"
                    forecast_confidence = 1.0 - (
                        np.mean(np.array(forecast_output.upper_bound) - np.array(forecast_output.lower_bound))
                        / np.mean(forecast_output.point_forecast)
                    ) if np.mean(forecast_output.point_forecast) > 0 else 0.5
                    
                    precedent_summary = self.orchestrator.find_precedents(
                        current_volatility=volatility,
                        trust_score=trust_score,
                        forecast_confidence=forecast_confidence,
                        volatility_state=volatility_state,
                        symbol=symbol
                    )
                    
                    # Proxy LLM decision
                    should_trade = self._proxy_llm_decision(trust_score, precedent_summary)
                    
                except Exception as e:
                    logger.debug(f"Precedent lookup failed at index {i} for {symbol}: {e}")
                    should_trade = False
                
                # If should trade, record outcome
                if should_trade:
                    # Calculate outcome (look ahead 24h)
                    pnl_pct = ((future_price - current_price) / current_price) * 100
                    is_win = pnl_pct > 0
                    
                    trade_record = {
                        "symbol": symbol,
                        "timestamp": df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i]),
                        "current_price": float(current_price),
                        "future_price": float(future_price),
                        "pnl_pct": float(pnl_pct),
                        "is_win": is_win,
                        "trust_score": float(trust_score),
                        "volatility": float(volatility),
                        "forecast_target": float(np.mean(forecast_output.point_forecast)),
                        "precedent_win_rate": self._parse_precedent_summary(precedent_summary).get("win_rate", 0.0)
                    }
                    
                    symbol_trades.append(trade_record)
                    self.trades.append(trade_record)
            
            except Exception as e:
                logger.debug(f"Error processing index {i} for {symbol}: {e}")
                continue
        
        # Calculate metrics
        if not symbol_trades:
            logger.warning(f"⚠️ No trades executed for {symbol}")
            return {
                "symbol": symbol,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }
        
        trades_df = pd.DataFrame(symbol_trades)
        wins = len(trades_df[trades_df["is_win"] == True])
        losses = len(trades_df[trades_df["is_win"] == False])
        win_rate = wins / len(trades_df) if len(trades_df) > 0 else 0.0
        
        # Calculate PnL metrics
        pnl_series = trades_df["pnl_pct"]
        total_pnl = float(pnl_series.sum())
        
        # Sharpe Ratio (annualized)
        if len(pnl_series) > 1:
            sharpe_ratio = float(np.mean(pnl_series) / np.std(pnl_series) * np.sqrt(252)) if np.std(pnl_series) > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max Drawdown
        cumulative = pnl_series.cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = float(abs(drawdown.min())) if len(drawdown) > 0 else 0.0
        
        results = {
            "symbol": symbol,
            "total_trades": len(trades_df),
            "wins": wins,
            "losses": losses,
            "win_rate": float(win_rate),
            "total_pnl": float(total_pnl),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown)
        }
        
        logger.info(
            f"✅ {symbol}: {len(trades_df)} trades, "
            f"{win_rate:.1%} win rate, {total_pnl:.2f}% total PnL"
        )
        
        return results
    
    def save_results(self):
        """Save detailed trade logs to CSV."""
        if not self.trades:
            logger.warning("⚠️ No trades to save")
            return
        
        # Create directory if needed
        results_path = Path(RESULTS_PATH)
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(self.trades)
        df.to_csv(results_path, index=False)
        
        logger.info(f"💾 Saved {len(self.trades)} trade records to {RESULTS_PATH}")
    
    def print_summary_by_asset_class(self):
        """Print summary table grouped by asset class."""
        if not self.trades:
            logger.warning("⚠️ No trades to summarize")
            return
        
        trades_df = pd.DataFrame(self.trades)
        
        # Group by asset class
        print("\n" + "=" * 80)
        print("📊 STRESS TEST SUMMARY BY ASSET CLASS")
        print("=" * 80)
        print()
        
        # Map symbols to asset classes
        symbol_to_class = {}
        for class_name, class_info in ASSET_CLASSES.items():
            if class_name != "FULL_TEST_SUITE":
                for symbol in class_info["assets"]:
                    symbol_to_class[symbol] = class_name
        
        # Add asset class column
        trades_df["asset_class"] = trades_df["symbol"].map(symbol_to_class).fillna("UNKNOWN")
        
        # Calculate metrics by asset class
        summary_rows = []
        for asset_class in trades_df["asset_class"].unique():
            class_trades = trades_df[trades_df["asset_class"] == asset_class]
            
            wins = len(class_trades[class_trades["is_win"] == True])
            losses = len(class_trades[class_trades["is_win"] == False])
            win_rate = wins / len(class_trades) if len(class_trades) > 0 else 0.0
            total_pnl = float(class_trades["pnl_pct"].sum())
            
            pnl_series = class_trades["pnl_pct"]
            if len(pnl_series) > 1:
                sharpe = float(np.mean(pnl_series) / np.std(pnl_series) * np.sqrt(252)) if np.std(pnl_series) > 0 else 0.0
            else:
                sharpe = 0.0
            
            summary_rows.append({
                "Asset Class": asset_class,
                "Trades": len(class_trades),
                "Wins": wins,
                "Losses": losses,
                "Win Rate": f"{win_rate:.1%}",
                "Total PnL %": f"{total_pnl:.2f}%",
                "Sharpe Ratio": f"{sharpe:.2f}"
            })
        
        # Print table
        summary_df = pd.DataFrame(summary_rows)
        print(summary_df.to_string(index=False))
        print()
        
        # Overall summary
        total_trades = len(trades_df)
        total_wins = len(trades_df[trades_df["is_win"] == True])
        overall_win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        overall_pnl = float(trades_df["pnl_pct"].sum())
        
        print("=" * 80)
        print("📈 OVERALL SUMMARY")
        print("=" * 80)
        print(f"Total Trades: {total_trades}")
        print(f"Wins: {total_wins}")
        print(f"Losses: {total_trades - total_wins}")
        print(f"Win Rate: {overall_win_rate:.1%}")
        print(f"Total PnL: {overall_pnl:.2f}%")
        
        pnl_series = trades_df["pnl_pct"]
        if len(pnl_series) > 1:
            overall_sharpe = float(np.mean(pnl_series) / np.std(pnl_series) * np.sqrt(252)) if np.std(pnl_series) > 0 else 0.0
            print(f"Sharpe Ratio: {overall_sharpe:.2f}")
        
        # Max Drawdown
        cumulative = pnl_series.cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = float(abs(drawdown.min())) if len(drawdown) > 0 else 0.0
        print(f"Max Drawdown: {max_drawdown:.2f}%")
        print("=" * 80)


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("🚀 FUGGERBOT STRESS TEST - Starting")
    logger.info("=" * 80)
    
    tester = StressTester()
    
    # Run tests for all assets in FULL_TEST_SUITE
    logger.info(f"📊 Testing {len(FULL_TEST_SUITE)} assets from FULL_TEST_SUITE")
    logger.info(f"Assets: {', '.join(FULL_TEST_SUITE)}")
    print()
    
    results = []
    for symbol in tqdm(FULL_TEST_SUITE, desc="Testing assets"):
        result = tester.run_test(symbol, start_date="2020-01-01")
        results.append(result)
        print()
    
    # Save results
    tester.save_results()
    
    # Print summary
    tester.print_summary_by_asset_class()
    
    logger.info("=" * 80)
    logger.info("✅ STRESS TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Stress test interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Stress test failed: {e}", exc_info=True)
        sys.exit(1)







