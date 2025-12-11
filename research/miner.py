"""
Learning Book Miner for FuggerBot v2.0.

Extracts historical trading patterns from the Data Lake to build the
"Learning Book" - a compressed knowledge base used by the simulator's
proxy logic.

Author: FuggerBot AI Team
Status: Operation Clean Slate - Patched
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LearningBookMiner:
    """
    Mines the Global Data Lake to extract trading patterns.
    """
    
    def __init__(
        self,
        db_path: Path = PROJECT_ROOT / "data" / "market_history.duckdb",
        output_path: Path = PROJECT_ROOT / "data" / "learning_book.json"
    ):
        self.db_path = db_path
        self.output_path = output_path
        self.conn = None
    
    def connect(self):
        """Connect to DuckDB database."""
        try:
            self.conn = duckdb.connect(str(self.db_path), read_only=True)
            logger.info(f"✅ Connected to Data Lake: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Data Lake: {e}")
            raise
    
    def mine_patterns(self, symbols: List[str] = None, lookback_days: int = 365) -> List[Dict[str, Any]]:
        """
        Mine historical patterns from the Data Lake.
        
        Args:
            symbols: List of symbols to analyze (default: all)
            lookback_days: Days of history to analyze
            
        Returns:
            List of pattern records
        """
        if not self.conn:
            self.connect()
        
        # Get available symbols if not specified
        if not symbols:
            symbols_df = self.conn.execute(
                "SELECT DISTINCT symbol FROM ohlcv_history WHERE asset_class IN ('CRYPTO', 'STOCKS') ORDER BY symbol"
            ).fetchdf()
            symbols = symbols_df['symbol'].tolist()
        
        logger.info(f"🔍 Mining patterns for {len(symbols)} symbols over {lookback_days} days...")
        
        all_patterns = []
        
        for symbol in symbols:
            try:
                # Fetch data for symbol
                query = f"""
                    SELECT date, open, high, low, close, volume
                    FROM ohlcv_history
                    WHERE symbol = '{symbol}'
                    AND date >= CURRENT_DATE - INTERVAL '{lookback_days} days'
                    ORDER BY date
                """
                
                df = self.conn.execute(query).fetchdf()
                
                if len(df) < 30:
                    logger.warning(f"⚠️  Insufficient data for {symbol} ({len(df)} rows)")
                    continue
                
                # Calculate technical indicators
                df['returns'] = df['close'].pct_change()
                df['volatility'] = df['returns'].rolling(window=30).std()
                df['sma_20'] = df['close'].rolling(window=20).mean()
                df['sma_50'] = df['close'].rolling(window=50).mean()
                df['trend'] = (df['sma_20'] > df['sma_50']).astype(int)
                
                # Mine patterns (look for high-conviction setups)
                for i in range(50, len(df) - 5):  # Need 50 days lookback, 5 days forward
                    row = df.iloc[i]
                    
                    # Pattern criteria: Strong trend + Low volatility
                    if pd.notna(row['trend']) and pd.notna(row['volatility']):
                        if row['trend'] == 1 and row['volatility'] < df['volatility'].quantile(0.3):
                            # Look ahead to see if trade was profitable
                            entry_price = row['close']
                            future_prices = df['close'].iloc[i+1:i+6]
                            max_gain = (future_prices.max() - entry_price) / entry_price
                            max_loss = (future_prices.min() - entry_price) / entry_price
                            
                            pattern = {
                                'symbol': symbol,
                                'date': str(row['date']),
                                'entry_price': float(entry_price),
                                'trend_signal': 'BULLISH',
                                'volatility': float(row['volatility']),
                                'max_gain_5d': float(max_gain * 100),
                                'max_loss_5d': float(max_loss * 100),
                                'outcome': 'WIN' if max_gain > 0.02 else 'LOSS'
                            }
                            
                            all_patterns.append(pattern)
                
                logger.info(f"✅ Mined {len([p for p in all_patterns if p['symbol'] == symbol])} patterns from {symbol}")
            
            except Exception as e:
                logger.error(f"❌ Failed to mine {symbol}: {e}")
        
        logger.info(f"📘 Total patterns mined: {len(all_patterns)}")
        
        return all_patterns
    
    def save_learning_book(self, patterns: List[Dict[str, Any]]):
        """Save patterns to learning book JSON."""
        learning_book = {
            'version': '2.0',
            'created_at': datetime.now().isoformat(),
            'total_patterns': len(patterns),
            'symbols_covered': list(set([p['symbol'] for p in patterns])),
            'patterns': patterns
        }
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w') as f:
            json.dump(learning_book, f, indent=2)
        
        logger.info(f"💾 Learning Book saved: {self.output_path} ({len(patterns)} records)")
    
    def run(self):
        """Execute full mining pipeline."""
        logger.info("=" * 80)
        logger.info("🚀 LEARNING BOOK MINER - Operation Clean Slate v2.0")
        logger.info("=" * 80)
        
        self.connect()
        
        # Mine patterns for key assets
        symbols = ["BTC-USD", "ETH-USD", "NVDA", "MSFT", "AAPL", "GOOGL"]
        patterns = self.mine_patterns(symbols=symbols, lookback_days=730)  # 2 years
        
        # Save to learning book
        self.save_learning_book(patterns)
        
        # Close connection
        if self.conn:
            self.conn.close()
        
        logger.info("=" * 80)
        logger.info("✅ MINING COMPLETE")
        logger.info("=" * 80)
        
        return patterns


if __name__ == "__main__":
    miner = LearningBookMiner()
    patterns = miner.run()
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"  - Total Patterns: {len(patterns)}")
    print(f"  - Win Rate: {len([p for p in patterns if p['outcome'] == 'WIN']) / len(patterns):.1%}")
    print(f"  - Symbols: {set([p['symbol'] for p in patterns])}")
    print(f"\n✅ Success! Learning Book ready for War Games.")
