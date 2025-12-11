"""
Memory Summarizer Agent - Level 2 Perception Layer.

Converts trade history stats into narrative insights.
Prevents the bot from repeating the same mistake multiple times.

Enhanced v2.0: Now integrates with Global Data Lake (DuckDB) for market context.
"""
import logging
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
from pathlib import Path
import numpy as np
import pandas as pd

# Initialize logger first (needed for import error handling)
logger = logging.getLogger(__name__)

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    logger.warning("DuckDB not available - market context features disabled")


class MemoryNarrative(BaseModel):
    """
    Processed memory summary with narrative insights.
    """
    regime_win_rate: float = Field(..., ge=0.0, le=1.0, description="Win rate in current regime")
    total_trades_in_regime: int = Field(..., ge=0, description="Total trades in this regime")
    primary_failure_mode: str = Field(..., description="Most common reason for losses")
    hallucination_rate: float = Field(..., ge=0.0, le=1.0, description="Rate of MODEL_HALLUCINATION outcomes")
    confidence_calibration: str = Field(..., description="Are we over/under-confident?")
    narrative: str = Field(..., description="Human-readable narrative for LLM")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this narrative was created")
    
    def to_prompt_string(self) -> str:
        """
        Format narrative for LLM injection.
        
        Returns:
            Formatted string for prompt
        """
        if self.hallucination_rate > 0.3:
            warning = "⚠️ HIGH HALLUCINATION RISK"
        elif self.regime_win_rate < 0.4:
            warning = "⚠️ LOW WIN RATE IN THIS REGIME"
        else:
            warning = "✅ PERFORMANCE ACCEPTABLE"
        
        return f"📊 MEMORY INSIGHT ({warning}):\n{self.narrative}"


