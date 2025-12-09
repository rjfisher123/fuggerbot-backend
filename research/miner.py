#!/usr/bin/env python3
"""
Learning Book Miner - Extract Golden Setups from Historical Data.

Builds a dataset of market conditions and their outcomes for training/analysis.
This script "mines" historical data to find winning trade setups from the past 2 years.
"""
import sys
import json
import logging
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import actual class names (note: user prompt mentioned TSFMPredictor/TrustEvaluator,
# but actual classes are ChronosInferenceEngine/TrustFilter)
from models.tsfm.inference import ChronosInferenceEngine
from models.tsfm.schemas import ForecastInput
from models.trust.filter import TrustFilter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MINER - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HistoryMiner")

# Configuration
TARGET_ASSETS = ['BTC-USD', 'ETH-USD', 'NVDA', 'MSFT', 'TSLA']
WINDOW_SIZE = 64  # hours
STEP_SIZE = 24    # hours (step between windows)
HORIZON = 24      # hours (lookahead for outcome)
BOOK_PATH = "data/learning_book.json"


class HistoryMiner:
    """Mines historical data to find winning trade setups."""
    
    def __init__(self):
        """Initialize the miner with TSFM and Trust components."""
        logger.info("Initializing HistoryMiner...")
        # Note: Using ChronosInferenceEngine (not TSFMPredictor)
        self.tsfm = ChronosInferenceEngine(model_name="amazon/chronos-t5-tiny")
        # Note: Using TrustFilter (not TrustEvaluator)
        self.trust_filter = TrustFilter()
        self.book = []
        logger.info("✅ HistoryMiner initialized")
    
    def fetch_history(self, symbol: str) -> pd.DataFrame:
        """
        Fetch historical data for a symbol.
        
        CRITICAL: Uses yf.Ticker().history() instead of yf.download() to avoid
        progress argument bugs in recent yfinance versions.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USD')
        
        Returns:
            DataFrame with 'Close' column, cleaned and ready for mining
        """
        logger.info(f"📊 Fetching 2y history for {symbol}...")
        
        try:
            import yfinance as yf
            
            # CRITICAL: Use Ticker().history() instead of download()
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="2y", interval="1h")
            
            if df.empty:
                logger.warning(f"⚠️ No data returned for {symbol}")
                return pd.DataFrame()
            
            # Handle MultiIndex columns (flatten if needed)
            if isinstance(df.columns, pd.MultiIndex):
                logger.debug(f"Flattening MultiIndex columns for {symbol}")
                df.columns = df.columns.get_level_values(0)
            
            # Handle timezone-aware index (localize if needed)
            if df.index.tz is not None:
                logger.debug(f"Converting timezone-aware index to naive for {symbol}")
                df.index = df.index.tz_localize(None)
            
            # Ensure we have a Close column (use Adj Close as fallback)
            if 'Close' not in df.columns:
                if 'Adj Close' in df.columns:
                    logger.debug(f"Using 'Adj Close' as 'Close' for {symbol}")
                    df['Close'] = df['Adj Close']
                else:
                    logger.error(f"❌ No 'Close' or 'Adj Close' column found for {symbol}")
                    return pd.DataFrame()
            
            # Drop rows with NaN in Close column
            df = df[['Close']].dropna()
            
            if df.empty:
                logger.warning(f"⚠️ No valid data after cleaning for {symbol}")
                return pd.DataFrame()
            
            logger.info(f"✅ Fetched {len(df)} data points for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching {symbol}: {e}", exc_info=True)
            return pd.DataFrame()
    
    def mine_asset(self, symbol: str):
        """
        Mine historical data for a single asset.
        
        Uses sliding window approach:
        - Window size: 64 hours (context for forecast)
        - Step size: 24 hours (check once per day)
        - Horizon: 24 hours (lookahead for outcome)
        
        Args:
            symbol: Trading symbol to mine
        """
        logger.info(f"🔍 Mining {symbol}...")
        
        # Fetch history
        df = self.fetch_history(symbol)
        
        if df.empty or len(df) < WINDOW_SIZE + HORIZON:
            logger.warning(f"⚠️ Insufficient data for {symbol}: {len(df)} points (need {WINDOW_SIZE + HORIZON})")
            return
        
        prices = df['Close'].values
        logger.info(f"📈 Processing {len(prices)} price points for {symbol}")
        
        # Sliding window through history
        records_count = 0
        start_idx = WINDOW_SIZE
        end_idx = len(prices) - HORIZON
        
        logger.info(f"🔄 Processing {end_idx - start_idx} windows (step={STEP_SIZE}h, window={WINDOW_SIZE}h)...")
        
        for i in range(start_idx, end_idx, STEP_SIZE):
            try:
                # Extract window
                window_prices = prices[i - WINDOW_SIZE:i]
                current_price = float(window_prices[-1])
                
                # Check if we have enough future data
                if i + HORIZON >= len(prices):
                    continue
                
                future_price = float(prices[i + HORIZON])
                
                # Calculate volatility from the window
                returns = np.diff(window_prices) / window_prices[:-1]
                volatility = float(np.std(returns) * np.sqrt(24))  # Annualized
                
                # Run TSFM forecast (simulating a past forecast)
                try:
                    forecast_input = ForecastInput(
                        series=window_prices.tolist(),
                        forecast_horizon=HORIZON,
                        context_length=None,
                        metadata={"symbol": symbol, "timestamp": df.index[i].isoformat()}
                    )
                    
                    forecast_output = self.tsfm.forecast(forecast_input)
                    
                except Exception as e:
                    logger.debug(f"Forecast failed at index {i} for {symbol}: {e}")
                    continue
                
                # Run TrustEvaluator (TrustFilter)
                try:
                    # Calculate historical volatility for trust evaluation
                    historical_volatility = float(np.std(returns) * np.sqrt(24)) if len(returns) > 0 else 0.0
                    
                    trust_evaluation = self.trust_filter.evaluate(
                        forecast=forecast_output,
                        input_data=forecast_input,
                        symbol=symbol,
                        current_volatility=volatility,
                        historical_volatility=historical_volatility
                    )
                    
                    trust_score = trust_evaluation.metrics.overall_trust_score
                    is_trusted = trust_evaluation.is_trusted
                    
                except Exception as e:
                    logger.debug(f"Trust evaluation failed at index {i} for {symbol}: {e}")
                    continue
                
                # IF TRUSTED: Record the setup and outcome
                if is_trusted:
                    # Calculate outcome (Win or Loss - must match orchestrator expectations)
                    pnl_pct = ((future_price - current_price) / current_price) * 100
                    outcome = "Win" if pnl_pct > 0 else "Loss"
                    
                    # Classify volatility state (for orchestrator compatibility)
                    if volatility > 0.3:
                        volatility_state = "High"
                    elif volatility > 0.15:
                        volatility_state = "Normal"
                    else:
                        volatility_state = "Low"
                    
                    # Create record (field names must match orchestrator's find_precedents expectations)
                    record = {
                        "symbol": symbol,
                        "timestamp": df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i]),
                        "current_price": float(current_price),
                        "future_price": float(future_price),
                        "current_volatility": float(volatility),  # Must match orchestrator field name
                        "volatility_state": volatility_state,     # Required by orchestrator
                        "trust_score": float(trust_score),
                        "forecast_target": float(np.mean(forecast_output.point_forecast)),
                        "forecast_confidence": float(1.0 - (
                            np.mean(np.array(forecast_output.upper_bound) - np.array(forecast_output.lower_bound))
                            / np.mean(forecast_output.point_forecast)
                        )) if np.mean(forecast_output.point_forecast) > 0 else 0.5,
                        "actual_outcome": outcome,  # Must match orchestrator field name ("Win" or "Loss")
                        "pnl_pct": float(pnl_pct),
                        "horizon_hours": HORIZON
                    }
                    
                    self.book.append(record)
                    records_count += 1
                    
                    if records_count % 10 == 0:
                        logger.debug(f"  Found {records_count} trusted setups for {symbol}...")
            
            except Exception as e:
                logger.debug(f"Error processing window at index {i} for {symbol}: {e}")
                continue
        
        logger.info(f"✅ Mined {records_count} trusted setups for {symbol}")
    
    def save_book(self):
        """
        Save the learning book to JSON file.
        
        Also prints the Global Historical Win Rate of the strategy.
        """
        # Create directory if missing
        os.makedirs(os.path.dirname(BOOK_PATH), exist_ok=True)
        
        # Prepare book structure
        book_data = {
            "created_at": datetime.now().isoformat(),
            "total_records": len(self.book),
            "records": self.book
        }
        
        # Calculate statistics
        if self.book:
            wins = len([r for r in self.book if r["actual_outcome"] == "Win"])
            losses = len([r for r in self.book if r["actual_outcome"] == "Loss"])
            win_rate = wins / len(self.book) if self.book else 0.0
            avg_pnl = np.mean([r["pnl_pct"] for r in self.book])
            
            book_data["statistics"] = {
                "wins": wins,
                "losses": losses,
                "win_rate": float(win_rate),
                "avg_pnl_pct": float(avg_pnl)
            }
        
        # Save to file
        book_path = Path(BOOK_PATH)
        with open(book_path, 'w') as f:
            json.dump(book_data, f, indent=2)
        
        logger.info(f"📚 Book saved with {len(self.book)} case studies to {BOOK_PATH}")
        
        # Print Global Historical Win Rate
        if self.book:
            stats = book_data["statistics"]
            logger.info("=" * 60)
            logger.info("📊 GLOBAL HISTORICAL WIN RATE")
            logger.info("=" * 60)
            logger.info(f"Total Setups: {stats['wins'] + stats['losses']}")
            logger.info(f"Wins: {stats['wins']}")
            logger.info(f"Losses: {stats['losses']}")
            logger.info(f"Win Rate: {stats['win_rate']:.1%}")
            logger.info(f"Average PnL: {stats['avg_pnl_pct']:.2f}%")
            logger.info("=" * 60)
        else:
            logger.warning("⚠️ No records to save - learning book is empty")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("🔍 LEARNING BOOK MINER - Starting")
    logger.info("=" * 60)
    
    miner = HistoryMiner()
    
    # Mine each asset
    for asset in TARGET_ASSETS:
        miner.mine_asset(asset)
    
    # Save the book
    miner.save_book()
    
    logger.info("=" * 60)
    logger.info("✅ MINING COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Mining interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Mining failed: {e}", exc_info=True)
        sys.exit(1)
