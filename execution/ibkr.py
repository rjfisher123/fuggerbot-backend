"""
Interactive Brokers execution wrapper using ib_insync.

Robust execution bridge for placing trades through Interactive Brokers TWS/IB Gateway.
"""
import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

# Lazy import ib_insync to handle import errors gracefully
try:
    from ib_insync import IB, Contract, Stock, Crypto, MarketOrder, Order
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    logger.warning("ib_insync not installed. Install with: pip install ib_insync")


class OrderAction(str, Enum):
    """Order action types."""
    BUY = "BUY"
    SELL = "SELL"


class IBKRBridge:
    """
    Robust execution wrapper for Interactive Brokers.
    
    Handles connection, contract creation, and trade execution with proper error handling.
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,  # 7497 for Paper, 7496 for Live
        client_id: int = 1
    ):
        """
        Initialize IBKR bridge.
        
        Args:
            host: TWS/IB Gateway host (default: 127.0.0.1)
            port: TWS/IB Gateway port (7497 for Paper, 7496 for Live)
            client_id: Client ID for connection (default: 1)
        """
        if not IBKR_AVAILABLE:
            raise ImportError("ib_insync not installed. Install with: pip install ib_insync")
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self.connected = False
        self.is_paper_trading = (port == 7497)
        
        logger.info(
            f"IBKRBridge initialized: host={host}, port={port} "
            f"({'Paper' if self.is_paper_trading else 'Live'}), client_id={client_id}"
        )
    
    def connect(self) -> bool:
        """
        Connect to TWS/IB Gateway.
        
        Handles ConnectionRefusedError gracefully by logging a warning
        and disabling execution (doesn't crash).
        
        Returns:
            True if connected successfully, False otherwise
        """
        if self.connected:
            logger.debug("Already connected to IBKR")
            return True
        
        try:
            logger.info(f"Connecting to IBKR at {self.host}:{self.port}...")
            self.ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id
            )
            self.connected = True
            logger.info(f"✅ Connected to IBKR ({'Paper' if self.is_paper_trading else 'Live'} trading)")
            return True
            
        except ConnectionRefusedError:
            logger.warning(
                f"⚠️ Connection refused to IBKR at {self.host}:{self.port}. "
                f"TWS/IB Gateway may not be running. Execution disabled."
            )
            self.connected = False
            return False
            
        except Exception as e:
            logger.error(f"❌ Error connecting to IBKR: {e}", exc_info=True)
            self.connected = False
            return False
    
    def get_contract(self, symbol: str) -> Optional[Contract]:
        """
        Get qualified contract for a symbol.
        
        Handles both crypto and stock contracts:
        - If symbol has "-USD" (e.g., "BTC-USD"), creates Crypto contract
          (exchange="PAXOS", currency="USD")
        - Otherwise (e.g., "NVDA"), creates Stock contract
          (exchange="SMART", currency="USD")
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USD", "NVDA")
        
        Returns:
            Qualified Contract object, or None if qualification fails
        """
        if not self.connected:
            logger.warning("Cannot get contract: not connected to IBKR")
            return None
        
        try:
            # Determine contract type based on symbol
            if "-USD" in symbol:
                # Crypto contract
                base_symbol = symbol.replace("-USD", "")
                contract = Crypto(
                    symbol=base_symbol,
                    exchange="PAXOS",
                    currency="USD"
                )
                logger.debug(f"Created Crypto contract: {base_symbol} on PAXOS")
            else:
                # Stock contract
                contract = Stock(
                    symbol=symbol,
                    exchange="SMART",
                    currency="USD"
                )
                logger.debug(f"Created Stock contract: {symbol} on SMART")
            
            # Qualify the contract
            qualified = self.ib.qualifyContracts(contract)
            
            if not qualified:
                logger.error(f"❌ Failed to qualify contract for {symbol}")
                return None
            
            if len(qualified) == 0:
                logger.error(f"❌ No qualified contracts found for {symbol}")
                return None
            
            # Return the first qualified contract
            qualified_contract = qualified[0]
            logger.debug(
                f"✅ Qualified contract for {symbol}: "
                f"{qualified_contract.localSymbol} on {qualified_contract.exchange}"
            )
            return qualified_contract
            
        except Exception as e:
            logger.error(f"❌ Error getting contract for {symbol}: {e}", exc_info=True)
            return None
    
    def execute_trade(
        self,
        action: str,
        symbol: str,
        quantity: float  # Can be int for stocks or float for crypto
    ) -> Optional[Order]:
        """
        Execute a market order trade.
        
        Creates a MarketOrder and places it asynchronously.
        Logs the trade execution.
        
        Args:
            action: Order action ("BUY" or "SELL")
            symbol: Trading symbol (e.g., "BTC-USD", "NVDA")
            quantity: Number of shares/units to trade
        
        Returns:
            Order object if placed successfully, None otherwise
        """
        # Safety check: Ensure connected before trading
        if not self.connected:
            logger.error(
                f"❌ Cannot execute trade: not connected to IBKR. "
                f"Call connect() first or ensure TWS/IB Gateway is running."
            )
            return None
        
        # Validate action
        action_upper = action.upper()
        if action_upper not in ["BUY", "SELL"]:
            logger.error(f"❌ Invalid action: {action}. Must be 'BUY' or 'SELL'")
            return None
        
        # Validate quantity
        if quantity <= 0:
            logger.error(f"❌ Invalid quantity: {quantity}. Must be > 0")
            return None
        
        try:
            # Get contract
            contract = self.get_contract(symbol)
            if contract is None:
                logger.error(f"❌ Cannot execute trade: failed to get contract for {symbol}")
                return None
            
            # Create market order
            order = MarketOrder(action_upper, quantity)
            
            # Place order asynchronously
            logger.info(
                f"📤 Placing {action_upper} order: {quantity} {symbol} "
                f"({'Paper' if self.is_paper_trading else 'Live'} trading)"
            )
            
            trade = self.ib.placeOrder(contract, order)
            
            # Log trade details
            logger.info(
                f"✅ Order placed: {trade.order.action} {trade.order.totalQuantity} "
                f"{contract.localSymbol} (Order ID: {trade.order.orderId})"
            )
            
            return trade.order
            
        except Exception as e:
            logger.error(
                f"❌ Error executing trade {action} {quantity} {symbol}: {e}",
                exc_info=True
            )
            return None
    
    def disconnect(self):
        """Disconnect from TWS/IB Gateway."""
        if not self.connected:
            logger.debug("Not connected, nothing to disconnect")
            return
        
        try:
            self.ib.disconnect()
            self.connected = False
            logger.info("✅ Disconnected from IBKR")
        except Exception as e:
            logger.warning(f"⚠️ Error disconnecting from IBKR: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        """
        Check if connected to IBKR.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