class MemorySummarizer:
    """
    Memory Summarizer Agent - The Historian.
    
    Analyzes trade history to create narrative insights and
    prevent repeated mistakes.
    """
    
    def __init__(self, memory_file: Optional[Path] = None, db_path: Optional[Path] = None):
        """
        Initialize the memory summarizer.
        
        Args:
            memory_file: Path to trade_memory.json (default: data/trade_memory.json)
            db_path: Path to market_history.duckdb (default: data/market_history.duckdb)
        """
        self.memory_file = memory_file or Path("data/trade_memory.json")
        self.db_path = db_path or Path("data/market_history.duckdb")
        self.db_available = DUCKDB_AVAILABLE and self.db_path.exists()
        
        if self.db_available:
            logger.info(f"MemorySummarizer initialized with {self.memory_file} and DuckDB at {self.db_path}")
        else:
            logger.info(f"MemorySummarizer initialized with {self.memory_file} (DuckDB not available)")
    
    def _load_memory(self) -> Dict:
        """
        Load trade memory from JSON file.
        
        Returns:
            Dict with trades list
        """
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Memory file not found: {self.memory_file}")
            return {"trades": []}
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
            return {"trades": []}
    
    def _filter_by_regime(self, trades: List[Dict], current_regime_id: str) -> List[Dict]:
        """
        Filter trades to only those in the current regime.
        
        Args:
            trades: List of trade records
            current_regime_id: Current regime ID (e.g., "INFLATIONARY", "NEUTRAL")
        
        Returns:
            Filtered list of trades
        """
        regime_trades = []
        for trade in trades:
            trade_regime = trade.get("regime_id", "").upper()
            
            # Extract base regime type (remove timestamps like "_2022")
            if "_" in trade_regime:
                trade_regime = trade_regime.split("_")[0]
            
            current_base = current_regime_id.upper()
            if "_" in current_base:
                current_base = current_base.split("_")[0]
            
            if trade_regime == current_base:
                regime_trades.append(trade)
        
        return regime_trades
    
    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        """
        Calculate win rate from completed trades.
        
        Args:
            trades: List of trade records
        
        Returns:
            Win rate (0.0 to 1.0)
        """
        completed_trades = [t for t in trades if t.get("pnl") is not None]
        
        if not completed_trades:
            return 0.5  # Neutral if no data
        
        wins = sum(1 for t in completed_trades if t.get("pnl", 0) > 0)
        return wins / len(completed_trades)
    
    def _identify_failure_mode(self, trades: List[Dict]) -> str:
        """
        Identify the most common failure mode from post-mortems.
        
        Args:
            trades: List of trade records
        
        Returns:
            Description of primary failure mode
        """
        # Collect outcome categories from post-mortems
        outcomes = []
        for trade in trades:
            if trade.get("pnl") is not None and trade.get("pnl") < 0:
                if trade.get("post_mortem"):
                    pm = trade.get("post_mortem")
                    if isinstance(pm, dict):
                        outcome_cat = pm.get("outcome_category")
                        root_cause = pm.get("root_cause")
                        if outcome_cat:
                            outcomes.append((outcome_cat, root_cause))
        
        if not outcomes:
            return "Insufficient data to identify failure patterns"
        
        # Count by category
        category_counts = {}
        category_causes = {}
        for outcome_cat, root_cause in outcomes:
            category_counts[outcome_cat] = category_counts.get(outcome_cat, 0) + 1
            if outcome_cat not in category_causes:
                category_causes[outcome_cat] = root_cause or "Unknown"
        
        # Find most common
        most_common = max(category_counts, key=category_counts.get)
        example_cause = category_causes.get(most_common, "Unknown")
        
        return f"{most_common} (Example: {example_cause})"
    
    def _calculate_hallucination_rate(self, trades: List[Dict]) -> float:
        """
        Calculate rate of MODEL_HALLUCINATION outcomes.
        
        Args:
            trades: List of trade records
        
        Returns:
            Hallucination rate (0.0 to 1.0)
        """
        trades_with_pm = []
        hallucinations = 0
        
        for trade in trades:
            if trade.get("post_mortem"):
                pm = trade.get("post_mortem")
                if isinstance(pm, dict):
                    trades_with_pm.append(trade)
                    if pm.get("outcome_category") == "MODEL_HALLUCINATION":
                        hallucinations += 1
        
        if not trades_with_pm:
            return 0.0  # No data
        
        return hallucinations / len(trades_with_pm)
    
    def _assess_confidence_calibration(self, trades: List[Dict]) -> str:
        """
        Assess whether confidence predictions are well-calibrated.
        
        Args:
            trades: List of trade records
        
        Returns:
            Description of calibration status
        """
        # Compare predicted confidence to actual outcomes
        calibration_data = []
        for trade in trades:
            if trade.get("pnl") is not None:
                confidence = trade.get("confidence", 0.5)
                won = trade.get("pnl", 0) > 0
                calibration_data.append((confidence, won))
        
        if len(calibration_data) < 10:
            return "Insufficient data for calibration assessment"
        
        # Group by confidence bins
        high_conf_trades = [(c, w) for c, w in calibration_data if c >= 0.8]
        med_conf_trades = [(c, w) for c, w in calibration_data if 0.5 <= c < 0.8]
        
        if high_conf_trades:
            high_conf_win_rate = sum(w for _, w in high_conf_trades) / len(high_conf_trades)
            
            if high_conf_win_rate < 0.5:
                return "OVERCONFIDENT: High confidence trades underperforming"
            elif high_conf_win_rate > 0.7:
                return "WELL_CALIBRATED: High confidence trades winning as expected"
        
        return "MODERATE: Confidence calibration unclear"
    
    def _get_db_connection(self) -> Optional["duckdb.DuckDBPyConnection"]:
        """
        Get DuckDB connection.
        
        Returns:
            DuckDB connection or None if not available
        """
        if not self.db_available:
            return None
        
        try:
            return duckdb.connect(str(self.db_path), read_only=True)  # type: ignore
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB: {e}")
            return None
    
    def _calculate_correlation(self, series1: pd.Series, series2: pd.Series) -> float:
        """
        Calculate correlation between two price series.
        
        Args:
            series1: First price series
            series2: Second price series
        
        Returns:
            Correlation coefficient (-1.0 to 1.0)
        """
        try:
            # Calculate returns
            returns1 = series1.pct_change().dropna()
            returns2 = series2.pct_change().dropna()
            
            # Align series
            aligned = pd.concat([returns1, returns2], axis=1, join='inner')
            
            if len(aligned) < 2:
                return 0.0
            
            corr = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
            return float(corr) if not np.isnan(corr) else 0.0
        
        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
            return 0.0
    
    def _calculate_volatility_ratio(self, current_series: pd.Series, lookback_days: int = 90) -> float:
        """
        Calculate ratio of recent volatility to historical volatility.
        
        Args:
            current_series: Price series
            lookback_days: Days to look back for historical volatility
        
        Returns:
            Volatility ratio (>1 means higher than historical, <1 means lower)
        """
        try:
            returns = current_series.pct_change().dropna()
            
            if len(returns) < lookback_days:
                return 1.0
            
            # Recent volatility (last 30 days)
            recent_vol = returns.tail(30).std()
            
            # Historical volatility (full period)
            hist_vol = returns.std()
            
            if hist_vol == 0:
                return 1.0
            
            return float(recent_vol / hist_vol)
        
        except Exception as e:
            logger.error(f"Volatility calculation failed: {e}")
            return 1.0
    
    def get_market_context(self, symbol: str, days: int = 30) -> str:
        """
        Query Global Data Lake for market context and correlations.
        
        Args:
            symbol: Trading symbol
            days: Number of days to analyze (default: 30)
        
        Returns:
            Market context narrative string
        """
        if not self.db_available:
            return "Market context unavailable (DuckDB not connected)"
        
        conn = self._get_db_connection()
        if conn is None:
            return "Market context unavailable (database connection failed)"
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).date()
            
            # Query symbol data
            symbol_df = conn.execute("""
                SELECT date, close
                FROM ohlcv_history
                WHERE symbol = ?
                AND date >= ?
                ORDER BY date
            """, [symbol, cutoff_date]).df()
            
            if symbol_df.empty:
                return f"No recent market data found for {symbol}"
            
            # Query S&P 500 for market correlation
            sp500_df = conn.execute("""
                SELECT date, close
                FROM ohlcv_history
                WHERE symbol = '^GSPC'
                AND date >= ?
                ORDER BY date
            """, [cutoff_date]).df()
            
            # Query Gold for safe-haven correlation
            gold_df = conn.execute("""
                SELECT date, close
                FROM ohlcv_history
                WHERE symbol = 'GC=F'
                AND date >= ?
                ORDER BY date
            """, [cutoff_date]).df()
            
            conn.close()
            
            # Calculate correlations
            context_parts = [f"Market Context ({days}-day analysis):"]
            
            # S&P 500 correlation (Tech/Risk-on correlation)
            if not sp500_df.empty:
                corr_sp500 = self._calculate_correlation(
                    symbol_df.set_index('date')['close'],
                    sp500_df.set_index('date')['close']
                )
                
                if abs(corr_sp500) > 0.7:
                    relationship = "strongly coupled with"
                elif abs(corr_sp500) > 0.3:
                    relationship = "moderately correlated with"
                elif abs(corr_sp500) < 0.1:
                    relationship = "decoupling from"
                else:
                    relationship = "weakly correlated with"
                
                direction = "positive" if corr_sp500 > 0 else "negative"
                context_parts.append(f"- {symbol} is {relationship} Tech/Equities ({direction} β={abs(corr_sp500):.2f})")
            
            # Gold correlation (Safe-haven behavior)
            if not gold_df.empty:
                corr_gold = self._calculate_correlation(
                    symbol_df.set_index('date')['close'],
                    gold_df.set_index('date')['close']
                )
                
                if corr_gold > 0.5:
                    context_parts.append(f"- Safe-haven behavior detected (Gold correlation: {corr_gold:.2f})")
                elif corr_gold < -0.5:
                    context_parts.append(f"- Risk-on behavior (inverse Gold correlation: {corr_gold:.2f})")
            
            # Volatility analysis
            vol_ratio = self._calculate_volatility_ratio(symbol_df['close'])
            if vol_ratio > 1.5:
                context_parts.append(f"- ⚠️ Elevated volatility ({vol_ratio:.1f}x historical average)")
            elif vol_ratio < 0.7:
                context_parts.append(f"- Low volatility regime ({vol_ratio:.1f}x historical average)")
            else:
                context_parts.append(f"- Normal volatility ({vol_ratio:.1f}x historical average)")
            
            # Price trend
            price_change = (symbol_df['close'].iloc[-1] - symbol_df['close'].iloc[0]) / symbol_df['close'].iloc[0]
            if abs(price_change) > 0.1:
                direction_word = "up" if price_change > 0 else "down"
                context_parts.append(f"- {days}-day trend: {direction_word} {abs(price_change):.1%}")
            
            return "\n".join(context_parts)
        
        except Exception as e:
            logger.error(f"Failed to get market context for {symbol}: {e}", exc_info=True)
            return f"Market context error: {str(e)}"
    
    def get_trade_narrative(self, symbol: str, current_regime_id: str) -> str:
        """
        Get trade history narrative (renamed from summarize for clarity).
        
        Args:
            symbol: Trading symbol
            current_regime_id: Current macro regime ID
        
        Returns:
            Trade narrative string
        """
        narrative_obj = self.summarize(symbol, current_regime_id)
        return narrative_obj.narrative
    
    def get_unified_context(self, symbol: str, current_regime_id: str, include_market: bool = True) -> str:
        """
        Get unified narrative combining trade history and market context.
        
        Args:
            symbol: Trading symbol
            current_regime_id: Current macro regime ID
            include_market: Whether to include market context from DuckDB
        
        Returns:
            Unified context string for LLM
        """
        parts = []
        
        # Trade history narrative
        trade_narrative = self.get_trade_narrative(symbol, current_regime_id)
        parts.append("=== TRADING HISTORY ===")
        parts.append(trade_narrative)
        
        # Market context from Global Data Lake
        if include_market and self.db_available:
            market_context = self.get_market_context(symbol, days=30)
            parts.append("\n=== GLOBAL MARKET CONTEXT ===")
            parts.append(market_context)
        
        return "\n".join(parts)
    
    def summarize(self, symbol: str, current_regime_id: str) -> MemoryNarrative:
        """
        Generate narrative summary for a symbol in the current regime.
        
        Args:
            symbol: Trading symbol
            current_regime_id: Current macro regime ID
        
        Returns:
            MemoryNarrative with insights
        """
        memory_data = self._load_memory()
        all_trades = memory_data.get("trades", [])
        
        # Filter to current regime
        regime_trades = self._filter_by_regime(all_trades, current_regime_id)
        
        # Further filter to this symbol (optional - could be removed for broader context)
        symbol_trades = [t for t in regime_trades if t.get("symbol") == symbol]
        
        # If not enough symbol-specific data, use all regime trades
        trades_to_analyze = symbol_trades if len(symbol_trades) >= 5 else regime_trades
        
        if not trades_to_analyze:
            logger.info(f"No historical trades for {symbol} in regime {current_regime_id}")
            return MemoryNarrative(
                regime_win_rate=0.5,
                total_trades_in_regime=0,
                primary_failure_mode="No historical data in this regime",
                hallucination_rate=0.0,
                confidence_calibration="N/A",
                narrative=f"No historical data for {symbol} in {current_regime_id} regime. Proceeding with caution."
            )
        
        # Calculate metrics
        win_rate = self._calculate_win_rate(trades_to_analyze)
        failure_mode = self._identify_failure_mode(trades_to_analyze)
        hallucination_rate = self._calculate_hallucination_rate(trades_to_analyze)
        calibration = self._assess_confidence_calibration(trades_to_analyze)
        
        # Generate narrative
        scope = f"{symbol}" if len(symbol_trades) >= 5 else f"{current_regime_id} regime (all symbols)"
        
        narrative_parts = [
            f"Historical performance for {scope}:",
            f"- Win Rate: {win_rate:.1%} ({len(trades_to_analyze)} trades)",
            f"- Primary failure mode: {failure_mode}",
            f"- Model hallucination rate: {hallucination_rate:.1%}",
            f"- Confidence calibration: {calibration}"
        ]
        
        # Add specific warnings
        if win_rate < 0.4:
            narrative_parts.append("⚠️ WARNING: Low historical win rate suggests unfavorable setup")
        if hallucination_rate > 0.3:
            narrative_parts.append("⚠️ WARNING: High hallucination rate - model may be unreliable")
        
        narrative = "\n".join(narrative_parts)
        
        logger.info(f"Memory narrative for {symbol} in {current_regime_id}: {win_rate:.1%} win rate, {hallucination_rate:.1%} hallucination")
        
        return MemoryNarrative(
            regime_win_rate=win_rate,
            total_trades_in_regime=len(trades_to_analyze),
            primary_failure_mode=failure_mode,
            hallucination_rate=hallucination_rate,
            confidence_calibration=calibration,
            narrative=narrative
        )


