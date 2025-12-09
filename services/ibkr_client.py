"""
IBKR client service for managing Interactive Brokers connections.

This service handles low-level IBKR connectivity, connection status,
and account information. It wraps the IBKRTrader class.
"""
import logging
from typing import Optional, Dict
import os

from core.ibkr_trader import get_live_trading_trader, get_paper_trading_trader, IBKRTrader
from core.logger import logger
from core.logging import log_ibkr_event


class IBKRClient:
    """Service for managing IBKR connections and status."""
    
    def __init__(self, paper_trading: bool = False):
        """
        Initialize IBKR client.
        
        Args:
            paper_trading: If True, use paper trading account (port 7497), 
                         if False use live trading (port 7496)
        """
        self.paper_trading = paper_trading
        self._trader: Optional[IBKRTrader] = None
        logger.info(f"IBKRClient initialized (paper_trading={paper_trading})")
    
    @property
    def trader(self) -> IBKRTrader:
        """Get or create IBKR trader instance."""
        if self._trader is None:
            if self.paper_trading:
                self._trader = get_paper_trading_trader()
            else:
                self._trader = get_live_trading_trader()
        return self._trader
    
    def get_connection_status(self) -> Dict:
        """
        Get current IBKR connection status.
        
        Returns:
            Dict with connection status information
        """
        try:
            trader = self.trader
            
            # Check if actually connected (may be connected but flag not set)
            is_connected = trader.connected
            if not is_connected:
                try:
                    if hasattr(trader.ib, 'isConnected') and trader.ib.isConnected():
                        trader.connected = True
                        is_connected = True
                        logger.info("Connection status updated - already connected")
                except Exception:
                    pass
            
            return {
                "connected": is_connected,
                "host": trader.host,
                "port": trader.port,
                "paper_trading": trader.is_paper_trading,
                "client_id": trader.client_id
            }
        except Exception as e:
            logger.error(f"Error getting connection status: {e}", exc_info=True)
            return {
                "connected": False,
                "error": str(e)
            }
    
    def connect(self) -> bool:
        """
        Connect to IBKR.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            trader = self.trader
            
            # Check if already connected
            if trader.connected:
                return True
            
            # Try to check if actually connected
            try:
                if hasattr(trader.ib, 'isConnected') and trader.ib.isConnected():
                    trader.connected = True
                    return True
            except Exception:
                pass
            
            # Attempt connection
            success = trader.connect()
            if success:
                log_ibkr_event(
                    event_type="connected",
                    message=f"Successfully connected to IBKR",
                    connected=True,
                    host=trader.host,
                    port=trader.port
                )
            else:
                log_ibkr_event(
                    event_type="connection_failed",
                    message=f"Failed to connect to IBKR",
                    connected=False,
                    host=trader.host,
                    port=trader.port
                )
            return success
        except Exception as e:
            logger.error(f"Error connecting to IBKR: {e}", exc_info=True)
            log_ibkr_event(
                event_type="error",
                message=f"Connection error: {str(e)}",
                connected=False
            )
            return False
    
    def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self._trader and self._trader.connected:
            try:
                self._trader.disconnect()
                log_ibkr_event(
                    event_type="disconnected",
                    message="Disconnected from IBKR",
                    connected=False,
                    host=self._trader.host if self._trader else None,
                    port=self._trader.port if self._trader else None
                )
            except Exception as e:
                logger.error(f"Error disconnecting from IBKR: {e}")
                log_ibkr_event(
                    event_type="error",
                    message=f"Disconnect error: {str(e)}",
                    connected=False
                )
    
    def get_account_summary(self) -> Optional[Dict]:
        """
        Get account summary information.
        
        Returns:
            Dict with account information, None if error
        """
        try:
            trader = self.trader
            if not trader.connected:
                return None
            return trader.get_account_summary()
        except Exception as e:
            logger.error(f"Error getting account summary: {e}", exc_info=True)
            return None
    
    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Place an order with IBKR (without confirmation).
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Number of shares
            order_type: MARKET, LIMIT, etc.
            limit_price: Limit price if order_type is LIMIT
        
        Returns:
            Dict with order result: {"success": bool, "order_id": str, "status": str, "message": str}
        """
        try:
            trader = self.trader
            
            # Ensure connected
            if not trader.connected:
                if not self.connect():
                    return {
                        "success": False,
                        "message": "Not connected to IBKR. Please connect first."
                    }
            
            # Execute order without confirmation
            result = trader.execute_trade(
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price,
                require_confirmation=False  # Direct execution, no SMS confirmation
            )
            
            return result
        except Exception as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error placing order: {str(e)}"
            }


# Global client instances
_live_client: Optional[IBKRClient] = None
_paper_client: Optional[IBKRClient] = None


def get_ibkr_client(paper_trading: bool = False) -> IBKRClient:
    """
    Get or create IBKR client instance.
    
    Args:
        paper_trading: If True, return paper trading client, else live trading
    
    Returns:
        IBKRClient instance
    """
    global _live_client, _paper_client
    
    if paper_trading:
        if _paper_client is None:
            _paper_client = IBKRClient(paper_trading=True)
        return _paper_client
    else:
        if _live_client is None:
            _live_client = IBKRClient(paper_trading=False)
        return _live_client

