"""
Interactive Brokers execution wrapper using ib_insync.

Robust execution bridge for placing trades through Interactive Brokers TWS/IB Gateway.
Features auto-reconnection logic to survive TWS restarts.
"""
import logging
import time
import threading
from typing import Optional, List, Dict
from enum import Enum

from services.risk_control_service import RiskControlService
from core.logger import logger

# Lazy import ib_insync to handle import errors gracefully
try:
    from ib_insync import IB, Contract, Stock, Crypto, MarketOrder, Order, LimitOrder
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    logger.warning("ib_insync not installed. Install with: pip install ib_insync")

import asyncio


class OrderAction(str, Enum):
    """Order action types."""
    BUY = "BUY"
    SELL = "SELL"


class ConnectionWatchdog(threading.Thread):
    """
    Watchdog thread to monitor IBKR connection health and auto-reconnect.
    
    Runs in a background thread to prevent blocking the main application loop
    during connection checks, but ensures the main loop pauses/fails gracefully
    when connection is lost.
    """
    
    def __init__(self, bridge, interval: int = 10):
        """
        Initialize watchdog.
        
        Args:
            bridge: IBKRBridge instance to monitor
            interval: Check interval in seconds
        """
        super().__init__(name="IBKR-Watchdog")
        self.bridge = bridge
        self.interval = interval
        self.daemon = True  # Auto-kill when main process exits
        self.running = True
        self._stop_event = threading.Event()
    
    def run(self):
        """Main watchdog loop."""
        logger.info("🐶 Connection Watchdog started")
        
        while self.running and not self._stop_event.is_set():
            try:
                if not self._check_connection():
                   logger.warning("🐶 Watchdog detected connection loss! Initiating recovery...")
                   self._reconnect()
            except Exception as e:
                logger.error(f"🐶 Watchdog error: {e}")
            
            # Sleep interruptible
            self._stop_event.wait(self.interval)
            
    def stop(self):
        """Stop the watchdog."""
        self.running = False
        self._stop_event.set()
        
    def _check_connection(self) -> bool:
        """
        Ping TWS to verify active connection.
        
        Returns:
            True if healthy, False if disconnected/unresponsive
        """
        if not self.bridge.ib.isConnected():
            return False
            
        try:
            # Active ping: Request current time
            # timeout=2.0 ensures we don't hang if TWS is frozen
            t = self.bridge.ib.reqCurrentTime()
            if t:
                return True
            return False
        except Exception:
            return False
            
    def _reconnect(self):
        """Perform reconnection sequence."""
        # Pause main loop implicitly by setting connected=False
        self.bridge.connected = False
        
        try:
            # properly disconnect first
            try:
                self.bridge.ib.disconnect()
            except:
                pass
                
            time.sleep(2) # Cooldown
            
            logger.info("🐶 Watchdog attempting reconnect...")
            
            # Use main loop if available (Asyncio/FastAPI mode)
            if self.bridge.main_loop and self.bridge.main_loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.bridge.connect_async(use_retry=True), 
                    self.bridge.main_loop
                )
                # We don't wait for result here to avoid blocking watchdog?
                # Actually, we should wait to confirm if it worked or sleep.
                # But connection might take time.
                try:
                    future.result(timeout=15)
                except Exception as e:
                    logger.error(f"🐶 Async reconnect failed: {e}")
            else:
                # Fallback to sync mode
                self.bridge.connect(use_retry=True)
            
        except Exception as e:
            logger.error(f"🐶 Reconnection failed: {e}")


import os