# Singleton instance
_memory_summarizer: Optional[MemorySummarizer] = None


def get_memory_summarizer() -> MemorySummarizer:
    """
    Get or create singleton MemorySummarizer instance.
    
    Returns:
        MemorySummarizer instance
    """
    global _memory_summarizer
    
    if _memory_summarizer is None:
        _memory_summarizer = MemorySummarizer()
    
    return _memory_summarizer


if __name__ == "__main__":
    # Test the memory summarizer with Global Data Lake integration
    logging.basicConfig(level=logging.INFO)
    
    summarizer = get_memory_summarizer()
    
    print("=" * 80)
    print("MEMORY SUMMARIZER v2.0 TEST")
    print("=" * 80)
    
    # Test 1: Trade narrative
    print("\n[TEST 1] Trade Narrative:")
    narrative = summarizer.summarize("BTC-USD", "NEUTRAL")
    print(f"Win Rate: {narrative.regime_win_rate:.1%}")
    print(f"Total Trades: {narrative.total_trades_in_regime}")
    print(f"Failure Mode: {narrative.primary_failure_mode}")
    print(f"Hallucination Rate: {narrative.hallucination_rate:.1%}")
    print(f"Calibration: {narrative.confidence_calibration}")
    
    # Test 2: Market context from Global Data Lake
    print("\n[TEST 2] Market Context from Global Data Lake:")
    market_context = summarizer.get_market_context("BTC-USD", days=30)
    print(market_context)
    
    # Test 3: Unified context
    print("\n[TEST 3] Unified Context (Trade History + Market):")
    unified = summarizer.get_unified_context("BTC-USD", "NEUTRAL", include_market=True)
    print(unified)
    
    print("\n" + "=" * 80)


