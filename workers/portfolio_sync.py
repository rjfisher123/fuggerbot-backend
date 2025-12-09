"""
Portfolio sync worker.

Continuously syncs IBKR account summary and positions to the database.
"""
import time
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.ibkr_client import get_ibkr_client
from persistence.db import SessionLocal
from persistence.repositories_portfolio import AccountStateRepository, PositionRepository
from core.logger import logger


class PortfolioSync:
    """Syncs IBKR portfolio data to database."""
    
    def __init__(self, interval_seconds: int = 60, paper_trading: bool = False):
        """
        Initialize portfolio sync worker.
        
        Args:
            interval_seconds: How often to sync (default: 60 seconds)
            paper_trading: Whether to sync paper trading account
        """
        self.interval_seconds = interval_seconds
        self.paper_trading = paper_trading
        self.ibkr_client = get_ibkr_client(paper_trading=paper_trading)
        self.running = False
        logger.info(f"PortfolioSync initialized (interval: {interval_seconds}s, paper_trading={paper_trading})")
    
    def get_ibkr_positions(self) -> List[Dict]:
        """
        Get open positions from IBKR.
        
        Returns:
            List of position dicts with symbol, quantity, avg_cost, market_value, unrealized_pnl
        """
        try:
            trader = self.ibkr_client.trader
            if not trader.connected:
                logger.warning("Not connected to IBKR, cannot fetch positions")
                return []
            
            if not trader.ib:
                return []
            
            # Get positions from IBKR
            positions = trader.ib.positions()
            
            result = []
            for pos in positions:
                try:
                    # Calculate market value and unrealized PnL
                    market_value = pos.position * pos.marketPrice if pos.marketPrice else 0.0
                    cost_basis = pos.position * pos.averageCost if pos.averageCost else 0.0
                    unrealized_pnl = market_value - cost_basis
                    
                    result.append({
                        "symbol": pos.contract.symbol,
                        "quantity": float(pos.position),
                        "avg_cost": float(pos.averageCost) if pos.averageCost else 0.0,
                        "market_value": market_value,
                        "unrealized_pnl": unrealized_pnl
                    })
                except Exception as e:
                    logger.warning(f"Error processing position {pos.contract.symbol if hasattr(pos, 'contract') else 'UNKNOWN'}: {e}")
                    continue
            
            return result
        except Exception as e:
            logger.error(f"Error getting IBKR positions: {e}", exc_info=True)
            return []
    
    def sync_account_state(self) -> bool:
        """
        Sync account summary to database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            summary = self.ibkr_client.get_account_summary()
            if not summary:
                logger.warning("No account summary available from IBKR")
                return False
            
            # Extract values
            cash = float(summary.get("TotalCashValue", {}).get("value", 0))
            buying_power = float(summary.get("BuyingPower", {}).get("value", 0))
            equity = float(summary.get("NetLiquidation", {}).get("value", 0))
            
            # Calculate PnL (simplified - would need historical data for accurate realized PnL)
            # Unrealized PnL will be calculated from individual positions during position sync
            # For account state, we'll use 0.0 and let positions sync update it
            realized_pnl = 0.0  # Would need to track from trade history
            unrealized_pnl = 0.0  # Will be calculated from positions
            
            # Save to database
            with SessionLocal() as session:
                repo = AccountStateRepository(session)
                state = repo.add_state(
                    cash=cash,
                    buying_power=buying_power,
                    realized_pnl=realized_pnl,
                    unrealized_pnl=unrealized_pnl,
                    equity=equity
                )
                logger.info(f"Synced account state: equity=${equity:,.2f}, cash=${cash:,.2f}, buying_power=${buying_power:,.2f}")
                return True
        except Exception as e:
            logger.error(f"Error syncing account state: {e}", exc_info=True)
            return False
    
    def sync_positions(self) -> bool:
        """
        Sync positions to database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            positions = self.get_ibkr_positions()
            
            # Save to database
            with SessionLocal() as session:
                repo = PositionRepository(session)
                
                # Get existing positions to track which ones to delete
                existing_positions = repo.list_positions()
                existing_symbols = {pos.symbol for pos in existing_positions}
                synced_symbols = set()
                
                if positions:
                    for pos_data in positions:
                        repo.upsert_position(
                            symbol=pos_data["symbol"],
                            quantity=pos_data["quantity"],
                            avg_cost=pos_data["avg_cost"],
                            market_value=pos_data["market_value"],
                            unrealized_pnl=pos_data["unrealized_pnl"]
                        )
                        synced_symbols.add(pos_data["symbol"].upper())
                    
                    logger.info(f"Synced {len(positions)} positions to database")
                else:
                    logger.debug("No positions found in IBKR account")
                
                # Delete positions that no longer exist in IBKR
                for symbol in existing_symbols - synced_symbols:
                    repo.delete_position(symbol)
                    logger.info(f"Deleted position for {symbol} (no longer in IBKR account)")
                
                return True
        except Exception as e:
            logger.error(f"Error syncing positions: {e}", exc_info=True)
            return False
    
    def sync_once(self) -> Dict:
        """
        Run a single sync cycle.
        
        Returns:
            Dict with sync results
        """
        logger.info("Starting portfolio sync cycle...")
        
        # Ensure connected
        if not self.ibkr_client.trader.connected:
            logger.info("Not connected to IBKR, attempting connection...")
            if not self.ibkr_client.connect():
                logger.warning("Failed to connect to IBKR, skipping sync")
                return {
                    "success": False,
                    "account_synced": False,
                    "positions_synced": False,
                    "message": "Not connected to IBKR"
                }
        
        # Sync account state
        account_synced = self.sync_account_state()
        
        # Sync positions
        positions_synced = self.sync_positions()
        
        success = account_synced or positions_synced
        
        logger.info(f"Portfolio sync complete. Account: {'✅' if account_synced else '❌'}, Positions: {'✅' if positions_synced else '❌'}")
        
        return {
            "success": success,
            "account_synced": account_synced,
            "positions_synced": positions_synced
        }
    
    def run_forever(self):
        """Run the sync continuously."""
        self.running = True
        logger.info(f"Portfolio sync started (interval: {self.interval_seconds}s, paper_trading={self.paper_trading})")
        
        try:
            while self.running:
                self.sync_once()
                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            logger.info("Portfolio sync stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Error in portfolio sync: {e}", exc_info=True)
            self.running = False
    
    def stop(self):
        """Stop the sync."""
        self.running = False
        logger.info("Portfolio sync stopped")


def main():
    """Main entry point for running the portfolio sync."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FuggerBot Portfolio Sync")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Sync interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Sync paper trading account (default: live trading)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)"
    )
    
    args = parser.parse_args()
    
    sync = PortfolioSync(
        interval_seconds=args.interval,
        paper_trading=args.paper
    )
    
    if args.once:
        sync.sync_once()
    else:
        sync.run_forever()


if __name__ == "__main__":
    main()