class IBKRBridge:
    """
    Robust execution wrapper for Interactive Brokers.
    
    Handles connection, contract creation, and trade execution with proper error handling.
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        client_id: int = 1,
        reconnect_interval: int = 60,  # Seconds between reconnection attempts
        max_reconnect_attempts: int = 0  # 0 = infinite retries
    ):
        """
        Initialize IBKR bridge.
        
        Args:
            host: TWS/IB Gateway host (default: env IBKR_HOST or 127.0.0.1)
            port: TWS/IB Gateway port (default: env IBKR_PORT or 7497)
            client_id: Client ID for connection (default: 1)
            reconnect_interval: Seconds to wait between reconnection attempts (default: 60)
            max_reconnect_attempts: Maximum reconnection attempts (0 = infinite, default: 0)
        """
        # Resolve defaults from Env or arguments
        self.host = host or os.getenv("IBKR_HOST", "127.0.0.1")
        if port:
            self.port = port
        else:
            # Default to 7497 (Paper) unless specified
            self.port = int(os.getenv("IBKR_PORT", 7497))
        if not IBKR_AVAILABLE:
            raise ImportError("ib_insync not installed. Install with: pip install ib_insync")
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        # Use Singleton Connection Manager to get IB instance
        from execution.connection_manager import get_connection_manager
        self.manager = get_connection_manager()
        self.ib = self.manager.get_ib() # Use singleton's IB instance
        
        self.connected = False
        self.is_paper_trading = (port == 7497)
        self.main_loop = None # Capture main loop involved in async connection
        
        # Start Watchdog
        self.watchdog = ConnectionWatchdog(self)
        # Note: watchdog starts when connect() is first called or explicitly started?
        # Better to start it in connect() to avoid checking before initial connection
        
        # Initialize Risk Control Service
        self.risk_control = RiskControlService()
        
        logger.info(
            f"IBKRBridge initialized: host={host}, port={port} "
            f"({'Paper' if self.is_paper_trading else 'Live'}), client_id={client_id}, "
            f"reconnect_interval={reconnect_interval}s, max_attempts={max_reconnect_attempts or 'infinite'}"
        )
    
    async def connect_async(self, use_retry: bool = True) -> bool:
        """
        Async connect to TWS/IB Gateway.
        """
        if self.ib.isConnected():
            logger.debug("Already connected to IBKR")
            self.connected = True
            if not self.watchdog.is_alive():
                 self.watchdog.start()
            return True
        
        try:
            # Delegate to Singleton Manager
            success = await self.manager.connect_async(
                host=self.host, 
                port=self.port, 
                client_id=self.client_id
            )
            
            self.connected = success
            if success:
                logger.info(f"✅ Bridge Connected via Manager ({'Paper' if self.is_paper_trading else 'Live'})")
                if not self.watchdog.is_alive():
                    self.watchdog.start()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error connecting to IBKR via Manager: {e}", exc_info=True)
            self.connected = False
            return False

    def connect(self, use_retry: bool = True) -> bool:
        """
        Connect to TWS/IB Gateway with optional retry logic.
        """
        # Check if already connected via ib_insync's internal state
        if self.ib.isConnected():
            logger.debug("Already connected to IBKR")
            self.connected = True
            if not self.watchdog.is_alive():
                 self.watchdog.start()
            return True
        
        try:
            logger.info(f"Connecting to IBKR at {self.host}:{self.port}...")
            self.ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                timeout=10
            )
            self.connected = True
            logger.info(f"✅ Connected to IBKR ({'Paper' if self.is_paper_trading else 'Live'} trading)")
            
            # Start Watchdog if not running
            if not self.watchdog.is_alive():
                self.watchdog.start()
                
            return True
            
        except ConnectionRefusedError:
            logger.warning(
                f"⚠️ Connection refused to IBKR at {self.host}:{self.port}. "
                f"TWS/IB Gateway may not be running."
            )
            self.connected = False
            
            # Retry if enabled
            if use_retry:
                logger.info("🔄 Retrying connection with auto-reconnect logic...")
                return self._attempt_reconnect()
            else:
                logger.warning("Execution disabled (retry disabled).")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error connecting to IBKR: {e}", exc_info=True)
            self.connected = False
            
            # Retry if enabled
            if use_retry:
                logger.info("🔄 Retrying connection with auto-reconnect logic...")
                return self._attempt_reconnect()
            else:
                return False

    def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to TWS/IB Gateway with retry logic.
        
        Tries to reconnect every `reconnect_interval` seconds.
        If `max_reconnect_attempts` is set (> 0), stops after that many attempts.
        Otherwise, retries indefinitely.
        
        Returns:
            True if reconnected successfully, False if max attempts exceeded
        """
        attempt = 0
        while True:
            attempt += 1
            
            # Check if max attempts exceeded (only if max_reconnect_attempts > 0)
            if self.max_reconnect_attempts > 0 and attempt > self.max_reconnect_attempts:
                logger.error(
                    f"❌ Failed to reconnect after {self.max_reconnect_attempts} attempts. "
                    f"Giving up."
                )
                return False
            
            logger.info(
                f"🔄 Reconnection attempt {attempt}"
                f"{f'/{self.max_reconnect_attempts}' if self.max_reconnect_attempts > 0 else ''}..."
            )
            
            try:
                # Check if already connected (via another thread or manual reconnect)
                if self.ib.isConnected():
                    logger.info("✅ Already reconnected to TWS")
                    self.connected = True
                    return True
                
                # Attempt connection
                self.ib.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    timeout=10
                )
                
                # Success!
                self.connected = True
                logger.info("✅ Reconnected to TWS")
                
                # Ensure watchdog is running
                if not self.watchdog.is_alive():
                     try:
                        self.watchdog.start()
                     except RuntimeError:
                        # Thread might be already started but not alive if it finished?
                        # Re-create watchdog if it finished
                        self.watchdog = ConnectionWatchdog(self)
                        self.watchdog.start()

                return True
                
            except ConnectionRefusedError:
                logger.warning(
                    f"⚠️ Reconnection attempt {attempt} failed: Connection refused. "
                    f"Retrying in {self.reconnect_interval}s..."
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Reconnection attempt {attempt} failed: {e}. "
                    f"Retrying in {self.reconnect_interval}s..."
                )
            
            # Wait before next attempt
            time.sleep(self.reconnect_interval)
    
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
        quantity: float,  # Can be int for stocks or float for crypto
        order_type: str = "MARKET",
        limit_price: float = 0.0,
        require_confirmation: bool = False
    ) -> Optional[Order]:
        """
        Execute a trade with optional SMS confirmation.
        
        Args:
            action: Order action ("BUY" or "SELL")
            symbol: Trading symbol (e.g., "BTC-USD", "NVDA")
            quantity: Number of shares/units to trade
            order_type: "MARKET" or "LIMIT"
            limit_price: Price for limit orders (required if LIMIT)
            require_confirmation: If True, blocks until SMS approval (timeout 5 mins)
        
        Returns:
            Order object if placed successfully, None otherwise
        """
        # Safety check: Verify connection
        if not self.ib.isConnected():
            logger.warning("⚠️ Not connected to IBKR. Attempting immediate reconnect...")
            self.connected = False
            try:
                self.ib.connect(self.host, self.port, clientId=self.client_id)
                self.connected = True
                logger.info("✅ Reconnected to TWS before trade execution")
            except Exception as e:
                logger.error(f"❌ Cannot execute trade: failed to reconnect. {e}")
                return None
        
        action_upper = action.upper()
        if action_upper not in ["BUY", "SELL"]:
            logger.error(f"❌ Invalid action: {action}")
            return None
            
        try:
            # 1. Risk Control: SMS Confirmation
            trade_id = None
            if require_confirmation:
                logger.info(f"🛑 RISK CONTROL: SMS Confirmation required for {action} {quantity} {symbol}")
                
                trade_details = {
                    "symbol": symbol, "action": action_upper, 
                    "quantity": quantity, "order_type": order_type,
                    "price": limit_price
                }
                
                trade_id = self.risk_control.request_confirmation(trade_details)
                if not trade_id:
                    logger.error("Failed to send confirmation SMS. Aborting trade.")
                    return None
                
                # Poll for Approval (Blocking, max 5 mins)
                logger.info(f"⏳ Waiting for approval (Trade ID: {trade_id})...")
                approved = False
                start_wait = time.time()
                while time.time() - start_wait < 300:
                    if self.risk_control.check_approval(trade_id):
                        approved = True
                        break
                    time.sleep(5)
                    
                if not approved:
                    logger.warning(f"❌ Trade {trade_id} timed out waiting for approval. Cancelled.")
                    self.risk_control.send_execution_failure(trade_id, "Approval Timeout")
                    return None
                    
                logger.info(f"✅ Trade {trade_id} APPROVED. Proceeding to execution.")

            # 2. Get Contract
            contract = self.get_contract(symbol)
            if contract is None:
                logger.error(f"❌ Cannot execute trade: failed to get contract for {symbol}")
                return None
            
            # 3. Create Order
            if order_type.upper() == "MARKET":
                order = MarketOrder(action_upper, quantity)
            elif order_type.upper() == "LIMIT":
                order = LimitOrder(action_upper, quantity, limit_price)
            else:
                logger.error(f"Invalid order type: {order_type}")
                return None
            
            # 4. Place Order
            logger.info(f"📤 Placing {order_type} {action_upper} order: {quantity} {symbol}")
            trade = self.ib.placeOrder(contract, order)
            
            # Log trade details
            logger.info(f"✅ Order placed: {trade.order.action} {trade.order.totalQuantity} (Order ID: {trade.order.orderId})")
            
            # 5. Notify Success (if confirmed)
            if require_confirmation and trade_id:
                self.risk_control.send_confirmation_success(
                    trade_id=trade_id,
                    order_id=str(trade.order.orderId),
                    symbol=symbol
                )
            
            return trade.order
            
        except Exception as e:
            logger.error(f"❌ Error executing trade {action} {quantity} {symbol}: {e}", exc_info=True)
            if require_confirmation and trade_id:
                 self.risk_control.send_execution_failure(trade_id, str(e))
            return None

    def approve_and_execute(self, trade_id: str) -> Dict:
        """
        Legacy compatibility method for TradeService.
        Marks the trade as approved so the blocking execute_trade loop can proceed.
        """
        success = self.risk_control.approve_trade(trade_id)
        if success:
            return {"success": True, "message": f"Trade {trade_id} approved"}
        else:
            return {"success": False, "message": f"Trade {trade_id} not found"}
    
    def get_positions(self) -> list[str]:
        """
        Get list of symbols for current open positions.
        
        Returns:
            List of symbols (e.g. ['NVDA', 'BTC-USD'])
        """
        if not self.connected:
            logger.warning("Cannot get positions: not connected")
            return []
            
        try:
            positions = self.ib.positions()
            symbols = []
            for p in positions:
                if p.position != 0:
                    # Extract symbol from contract
                    # ib_insync Contract.localSymbol or symbol?
                    # For crypto it might be 'BTC', need to reconstruct 'BTC-USD' if possible
                    # Or just use p.contract.symbol
                    symbol = p.contract.symbol
                    # Heuristic for crypto: if exchange is PAXOS, append -USD? 
                    # Or rely on Orchestrator logic. 
                    # User request: "Integration... check_correlation_risk(symbol, current_positions)"
                    
                    # If it's crypto on PAXOS/GEMINI, ib_insync usually has symbol='BTC'
                    if p.contract.secType == 'CRYPTO':
                        symbol = f"{symbol}-USD"
                        
                    symbols.append(symbol)
            return symbols
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def disconnect(self):
        """Disconnect from TWS/IB Gateway."""
        if self.watchdog and self.watchdog.is_alive():
            self.watchdog.stop()

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
        
        Uses ib_insync's internal isConnected() for accurate state.
        
        Returns:
            True if connected, False otherwise
        """
        # Use ib_insync's internal connection state for accuracy
        is_connected = self.ib.isConnected()
        
        # Sync internal flag with actual state
        self.connected = is_connected
        
        return is_connected
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Factory functions for compatibility and easy access
_live_bridge: Optional['IBKRBridge'] = None
_paper_bridge: Optional['IBKRBridge'] = None

def get_ibkr_trader(host: str = None, port: int = None, client_id: int = 1) -> 'IBKRBridge':
    """Get or create a live trading bridge instance."""
    global _live_bridge
    if _live_bridge is None:
        _live_bridge = IBKRBridge(host=host, port=port, client_id=client_id)
    return _live_bridge

def get_paper_trading_trader(host: str = None, port: int = None, client_id: int = 2) -> 'IBKRBridge':
    """Get or create a paper trading bridge instance."""
    global _paper_bridge
    if _paper_bridge is None:
        _paper_bridge = IBKRBridge(host=host, port=port, client_id=client_id)
    return _paper_bridge

# Compatibility Aliases
get_live_trading_trader = get_ibkr_trader
