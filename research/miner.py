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

# Import technical analysis library (Phase 3)
from models.technical_analysis import add_indicators, is_quality_setup

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
                
                if len(df) < 60:  # Need more data for technical indicators
                    logger.warning(f"⚠️  Insufficient data for {symbol} ({len(df)} rows, need 60+)")
                    continue
                
                # Phase 3: Add Technical Indicators (RSI, MACD, Volume, Trend)
                df = add_indicators(df)
                
                # Also keep legacy indicators for compatibility
                df['returns'] = df['close'].pct_change()
                df['volatility'] = df['returns'].rolling(window=30).std()
                
                # Mine patterns with STRICT quality filters
                patterns_before_filter = 0
                patterns_after_filter = 0
                
                for i in range(60, len(df) - 5):  # Need 60 days for indicators, 5 days forward
                    row = df.iloc[i]
                    patterns_before_filter += 1
                    
                    # Phase 3: QUALITY FILTER (The Alpha)
                    # Only record setups that meet ALL technical criteria
                    quality_check = is_quality_setup(
                        rsi=row['rsi_14'],
                        volume_ratio=row['volume_ratio'],
                        macd_hist=row['macd_hist'],
                        trend_sma=row['trend_sma'],
                        rsi_max=70.0,      # Not overbought
                        vol_min=1.0,       # Volume confirmed
                        macd_positive=True # Momentum positive
                    )
                    
                    if not quality_check:
                        continue  # Skip low-quality setups
                    
                    patterns_after_filter += 1
                    
                    # Look ahead to see if trade was profitable
                    entry_price = row['close']
                    future_prices = df['close'].iloc[i+1:i+6]
                    max_gain = (future_prices.max() - entry_price) / entry_price
                    max_loss = (future_prices.min() - entry_price) / entry_price
                    
                    # Calculate expected value for this setup
                    expected_gain = max_gain if max_gain > 0.02 else 0
                    
                    pattern = {
                        'symbol': symbol,
                        'date': str(row['date']),
                        'entry_price': float(entry_price),
                        'trend_signal': 'BULLISH',
                        
                        # Legacy metrics
                        'volatility': float(row['volatility']) if pd.notna(row['volatility']) else 0.0,
                        
                        # Phase 3: Technical Indicator Values
                        'rsi_14': float(row['rsi_14']),
                        'macd_hist': float(row['macd_hist']),
                        'volume_ratio': float(row['volume_ratio']),
                        'trend_sma': float(row['trend_sma']),
                        
                        # Outcome metrics
                        'max_gain_5d': float(max_gain * 100),
                        'max_loss_5d': float(max_loss * 100),
                        'expected_gain_pct': float(expected_gain * 100),
                        'outcome': 'WIN' if max_gain > 0.02 else 'LOSS'
                    }
                    
                    all_patterns.append(pattern)
                
                filtered_count = len([p for p in all_patterns if p['symbol'] == symbol])
                filter_rate = (patterns_after_filter / patterns_before_filter * 100) if patterns_before_filter > 0 else 0
                logger.info(f"✅ Mined {filtered_count} quality patterns from {symbol} (filter rate: {filter_rate:.1f}%)")
                
                logger.info(f"✅ Mined {len([p for p in all_patterns if p['symbol'] == symbol])} patterns from {symbol}")
            
            except Exception as e:
                logger.error(f"❌ Failed to mine {symbol}: {e}")
        
        logger.info(f"📘 Total patterns mined: {len(all_patterns)}")
        
        return all_patterns
    
    def save_learning_book(self, patterns: List[Dict[str, Any]]):
        """Save patterns to learning book JSON."""
        # Calculate quality metrics
        win_rate = len([p for p in patterns if p['outcome'] == 'WIN']) / len(patterns) if patterns else 0
        avg_gain = sum([p['max_gain_5d'] for p in patterns if p['outcome'] == 'WIN']) / len([p for p in patterns if p['outcome'] == 'WIN']) if [p for p in patterns if p['outcome'] == 'WIN'] else 0
        avg_loss = sum([abs(p['max_loss_5d']) for p in patterns if p['outcome'] == 'LOSS']) / len([p for p in patterns if p['outcome'] == 'LOSS']) if [p for p in patterns if p['outcome'] == 'LOSS'] else 0
        
        learning_book = {
            'version': '2.1-phase3',
            'created_at': datetime.now().isoformat(),
            'total_patterns': len(patterns),
            'symbols_covered': list(set([p['symbol'] for p in patterns])),
            'quality_filters': {
                'rsi_max': 70.0,
                'volume_min': 1.0,
                'macd_positive': True,
                'trend_positive': True
            },
            'statistics': {
                'win_rate': round(win_rate, 3),
                'avg_win_pct': round(avg_gain, 2),
                'avg_loss_pct': round(avg_loss, 2),
                'expected_value': round(win_rate * avg_gain - (1 - win_rate) * avg_loss, 2)
            },
            'patterns': patterns
        }
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w') as f:
            json.dump(learning_book, f, indent=2)
        
        logger.info(f"💾 Learning Book saved: {self.output_path} ({len(patterns)} records)")
    
    def run(self):
        """Execute full mining pipeline."""
        logger.info("=" * 80)
        logger.info("🚀 LEARNING BOOK MINER - Phase 3: Quality Signal Enhancement")
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
    
    # Calculate metrics
    win_rate = len([p for p in patterns if p['outcome'] == 'WIN']) / len(patterns) if patterns else 0
    avg_win = sum([p['max_gain_5d'] for p in patterns if p['outcome'] == 'WIN']) / len([p for p in patterns if p['outcome'] == 'WIN']) if [p for p in patterns if p['outcome'] == 'WIN'] else 0
    avg_loss = sum([abs(p['max_loss_5d']) for p in patterns if p['outcome'] == 'LOSS']) / len([p for p in patterns if p['outcome'] == 'LOSS']) if [p for p in patterns if p['outcome'] == 'LOSS'] else 0
    expected_value = win_rate * avg_win - (1 - win_rate) * avg_loss
    
    # Print summary
    print(f"\n📊 Phase 3 Mining Summary:")
    print(f"  - Total Quality Patterns: {len(patterns)}")
    print(f"  - Win Rate: {win_rate:.1%}")
    print(f"  - Avg Win: {avg_win:.2f}%")
    print(f"  - Avg Loss: {avg_loss:.2f}%")
    print(f"  - Expected Value: {expected_value:.2f}%")
    print(f"  - Symbols: {set([p['symbol'] for p in patterns])}")
    
    if expected_value > 0:
        print(f"\n✅ SUCCESS! Positive expected value (+{expected_value:.2f}%) - Strategy has edge!")
    else:
        print(f"\n⚠️  WARNING: Negative expected value ({expected_value:.2f}%) - Need stricter filters!")
    
    print(f"\n✅ Learning Book ready for War Games with technical filters.")
