#!/usr/bin/env python3
"""
Update Trade Outcomes - Calculate PnL for trades without outcomes.

This script should be run periodically to update trade outcomes based on current prices.
It looks at trades that don't have outcomes yet and calculates their PnL.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from reasoning.memory import TradeMemory
import yfinance as yf
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - OUTCOME_UPDATER - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OutcomeUpdater")


def update_trade_outcomes(memory: TradeMemory, lookback_hours: int = 24) -> int:
    """
    Update outcomes for trades that don't have them yet.
    
    For APPROVED trades: Calculate actual PnL from entry price to current price
    For REJECTED trades: Calculate "what if" PnL to track regret (MISSED_OP)
    
    Args:
        memory: TradeMemory instance
        lookback_hours: Only update trades from the last N hours (default: 24)
    
    Returns:
        Number of trades updated
    """
    trades = memory._memory.get("trades", [])
    
    # Filter trades that need outcomes
    # Process both approved (actual trades) and rejected (regret tracking)
    trades_to_update = [
        t for t in trades
        if (t.get("outcome") is None or t.get("pnl") is None)
        and t.get("price") is not None
    ]
    
    if not trades_to_update:
        logger.info("No trades need outcome updates")
        return 0
    
    logger.info(f"Found {len(trades_to_update)} trades without outcomes")
    
    updated_count = 0
    
    # Group by symbol to batch price fetches
    symbols = list(set([t.get("symbol") for t in trades_to_update if t.get("symbol")]))
    
    # Fetch current prices for all symbols
    current_prices = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                current_prices[symbol] = float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.debug(f"Could not fetch price for {symbol}: {e}")
            continue
    
    for trade in trades_to_update:
        try:
            symbol = trade.get("symbol")
            entry_price = trade.get("price")
            trade_id = trade.get("trade_id")
            decision = trade.get("decision")
            timestamp = trade.get("timestamp")
            
            if not symbol or not entry_price or not trade_id:
                continue
            
            # Check if trade is recent enough (within lookback window)
            if timestamp:
                try:
                    trade_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hours_ago = (datetime.now() - trade_time.replace(tzinfo=None)).total_seconds() / 3600
                    if hours_ago > lookback_hours:
                        continue  # Skip old trades
                except:
                    pass
            
            # Get current price
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            
            # Calculate PnL (simple: current - entry)
            # For BUY orders, profit = current - entry
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Update outcome (with error handling)
            try:
                success = memory.update_outcome(trade_id, pnl_pct)
                if success:
                    updated_count += 1
                    outcome_type = "APPROVED" if decision == "APPROVE" else "REJECTED"
                    logger.info(
                        f"Updated {outcome_type} {symbol}: Entry ${entry_price:.2f} -> Current ${current_price:.2f} "
                        f"(PnL: {pnl_pct:+.2f}%)"
                    )
            except Exception as save_error:
                logger.error(f"Error saving outcome for trade {trade_id}: {save_error}")
                # Don't break the loop, continue with other trades
                continue
                
        except Exception as e:
            logger.debug(f"Error updating trade {trade.get('trade_id')}: {e}")
            continue
    
    logger.info(f"✅ Updated {updated_count} trade outcomes")
    return updated_count


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("🔄 TRADE OUTCOME UPDATER - Starting")
    logger.info("=" * 60)
    
    memory = TradeMemory()
    
    # Update outcomes for trades from last 24 hours
    updated = update_trade_outcomes(memory, lookback_hours=24)
    
    logger.info("=" * 60)
    logger.info(f"✅ COMPLETE: Updated {updated} trade outcomes")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Update interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Update failed: {e}", exc_info=True)
        sys.exit(1)
