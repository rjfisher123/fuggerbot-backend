"""
IBKR heartbeat worker.

Continuously monitors IBKR connection status, attempts reconnection on failure,
and updates the database with current status.
"""
import time
from datetime import datetime
from typing import Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.ibkr_client import get_ibkr_client
from persistence.db import SessionLocal
from persistence.models_ibkr import IBKRStatus
from core.logger import logger


class IBKRHeartbeat:
    """Monitors and maintains IBKR connection."""
    
    def __init__(self, interval_seconds: int = 30, auto_reconnect: bool = True):
        """
        Initialize IBKR heartbeat worker.
        
        Args:
            interval_seconds: How often to check connection status (default: 30 seconds)
            auto_reconnect: Whether to automatically attempt reconnection on failure
        """
        self.interval_seconds = interval_seconds
        self.auto_reconnect = auto_reconnect
        self.running = False
        logger.info(f"IBKRHeartbeat initialized (interval: {interval_seconds}s, auto_reconnect: {auto_reconnect})")
    
    def update_status(self, paper_trading: bool, status: dict) -> IBKRStatus:
        """
        Update IBKR status in database.
        
        Args:
            paper_trading: Whether this is paper trading account
            status: Connection status dict from IBKRClient
        
        Returns:
            Updated IBKRStatus record
        """
        with SessionLocal() as session:
            # Get or create status record
            db_status = (
                session.query(IBKRStatus)
                .filter(IBKRStatus.paper_trading == paper_trading)
                .first()
            )
            
            if not db_status:
                db_status = IBKRStatus(paper_trading=paper_trading)
                session.add(db_status)
            
            # Update fields
            db_status.connected = status.get("connected", False)
            db_status.host = status.get("host")
            db_status.port = status.get("port")
            db_status.client_id = status.get("client_id")
            db_status.last_checked = datetime.utcnow()
            db_status.error_message = status.get("error")
            
            # Update last_connected timestamp if connected
            if db_status.connected:
                if not db_status.last_connected:
                    db_status.last_connected = datetime.utcnow()
                db_status.reconnect_attempts = 0
            else:
                # Increment reconnect attempts if disconnected
                if db_status.last_connected:
                    db_status.reconnect_attempts += 1
            
            session.commit()
            session.refresh(db_status)
            return db_status
    
    def check_and_reconnect(self, paper_trading: bool) -> dict:
        """
        Check connection status and attempt reconnection if needed.
        
        Args:
            paper_trading: Whether to check paper trading account
        
        Returns:
            Updated status dict
        """
        client = get_ibkr_client(paper_trading=paper_trading)
        
        # Get current status
        status = client.get_connection_status()
        
        # If disconnected and auto_reconnect is enabled, try to reconnect
        if not status.get("connected") and self.auto_reconnect:
            logger.info(f"IBKR {'Paper' if paper_trading else 'Live'} disconnected. Attempting reconnection...")
            reconnect_success = client.connect()
            
            if reconnect_success:
                # Refresh status after reconnection
                status = client.get_connection_status()
                logger.info(f"✅ Reconnected to IBKR {'Paper' if paper_trading else 'Live'}")
            else:
                logger.warning(f"❌ Failed to reconnect to IBKR {'Paper' if paper_trading else 'Live'}")
        
        # Update database
        db_status = self.update_status(paper_trading, status)
        
        return {
            **status,
            "last_checked": db_status.last_checked.isoformat(),
            "last_connected": db_status.last_connected.isoformat() if db_status.last_connected else None,
            "reconnect_attempts": db_status.reconnect_attempts
        }
    
    def run_once(self) -> dict:
        """
        Run a single heartbeat check for both paper and live trading.
        
        Returns:
            Dict with status for both accounts
        """
        logger.debug("Running IBKR heartbeat check...")
        
        results = {}
        
        # Check paper trading
        try:
            results["paper"] = self.check_and_reconnect(paper_trading=True)
        except Exception as e:
            logger.error(f"Error checking paper trading status: {e}", exc_info=True)
            results["paper"] = {"connected": False, "error": str(e)}
        
        # Check live trading
        try:
            results["live"] = self.check_and_reconnect(paper_trading=False)
        except Exception as e:
            logger.error(f"Error checking live trading status: {e}", exc_info=True)
            results["live"] = {"connected": False, "error": str(e)}
        
        # Log summary
        paper_status = "✅" if results["paper"].get("connected") else "❌"
        live_status = "✅" if results["live"].get("connected") else "❌"
        logger.info(f"IBKR Heartbeat: Paper {paper_status} | Live {live_status}")
        
        return results
    
    def run_forever(self):
        """Run the heartbeat continuously."""
        self.running = True
        logger.info(f"IBKR heartbeat started (interval: {self.interval_seconds}s)")
        
        try:
            while self.running:
                self.run_once()
                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            logger.info("IBKR heartbeat stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Error in IBKR heartbeat: {e}", exc_info=True)
            self.running = False
    
    def stop(self):
        """Stop the heartbeat."""
        self.running = False
        logger.info("IBKR heartbeat stopped")


def get_latest_status(paper_trading: bool = False) -> Optional[IBKRStatus]:
    """
    Get the latest IBKR status from database.
    
    Args:
        paper_trading: Whether to get paper trading status
    
    Returns:
        IBKRStatus record or None if not found
    """
    with SessionLocal() as session:
        return (
            session.query(IBKRStatus)
            .filter(IBKRStatus.paper_trading == paper_trading)
            .first()
        )


def main():
    """Main entry point for running the IBKR heartbeat."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FuggerBot IBKR Heartbeat")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Heartbeat interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--no-auto-reconnect",
        action="store_true",
        help="Disable automatic reconnection attempts"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)"
    )
    
    args = parser.parse_args()
    
    heartbeat = IBKRHeartbeat(
        interval_seconds=args.interval,
        auto_reconnect=not args.no_auto_reconnect
    )
    
    if args.once:
        heartbeat.run_once()
    else:
        heartbeat.run_forever()


if __name__ == "__main__":
    main()










